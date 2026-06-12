# Plan: Pipeline semi-automatizado de resultados en vivo → Monte Carlo condicionado (2026-06-11)

## Contexto verificado

- `scripts/admin_results.py` ya hace PATCH de un partido por vez vía `supabase_request` (reutilizable, stdlib).
- `scripts/simulate_group_stage.py`: `simulate_group(...)` muestrea TODOS los partidos; los items de `matches.json` traen `match_number` (1–72) que mapea 1:1 con `match_results.match_number` (ojo: los fixtures sintéticos en `tests/test_run_monte_carlo.py` NO traen `match_number`, usar `m.get('match_number')`).
- `scripts/export_to_supabase.py::export_mc_results` ya desactiva el run activo por `scenario_name` e inserta uno nuevo con `input_hash` (sha256 de todo `mc_data` → metadata nueva cambia el hash gratis). Pero el `main()` siempre exige y sube `team_strength_snapshots.json` antes del MC.
- `generate_predictions.py` emite `TRUNCATE public.predictions` en el SQL seed; el exporter (`export_predictions_seed`) ignora el TRUNCATE y hace upsert `on_conflict=match_id` (cumple la restricción de solo-upserts).
- Frontend: `js/supa-data.js::loadSimulationData()` lee el run `is_active=true` más reciente; `js/predicciones.js` renderiza una vez, sin polling ni realtime.
- `.gitignore` ya cubre `data/team_strength_snapshots.json`, `data/mc_results.json`, `data/predictions_seed.sql`. Falta agregar `data/fixed_results.json`.
- `scripts/pipeline.py` es el patrón de orquestación existente (subprocess por paso).

## Decisiones de diseño

1. **Fuente de verdad de resultados = Supabase `match_results`**, no un archivo local. El flujo siempre hace fetch de `status=eq.finished` antes de simular; así el MC queda condicionado a TODO lo cargado (hoy o antes), no solo al lote actual.
2. **`fixed_results: dict[int, tuple[int,int]]` como kwarg opcional con default `None`** en toda la cadena de simulación → backward-compatible, los tests existentes pasan sin cambios.
3. **`scenario_name` se mantiene `'baseline'`** para que el frontend siga funcionando sin tocar `supa-data.js` (el índice único parcial de `14_simulation_snapshots.sql` ya garantiza un solo activo).
4. **No regenerar predictions por defecto**: las probabilidades 1X2 por partido dependen solo de strengths, no de otros resultados. Solo tiene sentido regenerar si cambian pesos/strengths a mitad de torneo → flag opcional `--with-predictions` que excluye partidos finished.
5. **Sin trigger/cron en Supabase** (rechazado): pg_cron no puede correr el MC en Python; una Edge Function duplicaría el modelo en TS. Un solo admin → comando local + workflow_dispatch opcional bastan.
6. Solo fase de grupos por ahora (las 72 entradas de `matches.json`); la estructura `{match_number: (hg, ag)}` es extensible a knockout después.

---

## Fase 1 — Núcleo: simulación condicionada (riesgo: MEDIO)

**Modificar `scripts/simulate_group_stage.py`:**

- `simulate_group(group_id, group_matches, strengths, base_goals, elo_scale=400, xi_profiles=None, xi_matchup_weight=0.20, draw_bias=0.0, parity_scale=600.0, elo_lambda_scale=None, fixed_results=None)`
  - Dentro del loop de partidos:
    ```python
    mn = m.get('match_number')
    if fixed_results and mn in fixed_results:
        hg, ag = fixed_results[mn]
    else:
        # camino actual: matchup_adjusted_strengths + simulate_match
    ```
  - Importante: cuando el partido es fijo se salta también `matchup_adjusted_strengths` (más rápido, sin consumo de RNG).
- `simulate_all_groups(..., fixed_results=None)` — solo propagar el kwarg.

**Modificar `scripts/run_monte_carlo.py`:**

- `run_monte_carlo(runs, seed, matches, strengths, base_goals, elo_scale=400, xi_profiles=None, xi_matchup_weight=0.20, draw_bias=0.0, parity_scale=600.0, elo_lambda_scale=None, fixed_results=None)` — propaga a `simulate_all_groups`.
- Nueva función `load_fixed_results(path) -> dict[int, tuple[int, int]]`: lee JSON `{"fetched_at": "...", "results": {"2": [2, 0]}}` y normaliza claves str→int.
- CLI: `--fixed-results PATH` (opcional). Si se pasa, el output JSON agrega:
  ```json
  "fixed_results": {"2": [2, 0]},
  "fixed_count": 1,
  "results_fetched_at": "2026-06-11T22:00:00Z"
  ```
  (entra al `input_hash` del export sin tocar nada más).

