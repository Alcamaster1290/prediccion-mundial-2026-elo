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
│   ├── players/                    # 25 fotos de figura clave — una por selección
│   ├── xi/                         # 26 imágenes de XI Ideal (AlterFutbol)
│   ├── og-image.png                # Open Graph image (1200×630)
│   ├── yape-qr.jpeg                # QR de pago Yape
│   └── paypal-qr.jpeg              # QR de pago PayPal
│
├── js/
│   ├── config.js                   # SUPABASE_URL + SUPABASE_ANON_KEY (no subir service_role)
│   ├── auth.js                     # Autenticación Supabase — expone window.SupaAuth
│   ├── premium.js                  # Sección "Pronósticos" premium — expone window.PremiumSection
│   ├── predicciones.js             # Sección "Predicciones Monte Carlo" premium — expone window.PredicionesSection
│   └── standings.js                # Tablas de posiciones en vivo
│
├── data/
│   ├── groups.json                 # 12 grupos A-L, fixtures y fechas oficiales FIFA
│   ├── matches.json                # 72 partidos de fase de grupos (generado por generate_matches.py)
│   ├── match_context.json          # Matriz narrativa — análisis táctico por partido
│   ├── teams.json                  # 24 análisis completos + 46 planteles fuenteados (1196 jugadores)
│   ├── team_strength_snapshots.json # Fuerza de las 48 selecciones (v1.1 — ELO híbrido)
│   ├── international_elo.json      # ELO internacional real (international-football.net, 48 equipos)
│   ├── club_elo.json               # ELO de clubes de referencia (worldclubratings.com)
│   ├── model_weights.json          # Pesos del modelo (club_adj_weight, base_goals, elo_scale)
│   ├── mc_results.json             # Resultados Monte Carlo (10,000 runs, seed=42, 48 equipos)
│   ├── knockout_matches.json       # Fixture de la fase eliminatoria
│   └── predictions.mock.json       # Predicciones de demo (modo sin Supabase)
│
├── scripts/
│   ├── simulate_group_stage.py     # Motor de simulación Poisson — load_matches, load_strengths,
│   │                               #   simulate_all_groups, best_thirds
│   ├── run_monte_carlo.py          # Runner — 10,000 iteraciones, produce mc_results.json
│   │                               #   incluye proyección de tabla de mejores terceros
│   ├── build_team_strength.py      # Construye team_strength_snapshots.json con ELO híbrido
│   ├── extract_squads.py           # Extrae planteles de index.html → popula teams.json
│   ├── generate_matches.py         # Genera matches.json desde groups.json
│   ├── generate_seed_sql.py        # Produce SQL de seed para tablas Supabase
│   ├── export_to_supabase.py       # Sube datos vía API de Supabase (requiere service_role)
│   ├── seed_players.py             # Seed de jugadores en tabla players
│   └── validate_data.py            # Validaciones de integridad de datos
│
├── supabase/
│   ├── 01_schema.sql               # Tablas: profiles, premium_codes, predictions
│   ├── 02_rls.sql                  # Row Level Security — políticas de acceso
│   ├── 03_functions.sql            # RPC: redeem_premium_code (SECURITY DEFINER)
│   ├── 04_admin_codes.sql          # Helpers para crear/listar códigos premium
│   ├── 05_prediction_engine_schema.sql  # Tablas del motor de datos:
│   │                               #   players, national_elo_ratings,
│   │                               #   team_strength_snapshots,
│   │                               #   simulation_runs, simulation_group_standings
│   ├── 06_national_elo_schema.sql  # Tabla ELO internacional pública
│   ├── 07_prediction_engine_rls_hardening.sql # Lectura premium del motor
│   └── 08_security_advisors_hardening.sql # Permisos de funciones SECURITY DEFINER
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
                                  (48 equipos · v1.1 ELO híbrido)
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

### Modelo ELO híbrido (v1.1)

Combina el ranking internacional real con el ELO de clubes del XI titular de cada selección:

```
score = elo_intl + (xi_blend − avg_xi_blend) × club_adj_weight
```

