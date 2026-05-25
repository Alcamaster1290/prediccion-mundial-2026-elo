# Instrucciones para Claude Code — prediccion-mundial-2026-elo

Este documento guía a Claude Code en las tareas del proyecto. Léelo completo antes de ejecutar cualquier acción.

---

## Contexto del proyecto

Aplicación web de análisis táctico y predicciones para el Mundial 2026.
- Stack: HTML + CSS + JS vanilla (sin frameworks ni build step)
- El CSS y la mayoría del JS están **inline en `index.html`**; el sistema premium usa módulos JS separados en `js/`
- Fuente de análisis: [AlterFutbol](https://alterfutbol.com)
- Fuente de ELO de clubes: [worldclubratings.com](http://worldclubratings.com/rankings/elo_men/)
- Fuente de convocatorias nuevas: [alterfutbol.com/tag/convocatorias-al-mundial-2026/](https://alterfutbol.com/tag/convocatorias-al-mundial-2026/)

### Estado global (al 23 mayo 2026)
- **18 selecciones analizadas** con plantel, táctica, figura clave y XI probable
- **3 selecciones con convocatoria anunciada — carga manual pendiente:** Japón (15 may), Túnez (15 may), Curazao (18 may)
- **27 selecciones** aún sin convocatoria oficial
- **Sistema Premium añadido:** sección §06, Supabase Auth, flujo de pago manual

---

## Tarea 1 — Imagen del jugador estrella (`assets/players/`)

### Convención de nombres
`{código-equipo}-{apellido}.jpg`

### Estado actual (18 imágenes disponibles ✅)

| Archivo | Jugador | Selección |
|---|---|---|
| `bih-dzeko.jpg` | Edin Džeko | Bosnia |
| `sui-xhaka.webp` | Granit Xhaka | Suiza |
| `swe-gyokeres.jpg` | Viktor Gyökeres | Suecia |
| `kor-son.jpg` | Son Heung-min | Corea del Sur |
| `bra-vinicius.webp` | Vinicius Jr. | Brasil |
| `hti-bellegarde.webp` | J.-R. Bellegarde | Haití |
| `sco-mcginn.jpg` | John McGinn | Escocia |
| `civ-adingra.jpg` | Simon Adingra | Costa de Marfil |
| `bel-debruyne.webp` | Kevin De Bruyne | Bélgica |
| `nzl-wood.jpg` | Chris Wood | Nueva Zelanda |
| `cpv-rodrigues.jpg` | Garry Rodrigues | Cabo Verde |
| `fra-mbappe.webp` | Kylian Mbappé | Francia |
| `aut-alaba.webp` | David Alaba | Austria |
| `por-ronaldo.jpg` | Cristiano Ronaldo | Portugal |
| `cod-mbemba.webp` | Chancel Mbemba | RD del Congo |
| `ger-wirtz.webp` | Florian Wirtz | Alemania |
| `nor-haaland.webp` | Erling Haaland | Noruega |
| `eng-kane.webp` | Harry Kane | Inglaterra |

### Especificaciones técnicas
- Formato: `.jpg` o `.webp` (ambos válidos — usar el que esté disponible)
- Resolución mínima: **400 × 500 px** (portrait, cabeza y hombros)
- El CSS ya usa `object-fit: cover; object-position: top center`
- La tarjeta usa `onerror` para mostrar iniciales si no hay imagen

---

## Tarea 2 — Imagen del XI Probable (`assets/xi/`)

### Convención de nombres
`{código-equipo}-xi.png`

### Estado actual (18 imágenes disponibles ✅)

Todas las selecciones analizadas tienen su imagen en `assets/xi/`. La imagen se muestra dentro de `.xi-img-wrap` **antes de la tabla de plantel** en cada sección.

> **Nota:** El bloque de texto de la formación (`.xi-row`) fue eliminado del HTML en mayo 2026. Solo se muestra la **imagen** del XI probable — no el texto con posiciones.

### Estado de la columna Titular (al 22 mayo 2026)

| Selección | `titl-yes` | Nota |
|---|---|---|
| Corea del Sur | 11 | ✅ completo |
| Bosnia | 11 | ✅ completo |
| Suiza | 11 | ✅ completo |
| Brasil | 11 | ✅ completo |
| Haití | 11 | ✅ completo |
| Escocia | 11 | ✅ completo |
| Costa de Marfil | 11 | ✅ completo (Yan Diomandé y Ange-Yoan Bonny añadidos — #24 y #25) |
| Suecia | 11 | ✅ completo |
| Bélgica | 12 | ⚠️ AlterFutbol presenta doble opción en el #9: Lukaku / De Ketelaere |
| Nueva Zelanda | 11 | ✅ completo |
| Cabo Verde | 11 | ✅ completo |
| Francia | 11 | ✅ completo |
| Austria | 10 | ✅ completo (Marko Arnautovic añadido — #24, Titular) |
| Portugal | 11 | ✅ completo |
| RD del Congo | 11 | ✅ completo (Yoane Wissa y Cédric Bakambu añadidos — #24 y #23, Titulares) |
| Alemania | 11 | ✅ completo |
| Noruega | 11 | ✅ completo |
| Inglaterra | 11 | ✅ completo · Pickford, James, Guéhi, Stones, Livramento, Rice, Mainoo, Saka, Bellingham, Rashford, Kane |

> La columna Titular se rellena usando el XI de AlterFutbol como referencia. Si un jugador del XI no aparece en la lista de convocados → no se puede marcar, el conteo queda por debajo de 11.

### Cómo obtener la imagen para un equipo nuevo
1. Ir al artículo de AlterFutbol correspondiente (ver Tarea 3)
2. Localizar la imagen del XI Ideal (camisetas sobre campo, fondo oscuro con logo de AlterFutbol)
3. Descargar o capturar pantalla y recortar al área del XI
4. Guardar como PNG en `assets/xi/{código}-xi.png`
5. Resolución mínima recomendada: **800 × 900 px**

---

## Tarea 3 — Publicaciones de AlterFutbol por selección

### Selecciones ya analizadas (18)

| Selección | URL |
|---|---|
| 🇧🇦 Bosnia | https://www.alterfutbol.com/europa/bosnia/bosnia-dio-la-primera-lista-del-mundial-2026-los-convocados-y-el-analisis-tactico/ |
| 🇨🇭 Suiza | https://www.alterfutbol.com/europa/suiza/suiza-confirmo-sus-26-convocados-para-el-mundial/ |
| 🇸🇪 Suecia | https://www.alterfutbol.com/europa/suecia/suecia-confirmo-sus-convocados-para-el-mundial-analisis-tactico-y-ausencias-notables-en-la-lista-de-graham-potter/ |
| 🇰🇷 Corea del Sur | https://www.alterfutbol.com/asia/corea-del-sur/corea-del-sur-confirmo-sus-26-convocados-para-el-mundial-2026-analisis-historia-y-mejores-jugadores/ |
| 🇧🇷 Brasil | https://www.alterfutbol.com/sudamerica/brasil/brasil-anuncio-los-convocados-para-el-mundial-2026-la-sorpresa-de-neymar-y-las-principales-ausencias/ |
| 🇭🇹 Haití | https://www.alterfutbol.com/concacaf/haiti/haiti-confirmo-sus-26-convocados-para-el-mundial-2026-analisis-su-historia-y-mejores-jugadores/ |
| 🏴󠁧󠁢󠁳󠁣󠁴󠁿 Escocia | https://www.alterfutbol.com/europa/escocia/escocia-anuncio-sus-convocados-al-mundial-2026-lista-ausencias-y-analisis-tactico/ |
| 🇨🇮 Costa de Marfil | https://www.alterfutbol.com/africa/costa-de-marfil/costa-de-marfil-confirmo-su-lista-de-convocados-al-mundial-2026/ |
| 🇧🇪 Bélgica | https://www.alterfutbol.com/europa/belgica/belgica-anuncio-sus-convocados-para-el-mundial/ |
| 🇳🇿 Nueva Zelanda | https://www.alterfutbol.com/oceania/nueva-zelanda/nueva-zelanda-anuncio-sus-convocados-para-el-mundial-2026-analisis-tactico-y-la-lista-completa/ |
| 🇨🇻 Cabo Verde | https://www.alterfutbol.com/otras-noticias/cabo-verde-anuncio-sus-26-convocados-para-el-mundial-2026-analisis-como-juegan-y-su-historia/ |
| 🇫🇷 Francia | https://www.alterfutbol.com/europa/francia/francia-convocados-mundial-2026/ |
| 🇦🇹 Austria | https://www.alterfutbol.com/europa/austria/austria-confirmo-sus-convocados-para-el-mundial-2026-analisis-tactico-mejores-jugadores-y-lo-que-hay-que-saber/ |
| 🇵🇹 Portugal | https://www.alterfutbol.com/europa/portugal/portugal-confirmo-sus-convocados-para-el-mundial-2026/ |
| 🇨🇩 RD del Congo | https://www.alterfutbol.com/africa/republica-democratica-del-congo/rd-congo-confirmo-sus-26-convocados-para-el-mundial-2026-analisis-su-historia-y-mejores-jugadores/ |
| 🇩🇪 Alemania | https://www.alterfutbol.com/europa/alemania/ |
| 🇳🇴 Noruega | https://www.alterfutbol.com/europa/noruega/ |
| 🏴󠁧󠁢󠁥󠁮󠁧󠁿 Inglaterra | https://www.alterfutbol.com/europa/inglaterra/con-sorpresas-y-ausencias-inglaterra-anuncio-sus-convocados-al-mundial/ |

### Noticias generales del torneo
| Tema | URL |
|---|---|
| Todas las convocatorias al Mundial 2026 | https://www.alterfutbol.com/tag/convocatorias-al-mundial-2026/ |
| Noticias AlterFutbol | https://www.alterfutbol.com/noticias/ |

---

## Tarea 4 — Añadir una nueva convocatoria al sitio

Cuando haya una nueva convocatoria lista para analizar, seguir este flujo exacto:

### Paso 0 — Verificar si hay enlace disponible

**Si se recibe URL de AlterFutbol:** continuar con el Paso 1 normalmente.

**Si NO hay URL disponible (carga manual):** NO proceder con el análisis completo. En su lugar:
1. Confirmar qué archivos faltan para poder cargar:
   - Resumen de la convocatoria (lista de jugadores, DT, sistema, figura clave, ausencias)
   - Imagen del XI Probable → `assets/xi/{código}-xi.png`
   - Imagen del jugador estrella → `assets/players/{código}-{apellido}.jpg`
2. Actualizar la cronología §05 y la sección de pendientes en `index.html` con la fecha de anuncio conocida y badge `⏳ Carga manual`.
3. Esperar a que el usuario proporcione los archivos necesarios antes de completar el Paso 1 en adelante.

> **Selecciones con carga manual pendiente (al 23 mayo 2026):**
> - 🇯🇵 Japón — anunciada el 15 may 2026
> - 🇹🇳 Túnez — anunciada el 15 may 2026
> - 🇨🇼 Curazao — anunciada el 18 may 2026

---

### Paso 1 — Leer el artículo de AlterFutbol
- Plantilla completa (número, posición, jugador, edad, club)
- Sistema de juego y descripción táctica
- Figura clave y sus datos (club, ELO)
- Ausencias y dudas relevantes
- Dato histórico o de color si lo hay

### Paso 2 — Obtener assets
1. Imagen del XI Probable → `assets/xi/{código}-xi.png`
2. Imagen del jugador estrella → `assets/players/{código}-{apellido}.jpg`
3. Bandera SVG (si no existe) → `assets/flags/{código}.svg` desde flagcdn.com

### Paso 3 — Añadir sección en `index.html`

Copiar la estructura de un equipo existente (por ejemplo Bosnia o Francia) y adaptarla. La estructura de cada `team-section` es:

```html
<div class="team-section" id="{id-sin-tildes}">
  <div class="team-header">
    <div class="team-flag-big">
      <img src="assets/flags/{código}.svg" alt="{Nombre}" loading="lazy">
    </div>
    <div>
      <div class="team-name">{Nombre completo}</div>
      <div class="team-sub">DT: {Técnico} · Grupo {X}</div>
      <div class="team-pills">
        <span class="team-pill" style="color:var(--accent);border-color:var(--accent)">{Formación}</span>
        <span class="team-pill" style="color:var(--grp-{x});border-color:var(--grp-{x})">Grupo {X}</span>
      </div>
    </div>
    <div class="star-card" style="--sc:var(--grp-{x})">
      <div class="star-img-wrap">
        <img src="assets/players/{código}-{apellido}.jpg" alt="{Jugador}" loading="lazy"
             onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">
        <div class="star-placeholder">{Iniciales}</div>
      </div>
      <div class="star-info">
        <div class="star-label">Figura clave</div>
        <div class="star-name">{Nombre jugador}</div>
        <div class="star-meta">{Club}</div>
        <span class="elo-cell" style="font-size:11px;font-family:'JetBrains Mono',monospace">ELO {valor}</span>
      </div>
    </div>
  </div>

  <div class="two-col">
    <div class="info-card">
      <h4>Sistema de juego</h4>
      <p class="tactic-prose">{Texto de análisis en prosa corrida. Sin bullets, sin guiones, sin flechas.
      Incluir: sistema base, roles clave, fortalezas, debilidades y dato de contexto.}</p>
    </div>
    <div class="info-card">
      <h4>Dudas y novedades</h4>
      <ul class="absence-list">
        <li>
          <span class="absence-name">{Jugador (estado)}</span><br>
          <span class="absence-reason">{Razón o contexto}</span>
        </li>
      </ul>
    </div>
  </div>

  <div class="xi-img-wrap">
    <div class="xi-img-label">XI Probable · {Nombre}</div>
    <img src="assets/xi/{código}-xi.png" alt="XI Ideal {Nombre}" loading="lazy" class="xi-img">
  </div>

  <div class="squad-wrap">
    <table class="squad-table">
      <thead>
        <tr><th>#</th><th>Pos</th><th>Jugador</th><th>Edad</th><th>Club</th><th>País</th><th>ELO</th><th>Titular</th></tr>
      </thead>
      <tbody>
        <!-- Una fila por jugador: -->
        <tr>
          <td style="color:var(--muted);font-size:12px">{#}</td>
          <td><span class="pos-badge pos-{gk|def|med|del}">{GK|DEF|MED|DEL}</span></td>
          <td class="player-name">{Nombre} <span class="captain-star">★</span></td>
          <td style="color:var(--muted)">{Edad}</td>
          <td style="font-size:13px">{Club}</td>
          <td style="font-size:12px;color:var(--muted)">{País del club}</td>
          <td class="elo-cell">{ELO o N/D}</td>
          <td><span class="titl-yes">Sí</span></td>   <!-- o titl-pending para — -->
        </tr>
      </tbody>
    </table>
  </div>
  <div class="nd-note">{Nota sobre ligas sin ELO, si aplica}</div>
</div>
```

> **Sistema de juego — formato de prosa:**
> Escribir un único párrafo `<p class="tactic-prose">` con el análisis táctico completo.
> **No usar** `<ul>`, bullets, flechas `→`, guiones como marcadores ni dos puntos como separadores visuales.
> Ejemplo correcto: *"Sistema 4-3-3 con presión alta y verticalidad. Xhaka es el eje organizador..."*

### Paso 4 — Actualizar los 9 lugares del HTML

Todos están en `index.html`. Tocarlos en este orden para no perder ninguno:

#### 4a · Modal de grupos §03 — hacer el equipo clickable
Buscar el bloque `<!-- {LETRA} -->` dentro de `<div class="grupos-modal-body">`.
Cambiar el `<div class="gmod-team">` del equipo analizado por un enlace con dot verde:
```html
<!-- ANTES -->
<div class="gmod-team" data-name="{Nombre}">
  <img src="assets/flags/{código}.svg" alt=""><span class="gmod-name">{Nombre}</span>
</div>

<!-- DESPUÉS -->
<a class="gmod-team has-analysis" data-name="{Nombre}" href="#{id-seccion}">
  <img src="assets/flags/{código}.svg" alt=""><span class="gmod-name">{Nombre}</span>
  <span class="gmod-ana"></span>
</a>
```

#### 4b · Cards de grupos §03 — marcar como analizado
Buscar el `<div class="group-card">` del Grupo {X} en la sección `<div class="groups-grid">` de §03.
```html
<!-- ANTES -->
<div class="group-card">
  <div class="group-label"><span class="group-dot"></span> Grupo {X}</div>
  <ul class="group-teams">
    <li><img ...> {Equipo}</li>

<!-- DESPUÉS — añadir border-color, color en label, link + badge en el equipo -->
<div class="group-card" style="border-color:rgba({r},{g},{b},.2)">
  <div class="group-label" style="color:var(--grp-{x})">
    <span class="group-dot" style="background:var(--grp-{x})"></span> Grupo {X} — 1/4 analizado
  </div>
  <ul class="group-teams">
    <li>
      <a href="#{id-seccion}" class="group-team-link"><img ...> {Equipo}</a>
      <span class="analyzed-badge">✓</span>
    </li>
```
> Si ya había otro equipo analizado en el mismo grupo, incrementar el contador: "2/4 analizado", etc.

#### 4c · Sección del grupo — reemplazar pending-card por team-section
En `<!-- ═══════ GRUPO {X} ═══════ -->`, localizar el `<div class="pending-card">` del equipo.
Reemplazarlo con el bloque `<div class="team-section" id="{id-seccion}">` completo (ver Paso 3).
Dejar los `pending-card` de los equipos del grupo que aún no tienen análisis.

#### 4d · TEAM_CODES en JS — habilitar fixtures automáticos
Buscar `var TEAM_CODES = {` dentro del bloque `// ── CALENDAR ──`.
Añadir la entrada del equipo nuevo:
```js
var TEAM_CODES = {
  // ... entradas existentes ...
  '{id-seccion}': '{código-3-letras}'
};
```
Esto hace que `renderTeamFixtures()` pinte automáticamente los 3 partidos de grupos con click-CTA.

#### 4e · Tabla del tracker §05 — añadir fila
En `<table class="squad-table">` dentro de `id="tracker"`, añadir fila en el grupo correspondiente:
```html
<tr>
  <td rowspan="1"><strong style="color:var(--grp-{x})">{X}</strong><br>
    <span style="font-size:11px;color:var(--muted)">{COD1}·{COD2}<br>{COD3}·{COD4}</span></td>
  <td><img class="flag-svg" src="assets/flags/{código}.svg" loading="lazy">
    <strong class="player-name">{Nombre}</strong></td>
  <td style="font-size:13px">{DT}</td>
  <td><span class="team-pill tp-scheme" style="font-size:11px;padding:.1rem .5rem">{Sistema}</span></td>
  <td style="font-size:13px">{Figura clave y club}</td>
  <td style="font-size:12px;color:var(--muted)">{Dato destacado del equipo}</td>
  <td><span class="analyzed-badge">✓ Detallado</span></td>
</tr>
```
> Si el grupo ya tiene filas (`rowspan`), omitir la celda `<td rowspan>` y ajustar el rowspan existente.

#### 4f · Cronología §05 — añadir entrada de fecha
En `<!-- Timeline publicación -->`, añadir un bloque nuevo en orden cronológico:
```html
<div style="display:flex;align-items:center;gap:1rem;padding:.75rem 1rem;background:var(--card);border-radius:8px;border-left:3px solid var(--border)">
  <span style="font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--muted);min-width:80px">{DD} {Mes}</span>
  <img class="flag-svg" src="assets/flags/{código}.svg" loading="lazy">
  <span style="font-size:13px"><strong style="color:var(--white)">{Nombre}</strong></span>
  <span class="analyzed-badge" style="margin-left:auto">✓ Detallado</span>
</div>
```
> Si varias selecciones se anunciaron el mismo día, incluirlas en un solo bloque con todas las banderas juntas (ver ejemplo del 15 May con Bélgica · Costa de Marfil · Haití).
> Cambiar `border-left: 3px solid var(--border)` a `var(--accent)` solo si es la fecha más reciente.

#### 4g · Contadores §05 — actualizar 4 cifras
En `<div class="format-grid">` dentro de `id="tracker"`:
- **Listas publicadas en AlterFutbol**: +1
- **Grupos con al menos una lista**: +1 solo si es el primer equipo de ese grupo
- **Selecciones sin publicar**: -1
- **Con análisis completo**: +1 (siempre es igual a "Listas publicadas")

#### 4h · Texto intro §05 — actualizar descripción
El párrafo debajo del `<h2>Tracker de Convocatorias</h2>`:
- Actualizar el número total de selecciones
- Actualizar la fecha más reciente si corresponde (ej: "22 mayo" → "23 mayo")
- Mantener el formato: `{N} selecciones han publicado... entre el {fecha inicio} y el {fecha más reciente}`

#### 4i · Pendientes §05 — actualizar card del grupo
En `<!-- Selecciones pendientes por grupo -->` (`.groups-grid` al final del tracker):
- Si el grupo pasa de 0 a 1 analizado: cambiar label a "X/4 analizado", añadir `border-color` y `color` del grupo, listar solo los equipos que aún faltan con `<em>(listas pendientes)</em>`
- Si ya tenía analizados: incrementar el contador del label

### Paso 5 — Actualizar INSTRUCTIONS.md
- **Tarea 1**: añadir fila a la tabla de imágenes de jugadores (o marcar ✅ si estaba pendiente)
- **Tarea 2**: añadir fila a la tabla de XI titulares con el conteo de `titl-yes`
- **Tarea 3**: añadir URL del artículo; cambiar "(N)" del encabezado a N+1
- **Estado global**: actualizar los contadores de selecciones analizadas y pendientes
- **Selecciones pendientes**: eliminar el equipo de la lista

### Paso 6 — Commit y push
```bash
git add assets/ index.html claude/INSTRUCTIONS.md
git commit -m "feat: add {Selección} ({Grupo}) — convocatoria {DT} WC2026"
git push
```

---

## Selecciones pendientes (al 23 mayo 2026)

### Con convocatoria anunciada — carga manual pendiente (sin enlace disponible)
| Selección | Fecha anuncio | Archivos necesarios |
|---|---|---|
| 🇯🇵 Japón | 15 may 2026 | Resumen lista · `jpn-xi.png` · `jpn-{apellido}.jpg` |
| 🇹🇳 Túnez | 15 may 2026 | Resumen lista · `tun-xi.png` · `tun-{apellido}.jpg` |
| 🇨🇼 Curazao | 18 may 2026 | Resumen lista · `cuw-xi.png` · `cuw-{apellido}.jpg` |

### Sin convocatoria oficial publicada aún
Grupo D completo (USA, Paraguay, Australia, Turquía) · Canadá · Qatar · Marruecos · Países Bajos · Egipto · Irán · España · Arabia Saudita · Uruguay · Senegal · Irak · Argentina · Argelia · Jordania · Uzbekistán · Colombia · Croacia · Ghana · Panamá · Ecuador · México · Sudáfrica · Chequia

---

## Reglas de seguridad — sistema premium

- **Nunca incluir** la `service_role key` de Supabase en ningún archivo del repositorio
- `js/config.js` contiene solo la **anon key** (pública y segura) — está commiteado intencionalmente
- **Nunca colocar** contenido premium real en `data/*.json` públicos
- `supabase/04_admin_codes.sql` no debe contener códigos en texto plano
- La `service_role key` de Supabase **nunca** va en el frontend — solo en el dashboard

---

## Reglas generales para Claude Code

- **No modificar** los colores CSS por grupo (`--grp-a` … `--grp-l`) — son identidad de cada grupo
- **No cambiar** los `id` de los team-sections — se usan para la nav y los scripts
- **No usar** listas con bullets, flechas `→` ni dos puntos como marcadores en la sección táctica — solo prosa en `<p class="tactic-prose">`
- El ELO de clubes debe provenir de `worldclubratings.com` — no inventar valores
- Ligas sin ELO rankeado → usar `N/D` con clase `elo-nd` y añadir nota al pie en `.nd-note`
- La columna `Titular` se rellena usando la imagen del XI probable como referencia: `titl-yes` para titulares confirmados, `titl-pending` (`—`) para el resto
- Scripts Python de transformación → eliminar después de ejecutar (no commitear)
- El toggle light/dark guarda la preferencia en `localStorage` — no tocar esa lógica

---

## Estructura de carpetas

```
prediccion-mundial-2026-elo/
├── index.html              ← toda la app (HTML + CSS inline + JS inline)
├── README.md
├── .nojekyll               ← GitHub Pages: deshabilita Jekyll
├── claude/
│   └── INSTRUCTIONS.md    ← este archivo
├── js/
│   ├── config.example.js  ← template de credenciales Supabase (committeable)
│   ├── config.js          ← credenciales reales (GITIGNOREADO — no committear)
│   ├── auth.js            ← cliente Supabase, modal auth, estado de sesión
│   └── premium.js         ← sección premium, cards, canje de código
├── supabase/
│   ├── 01_schema.sql      ← tablas: profiles, premium_codes, predictions
│   ├── 02_rls.sql         ← Row Level Security
│   ├── 03_functions.sql   ← RPC redeem_premium_code + trigger
│   └── 04_admin_codes.sql ← snippets para gestionar códigos manualmente
├── docs/
│   └── supabase-premium.md ← referencia técnica del sistema premium
├── assets/
│   ├── flags/             ← {código}.svg  (48 banderas, ISO 3166-1 alpha-3)
│   ├── players/           ← {código}-{apellido}.jpg  (1 por equipo analizado)
│   └── xi/                ← {código}-xi.png  (XI probable de AlterFutbol)
└── data/
    ├── teams.json          ← planteles con ELO por club
    ├── groups.json         ← grupos A-L, fixtures y fechas
    ├── match_context.json  ← narrativa táctica de los 72 partidos de grupos
    └── predictions.mock.json ← mock para desarrollo local (no fuente real)
```