**Nota documentada:** con el mismo seed, el stream de RNG cambia respecto a runs anteriores porque los partidos fijos ya no consumen randoms — esperado y aceptable.

**Tests (`tests/test_fixed_results_simulation.py`):**
- Partido fijo fuerza el marcador exacto: `simulate_group` con `fixed_results={1:(2,0)}` y varios seeds → stats del partido 1 idénticas siempre.
- Los 6 partidos de un grupo fijos → `run_monte_carlo` degenera: `points_pct` con 100.0 en un solo bucket por equipo; `first_pct/second_pct/...` en {0.0, 100.0}.
- Fijación parcial: el ganador del partido fijo nunca tiene buckets de puntos imposibles (< 3).
- `fixed_results=None` reproduce bit a bit el resultado actual con mismo seed (regresión).
- `load_fixed_results` normaliza claves y tolera archivo ausente (error claro).

**Validación:** `pytest tests/test_run_monte_carlo.py tests/test_fixed_results_simulation.py tests/test_calibration.py`.

---

## Fase 2 — Cargador por lote `scripts/load_results.py` (riesgo: BAJO)

Nuevo script. Uso:
```
python scripts/load_results.py 2:2-0 3:1-1            # lote inline
python scripts/load_results.py --csv data/jornada.csv  # match_number,home_goals,away_goals
python scripts/load_results.py --fetch-only            # solo descarga finished → data/fixed_results.json
```

Funciones (puras y testeables, reutiliza `supabase_request` de `export_to_supabase`):

- `parse_result_token(token: str) -> tuple[int, int, int]` — `"2:2-0"` → `(2, 2, 0)`; `ValueError` con mensaje claro si el formato es inválido o hay goles negativos.
- `parse_results_csv(path: Path) -> list[tuple[int, int, int]]` — `csv` stdlib, cabecera `match_number,home_goals,away_goals`.
- `validate_against_matches(parsed: list, matches: list) -> list[dict]` — valida `match_number` ∈ 1..72 y presente en `data/matches.json`; enriquece con `home_team/away_team/group/match_id`; calcula `winner_team` (código del ganador, `None` en empate). Falla todo el lote si un token es inválido (atómico antes de tocar la red).
- `build_patch(row: dict, status: str = 'finished') -> dict` — `{'home_goals', 'away_goals', 'status', 'winner_team'}`.
- `apply_results(supabase_url, key, rows, dry_run=False) -> bool` — un PATCH por fila a `match_results?match_number=eq.{n}` con `prefer='return=minimal'`.
- `fetch_finished_results(supabase_url, key) -> dict[int, tuple[int, int]]` — GET `match_results?status=eq.finished&phase=eq.group&select=match_number,home_goals,away_goals&order=match_number` (RLS es lectura pública: sirve anon o service key).
- `write_fixed_results(path: Path, results: dict) -> None` — escribe `data/fixed_results.json` con `fetched_at` UTC.
- `main()` — flags: tokens posicionales (`nargs='*'`), `--csv`, `--status` (default `finished`, permite `live` sin winner), `--dry-run`, `--yes` (salta confirmación interactiva). La confirmación imprime tabla `P2  mex 2-0 zaf  → finished, winner=mex`.

**También:** agregar `data/fixed_results.json` a `.gitignore`.

**Tests (`tests/test_load_results.py`):** parseo válido/inválido, validación contra un `matches.json` sintético, `winner_team` en victoria local/visita/empate, `fetch_finished_results` con `supabase_request` monkeypatcheado, y que `--dry-run` no llame a la red.

---

## Fase 3 — Export: flag `--mc-only` en `scripts/export_to_supabase.py` (riesgo: BAJO)

