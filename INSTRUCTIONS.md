# Guía de diseño — prediccion-mundial-2026-elo

Proyecto: página estática (`index.html`) con análisis táctico, plantel y ruta eliminatoria de cada selección del Mundial 2026. Todo el contenido vive en un único archivo HTML/CSS/JS.

---

## Estructura de una sección de equipo

Cada país analizado ocupa un bloque `<div class="team-section" id="[id-seccion]">` dentro de la sección HTML de su grupo (`<section id="grupo-X">`). El orden dentro del grupo sigue la tabla de posiciones predicha (1°, 2°, 3°, 4°).

```html
<!-- ─── NOMBRE PAÍS ─── -->
<div class="team-section" id="[id-seccion]">

  <!-- 1. Cabecera -->
  <div class="team-header">
    <div class="team-flag-big"><img src="assets/flags/[cod].svg" ...></div>
    <div>
      <div class="team-name">Nombre</div>
      <div class="team-sub">DT: Nombre · Grupo X</div>
      <div class="team-pills">
        <span class="team-pill" style="color:var(--accent);border-color:var(--accent)">4-3-3</span>
        <span class="team-pill" style="color:var(--grp-x);border-color:var(--grp-x)">Grupo X</span>
        <span class="team-pill" style="color:var(--gold);border-color:var(--gold)">Dato histórico</span>
      </div>
    </div>
    <!-- 2. Tarjeta estrella -->
    <div class="star-card">
      <div class="star-img-wrap" style="--sc:[color-grupo]">
        <img src="assets/players/[cod]-[apellido].jpg" alt="Nombre" loading="lazy"
             onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">
        <div class="star-placeholder">XX</div>   <!-- iniciales -->
      </div>
      <div class="star-info">
        <div class="star-label">Figura clave</div>
        <div class="star-name">Nombre Jugador</div>
        <div class="star-meta">Club</div>
        <span class="elo-cell elo-high" style="font-size:11px;font-family:'JetBrains Mono',monospace">ELO XXXX</span>
      </div>
    </div>
  </div>

  <!-- 3. Dos columnas: sistema de juego + ausencias -->
  <div class="two-col">
    <div class="info-card">
      <h4>Sistema de juego</h4>
      <p class="tactic-prose">...</p>
      <a href="[url-nota]" target="_blank" rel="noopener" style="...">↗ Nota en AlterFutbol</a>
    </div>
    <div class="info-card">
      <h4>Ausencias notables</h4>
      <ul class="absence-list">
        <li><span class="absence-name">Nombre (motivo)</span><br>
            <span class="absence-reason">Descripción</span></li>
      </ul>
    </div>
  </div>

  <!-- 4. XI probable (imagen) -->
  <div class="xi-img-wrap">
    <div class="xi-img-label">XI Probable · País</div>
    <img src="assets/xi/[cod]-xi.png" alt="XI Ideal País" loading="lazy" class="xi-img">
  </div>

  <!-- 5. Tabla de plantel (26 jugadores, 7 columnas) -->
  <div class="squad-wrap">
    <table class="squad-table">
      <thead><tr><th>Pos</th><th>Jugador</th><th>Edad</th><th>Club</th><th>País</th><th>ELO</th><th>Titular</th></tr></thead>
      <tbody>
        <!-- una fila por jugador, todo en una sola línea HTML -->
        <tr>
          <td><span class="pos-badge pos-gk">GK</span></td>
          <td class="player-name">Nombre [★(C) si es capitán]</td>
          <td style="color:var(--muted)">23</td>
          <td style="font-size:13px">Club FC</td>
          <td style="font-size:12px;color:var(--muted)">País Club</td>
          <td class="elo-cell elo-high">1860</td>    <!-- elo-high / elo-mid / elo-low / elo-nd -->
          <td><span class="titl-yes">Sí</span></td>  <!-- o titl-no -->
        </tr>
      </tbody>
    </table>
  </div>

  <!-- 6. Nota ELO (siempre igual) -->
  <div class="nd-note">ELO de clubes: <a href="http://worldclubratings.com/rankings/elo_men/" target="_blank" rel="noopener">worldclubratings.com/rankings/elo_men</a></div>

  <!-- 7. Fase de grupos + Ruta Eliminatoria → generados por JS automáticamente -->

</div>
```

---

## Colores de grupo (`--grp-x`)

