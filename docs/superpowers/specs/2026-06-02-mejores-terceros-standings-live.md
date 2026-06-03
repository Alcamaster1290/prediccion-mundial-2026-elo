---
name: mejores-terceros-standings-live
description: Tabla de mejores terceros en #grupos + standings en tiempo real desde Supabase + banderas en Ruta Posible
metadata:
  type: project
---

# Spec: Mejores Terceros + Standings Live + Banderas KO Path

**Fecha:** 2026-06-02  
**Estado:** Aprobado para implementación

---

## Resumen

Tres cambios coordinados:

1. **Standings live** — los 12 grupos leen resultados desde Supabase en lugar de mostrar ceros estáticos.
2. **Tabla de Mejores Terceros** — nueva sección al final de `#grupos` que ordena los 12 terceros por criterios FIFA y marca los 8 clasificados.
3. **Banderas en Ruta Posible** — cada tarjeta `ko-card` en la sección "Ruta Eliminatoria Posible" resuelve el rival textual (`"2.° Grupo B"`) y muestra la bandera + nombre del equipo que ocupa esa posición en los standings actuales, usando el orden predeterminado del HTML si no hay resultados cargados aún.

---

## 1. Esquema Supabase

### Tabla `match_results`

```sql
CREATE TABLE match_results (
  id            UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
  match_number  INTEGER     UNIQUE NOT NULL,         -- P1–P104
  phase         TEXT        NOT NULL,                 -- 'group', 'r32', 'r16', 'qf', 'sf', 'final'
  group_id      TEXT,                                 -- 'a'…'l', NULL para KO
  home_team     TEXT,                                 -- código: 'mex', 'usa', NULL si aún no se sabe
  away_team     TEXT,
  home_goals    INTEGER,                              -- NULL = no jugado
  away_goals    INTEGER,
  home_label    TEXT,       -- texto descriptivo: "1.° Grupo A", "Ganador Partido 73"
  away_label    TEXT,       -- ídem para partidos KO (solo lectura, no se actualiza)
  kickoff_utc   TIMESTAMPTZ,
  stadium       TEXT,
  city          TEXT,
  updated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_match_results_updated_at
  BEFORE UPDATE ON match_results
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```

### Row Level Security

```sql
ALTER TABLE match_results ENABLE ROW LEVEL SECURITY;

-- Lectura pública
CREATE POLICY "public read" ON match_results
  FOR SELECT USING (true);

-- Escritura solo service_role (admin)
-- (service_role bypasses RLS por defecto en Supabase)
```

### Seed script

Un script Node.js `scripts/seed_matches.js` pre-inserta los 104 partidos con `home_goals = NULL` / `away_goals = NULL`:

**Fase de grupos (P1–P72):** Lee `data/groups.json`, extrae cada fixture con sus códigos de equipo (`home_team`, `away_team`), kickoff, estadio y ciudad. `home_label` y `away_label` se completan con el nombre del equipo (ej: `"México"`).

**16avos (P73–P88):** `home_team = NULL`, `away_team = NULL`. `home_label` y `away_label` se toman de `KNOCKOUT_MATCHES.homeLabel` / `.awayLabel` ya definidos en el HTML (ej: `"1.° Grupo A"`, `"3.° A/B/C/D/F"`). Estos labels **no cambian nunca** — son la descripción del bracket.

**Octavos–Final (P89–P104):** `home_team = NULL`, `away_team = NULL`, `home_label = NULL`, `away_label = NULL`. Solo se guarda fixture data (fecha, hora, estadio, ciudad, número de partido). El display en la UI usa directamente el número de partido: `"Partido 89"`, `"Partido 104 — Final"`.

Los datos de `KNOCKOUT_MATCHES` ya están hardcodeados en el HTML y el seed script los extrae desde un JSON equivalente en `data/knockout_matches.json` (a crear junto con el seed).

---

## 2. Arquitectura JavaScript

Toda la lógica se agrega en un bloque `<script>` nuevo justo antes del `</body>`, después del bloque JS existente.

**Extracción del IIFE — hallazgos exactos (líneas verificadas):**

Las siguientes declaraciones están DENTRO del IIFE (líneas 4793–5186) y deben moverse al scope global ANTES del IIFE para que el nuevo código pueda usarlas:

| Variable/Función | Línea actual | Tipo | Notas |
|---|---|---|---|
| `PHASE_LABELS` | 4810 | objeto | Etiquetas de fase |
| `PHASE_COLORS` | 4811 | objeto | Colores por fase |
| `KNOCKOUT_MATCHES` | 4812 | array | P73–P104, ya tiene homeLabel/awayLabel |
| `TEAM_CODES` | 4941 | objeto | sectionId → código equipo |
| `TEAM_KO_PATH` | 4998 | objeto | rutas 1.° y 2.° por equipo |
| `TEAM_KO_3RD` | 5045 | objeto | rutas como 3.° |
| `labelDate()` | 4862 | función | formatea fecha YYYY-MM-DD |
| `renderTeamKOPaths()` | 5069–5139 | función | genera rutas KO en DOM |