- Nuevo flag `--mc-only`: salta el bloque de strengths (hoy obligatorio) y va directo a `export_mc_results`. La `version` se toma de `mc_data['version']` (ya se escribe desde `model_weights._version`); si falta, fallback `'1.3'` con WARN.
- `export_mc_results` sin cambios de lógica (ya desactiva el activo e inserta el nuevo); solo agregar un print de `fixed_count` si está presente en `mc_data`, para trazabilidad en consola.
- **Opcional (puede diferirse):** migración `supabase/28_simulation_run_live_metadata.sql` con `ALTER TABLE public.simulation_runs ADD COLUMN IF NOT EXISTS fixed_count integer, ADD COLUMN IF NOT EXISTS results_through timestamptz;` y que el exporter los incluya en el INSERT solo si existen en `mc_data`. Permite al frontend mostrar "condicionado a N resultados reales". Si no se aplica la migración, no enviar esos campos (PostgREST rechazaría columnas desconocidas) → enviar solo si `--with-live-metadata`.

**Tests:** extender `tests/test_supabase_exports.py` — `--mc-only` no exige `team_strength_snapshots.json`; dry-run imprime el plan; el INSERT del run no incluye `fixed_count` salvo flag.

---

## Fase 4 — Orquestador `scripts/update_results.py` (riesgo: BAJO-MEDIO)

Nuevo script, patrón de `scripts/pipeline.py` (subprocess por paso, salvo el fetch que importa directo de `load_results`):

```
python scripts/update_results.py 2:2-0 3:1-1                 # flujo completo
python scripts/update_results.py --sync-only                  # sin carga: re-sincroniza MC con lo ya cargado
python scripts/update_results.py --csv data/dia1.csv --with-predictions
```

`main()` con flags: tokens, `--csv`, `--sync-only`, `--runs` (default 10000), `--seed` (default 42), `--with-predictions`, `--dry-run`.

Secuencia:
1. **Cargar** (si hay tokens/CSV): `python scripts/load_results.py <tokens> --yes` (o `--dry-run`).
2. **Fetch**: `fetch_finished_results(...)` + `write_fixed_results(REPO_ROOT/'data'/'fixed_results.json', ...)` — importado de `load_results` (mismo proceso; en `--dry-run` se permite el fetch porque es solo lectura).
3. **MC condicionado**: `python scripts/run_monte_carlo.py --runs N --seed S --fixed-results data/fixed_results.json --output data/mc_results.json`. Prerrequisito: `data/team_strength_snapshots.json` existe (si no, error con instrucción de correr `build_team_strength.py`).
4. **Export**: `python scripts/export_to_supabase.py --mc-only --mc-results data/mc_results.json [--dry-run]`.
5. **Opcional** (`--with-predictions`): `generate_predictions.py --exclude-finished data/fixed_results.json` + `export_to_supabase.py --predictions`.

Requiere `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` en el entorno (igual que hoy; nunca en el repo). Salida final: id del run nuevo y resumen (`N resultados fijos, M pendientes simulados`).

**Tests (`tests/test_update_results.py`):** composición de comandos con subprocess mockeado (orden correcto, flags propagados), `--sync-only` salta el paso 1, abort si falta `team_strength_snapshots.json`.

---

## Fase 5 — Predictions solo-pendientes (riesgo: BAJO, opcional)

**Modificar `scripts/generate_predictions.py`:**

- Flag `--exclude-finished PATH` (lee `data/fixed_results.json` con `load_fixed_results`): filtra del loop los matches cuyo `match_number` está fijo.
- **Guardia crítica:** en modo exclusión NO emitir la línea `TRUNCATE public.predictions RESTART IDENTITY;` en el SQL (si alguien lo aplicara a mano borraría las predicciones históricas de partidos jugados). El exporter ya hace solo upsert por `match_id`, así las predicciones pre-partido de los finished quedan intactas como registro histórico.
- Documentar en `docs/prediction-engine.md`: regenerar predictions solo tiene efecto si cambiaron strengths/pesos; los resultados de otros partidos no alteran el 1X2 de un partido pendiente.

**Tests:** extender `tests/test_generate_predictions_calendar.py` o nuevo test — con exclusión, el SQL no contiene TRUNCATE ni los `match_id` excluidos, y sí los pendientes.

---

## Fase 6 — Señal de refresco en frontend (riesgo: BAJO)

**Modificar `js/predicciones.js` (+ helper en `js/supa-data.js`):**

