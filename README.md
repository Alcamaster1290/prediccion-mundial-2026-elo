# Mundial 2026 — Predicciones y Análisis

Proyecto web para análisis táctico, ELO de clubes y predicciones del Mundial 2026 (Canadá · México · Estados Unidos).

Fuente de análisis: [AlterFutbol](https://alterfutbol.com) · ELO de clubes: [worldclubratings.com](http://worldclubratings.com/rankings/elo_men/) · ELO internacional: [international-football.net](https://www.international-football.net)

**Sitio en vivo:** [https://alcamaster1290.github.io/prediccion-mundial-2026-elo/](https://alcamaster1290.github.io/prediccion-mundial-2026-elo/)

---

## Estructura del proyecto

```
mundial-2026/
│
├── index.html                      # App principal (dark editorial, navegación por grupo)
├── auth/
│   └── callback.html               # Callback de confirmación de email Supabase
│                                   #   → verificación de cuenta + pago + código de activación
├── assets/
│   ├── flags/                      # 48 banderas SVG — código ISO 3166-1 alpha-3
│   ├── players/                    # 24 fotos verificadas de figura clave; nuevos perfiles usan placeholder
│   ├── xi/                         # 46 imágenes de XI Ideal / formación (AlterFutbol)
│   ├── og-image.png                # Open Graph image (1200×630)
│   ├── yape-qr.jpeg                # QR de pago Yape
│   └── paypal-qr.jpeg              # QR de pago PayPal
│
├── js/
│   ├── config.js                   # SUPABASE_URL + SUPABASE_ANON_KEY (no subir service_role)
│   ├── config.example.js           # Plantilla de credenciales para clonar como config.js
│   ├── auth.js                     # Autenticación Supabase — expone window.SupaAuth
│   ├── supa-data.js                # Capa de lectura pública Supabase (loadMatchResults, loadPredictions, RPCs)
│   ├── premium.js                  # Sección "Pronósticos" premium — expone window.PremiumSection
│   ├── predicciones.js             # Sección "Predicciones Monte Carlo" premium — expone window.PredicionesSection
│   ├── bracket.js                  # Llave de eliminatoria (16avos → Final); proyección pública sin % para no-premium
│   ├── standings.js                # Tablas de posiciones en vivo
│   └── admin-premium-codes.js      # Panel admin para generar/listar códigos premium
│
├── data/
│   ├── groups.json                 # 12 grupos A-L, fixtures y fechas oficiales FIFA
│   ├── matches.json                # 72 partidos de fase de grupos (generado por generate_matches.py)
│   ├── match_context.json          # Matriz narrativa — análisis táctico por partido
│   ├── teams.json                  # 46 perfiles publicados + 46 planteles fuenteados (1196 jugadores)
│   ├── team_strength_snapshots.json # Output local ignorado: fuerza v1.3 para exportar a Supabase
│   ├── international_elo.json      # ELO internacional real (international-football.net, 48 equipos)
│   ├── club_elo.json               # ELO de clubes de referencia (worldclubratings.com)
│   ├── club_elo_*_supplement.json  # Suplementos de ELO de clubes (elofootball, flerosport)
│   ├── model_weights.json          # Config del modelo (_version, club_adj_weight, xi_matchup_weight, base_goals_per_team, elo_scale, elo_lambda_scale, draw_bias, parity_scale)
│   ├── mc_results.json             # Output local ignorado: Monte Carlo premium para exportar a Supabase
│   ├── knockout_matches.json       # Fixture de la fase eliminatoria (16avos → Final, matchNum 73-104)
│   ├── fixed_results.json          # Marcadores reales generados desde la tabla live match_results (gitignored)
│   ├── final_phase_predictions.json # Proyección editorial de la fase eliminatoria (generado)
│   ├── match_results.mock.json     # Mock local de resultados para desarrollo sin Supabase
│   ├── squad_publication_tracker.json # Seguimiento de publicación de planteles/perfiles
│   ├── team-content-manifest.json  # Manifiesto de contenido por equipo (secciones HTML)
│   └── predictions.mock.json       # Predicciones ficticias solo para desarrollo local
│
├── scripts/
│   ├── simulate_group_stage.py     # Motor de simulación Poisson — load_matches, load_strengths,
│   │                               #   simulate_all_groups, best_thirds, fixed_results
│   ├── run_monte_carlo.py          # Runner — 10,000 iteraciones, produce mc_results.json
│   │                               #   incluye proyección de tabla de mejores terceros
│   ├── elo_probability.py          # Probabilidad 1X2 + marcadores top-N desde la matriz Poisson (draw_bias)
│   ├── elo_narrative.py            # Narrativa editorial v2 (interpretación ELO + capa de banquillo)
│   ├── xi_matchups.py              # Capa de matchup por líneas del XI titular
│   ├── calibration_report.py       # Diagnóstico de calibración: empates, goles,
│   │                               #   distribución de puntos y grid search de parámetros
│   ├── build_team_strength.py      # Construye team_strength_snapshots.json con ELO híbrido
│   ├── generate_predictions.py     # Pronósticos por partido (1X2, marcadores, narrativa) → predictions_seed.sql
│   ├── generate_final_phase_predictions.py # Proyección de la fase eliminatoria → final_phase_predictions.json
│   ├── load_results.py             # Carga marcadores reales (match_number:home-away) en match_results
│   ├── update_results.py           # Flujo de jornada: load_results + Monte Carlo + export (--sync-only)
│   ├── admin_results.py            # Carga puntual de un resultado en match_results (admin)
│   ├── pipeline.py                 # Orquestador de la cadena completa de generación
│   ├── extract_squads.py           # Extrae planteles de index.html → popula teams.json
│   ├── import_alterfutbol_squads.py # Importa planteles desde AlterFutbol
│   ├── render_team_sections.py     # Renderiza las secciones HTML de equipo desde teams.json
│   ├── build_team_content_manifest.py # Construye team-content-manifest.json
│   ├── update_club_elo_from_worldclubratings.py # Refresca club_elo.json desde la fuente
│   ├── audit_fifa_dates.py         # Valida/corrige fechas kickoff_utc en groups/matches
│   ├── audit_bench_elo.py          # Auditoría de la capa de banquillo de la narrativa
│   ├── generate_matches.py         # Genera matches.json desde groups.json
│   ├── generate_seed_sql.py        # Produce SQL de seed para tablas Supabase
│   ├── export_to_supabase.py       # Sube datos vía API de Supabase (requiere service_role)
│   ├── seed_players.py             # Seed de jugadores en tabla players
│   ├── serve_demo.py               # Servidor local de demostración
│   └── validate_data.py            # Validaciones de integridad de datos
│
├── supabase/                       # Migraciones numeradas 01-30 (aplicar en orden)
│   ├── 01_schema.sql               # Tablas: profiles, premium_codes, predictions
│   ├── 02_rls.sql                  # Row Level Security — políticas de acceso
│   ├── 03_functions.sql            # RPC: redeem_premium_code (SECURITY DEFINER)
│   ├── 04_admin_codes.sql          # Helpers para crear/listar códigos premium
│   ├── 05_prediction_engine_schema.sql  # Motor: players, national_elo_ratings,
│   │                               #   team_strength_snapshots, simulation_runs,
│   │                               #   simulation_group_standings
│   ├── 06_national_elo_schema.sql  # Tabla ELO internacional pública
│   ├── 07_prediction_engine_rls_hardening.sql # Lectura premium del motor
│   ├── 08_security_advisors_hardening.sql # Permisos de funciones SECURITY DEFINER
│   ├── 09_tournament_core.sql      # Datos canónicos del torneo + tabla live match_results
│   ├── 10_standings_views.sql      # Vistas públicas de posiciones y mejores terceros
│   ├── 11_knockout_rules.sql       # Reglas de slots de la llave y resolución de cruces
│   ├── 12_team_profiles.sql        # Metadata de perfiles de equipo (público/premium)
│   ├── 13_staff_roles.sql          # Autorización de staff, políticas admin/editor
│   ├── 14_simulation_snapshots.sql # Snapshots MC activos/versionados
│   ├── 15_premium_ops.sql          # Grants premium, log de auditoría y RPCs admin
│   ├── 16–21 …                     # Endurecimiento de advisors, códigos y monitoreo admin
│   ├── 22–26 …                     # Explicadores SQL del modelo ELO (fórmula, XI, calibración v1.3)
│   ├── 27_predictions_top_scorelines.sql # Columna jsonb top_scorelines en predictions
│   ├── 28_predictions_free_finished.sql  # Auto-desbloqueo free de pronósticos ya jugados
│   ├── 29_bracket_public_projection.sql  # RPC get_bracket_projection (sin % para anon)
│   └── 30_resolve_knockout_best_thirds.sql # Resolución de mejores terceros y cruces de llave
│
└── docs/
    └── superpowers/
        ├── specs/                  # Specs de diseño por feature
        └── plans/                  # Planes de implementación
```

---

## Motor de datos (Pipeline de predicción)

El motor de predicción es un pipeline Python + Supabase que transforma datos de fuentes públicas en probabilidades de clasificación por equipo.

### Arquitectura

```
AlterFutbol (HTML)          international-football.net   worldclubratings.com
      │                              │                          │
extract_squads.py           international_elo.json         club_elo.json
      │                              │                          │
 teams.json                          └──────────┬──────────────┘
(46 planteles · 1196 jugadores)                 │
                                     build_team_strength.py
                                                │
                                  team_strength_snapshots.json
                                  (48 equipos · v1.3 ELO híbrido + matchup XI)
                                                │
                                   run_monte_carlo.py
                                   simulate_group_stage.py
                                                │
                                       mc_results.json
                               (10,000 sims · 48 equipos · 12 terceros)
                                                │
                                  generate_seed_sql.py
                                                │
                              Supabase (MCP / export_to_supabase.py)
                              ├── players (1196 filas)
                              ├── national_elo_ratings (48 filas)
                              ├── team_strength_snapshots (48 filas)
                              ├── simulation_runs (1 fila)
                              ├── simulation_group_standings (48 filas)
                              └── simulation_terceros_table (12 filas)
```

### Modelo ELO híbrido (v1.3)

Combina el ranking internacional real con el ELO de clubes del XI titular de cada selección:

```
score = elo_intl + (xi_blend − avg_xi_blend) × club_adj_weight
```

| Parámetro | Valor |
|-----------|-------|
| `_version` | 1.3 |
| `club_adj_weight` | 0.35 |
| `xi_matchup_weight` | 0.20 |
| `avg_xi_blend` (promedio global actual) | 1585.0 |
| `base_goals_per_team` | 1.25 |
| `elo_scale` | 400 |
| `elo_lambda_scale` | 800 |
| `draw_bias` | 0.08 |
| `parity_scale` | 800 |

- **`elo_intl`**: ELO nacional de international-football.net (rango real: 1423–2165)
- **`xi_blend`**: promedio de ELO de club de los 11 titulares (worldclubratings.com)
- Las selecciones con XI titular fuenteado usan ELO híbrido; Arabia Saudita y Jordania siguen con `elo_intl` hasta tener fuente directa confiable.
- En cada partido se aplica una capa pequeña de `xi_matchup_weight` que compara líneas del XI: ataque vs defensa rival, mediocampo vs mediocampo, defensa vs ataque rival y arquero vs ataque rival.

### Simulación de goles (Poisson calibrado v1.3)

```
share_A = 1 / (1 + 10^(-(score_A − score_B) / elo_lambda_scale))
total_goals = 2 × base_goals_per_team
λ_A = total_goals × share_A
λ_B = total_goals × (1 − share_A)
```

Sobre el resultado 1X2 se aplica una corrección de empate consciente de la paridad:
`boost = draw_bias × max(0, 1 − |score_A − score_B| / parity_scale)`, restando la masa
proporcionalmente de ambas victorias. Calibrado en v1.3 para producir ~25.5% de empates,
2.46 goles por partido y una distribución de puntos con masa visible en 1, 2, 4, 5 y 7
(detalle en `docs/prediction-engine.md`). Los goles se muestrean de la matriz conjunta
de Poisson ajustada (con `draw_bias = 0` se conserva el muestreo Knuth legacy).

### Monte Carlo

- **10,000 iteraciones**, semilla reproducible `seed=42`
- Trackea por equipo: `first_pct`, `second_pct`, `third_pct`, `best_third_pct`, `fourth_pct`, `qualified_pct`, `points_pct`
- Trackea por grupo (terceros): `avg_pts`, `avg_gd`, `avg_gf`, `qualifies_pct`, equipo más frecuente en 3°
- Los **8 mejores terceros** de 12 grupos avanzan a octavos, clasificados por criterios actuales del simulador: PTS promedio > DG promedio > GF promedio.
- En la tabla de terceros, `qualifies_pct` describe el slot de tercer lugar del grupo, no una probabilidad individual del equipo mostrado.

### Fase eliminatoria (16avos → Final)

Terminada la fase de grupos, la llave se resuelve con los 32 clasificados (1.º y 2.º de
cada grupo + 8 mejores terceros) y se proyecta partido a partido:

```
data/fixed_results.json  (marcadores reales, generado desde match_results)
data/knockout_matches.json (fixture 16avos → Final, matchNum 73-104)
                    │
      generate_final_phase_predictions.py
                    │
        data/final_phase_predictions.json
   (6 rondas: r32 · r16 · qf · sf · tp · final)
                    │
         js/bracket.js (Llave visual)
```

- `generate_final_phase_predictions.py` reutiliza el modelo v1.3 (`elo_probability`,
  `xi_matchups`, `elo_narrative`) para producir, por cruce, probabilidad de avance,
  ganador proyectado, tag global y texto editorial. Sin empates: la corrección de
  `draw_bias` se reparte entre las dos victorias (avance directo).
- Las rondas cubiertas: `r32` (16avos, 16 partidos), `r16` (Octavos, 8), `qf` (Cuartos, 4),
  `sf` (Semifinales, 2), `tp` (Tercer Puesto, 1) y `final` (1).
- A medida que se cargan resultados reales de la llave, se vuelve a correr el script para
  recomputar los cruces siguientes con los clasificados ya conocidos.
- La Llave (`js/bracket.js`) muestra a no-premium/anon las banderas y posiciones de los
  clasificados **sin porcentajes**; el % y la simulación MC siguen premium (RPC
  `get_bracket_projection`, migración `29`).

### Re-ejecutar la simulación

```bash
# 1. Extraer planteles del HTML (si se agregan nuevos equipos)
python scripts/extract_squads.py

# 2. Recalcular fuerzas ELO
python scripts/build_team_strength.py

# 3. Correr Monte Carlo
python scripts/run_monte_carlo.py --runs 10000 --seed 42

# 3b. Diagnóstico de calibración (empates, goles, distribución de puntos)
python scripts/calibration_report.py --runs 10000 --seed 42
#     Grid search de parámetros:
python scripts/calibration_report.py --grid --grid-runs 1000 --seed 42

# 4. Generar SQL de seed para Supabase
python scripts/generate_seed_sql.py

# 5. Verificar export sin escribir
python scripts/export_to_supabase.py --all --dry-run

# 6. Exportar con service role solo desde terminal local/admin
python scripts/export_to_supabase.py --all
```

### Flujo de jornada (cargar resultados reales)

Cuando se juegan partidos, se cargan como tokens `match_number:home-away` y el Monte
Carlo se recalcula condicionado a lo ya jugado:

```bash
# Previsualizar sin escribir
python scripts/load_results.py 86:2-1 87:0-0 --dry-run --yes

# Flujo admin completo: cargar resultados + MC condicionado + export del run nuevo
python scripts/update_results.py 86:2-1 87:0-0 --runs 10000 --seed 42

# Re-sincronizar proyección desde resultados ya cargados en Supabase
python scripts/update_results.py --sync-only --runs 10000 --seed 42

# Recomputar la proyección de la fase eliminatoria (16avos → Final)
python scripts/generate_final_phase_predictions.py
```

Detalle completo del flujo en [`docs/prediction-engine.md`](docs/prediction-engine.md)
(secciones *Matchday update* y *Conditioning on played results*).

---

## Tablas Supabase

| Tabla | Filas | Descripción |
|-------|-------|-------------|
| `profiles` | dinámica | Usuarios registrados — `is_premium`, email |
| `premium_codes` | manual | Códigos hash SHA-256 para activación |
| `predictions` | 72+ | Pronósticos por partido (1X2, marcadores `top_scorelines`, narrativa) |
| `match_results` | dinámica | Marcadores reales cargados en vivo (grupos + eliminatoria) |
| `players` | 1196 | Planteles: pos, nombre, edad, club, país del club, ELO, titular |
| `national_elo_ratings` | 48 | ELO internacional por selección |
| `team_strength_snapshots` | 48 | Fuerza compuesta (ELO híbrido v1.3) |
| `simulation_runs` | 1+ | Metadatos versionados del run: iteraciones, semilla, escenario, hash, activo |
| `simulation_group_standings` | 48 | Probabilidades de clasificación por equipo |
| `simulation_terceros_table` | 12 | Proyección de mejores terceros por grupo |

Vistas y RPC públicos (migraciones `09`–`11`, `29`–`30`): `get_group_standings`
(tabla real derivada de `match_results`), `get_bracket_projection` (llave sin %) y
las reglas de resolución de cruces de la fase eliminatoria.

Orden mínimo recomendado para el motor:

```text
01_schema.sql
02_rls.sql
03_functions.sql
05_prediction_engine_schema.sql
07_prediction_engine_rls_hardening.sql
08_security_advisors_hardening.sql
```

`05_prediction_engine_schema.sql` crea un baseline público para las tablas del
motor. Si las simulaciones son producto de acceso completo, aplicar `07` después:
revoca `anon`, deja lectura a `authenticated` solo con `profiles.is_premium =
true`, y conserva escritura para `service_role`. `08` limita exposición de
funciones. `national_elo_ratings` queda público porque replica una fuente pública
de ELO internacional.

Datos públicos: calendario/torneo, perfiles publicados y ELO internacional.
Datos premium: `predictions`, `team_strength_snapshots`, `simulation_runs`,
`simulation_group_standings`, `simulation_terceros_table`, `players` como fuente
Supabase del motor, `team_profile_premium` y el explicador ELO.

---

## Sistema Premium

### Flujo de usuario

```
Registro → Email de confirmación → auth/callback.html
  → Tabs de pago (Yape QR / PayPal QR)
  → Envío de código de activación
  → Acceso a secciones "Pronósticos" y "Predicciones"
```

### Crear un código premium

```sql
INSERT INTO public.premium_codes (code_hash, notes)
VALUES (
  encode(digest('TU-CODIGO-AQUI', 'sha256'), 'hex'),
  'Pago Yape S/15 - Nombre - fecha'
);
```

Enviar el código en texto plano al usuario por email. **Nunca almacenar en texto plano.**

### Validar usuarios premium

```sql
SELECT id, email, is_premium, updated_at
FROM public.profiles WHERE is_premium = true;
```

### Por qué RLS es suficiente

La `anon key` es pública y segura porque:
1. RLS garantiza que cada usuario solo lee lo que le corresponde
2. `premium_codes` no tiene política SELECT pública
3. `redeem_premium_code` es `SECURITY DEFINER` — bypass controlado
4. Las predicciones premium solo son accesibles si `is_premium = true`

**Nunca colocar la `service_role key` en ningún archivo del repo.**

---

## Convenciones de assets

### `assets/flags/`
- Código ISO 3166-1 **alpha-3** en minúsculas: `bih.svg`, `esp.svg`, `usa.svg`
- Fuente: [flagcdn.com](https://flagcdn.com)

### `assets/players/`
- Formato: `{código-equipo}-{apellido}.jpg` (o `.webp`, `.png`)
- Excepción histórica: `jap-kubo.webp` (Japón usa `jap`, no `jpn`), `cur-bacuna.jpg` (Curazao usa `cur`, no `cuw`)

### `assets/xi/`
- Formato: `{código-equipo}-xi.png` — capturas de AlterFutbol
- 46 selecciones disponibles al 6 de junio de 2026

---

## Estado del análisis

### Progreso del torneo (al 10 de julio de 2026)

| Fase | Estado |
|------|--------|
| Fase de grupos (72 partidos) | ✅ Completa — resultados reales cargados |
| 16avos de Final (16 partidos, 73-88) | ⏳ En curso — 13 de 16 jugados |
| Octavos → Final | 🔲 Proyectados en `final_phase_predictions.json` |

Los marcadores reales viven en la tabla `match_results` (Supabase) y se replican en
`data/fixed_results.json`. Tras cada tanda de resultados se re-corre el Monte Carlo
condicionado y `generate_final_phase_predictions.py` para actualizar la llave.

### Cobertura de análisis

| Cobertura | Estado |
|-----------|--------|
| Perfiles HTML publicados | 46 selecciones |
| Planteles fuenteados | 46 selecciones · 1196 jugadores |
| XI probable local | 46 imágenes en `assets/xi` |
| Titulares marcados | 46 selecciones con 11 `players[].titular` |
| Retratos reales de figura | 24 selecciones; los 22 perfiles nuevos usan placeholder |
| Pendientes por fuente directa | Arabia Saudita (`ksa`) y Jordania (`jor`) |

---

## Paleta de colores por grupo

| Grupo | Variable CSS | Hex |
|-------|-------------|-----|
| A | `--grp-a` | `#e55c5c` |
| B | `--grp-b` | `#3b8beb` |
| C | `--grp-c` | `#10b981` |
| D | `--grp-d` | `#6366f1` |
| E | `--grp-e` | `#f97316` |
| F | `--grp-f` | `#f59e0b` |
| G | `--grp-g` | `#8b5cf6` |
| H | `--grp-h` | `#ec4899` |
| I | `--grp-i` | `#06b6d4` |
| J | `--grp-j` | `#84cc16` |
| K | `--grp-k` | `#d97706` |
| L | `--grp-l` | `#94a3b8` |

---

## Cómo usar

```bash
git clone https://github.com/Alcamaster1290/prediccion-mundial-2026-elo.git
cd prediccion-mundial-2026-elo

# No hay build step — abrir directamente en el navegador
# (Para fetch() de JSON se necesita servidor local)
python3 -m http.server 8080
# o
npx serve .
```

Para activar el sistema premium, copiar `js/config.example.js` como `js/config.js` y rellenar las credenciales de Supabase.

---

## Roadmap

### Completado ✅

- [x] 48 banderas SVG descargadas (grupos A-L)
- [x] 46 selecciones con perfil HTML publicado (sistema, ausencias, XI, tabla, partidos y ruta)
- [x] 1196 jugadores en `teams.json` con club y país de club desde AlterFutbol
- [x] 46 imágenes de XI/formación en `assets/xi`, tácticas fuenteadas y 22 `scheme` completos para equipos squad-only
- [x] 46 selecciones cargadas con 11 titulares marcados en `players[].titular`
- [x] ELO internacional real de 48 selecciones (international-football.net)
- [x] Modelo ELO híbrido v1.3 (ranking intl + xi_blend de clubes + matchup XI, calibrado)
- [x] `team_strength_snapshots.json` generado localmente — 48 selecciones con fuerza compuesta
- [x] Simulación Poisson Monte Carlo — 10,000 iteraciones, seed=42
- [x] Calibración v1.3 (draw_bias, elo_lambda_scale) — empates ~25.5%, 2.46 goles/partido
- [x] Proyección tabla mejores terceros (12 grupos, criterios FIFA)
- [x] Motor de datos completo en Supabase (30 migraciones, RLS por rol)
- [x] Sección "Predicciones" premium — 2 tablas (clasificación + mejores terceros)
- [x] Sección "Pronósticos" premium — pronóstico por partido (1X2, marcadores top-10, narrativa v2)
- [x] Pronósticos por partido en tabla `predictions` (auto-desbloqueo free al finalizar)
- [x] Carga de resultados reales en vivo (`load_results.py`/`update_results.py` → match_results)
- [x] Monte Carlo condicionado a resultados jugados (`--results-source live`)
- [x] Llave de eliminatoria (`bracket.js`) con proyección pública sin % para no-premium
- [x] Proyección de la fase final (`final_phase_predictions.json`, 6 rondas)
- [x] Sistema de pago con QR Yape + PayPal (tabs interactivos)
- [x] Callback de confirmación de email con flujo de activación premium
- [x] SEO: Schema.org @graph, keywords, preconnects, sitemap daily, robots
- [x] GitHub Pages publicado con dominio alcamaster1290.github.io

### Pendiente 🔲

- [ ] Cargar los 3 resultados restantes de 16avos y recomputar octavos
- [ ] v1.4: fecha1_caution_draw_boost / fecha3_context_draw_boost (reservados, no leídos)
- [ ] Imputar ELO `N/D` de titulares (`ksa`, `jor`) con fuente directa confiable
- [ ] Migración para explicadores SQL 22/24/25 (aún citan base_goals 1.3)
- [ ] Configurar templates de email de Supabase (confirmación, reset de contraseña)
- [ ] Comparador de ELO entre equipos del mismo cruce

---

*Datos actualizados al 10 de julio de 2026 (fase eliminatoria, 16avos en curso). Fuentes: AlterFutbol · worldclubratings.com · international-football.net · FIFA*
