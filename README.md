# Mundial 2026 — Predicciones y Análisis

Proyecto web para análisis táctico, ELO de clubes y predicciones del Mundial 2026 (Canadá · México · Estados Unidos).

Fuente de análisis: [AlterFutbol](https://alterfutbol.com) · ELO de clubes: [worldclubratings.com](http://worldclubratings.com/rankings/elo_men/)

**Sitio en vivo:** [https://alcamaster1290.github.io/prediccion-mundial-2026-elo/](https://alcamaster1290.github.io/prediccion-mundial-2026-elo/)

---

## Estructura del proyecto

```
mundial-2026/
│
├── index.html              # App principal (dark editorial, navegación por grupo)
├── .nojekyll               # GitHub Pages — deshabilita Jekyll
├── README.md
│
├── assets/
│   ├── flags/              # Banderas en SVG — código ISO 3166-1 alpha-3 (48 total)
│   ├── players/            # Foto de la figura clave — UNA por selección (23 total)
│   └── xi/                 # XI Ideal por selección — 1024×1024px PNG (26 total)
│
└── data/
    ├── teams.json          # Planteles con ELO por club (bih, kor completos)
    ├── groups.json         # Grupos A-L (sin D), fixtures y fechas oficiales FIFA
    └── match_context.json  # Matriz narrativa de los 72 partidos de fase de grupos
```

---

## Convenciones de nombres

### `assets/flags/`
- Código ISO 3166-1 **alpha-3** en minúsculas: `bih.svg`, `sui.svg`, `swe.svg`, `kor.svg`
- Fuente: [flagcdn.com](https://flagcdn.com)

### `assets/players/`
- Formato: `.jpg`, `.png` o `.webp`
- Una imagen por selección — la figura más reconocida o el mayor ELO de club
- Convención: `{cod}-{apellido}.{ext}` — excepciones ya en uso: `jap-` (Japón), `cur-` (Curazao)

| Equipo | Archivo | Jugador | Club |
|--------|---------|---------|------|
| Bosnia | `bih-dzeko.jpg` | Edin Džeko | Schalke 04 |
| Suiza | `sui-xhaka.webp` | Granit Xhaka | Sunderland |
| Suecia | `swe-gyokeres.jpg` | Viktor Gyökeres | Arsenal |
| Corea del Sur | `kor-son.jpg` | Son Heung-min | LAFC |
| Brasil | `bra-vinicius.webp` | Vinicius Jr. | Real Madrid |
| Haití | `hti-bellegarde.webp` | J.-R. Bellegarde | Wolverhampton |
| Escocia | `sco-mcginn.jpg` | John McGinn | Aston Villa |
| Costa de Marfil | `civ-adingra.jpg` | Simon Adingra | AS Monaco |
| Bélgica | `bel-debruyne.webp` | Kevin De Bruyne | Napoli |
| Nueva Zelanda | `nzl-wood.jpg` | Chris Wood | Nottingham Forest |
| Cabo Verde | `cpv-rodrigues.jpg` | Garry Rodrigues | Apollon Limassol |
| Francia | `fra-mbappe.webp` | Kylian Mbappé | Real Madrid |
| Austria | `aut-alaba.webp` | David Alaba | Real Madrid |
| Portugal | `por-ronaldo.jpg` | Cristiano Ronaldo | Al-Nassr |
| RD del Congo | `cod-mbemba.webp` | Chancel Mbemba | Lille |
| Alemania | `ger-wirtz.webp` | Florian Wirtz | Liverpool |
| Noruega | `nor-haaland.webp` | Erling Haaland | Manchester City |
| Inglaterra | `eng-kane.webp` | Harry Kane | Bayern München |
| España | `esp-yamal.png` | Lamine Yamal | FC Barcelona |
| Colombia | `col-diaz.webp` | Luis Díaz | Bayern Múnich |
| Japón | `jap-kubo.webp` | Takefusa Kubo | Real Sociedad |
| Túnez | `tun-mejbri.jpg` | Hannibal Mejbri | Burnley FC |
| Curazao | `cur-bacuna.jpg` | Leandro Bacuna | Idgir FK |

### `assets/xi/`
- Formato: `{código-equipo}-xi.png`
- Capturas de AlterFutbol — 1024×1024 px, mostradas en la sección de cada equipo

---

## Estructura de `data/match_context.json`

Matriz narrativa con los 72 partidos de la fase de grupos (12 grupos × 6 partidos).

```json
{
  "match_id": "grp-c-j1-bra-mar",
  "grupo": "C",
  "jornada": 1,
  "date": "2026-06-13",
  "venue": "Por confirmar",
  "team_a": "bra",
  "team_b": "mar",
  "team_a_context": {
    "sistema": "4-2-3-1",
    "figura": "Vinicius Jr.",
    "elo_intl": 1836,
    "incentivo_competitivo": "Brasil favorito absoluto del grupo...",
    "ausencias_clave": ["Gabigol (no convocado)"],
    "amenaza_principal": "Vinicius Jr. + Raphinha en extremos"
  },
  "team_b_context": { "..." : "..." },
  "prediccion_narrativa": "...",
  "resultado_predicho": "2-0",
  "confianza": "media"
}
```

---

## Paleta de colores por grupo

| Grupo | Variable CSS | Hex |
|-------|-------------|-----|
| A | `--grp-a` | `#e55c5c` |
| B | `--grp-b` | `#3b8beb` |
| C | `--grp-c` | `#10b981` |
| E | `--grp-e` | `#f97316` |
| F | `--grp-f` | `#f59e0b` |
| G | `--grp-g` | `#8b5cf6` |
| H | `--grp-h` | `#ec4899` |
| I | `--grp-i` | `#06b6d4` |
| J | `--grp-j` | `#84cc16` |
| K | `--grp-k` | `#d97706` |
| L | `--grp-l` | `#94a3b8` |

---

## Estado del análisis

| Selección | Grupo | XI visible | Titulares | Análisis táctico |
|-----------|-------|-----------|-----------|-----------------|
| Bosnia | B | ✅ | ✅ 11 titulares | ✅ |
| Suiza | B | ✅ | ✅ 11 titulares | ✅ |
| Suecia | F | ✅ | ✅ 11 titulares | ✅ |
| Corea del Sur | A | ✅ | ✅ 11 titulares | ✅ |
| Brasil | C | ✅ | ✅ 11 titulares | ✅ |
| Haití | C | ✅ | ✅ 11 titulares | ✅ |
| Escocia | C | ✅ | ✅ 11 titulares | ✅ |
| Costa de Marfil | E | ✅ | ✅ 11 titulares | ✅ |
| Bélgica | G | ✅ | ✅ 12 titulares* | ✅ |
| Nueva Zelanda | G | ✅ | ✅ 11 titulares | ✅ |
| Cabo Verde | H | ✅ | ✅ 11 titulares | ✅ |
| Francia | I | ✅ | ✅ 11 titulares | ✅ |
| Austria | J | ✅ | ✅ 10 titulares** | ✅ |
| Portugal | K | ✅ | ✅ 11 titulares | ✅ |
| RD del Congo | K | ✅ | ✅ 11 titulares | ✅ |
| Alemania | E | ✅ | ✅ 11 titulares | ✅ |
| Noruega | I | ✅ | ✅ 11 titulares | ✅ |
| Inglaterra | L | ✅ | ✅ 11 titulares | ✅ |
| España | H | ✅ | ✅ 11 titulares | ✅ |
| Colombia | K | ✅ | ✅ 11 titulares | ✅ |
| Japón | F | ✅ | ✅ 11 titulares | ✅ |
| Túnez | F | ✅ | ✅ 11 titulares | ✅ |
| Curazao | E | ✅ | ✅ 11 titulares | ✅ |

\* El XI publicado muestra dos opciones para una posición (Lukaku / De Ketelaere)
\*\* Un jugador del XI publicado no figura en la lista oficial de convocados

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

---

## Roadmap

- [x] Descargar 48 banderas SVG (todos los grupos A-L)
- [x] Analizar 18 selecciones con táctica, ausencias y ELO de clubes
- [x] Cargar XI Ideal y jugador estrella para las 18 selecciones
- [x] Columna Titular marcada en cada plantel (sí/no)
- [x] Mostrar imagen del XI probable en la sección de cada equipo
- [x] `match_context.json` — matriz narrativa de los 72 partidos de fase de grupos
- [x] Publicar en GitHub Pages
- [x] Tablas de plantel ordenadas: GK→DEF→MED→DEL, titular primero, ELO desc.
- [x] Mobile: tablas de convocados expandibles (accordion ≤600px, sin scroll horizontal)
- [x] Convocatorias pendientes (carga manual): jpn, tun, cuw
- [ ] Análisis pendientes (XI preparado, falta sección): usa, mar, pan
- [ ] Convocatorias pendientes (sin publicar aún): mex, zaf, cze, can, qat, ecu, ned, egy, irn, ksa, ury, sen, irq, arg, alg, jor, uzb, cro, gha, pry, aus, tur
- [ ] Sección interactiva de predicciones por partido
- [ ] Comparador de ELO entre equipos del mismo grupo

---

*Datos actualizados al 1 de junio de 2026. Fuentes: AlterFutbol · worldclubratings.com · FIFA*

---

## Sistema Premium — Pronósticos Fase de Grupos

### Por qué Supabase + GitHub Pages

El sitio sigue siendo 100% estático en GitHub Pages (no hay servidor propio). La autenticación y los datos premium los gestiona Supabase, que actúa como backend-as-a-service. Esta arquitectura permite:

- **Costo cero** de hosting para el frontend
- **Seguridad real** via Row Level Security (RLS) en PostgreSQL
- **Sin mantenimiento** de servidores propios
- **Escalabilidad** automática si el tráfico crece

### Por qué RLS es suficiente como capa de seguridad

La `anon key` de Supabase puede estar en el frontend porque:
1. RLS garantiza que cada usuario solo lee lo que le corresponde
2. La tabla `premium_codes` no tiene política SELECT pública — nadie puede leerla
3. `redeem_premium_code` es una función RPC `SECURITY DEFINER` — bypass controlado de RLS
4. Las predicciones premium solo son accesibles si `profiles.is_premium = true`

**NUNCA coloques la `service_role key` en el frontend.** Solo pertenece al dashboard de Supabase.

### Configurar Supabase

1. Crear proyecto en [supabase.com](https://supabase.com)
2. Ir a **Settings → API** y copiar:
   - `Project URL` → `SUPABASE_URL`
   - `anon public` key → `SUPABASE_ANON_KEY`
3. Copiar `js/config.example.js` como `js/config.js` y rellenar las credenciales
4. Ejecutar los SQL en **Supabase Dashboard → SQL Editor** en orden:
   ```
   supabase/01_schema.sql
   supabase/02_rls.sql
   supabase/03_functions.sql
   ```

### Crear códigos premium manualmente

1. Decidir el código en texto plano (ej: `WWCJUN2026-JUAN`)
2. En Supabase SQL Editor:
   ```sql
   INSERT INTO public.premium_codes (code_hash, notes)
   VALUES (
     encode(digest('WWCJUN2026-JUAN', 'sha256'), 'hex'),
     'Pago Yape S/15 - Juan Pérez - 1 jun 2026'
   );
   ```
3. Enviar el código en texto plano al usuario por email
4. **Nunca almacenar el código en texto plano** en ningún sistema

### Validar que un usuario es premium

```sql
SELECT id, email, is_premium, updated_at
FROM public.profiles
WHERE is_premium = true;
```

### Cómo probar localmente

```bash
python3 -m http.server 8080
# o
npx serve .
```
Abrir `http://localhost:8080`. Sin `config.js` real, la sección premium mostrará estado de "demo activo" y vista locked.

### Qué falta para producción

- [ ] Configurar Supabase email templates (confirmación, reset de contraseña)
- [ ] Habilitar confirmación de email en Supabase Auth settings
- [ ] Insertar predicciones reales en la tabla `predictions` (con `published = true`)
- [ ] Configurar dominio personalizado (opcional)
- [ ] Activar protección rate-limit en la RPC (Supabase lo gestiona por plan)