Estas son todas declaraciones de datos o funciones puras — **no hay closures ni estado privado que impida extraerlas**. `allMatches`, `activeFilter`, `tzOffset` y `renderCalendar()` permanecen dentro del IIFE.

`koCard()` y `shortVenue()` son funciones locales dentro de `renderTeamKOPaths()` — se quedan ahí, no necesitan ser globales.

**Cliente Supabase:** Supabase ya está inicializado para auth/premium. Durante implementación se identifica la variable global existente (probablemente en `js/auth.js`) y se reutiliza en lugar de crear un segundo cliente.

### 2.1 Inicialización de standings predeterminados

Al cargar la página (antes de que llegue Supabase), se leen los `<tbody>` de las 12 tablas de standings existentes:

```javascript
// Devuelve objeto: { 'a': [{team, name, flagSrc, PJ:0, PG:0, ...}, ...], ... }
function initDefaultStandings() { ... }
```

Esto garantiza que `CURRENT_STANDINGS` siempre tiene datos (posición predeterminada = orden HTML), incluso antes del torneo.

### 2.2 Cálculo de standings desde resultados

```javascript
// results: filas de match_results donde phase='group' y group_id=groupId
// Devuelve array de 4 equipos ordenados por criterios FIFA
function calcGroupStandings(groupId, results) { ... }
```

**Criterios de ordenamiento intragrupo (FIFA):**
1. Puntos (PG×3 + PE×1)
2. Enfrentamiento directo: puntos, DG, GF
3. DG general del grupo
4. GF general del grupo
5. Fair play score (si se implementan tarjetas)
6. Ranking FIFA (lookup tabla hardcodeada por código de equipo)

> **Nota:** Los pasos 2 (enfrentamiento directo) y 5 (fair play) se omiten en v1; se añaden cuando haya datos de tarjetas. El ranking FIFA (paso 6) se usa como desempate final con un objeto estático `FIFA_RANK`.

### 2.3 Actualización de tablas HTML

```javascript
// Escribe los valores calculados en los <td> del <tbody> del grupo
// Ajusta clases st-qualify / st-third / (sin clase) según posición
function updateStandingsTable(groupId, rankedTeams) { ... }
```

Las celdas identificadas por atributo `data-stat="PJ"` etc. (hay que agregar estos atributos al HTML de todas las tablas durante implementación). Alternativamente, por índice de columna (más frágil pero sin cambios al HTML).

**Decisión v1:** usar índice de columna para no tocar 12 tablas × 4 filas de HTML.

### 2.4 Recolección y ordenamiento de mejores terceros

```javascript
// Lee el 3.° de cada grupo desde CURRENT_STANDINGS
// Ordena por criterios FIFA para mejores terceros
// Devuelve array de 12 items, top 8 marcados classified=true
function collectBestThirds() { ... }
```

**Criterios FIFA para mejores terceros** (diferente a intragrupo):
1. Puntos
2. DG total
3. GF total
4. Fair play
5. Ranking FIFA

### 2.5 Renderizado de la tabla

```javascript
function renderBestThirds(thirds) {
  // Genera <tr> para cada tercero y los inserta en #best-thirds-tbody
  // Top 8: clase st-third-qualify (borde naranja), bottom 4: st-third-out (gris)
}
```

### 2.6 Resolución de banderas en Ruta Posible

```javascript
// Parsea strings como "2.° Grupo B", "1.° Grupo A", "3.° mejor 3.°"
// Busca en CURRENT_STANDINGS y devuelve {flagSrc, name} o null
function resolveOpponent(oppText) { ... }
```

`renderTeamKOPaths()` se **reescribe** para llamar `resolveOpponent()` en cada tarjeta. Si resuelve, muestra `<img flag> + nombre (oppText)`. Si no puede resolver (partido KO no jugado, bracket no definido), muestra solo `oppText`.

Los standings predeterminados garantizan que **siempre se resuelve** para los rivales de fase de grupos (1.°/2.°/3.° de cada grupo).

### 2.7 Supabase Realtime

```javascript
// Reutilizar el cliente Supabase ya inicializado por auth.js / premium.js
// (buscar la variable global existente en js/auth.js durante implementación)
const supabaseClient = window._supabase; // nombre exacto a confirmar durante implementación

async function loadAndRenderStandings() {
  const { data } = await supabaseClient
    .from('match_results')
    .select('*')
    .eq('phase', 'group');

  const byGroup = groupBy(data || [], 'group_id');
  Object.keys(byGroup).forEach(gid => {
    const ranked = calcGroupStandings(gid, byGroup[gid]);
    CURRENT_STANDINGS[gid] = ranked;
    updateStandingsTable(gid, ranked);
  });

  const thirds = collectBestThirds();
  renderBestThirds(thirds);
  renderTeamKOPaths(); // re-render con banderas actualizadas
}

// Suscripción Realtime
supabaseClient.channel('standings-live')
  .on('postgres_changes', { event: '*', schema: 'public', table: 'match_results' },
    () => loadAndRenderStandings())
  .subscribe();

// Carga inicial
loadAndRenderStandings();
```

---

## 3. HTML — Nueva sección Mejores Terceros