- Nuevo helper `SupaData.getActiveRunId()`: `select id from simulation_runs where is_active=true order created_at desc limit 1` (consulta mínima, 1 fila).
- En `predicciones.js`, guardar `currentRunId` tras el render inicial; listener de `visibilitychange` (al volver a la pestaña) + intervalo suave (ej. cada 5 min solo si la pestaña está visible) que compara el id; si cambió, mostrar un banner "Hay una proyección nueva con resultados reales — Actualizar" cuyo botón re-ejecuta la carga/render (o `location.reload()` como mínimo viable).
- **Realtime (nota, no recomendado como primera versión):** `match_results` ya está en `supabase_realtime`, útil para la página de standings/resultados en vivo. Para predicciones habría que añadir `simulation_runs` a la publicación (`ALTER PUBLICATION supabase_realtime ADD TABLE public.simulation_runs;`) y suscribirse a INSERT con sesión premium (realtime respeta RLS). Es barato pero suma complejidad de canal/reconexión; el polling on-visibility cubre el caso de un solo admin que actualiza pocas veces al día.

---

## Fase 7 — GitHub Actions `workflow_dispatch` (riesgo: BAJO, opcional)

`.github/workflows/update-results.yml`:
- `on: workflow_dispatch` con input `results` (string opcional, ej. `"2:2-0 3:1-1"`; vacío = `--sync-only`).
- Steps: checkout → setup-python 3.12 → `python scripts/build_team_strength.py` (**necesario**: `team_strength_snapshots.json` está gitignored; sus insumos `teams.json`, `international_elo.json`, `model_weights.json` sí están commiteados) → `python scripts/update_results.py ${{ inputs.results }}` (o `--sync-only`).
- Secrets `SUPABASE_URL` y `SUPABASE_SERVICE_KEY` en GitHub Settings (nunca en el repo). Sin pip installs (stdlib only → el runner funciona tal cual). No commitea nada al repo.
- Útil para cargar resultados desde el celular. Es complemento, no reemplazo, del comando local.

**Descartado:** trigger/cron en Supabase (pg_cron/Edge Function) — implicaría reimplementar el modelo fuera de Python; sobre-ingeniería para un admin único.

---

## Orden de implementación

| # | Paso | Archivos | Riesgo | Validación |
|---|------|----------|--------|------------|
| 1 | Simulación condicionada | `scripts/simulate_group_stage.py`, `scripts/run_monte_carlo.py` | **Medio** (corazón del modelo; mitigado: kwarg default None + test de regresión bit-a-bit) | pytest nuevos + suite existente |
| 2 | `load_results.py` + .gitignore | `scripts/load_results.py`, `.gitignore` | Bajo | pytest + `--dry-run` real |
| 3 | `--mc-only` en exporter | `scripts/export_to_supabase.py` | Bajo | `--mc-only --dry-run` |
| 4 | Orquestador | `scripts/update_results.py` | Bajo-Medio (integración) | `--dry-run` end-to-end con partido 2 ya cargado |
| 5 | Frontend refresh | `js/predicciones.js`, `js/supa-data.js` | Bajo | manual local + Pages |
| 6 | Predictions pendientes (opcional) | `scripts/generate_predictions.py` | Bajo | pytest (sin TRUNCATE) |
| 7 | GH Actions (opcional) | `.github/workflows/update-results.yml` | Bajo | dispatch con `--dry-run` primero |
| 8 | Migración metadata run (opcional) | `supabase/28_simulation_run_live_metadata.sql` | Bajo | SQL editor + export con flag |

**Checkpoint de aceptación final:** con el partido 2 (mex 2-0 zaf) ya en la DB, correr `python scripts/update_results.py --sync-only --runs 10000 --seed 42` y verificar: (a) México sin masa en buckets de puntos < 3 y Sudáfrica sin masa en 9/7 imposibles, (b) run nuevo activo y el anterior desactivado, (c) la página de Predicciones muestra el run nuevo tras refrescar.

## Riesgos transversales

- **Stream RNG desplazado** con partidos fijos: mismo seed ≠ mismos resultados de pendientes que antes. Documentar en `docs/prediction-engine.md`.
- **Empates en fixed**: `winner_team = NULL` (columna nullable, válido en grupos).
- **Partidos `live`**: se excluyen del fetch (solo `finished`) → siguen simulándose como pendientes; coherente.
- **Doble fuente** (token recién cargado vs fetch): el fetch posterior a la carga elimina cualquier divergencia.
- **Service key**: sigue solo en entorno local / GitHub Secrets, jamás en archivos.