| Grupo | Variable CSS     | Hex       |
|-------|-----------------|-----------|
| A     | `--grp-a`       | `#e55c5c` |
| B     | `--grp-b`       | `#3b8beb` |
| C     | `--grp-c`       | `#10b981` |
| D     | `--grp-d`       | `#6366f1` |
| E     | `--grp-e`       | `#f97316` |
| F     | `--grp-f`       | `#f59e0b` |
| G     | `--grp-g`       | `#8b5cf6` |
| H     | `--grp-h`       | `#ec4899` |
| I     | `--grp-i`       | `#06b6d4` |
| J     | `--grp-j`       | `#84cc16` |
| K     | `--grp-k`       | `#d97706` |
| L     | `--grp-l`       | `#94a3b8` |

El color de grupo se usa en `--sc` de la tarjeta estrella y en las pills de grupo.

---

## Clasificación ELO de clubes

Fuente: [worldclubratings.com/rankings/elo_men](http://worldclubratings.com/rankings/elo_men/)

| Clase CSS   | Rango         |
|-------------|---------------|
| `elo-high`  | ≥ 1664        |
| `elo-mid`   | 1400 – 1663   |
| `elo-low`   | < 1400        |
| `elo-nd`    | N/D (sin dato)|

---

## Insignias de posición

```html
<span class="pos-badge pos-gk">GK</span>
<span class="pos-badge pos-def">DEF</span>
<span class="pos-badge pos-med">MED</span>
<span class="pos-badge pos-del">DEL</span>
```

---

## Partidos de fase de grupos y ruta eliminatoria (JS dinámico)

Los 3 partidos del grupo y la ruta hasta Octavos **se renderizan automáticamente por JavaScript** al cargar la página. Para activarlos hay que registrar el equipo en tres objetos JS dentro del `<script>` al final de `index.html`.

### 1. `TEAM_CODES` (línea ~4250)

Mapea el `id` del `<div class="team-section">` al código FIFA de 3 letras.

```js
var TEAM_CODES = {
  // equipos existentes...
  'espana':   'esp',
  'colombia': 'col',
  // añadir aquí cada nuevo equipo analizado
};
```

**Regla**: el código debe coincidir con el usado en `data/groups.json` (campo `home`/`away`) y en el objeto `NAMES`.

### 2. `TEAM_KO_PATH` (línea ~4305)

Define la ruta R32 → R16 según si el equipo termina 1° o 2° en su grupo.  
**Todos los equipos del mismo grupo comparten la misma ruta** — basta copiar los valores de otro equipo ya registrado del mismo grupo.

```js
var TEAM_KO_PATH = {
  // Grupo H — mismo path para esp y cpv
  'esp': [{pos:'1°', r32:84, r32opp:'2.° Grupo J',  r16:93, r16opp:'Ganador P83 (2.° K ó 2.° L)'},
          {pos:'2°', r32:86, r32opp:'1.° Grupo J',  r16:95, r16opp:'Ganador P88 (2.° D ó 2.° G)'}],

  // Grupo K — mismo path para col, por y cod
  'col': [{pos:'1°', r32:87, r32opp:'3.° D/E/I/J/L', r16:96, r16opp:'Ganador P85 (1.° B ó 3.° E/F/G/I/J)'},
          {pos:'2°', r32:83, r32opp:'2.° Grupo L',   r16:93, r16opp:'Ganador P84 (1.° H ó 2.° J)'}],
};
```

Campos:
- `pos`: `'1°'` o `'2°'` (se muestra como badge).
- `r32`: número de partido de 16avos (P73–P88).
- `r32opp`: texto descriptivo del rival en 16avos.
- `r16`: número de partido de Octavos.
- `r16opp`: texto descriptivo del rival potencial en Octavos.

### 3. `TEAM_KO_3RD` (línea ~4346)

Define los partidos de R32 a los que podría ir el equipo si termina 3° y clasifica entre los 8 mejores terceros. **Igual para todos los equipos del mismo grupo.**

```js
var TEAM_KO_3RD = {
  // Grupo H
  'esp': [{r32:77,r16:89},{r32:79,r16:92},{r32:80,r16:92},{r32:82,r16:94}],
  // Grupo K
  'col': [{r32:80,r16:92},{r32:87,r16:96}],
};
```

---

## Rutas por grupo (referencia rápida)

| Grupo | TEAM_KO_PATH 1° | TEAM_KO_PATH 2° | TEAM_KO_3RD |
|-------|-----------------|-----------------|-------------|
| A     | r32:79, r16:92  | r32:74, r16:89  | [{r32:74,r16:89},{r32:82,r16:94}] |
| B     | r32:85, r16:96  | r32:73, r16:90  | [{r32:74,r16:89},{r32:81,r16:94}] |
| C     | r32:76, r16:91  | r32:75, r16:90  | [{r32:74,r16:89},{r32:77,r16:89},{r32:79,r16:92}] |
| D     | — (sin datos)   | —               | — |
| E     | r32:74, r16:89  | r32:78, r16:91  | [{r32:79,r16:92},{r32:80,r16:92},{r32:81,r16:94},{r32:82,r16:94},{r32:85,r16:96},{r32:87,r16:96}] |
| F     | r32:75, r16:90  | r32:76, r16:91  | [{r32:74,r16:89},{r32:77,r16:89},{r32:79,r16:92},{r32:81,r16:94},{r32:85,r16:96}] |
| G     | r32:82, r16:94  | r32:88, r16:95  | [{r32:77,r16:89},{r32:85,r16:96}] |
| H     | r32:84, r16:93  | r32:86, r16:95  | [{r32:77,r16:89},{r32:79,r16:92},{r32:80,r16:92},{r32:82,r16:94}] |
| I     | r32:77, r16:89  | r32:78, r16:91  | [{r32:77,r16:89},{r32:79,r16:92},{r32:80,r16:92},{r32:81,r16:94},{r32:82,r16:94},{r32:85,r16:96},{r32:87,r16:96}] |
| J     | r32:86, r16:95  | r32:84, r16:93  | [{r32:80,r16:92},{r32:81,r16:94},{r32:82,r16:94},{r32:85,r16:96},{r32:87,r16:96}] |
| K     | r32:87, r16:96  | r32:83, r16:93  | [{r32:80,r16:92},{r32:87,r16:96}] |
| L     | r32:80, r16:92  | r32:83, r16:93  | [{r32:87,r16:96}] |

Para los textos de `r32opp` y `r16opp` de un grupo nuevo, copiar literalmente de otro equipo ya registrado en el mismo grupo.

---

## Navegación: 4 lugares a actualizar por equipo nuevo

Cuando se agrega un equipo con sección completa (`has-analysis`), actualizar:

1. **Modal de grupos** (`gmod-team`):
   ```html
   <a class="gmod-team has-analysis" data-name="País" href="#id-seccion">
     <img src="assets/flags/[cod].svg" alt=""><span class="gmod-name">País</span><span class="gmod-ana"></span>
   </a>
   ```

2. **Tarjeta de grupo** (`group-card` → `group-teams`):
   ```html
   <li><a href="#id-seccion" class="group-team-link">
     <img class="flag-svg" src="assets/flags/[cod].svg" alt="País" loading="lazy"> País
   </a> <span class="analyzed-badge">✓</span></li>
   ```

3. **Tabla de posiciones** (`standings-table` del grupo):
   ```html
   <td class="st-team-cell">
     <a href="#id-seccion" class="st-team-link">
       <img class="flag-svg" src="assets/flags/[cod].svg" alt="País" loading="lazy"> País
     </a>
   </td>
   ```

4. **JS `TEAM_CODES`**: agregar `'id-seccion': 'cod'` (ver sección anterior).

---

## Assets necesarios por equipo

| Archivo | Ruta | Notas |
|---------|------|-------|
| Bandera | `assets/flags/[cod].svg` | Ya presente para los 48 equipos |
| Jugador estrella | `assets/players/[cod]-[apellido].ext` | jpg / png / webp |
| XI probable | `assets/xi/[cod]-xi.png` | Imagen del once formación |

---

## Orden de equipos dentro de cada grupo

Los `<div class="team-section">` deben aparecer en el mismo orden que la tabla de posiciones predicha (1°→4°). Los equipos sin sección completa se representan con un `pending-card` en la posición correspondiente:

```html
<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:1rem;margin-top:2rem">
  <div class="pending-card">
    <img class="flag-svg" src="assets/flags/[cod].svg" alt="País" loading="lazy"> País<br>
    <small style="font-size:11px;opacity:.6">Lista pendiente</small>
  </div>
</div>
```