Se inserta al final del contenedor de `#grupos`, después del último grupo (L), antes del `</section>` de cierre:

```html
<!-- ═══════ MEJORES TERCEROS ═══════ -->
<div id="mejores-terceros" style="margin-top:3rem">
  <div class="group-section-header" style="margin-bottom:1.5rem">
    <div class="group-big-label" style="color:rgba(245,158,11,.15)">3°</div>
    <div class="group-section-info">
      <h2>Mejores Terceros</h2>
      <div style="color:var(--muted);font-size:14px;margin-top:.4rem">
        8 de los 12 terceros clasifican a 16avos · ordenados por criterios FIFA
      </div>
    </div>
  </div>

  <div class="standings-wrap" style="--grp-col:rgba(245,158,11,.7)">
    <table class="standings-table">
      <thead>
        <tr>
          <th class="st-pos-hdr">#</th>
          <th style="font-size:12px;padding:.4rem .5rem">Grp</th>
          <th class="st-team-hdr">Equipo</th>
          <th title="Partidos jugados">PJ</th>
          <th title="Ganados">PG</th>
          <th title="Empates">PE</th>
          <th title="Derrotas">PP</th>
          <th title="Goles a favor">GF</th>
          <th title="Goles en contra">GC</th>
          <th title="Diferencia de goles">DG</th>
          <th class="st-pts-hdr" title="Puntos">PTS</th>
        </tr>
      </thead>
      <tbody id="best-thirds-tbody">
        <!-- Generado por JS -->
      </tbody>
    </table>
  </div>

  <div class="standings-legend" style="margin-top:.75rem">
    <span><span class="st-legend-dot" style="background:rgba(245,158,11,.7)"></span>Clasifican (8 mejores)</span>
    <span><span class="st-legend-dot" style="background:rgba(100,116,139,.3)"></span>Eliminados</span>
  </div>

  <details class="st-tiebreak" style="margin-top:1rem">
    <summary>Criterios de ordenamiento para mejores terceros ▸</summary>
    <ol class="st-tiebreak-list">
      <li>Puntos totales en fase de grupos</li>
      <li>Diferencia de goles en todos los partidos del grupo</li>
      <li>Goles marcados en todos los partidos del grupo</li>
      <li>Fair play (−1 amarilla · −4 roja directa · −5 amarilla+roja)</li>
      <li>Ranking FIFA/Coca-Cola</li>
    </ol>
  </details>
</div>
```

### CSS adicional (mínimo)

```css
/* Fila de tercero clasificado — ya existe st-third, añadir para terceros-tabla */
.st-third-qualify > td:first-child { border-left: 3px solid rgba(245,158,11,.7); }
.st-third-out > td:first-child     { border-left: 3px solid rgba(100,116,139,.3); }
.st-third-out td                   { color: var(--muted); }

/* Separador visual entre top-8 y bottom-4 */
.st-thirds-cutline > td {
  border-top: 1px dashed rgba(245,158,11,.4);
}
```

---

## 4. Cambio en ko-card — banderas de rival

### Estado actual

```javascript
function koCard(matchNum, oppText, color, phase, date, time, venue) {
  return `...<div class="ko-card-opp">vs ${oppText}</div>...`;
}
```

### Estado nuevo

```javascript
function koCard(matchNum, oppText, color, phase, date, time, venue) {
  const resolved = resolveOpponent(oppText); // {flagSrc, name} | null
  const oppDisplay = resolved
    ? `<img class="flag-svg" src="${resolved.flagSrc}" style="height:14px;vertical-align:middle"> 
       <strong>${resolved.name}</strong> <span style="opacity:.6;font-size:11px">${oppText}</span>`
    : oppText;
  return `...<div class="ko-card-opp">vs ${oppDisplay}</div>...`;
}
```

`resolveOpponent` solo puede resolver patrones `"N.° Grupo X"`. Los patrones `"Ganador P73"` devuelven null hasta que el partido esté jugado y el bracket se actualice en Supabase.

---

## 5. Archivos a crear / modificar

| Archivo | Acción | Descripción |
|---|---|---|
| `scripts/seed_matches.js` | Crear | Script Node.js que lee `data/groups.json` y hace upsert de los 72 partidos de grupos en Supabase |
| `index.html` | Modificar | Extraer `koCard()` y `renderTeamKOPaths()` del IIFE y hacerlas globales |
| `index.html` | Modificar | Insertar HTML de `#mejores-terceros` al final del `<section id="grupos">` |
| `index.html` | Modificar | Agregar `<script>` con la lógica live: `initDefaultStandings`, `calcGroupStandings`, `renderBestThirds`, `resolveOpponent`, Supabase Realtime |
| `index.html` (CSS) | Modificar | Agregar 4 reglas CSS para `.st-third-qualify`, `.st-third-out`, `.st-thirds-cutline` |

---

## 6. Fuera de alcance (v1)

- Tarjetas / fair play tracking (puntos 5 y 6 de desempate intragrupo)
- Resolución de `"Ganador P73"` para partidos KO
- Panel de administración para ingresar resultados (usar Supabase dashboard directamente)
- Partidos de fase eliminatoria en standings
