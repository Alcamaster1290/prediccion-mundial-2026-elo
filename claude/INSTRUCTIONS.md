# Instrucciones para Claude Code — prediccion-mundial-2026-elo

Este documento guía a Claude Code en las tareas del proyecto. Léelo completo antes de ejecutar cualquier acción.

---

## Contexto del proyecto

Aplicación web de análisis táctico y predicciones para el Mundial 2026.
- Stack: HTML + CSS + JS vanilla (sin frameworks ni build step)
- Datos: `data/teams.json` y `data/groups.json`
- Estilos: inline en `index.html` (pendiente extracción a `css/styles.css`)
- Fuente de análisis: [AlterFutbol](https://alterfutbol.com)
- Fuente de ELO de clubes: [worldclubratings.com](http://worldclubratings.com/rankings/elo_men/)

---

## Tarea 1 — Imagen del jugador estrella (`assets/players/`)

### Qué se necesita
Una foto por selección. La tarjeta ya está implementada en `index.html` con `onerror` que muestra las iniciales si no hay imagen. Solo hay que colocar el archivo con el nombre correcto.

### Convención de nombres
`{código-equipo}-{apellido}.jpg`

### Lista completa de imágenes a buscar

| Archivo esperado | Jugador | Selección | Sugerencia de búsqueda |
|---|---|---|---|
| `bih-dzeko.jpg` | Edin Džeko | Bosnia | "Edin Dzeko Schalke 2025 wikimedia" |
| `sui-xhaka.jpg` | Granit Xhaka | Suiza | "Granit Xhaka Switzerland national team" |
| `swe-gyokeres.jpg` | Viktor Gyökeres | Suecia | "Viktor Gyokeres Arsenal 2025" |
| `kor-son.jpg` | Son Heung-min | Corea del Sur | "Son Heung-min LAFC 2026" |
| `bra-vinicius.jpg` | Vinicius Jr. | Brasil | "Vinicius Junior Real Madrid 2025 wikimedia" |
| `hti-bellegarde.jpg` | J.-R. Bellegarde | Haití | "Jean-Ricner Bellegarde Wolverhampton" |
| `sco-mcginn.jpg` | John McGinn | Escocia | "John McGinn Aston Villa Scotland" |
| `civ-adingra.jpg` | Simon Adingra | Costa de Marfil | "Simon Adingra Monaco 2025" |
| `bel-debruyne.jpg` | Kevin De Bruyne | Bélgica | "Kevin De Bruyne Napoli 2025" |
| `nzl-wood.jpg` | Chris Wood | Nueva Zelanda | "Chris Wood Nottingham Forest" |
| `cpv-rodrigues.jpg` | Garry Rodrigues | Cabo Verde | "Garry Rodrigues Apollon footballer" |
| `fra-mbappe.jpg` | Kylian Mbappé | Francia | "Kylian Mbappe Real Madrid 2025 wikimedia" |
| `aut-alaba.jpg` | David Alaba | Austria | "David Alaba Real Madrid Austria" |
| `por-ronaldo.jpg` | Cristiano Ronaldo | Portugal | "Cristiano Ronaldo Al-Nassr Portugal" |
| `cod-mbemba.jpg` | Chancel Mbemba | RD del Congo | "Chancel Mbemba Lille 2025" |

### Fuentes permitidas (libres de derechos)
1. **Wikimedia Commons** — buscar `https://commons.wikimedia.org/wiki/File:{nombre}`
2. **Sitios oficiales de federaciones nacionales** — sección "plantilla" o "squad"
3. **Transfermarkt** — foto de perfil del jugador (baja resolución, uso editorial)

### Especificaciones técnicas
- Formato: `.jpg` o `.webp` (renombrar si es necesario)
- Resolución mínima: **400 × 500 px** (portrait)
- Encuadre ideal: cabeza y hombros centrados (object-fit: cover; object-position: top center ya está en el CSS)
- Si la imagen descargada es horizontal, recortar al área de la cara/torso

### Comportamiento en el HTML
La tarjeta ya usa `onerror` para mostrar las iniciales si no encuentra la imagen:
```html
<img src="assets/players/swe-gyokeres.jpg" alt="Viktor Gyökeres" loading="lazy"
     onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">
<div class="star-placeholder">VG</div>  <!-- se muestra si no hay imagen -->
```

---

## Tarea 2 — Imagen del XI Ideal (`assets/xi/`)

### Qué se necesita
Captura del XI Ideal publicado por AlterFutbol para cada selección. Ya hay 4 imágenes disponibles (Bosnia, Suecia, Suiza, Corea del Sur — subidas durante la construcción del proyecto).

### Convención de nombres
`{código-equipo}-xi.png`

### Estado actual

| Archivo | Estado | Fuente |
|---|---|---|
| `bih-xi.png` | ✅ Disponible | Subida por el usuario |
| `swe-xi.png` | ✅ Disponible | Subida por el usuario |
| `sui-xi.png` | ✅ Disponible | Pendiente de subir |
| `kor-xi.png` | ✅ Disponible | Subida por el usuario |
| `bra-xi.png` | ⏳ Pendiente | Ver enlace abajo |
| `hti-xi.png` | ⏳ Pendiente | Ver enlace abajo |
| `sco-xi.png` | ⏳ Pendiente | Ver enlace abajo |
| `civ-xi.png` | ⏳ Pendiente | Ver enlace abajo |
| `bel-xi.png` | ⏳ Pendiente | Ver enlace abajo |
| `nzl-xi.png` | ⏳ Pendiente | Ver enlace abajo |
| `cpv-xi.png` | ⏳ Pendiente | Ver enlace abajo |
| `fra-xi.png` | ⏳ Pendiente | Ver enlace abajo |
| `aut-xi.png` | ⏳ Pendiente | Ver enlace abajo |
| `por-xi.png` | ⏳ Pendiente | Ver enlace abajo |
| `cod-xi.png` | ⏳ Pendiente | Ver enlace abajo |

### Cómo obtener las imágenes
1. Ir al enlace de AlterFutbol correspondiente (Tarea 3)
2. Localizar la imagen del XI Ideal en el artículo (formato: camisetas sobre campo de fútbol, fondo oscuro con logo de AlterFutbol)
3. Descargar o hacer captura de pantalla
4. Recortar al área del XI (excluir encabezado del post si hay texto alrededor)
5. Guardar como PNG con el nombre correcto en `assets/xi/`

### Especificaciones técnicas
- Formato: PNG preferido (el fondo oscuro del XI funciona bien con PNG)
- Resolución mínima: **800 × 900 px**
- Las imágenes del XI se usan como referencia visual en el análisis (actualmente en la sección `xi-row` del HTML, futuro: galería de XI)

---

## Tarea 3 — Publicaciones de AlterFutbol por selección

### URLs completas de cada artículo

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

### Noticias generales del torneo
| Tema | URL |
|---|---|
| Página de noticias AlterFutbol | https://www.alterfutbol.com/noticias/ |
| Todas las convocatorias al Mundial 2026 | https://www.alterfutbol.com/tag/convocatorias-al-mundial-2026/ |

---

## Tarea 4 — Nuevas convocatorias (pendientes de análisis)

Cuando AlterFutbol publique nuevas listas, seguir este flujo:
1. Ir a `https://www.alterfutbol.com/noticias/` y buscar artículos con "convocados" y "Mundial"
2. Leer el artículo completo (plantilla, análisis táctico, figura clave, ausencias)
3. Actualizar `data/teams.json` con los jugadores y ELO
4. Buscar la imagen del XI Ideal en el artículo → guardar en `assets/xi/{código}-xi.png`
5. Buscar imagen del jugador estrella → guardar en `assets/players/{código}-{apellido}.jpg`
6. Actualizar `index.html`: sección del equipo con táctica ampliada, tabla de jugadores y `"titular": true/false`
7. Marcar `"analyzed": true` en `data/teams.json`

### Selecciones que aún no han publicado lista (al 20 mayo 2026)
Grupos D (completo), y en otros grupos: Canadá, Qatar, Marruecos, Países Bajos, Japón, Túnez, Egipto, Irán, España, Arabia Saudita, Uruguay, Senegal, Irak, Noruega, Argentina, Argelia, Jordania, Uzbekistán, Colombia, Inglaterra, Croacia, Ghana, Panamá.

---

## Reglas generales para Claude Code

- **No modificar** la lógica CSS de colores por grupo (`--grp-a` … `--grp-l`) — están calibradas
- **No cambiar** los `id` de los team sections (se usan para la nav y para las inyecciones de Python)
- Al agregar un equipo nuevo, copiar exactamente la estructura de un equipo existente (ej. Bosnia)
- Siempre mantener la columna `Titular` con `—` hasta recibir la imagen del XI Ideal
- El ELO debe provenir de `worldclubratings.com` — no inventar valores
- Los archivos JSON en `data/` son la fuente de verdad; `index.html` es la vista

---

## Estructura de carpetas (recordatorio)

```
prediccion-mundial-2026-elo/
├── index.html
├── README.md
├── .gitignore
├── claude/
│   └── INSTRUCTIONS.md     ← este archivo
├── assets/
│   ├── flags/              ← {código}.svg  (48 banderas)
│   ├── players/            ← {código}-{apellido}.jpg  (1 por equipo)
│   └── xi/                 ← {código}-xi.png  (XI ideal de AlterFutbol)
├── css/
│   └── styles.css          ← extraer de index.html cuando sea oportuno
├── js/
│   ├── main.js
│   └── filters.js
└── data/
    ├── teams.json
    └── groups.json
```
