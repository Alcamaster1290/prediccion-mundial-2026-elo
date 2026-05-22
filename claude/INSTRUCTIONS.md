# Instrucciones para Claude Code — prediccion-mundial-2026-elo

Este documento guía a Claude Code en las tareas del proyecto. Léelo completo antes de ejecutar cualquier acción.

---

## Contexto del proyecto

Aplicación web de análisis táctico y predicciones para el Mundial 2026.
- Stack: HTML + CSS + JS vanilla (sin frameworks ni build step)
- Todo el CSS y JS está **inline en `index.html`** — no existen `css/` ni `js/` por separado
- Fuente de análisis: [AlterFutbol](https://alterfutbol.com)
- Fuente de ELO de clubes: [worldclubratings.com](http://worldclubratings.com/rankings/elo_men/)
- Fuente de convocatorias nuevas: [alterfutbol.com/tag/convocatorias-al-mundial-2026/](https://alterfutbol.com/tag/convocatorias-al-mundial-2026/)

### Estado global (al 22 mayo 2026)
- **17 selecciones analizadas** con plantel, táctica, figura clave y XI probable
- **Más de 25 selecciones** aún sin convocatoria oficial

---

## Tarea 1 — Imagen del jugador estrella (`assets/players/`)

### Convención de nombres
`{código-equipo}-{apellido}.jpg`

### Estado actual (17 imágenes disponibles ✅)

| Archivo | Jugador | Selección |
|---|---|---|
| `bih-dzeko.jpg` | Edin Džeko | Bosnia |
| `sui-xhaka.jpg` | Granit Xhaka | Suiza |
| `swe-gyokeres.jpg` | Viktor Gyökeres | Suecia |
| `kor-son.jpg` | Son Heung-min | Corea del Sur |
| `bra-vinicius.jpg` | Vinicius Jr. | Brasil |
| `hti-bellegarde.jpg` | J.-R. Bellegarde | Haití |
| `sco-mcginn.jpg` | John McGinn | Escocia |
| `civ-adingra.jpg` | Simon Adingra | Costa de Marfil |
| `bel-debruyne.jpg` | Kevin De Bruyne | Bélgica |
| `nzl-wood.jpg` | Chris Wood | Nueva Zelanda |
| `cpv-rodrigues.jpg` | Garry Rodrigues | Cabo Verde |
| `fra-mbappe.jpg` | Kylian Mbappé | Francia |
| `aut-alaba.jpg` | David Alaba | Austria |
| `por-ronaldo.jpg` | Cristiano Ronaldo | Portugal |
| `cod-mbemba.jpg` | Chancel Mbemba | RD del Congo |
| `ger-wirtz.jpg` | Florian Wirtz | Alemania |
| `nor-haaland.jpg` | Erling Haaland | Noruega |

### Especificaciones técnicas
- Formato: `.jpg` o `.webp` (renombrar si es necesario)
- Resolución mínima: **400 × 500 px** (portrait, cabeza y hombros)
- El CSS ya usa `object-fit: cover; object-position: top center`
- La tarjeta usa `onerror` para mostrar iniciales si no hay imagen

---

## Tarea 2 — Imagen del XI Probable (`assets/xi/`)

### Convención de nombres
`{código-equipo}-xi.png`

### Estado actual (17 imágenes disponibles ✅)

Todas las selecciones analizadas tienen su imagen en `assets/xi/`. La imagen se muestra dentro de `.xi-img-wrap` **antes de la tabla de plantel** en cada sección.

> **Nota:** El bloque de texto de la formación (`.xi-row`) fue eliminado del HTML en mayo 2026. Solo se muestra la **imagen** del XI probable — no el texto con posiciones.

### Estado de la columna Titular (al 21 mayo 2026)

| Selección | `titl-yes` | Nota |
|---|---|---|
| Corea del Sur | 11 | ✅ completo |
| Bosnia | 11 | ✅ completo |
| Suiza | 11 | ✅ completo |
| Brasil | 11 | ✅ completo |
| Haití | 11 | ✅ completo |
| Escocia | 11 | ✅ completo |
| Costa de Marfil | 9 | ⚠️ Yan Diomandé y Ange-Yoan Bonny (XI) no figuran en la lista oficial |
| Suecia | 11 | ✅ completo |
| Bélgica | 12 | ⚠️ AlterFutbol presenta doble opción en el #9: Lukaku / De Ketelaere |
| Nueva Zelanda | 11 | ✅ completo |
| Cabo Verde | 11 | ✅ completo |
| Francia | 11 | ✅ completo |
| Austria | 10 | ⚠️ Marko Arnautovic (XI) no figura en la lista oficial |
| Portugal | 11 | ✅ completo |
| RD del Congo | 9 | ⚠️ Yoanne Wissa y Cédric Bakambu (XI) no figuran en la lista oficial |

> La columna Titular se rellena usando el XI de AlterFutbol como referencia. Si un jugador del XI no aparece en la lista de convocados → no se puede marcar, el conteo queda por debajo de 11.

### Cómo obtener la imagen para un equipo nuevo
1. Ir al artículo de AlterFutbol correspondiente (ver Tarea 3)
2. Localizar la imagen del XI Ideal (camisetas sobre campo, fondo oscuro con logo de AlterFutbol)
3. Descargar o capturar pantalla y recortar al área del XI
4. Guardar como PNG en `assets/xi/{código}-xi.png`
5. Resolución mínima recomendada: **800 × 900 px**

---

## Tarea 3 — Publicaciones de AlterFutbol por selección

### Selecciones ya analizadas (17)

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
| 🇩🇪 Alemania | Buscar en https://www.alterfutbol.com/tag/convocatorias-al-mundial-2026/ |
| 🇳🇴 Noruega | Buscar en https://www.alterfutbol.com/tag/convocatorias-al-mundial-2026/ |

### Noticias generales del torneo
| Tema | URL |
|---|---|
| Todas las convocatorias al Mundial 2026 | https://www.alterfutbol.com/tag/convocatorias-al-mundial-2026/ |
| Noticias AlterFutbol | https://www.alterfutbol.com/noticias/ |

---

## Tarea 4 — Añadir una nueva convocatoria al sitio

Cuando haya una nueva convocatoria lista para analizar, seguir este flujo exacto:

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

### Paso 4 — Actualizar el tracker (§05)

En la sección `id="tracker"` de `index.html`:
- Cambiar el contador de análisis completados
- Actualizar la cronología de anuncios con la nueva selección
- Mover la selección de "Pendientes" a "Analizadas" en la lista

### Paso 5 — Actualizar la sección de grupos (§02)

En el card del grupo correspondiente, añadir `analyzed-badge` y marcar el estado:
```html
<span class="analyzed-badge">✓</span>
```

### Paso 6 — Commit y push
```bash
git add assets/ index.html
git commit -m "Add {selección}: plantel, táctica y XI probable"
git push origin main
```

---

## Selecciones pendientes (al 22 mayo 2026)

### Sin convocatoria oficial publicada aún
Grupo D completo (USA, Paraguay, Australia, Turquía) · Canadá · Qatar · Marruecos · Países Bajos · Japón · Túnez · Egipto · Irán · España · Arabia Saudita · Uruguay · Senegal · Irak · Argentina · Argelia · Jordania · Uzbekistán · Colombia · Inglaterra · Croacia · Ghana · Panamá · Curazao · Ecuador · México · Sudáfrica · Chequia

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
├── assets/
│   ├── flags/             ← {código}.svg  (48 banderas, ISO 3166-1 alpha-3)
│   ├── players/           ← {código}-{apellido}.jpg  (1 por equipo analizado)
│   └── xi/                ← {código}-xi.png  (XI probable de AlterFutbol)
└── data/
    ├── teams.json          ← planteles con ELO por club
    ├── groups.json         ← grupos A-L, fixtures y fechas
    └── match_context.json  ← narrativa táctica de los 72 partidos de grupos
```
