# Plan: Narrativa de predicciones v2 — interpretación ELO + capa de banquillo (2026-06-12)

## Diagnóstico del texto actual

Generado por `generate_predictions.py` + `xi_matchups.py`. Tres problemas:

1. **Plantilla fija de 3 frases** para los 72 partidos: `"Comparación XI: X promedia A de ELO titular y Y B..." + nota de probabilidad + nota de calendario`. Solo cambian los números → todas las predicciones suenan iguales aunque los planteles sean radicalmente distintos.
2. **Números ELO crudos sin interpretación.** "1594.6 vs 1418.9" no le dice nada al lector. Nunca se traduce a qué significa la brecha (probabilidad esperada de imponerse, magnitud de la ventaja).
3. **Datos ricos sin usar:** `names_by_line` (nombres de titulares por línea) existe en los perfiles y no se imprime; los **15 suplentes con ELO por equipo** en `teams.json` (`titular: false`, con `elo`, `pos`, `club`) se ignoran por completo.

**Limitación de datos a declarar:** `elo` por jugador = ELO del **club** del jugador (los 3 suplentes del Arsenal comparten 2106; todos los Sundowns 1567). La narrativa debe hablar de "roce de club" / "nivel del club donde juega", nunca de rating individual.

**Outliers a auditar antes de publicar nombres:** Obed Vargas 1832 (figura como Atlético Madrid en banca de México), bloques de club idéntico (zaf: 3 suplentes Sundowns 1567). Paso previo: script de sanidad que liste suplentes con ELO > XI blend para revisión manual.

---

## Fase 1 — Módulo `scripts/elo_narrative.py` (nuevo, stdlib only)

Funciones puras y testeables:

- `expected_duel_pct(gap, elo_scale=400) -> float` — `1/(1+10^(-gap/elo_scale))*100`. Es la misma curva del modelo; traduce brechas a lenguaje: "+176 puntos equivale a imponerse en ~73 de cada 100 duelos directos".
- `gap_bucket(gap) -> str` — léxico por magnitud: `<25` "prácticamente parejos", `25–60` "ventaja ligera", `60–120` "ventaja clara", `120–200` "dominio esperado", `>200` "diferencia de categoría".
- `line_duel_sentence(line, profile_a, profile_b, names)` — frase del duelo de líneas con **nombres reales** (mejor jugador por línea + su club): "El ataque de EE.UU. (Tillman, Pulisic) promedia 1650 de roce de club contra una defensa paraguaya de 1490: brecha de +160, ventaja clara".
- **Capa banquillo** — `build_bench_profiles(teams_data)`:
  - `bench_top`: top-3 suplentes por ELO (nombre, línea, club, elo).
  - `bench_upgrade[line]` = `max(0, mejor suplente de la línea − promedio titular de la línea)` → cuánto SUBE la línea si entra.
  - `bench_depth` = media del top-5 de banca − xi_blend → índice de profundidad (gestión de minutos, calor, J3).
- `bench_note(profile, bench)` — la frase distintiva por equipo: "El banquillo puede mover el partido: Ricardo Pepi (PSV, roce 1726) no arranca y su ingreso elevaría el ataque de 1588 a ~1640; es la carta de gol si el plan A se atasca". Si `bench_upgrade` ≈ 0 en todas las líneas: "la banca no sube el nivel del XI: lo que se ve de arranque es el techo".
- **Anti-plantilla:** 3–4 esqueletos narrativos por arquetipo (`global_tag`: favorito claro / ligero / parejo / empate probable / abierto), con variantes léxicas elegidas determinísticamente por `hash(match_id) % n` (reproducible, sin RNG). El gancho inicial es el dato más distintivo del cruce (el edge con mayor `|valor|`), no siempre "Comparación XI:".

## Fase 2 — Integración en `generate_predictions.py` (solo texto; números intactos)

- `explanation` pasa de 3 frases a **3 párrafos** separados por `\n\n`:
  1. Lectura del cruce: brecha global interpretada (`gap_bucket` + `expected_duel_pct`) y por qué el modelo da lo que da.
  2. Duelos de líneas con nombres + la capa de banquillo de ambos equipos (qué cambio puede alterar el desarrollo).
  3. Probabilidad 1X2 + nota de calendario (lo actual, al final). Si la probabilidad es más pareja que la brecha de ELO, explicarlo: "el modelo comprime favoritos en torneos cortos (draw_bias/parity), por eso 36/34/30 y no 50/28/22".