| Parámetro | Valor |
|-----------|-------|
| `club_adj_weight` | 0.35 |
| `avg_xi_blend` (promedio global) | 1675.3 |
| `base_goals_per_team` | 1.3 |
| `elo_scale` | 400 |

- **`elo_intl`**: ELO nacional de international-football.net (rango real: 1423–2165)
- **`xi_blend`**: promedio de ELO de club de los 11 titulares (worldclubratings.com)
- Las 24 selecciones con análisis completo usan ELO híbrido; las demás usan solo `elo_intl` hasta tener XI titular fuenteado.

### Simulación de goles (Poisson / Knuth)

```
λ_A = base_goals × 10^((score_A − score_B) / 800)
λ_B = base_goals × 10^((score_B − score_A) / 800)
```

Los goles se generan con el algoritmo de Knuth para muestras de distribución Poisson.

### Monte Carlo

- **10,000 iteraciones**, semilla reproducible `seed=42`
- Trackea por equipo: `first_pct`, `second_pct`, `third_pct`, `best_third_pct`, `fourth_pct`, `qualified_pct`
- Trackea por grupo (terceros): `avg_pts`, `avg_gd`, `avg_gf`, `qualifies_pct`, equipo más frecuente en 3°
- Los **8 mejores terceros** de 12 grupos avanzan a octavos, clasificados por criterios FIFA (PTS > DG > GF)

### Re-ejecutar la simulación

```bash
# 1. Extraer planteles del HTML (si se agregan nuevos equipos)
python scripts/extract_squads.py

# 2. Recalcular fuerzas ELO
python scripts/build_team_strength.py

# 3. Correr Monte Carlo
python scripts/run_monte_carlo.py --runs 10000 --seed 42

# 4. Generar SQL de seed para Supabase
python scripts/generate_seed_sql.py

# 5. Ejecutar los .sql en Supabase Dashboard → SQL Editor
#    data/seed_strengths.sql
#    data/seed_players.sql
#    data/seed_mc.sql
```

---

## Tablas Supabase

| Tabla | Filas | Descripción |
|-------|-------|-------------|
| `profiles` | dinámica | Usuarios registrados — `is_premium`, email |
| `premium_codes` | manual | Códigos hash SHA-256 para activación |
| `predictions` | manual | Pronósticos por partido (tabla legacy) |
| `players` | 1196 | Planteles: pos, nombre, edad, club, país, ELO, titular |
| `national_elo_ratings` | 48 | ELO internacional por selección |
| `team_strength_snapshots` | 48 | Fuerza compuesta (ELO híbrido v1.1) |
| `simulation_runs` | 1 | Metadatos del run: iteraciones, semilla, fecha |
| `simulation_group_standings` | 48 | Probabilidades de clasificación por equipo |
| `simulation_terceros_table` | 12 | Proyección de mejores terceros por grupo |

`national_elo_ratings` queda con lectura pública. Las tablas del motor premium
(`team_strength_snapshots`, `simulation_runs`, `simulation_group_standings`,
`players` y `simulation_terceros_table`, si existe) se endurecen con
`supabase/07_prediction_engine_rls_hardening.sql`: `authenticated` puede leer
solo si `profiles.is_premium = true`, `anon` no tiene acceso y `service_role`
mantiene permisos de carga.

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
- 26 selecciones disponibles al 6 de junio de 2026

---

## Estado del análisis