- `team_a_context`/`team_b_context`: fortaleza + riesgo (como hoy) + **la carta del banquillo con nombre**.
- Sin migración SQL: mismas columnas text; re-export con `export_to_supabase.py --predictions` (upsert por match_id; probabilidades idénticas, solo texto).
- La aclaración "ELO = nivel del club del jugador" va una sola vez en el explainer del modelo (RPC `get_elo_model_explainer`), no repetida en cada tarjeta.

## Fase 3 — UI (`js/premium.js`)

- Renderizar `explanation` por párrafos: `split('\n\n')` → `<p class="prono-explanation-p">` (hoy es un único bloque).
- Opcional: chip "Supersub" junto a los marcadores (requiere columna jsonb `bench_impact` → migración 28). Alternativa sin migración: el nombre va dentro del context text. **Recomendación: empezar sin migración.**

## Fase 4 (opcional, separada) — Impacto en números

- `bench_weight` (0.05–0.10) sobre `bench_upgrade` ponderado para ajustar la fuerza efectiva (banca profunda vale más en J3 / calor / rotación). **No mezclar con el cambio narrativo**: requiere recalibrar con `calibration_report.py --grid` y re-export de MC. Hacerlo solo si la v2 narrativa convence.

## Pre-requisito — Sanidad de datos de banca

- Script `scripts/audit_bench_elo.py --report`: lista por equipo los suplentes con ELO > XI blend y los bloques de club repetido; salida para revisión manual (ej. ¿Obed Vargas está bien cargado como Atlético Madrid?). Solo tras el visto bueno se publican narrativas con nombres.

## Tests (pytest, `tests/test_elo_narrative.py`)

- Determinismo: mismo input → mismo texto exacto.
- Anti-similitud: ningún par de explicaciones comparte un 8-grama fuera de la nota de calendario y términos del modelo (umbral medible, falla si vuelve la plantilla).
- Nombres: todo jugador citado pertenece al plantel correcto y a la línea correcta.
- Longitud: explanation entre ~450 y ~900 caracteres (hoy ~280).
- `expected_duel_pct` en valores conocidos (0→50%, +400→~90.9%); buckets en los límites.

## Ejemplo antes / después (EE.UU. vs Paraguay, datos reales)

**Hoy (281 caracteres, plantilla):**
> Comparación XI: EE.UU. promedia 1594.6 de ELO titular y Paraguay 1418.9. EE.UU. tiene su mejor cruce en defensa vs ataque rival (+226.1) y su mayor alerta en arquero vs ataque rival (-81.7). [...] El modelo ELO deja un cruce parejo: EE.UU. 36.0%, empate 34.5% y Paraguay 29.6%. Calendario: [...]

**Propuesto (~750 caracteres, único por partido):**
> La brecha global es de +176 puntos de roce de club a favor de EE.UU. — en términos ELO, imponerse en ~73 de cada 100 duelos directos: ventaja clara, no dominio. El cruce que más desequilibra es la defensa estadounidense contra el ataque guaraní (+226): Paraguay no suele generar volumen contra zagas de ese nivel.
>
> El partido también se decide en los cambios. EE.UU. guarda a Ricardo Pepi (PSV, roce 1726) como revulsivo: su ingreso eleva el ataque de 1588 a ~1640, la carta si el plan A se atasca. Paraguay responde con Mauricio Magalhães (Palmeiras, 1538), único suplente que sube el nivel de su mediocampo; fuera de él, lo que arranca es el techo del plantel.
>
> Aun así el 1X2 queda más parejo de lo que sugiere el ELO bruto (36.0% / 34.5% / 29.6%): en torneos cortos el modelo comprime favoritos y un solo gol cambia el guion. Calendario: el debut define el margen inicial del Grupo D [...]

## Orden de implementación y riesgo

| # | Paso | Archivos | Riesgo | Validación |
|---|------|----------|--------|------------|
| 0 | Auditoría banca | `scripts/audit_bench_elo.py` | Bajo | revisión manual del reporte |
| 1 | Módulo narrativa | `scripts/elo_narrative.py` + tests | Bajo (no toca números) | pytest |
| 2 | Integración texto | `scripts/generate_predictions.py` | Medio (regenerar 72 textos) | pytest + diff de probabilidades == 0 |
| 3 | Re-export | `export_to_supabase.py --predictions` | Bajo (upsert) | spot-check en Supabase |
| 4 | UI párrafos | `js/premium.js` (+ CSS) | Bajo | smoke test Node |
| 5 | (Opc.) bench_weight | model_weights + simulador | Alto (recalibrar) | calibration_report --grid |