| Selección | Grupo | XI | Figura | Plantilla | ELO híbrido |
|-----------|-------|----|--------|-----------|-------------|
| Bosnia | B | ✅ | ✅ | ✅ 26 jugadores | ✅ |
| Suiza | B | ✅ | ✅ | ✅ 26 jugadores | ✅ |
| Suecia | F | ✅ | ✅ | ✅ 26 jugadores | ✅ |
| Corea del Sur | A | ✅ | ✅ | ✅ 26 jugadores | ✅ |
| Brasil | C | ✅ | ✅ | ✅ 26 jugadores | ✅ |
| Haití | C | ✅ | ✅ | ✅ 26 jugadores | ✅ |
| Escocia | C | ✅ | ✅ | ✅ 26 jugadores | ✅ |
| Costa de Marfil | E | ✅ | ✅ | ✅ 26 jugadores | ✅ |
| Bélgica | G | ✅ | ✅ | ✅ 26 jugadores | ✅ |
| Nueva Zelanda | G | ✅ | ✅ | ✅ 26 jugadores | ✅ |
| Cabo Verde | H | ✅ | ✅ | ✅ 26 jugadores | ✅ |
| Francia | I | ✅ | ✅ | ✅ 26 jugadores | ✅ |
| Austria | J | ✅ | ✅ | ✅ 26 jugadores | ✅ |
| Portugal | K | ✅ | ✅ | ✅ 26 jugadores | ✅ |
| RD del Congo | K | ✅ | ✅ | ✅ 26 jugadores | ✅ |
| Alemania | E | ✅ | ✅ | ✅ 26 jugadores | ✅ |
| Noruega | I | ✅ | ✅ | ✅ 26 jugadores | ✅ |
| Inglaterra | L | ✅ | ✅ | ✅ 26 jugadores | ✅ |
| España | H | ✅ | ✅ | ✅ 26 jugadores | ✅ |
| Colombia | K | ✅ | ✅ | ✅ 26 jugadores | ✅ |
| Japón | F | ✅ | ✅ | ✅ 26 jugadores | ✅ |
| Túnez | F | ✅ | ✅ | ✅ 26 jugadores | ✅ |
| Curazao | E | ✅ | ✅ | ✅ 26 jugadores | ✅ |
| Estados Unidos | D | ✅ | ✅ | ✅ 26 jugadores | ✅ |
| Marruecos | C | ✅ | ❌ | ✅ 26 jugadores (squad-only) | solo elo_intl |
| Panamá | L | ✅ | ❌ | ✅ 26 jugadores (squad-only) | solo elo_intl |
| Squad-only restantes (20) | varios | fuente remota | pendiente | ✅ 26 jugadores | solo elo_intl |
| Arabia Saudita / Jordania | H / J | ❌ | ❌ | ❌ sin artículo directo | solo elo_intl |

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
- [x] 24 selecciones con análisis táctico completo (XI, figura, plantilla)
- [x] 1196 jugadores en `teams.json`: 624 de análisis completo + 572 squad-only desde AlterFutbol
- [x] ELO internacional real de 48 selecciones (international-football.net)
- [x] Modelo ELO híbrido v1.1 (ranking intl + xi_blend de clubes, weight=0.35)
- [x] `team_strength_snapshots.json` — 48 selecciones con fuerza compuesta
- [x] Simulación Poisson Monte Carlo — 10,000 iteraciones, seed=42
- [x] Proyección tabla mejores terceros (12 grupos, criterios FIFA)
- [x] Motor de datos completo en Supabase (6 tablas, RLS, 1196+48+1+48+48+12 filas)
- [x] Sección "Predicciones" premium — 2 tablas (clasificación + mejores terceros)
- [x] Sección "Pronósticos" premium — análisis por partido (estructura lista)
- [x] Sistema de pago con QR Yape + PayPal (tabs interactivos)
- [x] Callback de confirmación de email con flujo de activación premium
- [x] SEO: Schema.org @graph, keywords, preconnects, sitemap daily, robots
- [x] GitHub Pages publicado con dominio alcamaster1290.github.io

### Pendiente 🔲

- [ ] Análisis táctico de Marruecos y Panamá (XI pendiente de AlterFutbol)
- [ ] Insertar predicciones reales en tabla `predictions` (pronósticos por partido)
- [ ] Actualizar `mc_results.json` cuando se añadan los 2 equipos pendientes
- [ ] Configurar templates de email de Supabase (confirmación, reset de contraseña)
- [ ] Sección interactiva de predicciones por partido (Pronósticos §06)
- [ ] Conectar `#predicciones` con Ruta Posible hasta octavos (banderas dinámicas)
- [ ] Comparador de ELO entre equipos del mismo grupo

---

*Datos actualizados al 6 de junio de 2026. Fuentes: AlterFutbol · worldclubratings.com · international-football.net · FIFA*
