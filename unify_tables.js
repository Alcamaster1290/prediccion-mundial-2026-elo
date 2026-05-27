const fs = require('fs');
const raw = fs.readFileSync('index.html', 'utf8');
const crlf = raw.includes('\r\n');
let h = crlf ? raw.replace(/\r\n/g, '\n') : raw;
let log = [];

// ── 1. Eliminar columna # de las 18 tablas que la tienen ─────────────────────
// Header
const headBefore = (h.match(/<th>#<\/th>/g) || []).length;
h = h.replace(/<th>#<\/th>(?=<th>Pos<\/th>)/g, '');
log.push(`✓ ${headBefore} cabeceras <th>#</th> eliminadas`);

// Celdas de número en cada fila: <td style="color:var(--muted);font-size:12px">N</td>
const cellBefore = (h.match(/<td style="color:var\(--muted\);font-size:12px">\d+<\/td>/g) || []).length;
h = h.replace(/<td style="color:var\(--muted\);font-size:12px">\d+<\/td>(?=<td><span class="pos-badge)/g, '');
const cellAfter = (h.match(/<td style="color:var\(--muted\);font-size:12px">\d+<\/td>/g) || []).length;
log.push(`✓ ${cellBefore - cellAfter} celdas de número eliminadas`);

// ── 2. Eliminar clase tbl-nonum (ya no necesaria) ────────────────────────────
h = h.replace(/ tbl-nonum/g, '').replace(/tbl-nonum /g, '');
log.push('✓ clase tbl-nonum eliminada de tablas HTML');

// ── 3. CSS mobile: reemplazar reglas antiguas por regla unificada ─────────────
const OLD_CSS =
`    /* Ocultar #, Edad, Club, País, ELO, Titular — dejar solo Pos + Jugador */
    .squad-table th:nth-child(1), .squad-table td:nth-child(1),
    .squad-table th:nth-child(4), .squad-table td:nth-child(4),
    .squad-table th:nth-child(5), .squad-table td:nth-child(5),
    .squad-table th:nth-child(6), .squad-table td:nth-child(6),
    .squad-table th:nth-child(7), .squad-table td:nth-child(7),
    .squad-table th:nth-child(8), .squad-table td:nth-child(8) { display: none; }
    /* 7-col sin # (Japón, Túnez, Curazao): corregir columnas visibles */
    .tbl-nonum th:nth-child(1), .tbl-nonum td:nth-child(1) { display: table-cell; }
    .tbl-nonum th:nth-child(3), .tbl-nonum td:nth-child(3) { display: none; }
    .tbl-nonum th:nth-child(8), .tbl-nonum td:nth-child(8) { display: table-cell; }`;
const NEW_CSS =
`    /* Ocultar Edad, Club, País, ELO, Titular — mostrar Pos + Jugador */
    .squad-table th:nth-child(3), .squad-table td:nth-child(3),
    .squad-table th:nth-child(4), .squad-table td:nth-child(4),
    .squad-table th:nth-child(5), .squad-table td:nth-child(5),
    .squad-table th:nth-child(6), .squad-table td:nth-child(6),
    .squad-table th:nth-child(7), .squad-table td:nth-child(7) { display: none; }`;
if (h.includes(OLD_CSS)) { h = h.replace(OLD_CSS, NEW_CSS); log.push('✓ CSS mobile unificado'); }
else { log.push('✗ NOT FOUND: CSS mobile'); }

// ── 4. JS: limpiar noNum/offset y fijar índices correctos ───────────────────
// 4a. Quitar var noNum
const OLD_JS_SETUP =
`    document.querySelectorAll('.team-section .squad-table').forEach(function(tbl) {
      var noNum = tbl.classList.contains('tbl-nonum');
      var hdrRow = tbl.querySelector('thead tr');`;
const NEW_JS_SETUP =
`    document.querySelectorAll('.team-section .squad-table').forEach(function(tbl) {
      var hdrRow = tbl.querySelector('thead tr');`;
if (h.includes(OLD_JS_SETUP)) { h = h.replace(OLD_JS_SETUP, NEW_JS_SETUP); log.push('✓ JS: var noNum eliminado'); }
else { log.push('✗ NOT FOUND: JS setup'); }

// 4b. Quitar offset y fijar índices a formato 7-col, más colspan dinámico
const OLD_JS_CELLS =
`          var cells = row.querySelectorAll('td');
          var o = noNum ? -1 : 0;
          var edad  = cells[3+o] ? cells[3+o].textContent.trim() : '';
          var club  = cells[4+o] ? cells[4+o].textContent.trim() : '';
          var pais  = cells[5+o] ? cells[5+o].textContent.trim() : '';
          var eloTd = cells[6+o];
          var eloVal   = eloTd ? eloTd.textContent.trim() : 'N/D';
          var eloCls   = eloTd ? (Array.from(eloTd.classList).find(function(c){ return c.startsWith('elo-'); }) || '') : '';
          var titlEl   = cells[7+o] ? cells[7+o].querySelector('[class^="titl-"]') : null;`;
const NEW_JS_CELLS =
`          var cells = row.querySelectorAll('td');
          var edad  = cells[2] ? cells[2].textContent.trim() : '';
          var club  = cells[3] ? cells[3].textContent.trim() : '';
          var pais  = cells[4] ? cells[4].textContent.trim() : '';
          var eloTd = cells[5];
          var eloVal   = eloTd ? eloTd.textContent.trim() : 'N/D';
          var eloCls   = eloTd ? (Array.from(eloTd.classList).find(function(c){ return c.startsWith('elo-'); }) || '') : '';
          var titlEl   = cells[6] ? cells[6].querySelector('[class^="titl-"]') : null;`;
if (h.includes(OLD_JS_CELLS)) { h = h.replace(OLD_JS_CELLS, NEW_JS_CELLS); log.push('✓ JS: índices de celdas corregidos'); }
else { log.push('✗ NOT FOUND: JS cells'); }

// 4c. colspan dinámico para que el detalle abarque toda la fila
const OLD_COLSPAN = `'<tr class="sq-detail"><td colspan="3">'`;
const NEW_COLSPAN = `'<tr class="sq-detail"><td colspan="' + cells.length + '">'`;
if (h.includes(OLD_COLSPAN)) { h = h.replace(OLD_COLSPAN, NEW_COLSPAN); log.push('✓ JS: colspan dinámico'); }
else { log.push('✗ NOT FOUND: JS colspan'); }

// ── 5. Cronología: mergear entradas duplicadas por fecha ─────────────────────

// 5a. Fusionar tres entradas del 15 May → una sola
const OLD_15 =
`      <div style="display:flex;align-items:center;gap:1rem;padding:.75rem 1rem;background:var(--card);border-radius:8px;border-left:3px solid var(--border)">
        <span style="font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--muted);min-width:80px">15 May</span>
        <span><img class="flag-svg" src="assets/flags/bel.svg" alt="Bélgica" loading="lazy"> <img class="flag-svg" src="assets/flags/civ.svg" alt="Costa de Marfil" loading="lazy"> <img class="flag-svg" src="assets/flags/hti.svg" alt="Haití" loading="lazy"></span><span style="font-size:13px"><strong style="color:var(--white)">Bélgica · Costa de Marfil · Haití</strong></span>
        <span class="analyzed-badge" style="margin-left:auto">✓ Detallado</span>
      </div>
      <div style="display:flex;align-items:center;gap:1rem;padding:.75rem 1rem;background:var(--card);border-radius:8px;border-left:3px solid var(--border)">
        <span style="font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--muted);min-width:80px">15 May</span>
        <span><img class="flag-svg" src="assets/flags/jpn.svg" alt="Japón" loading="lazy"></span><span style="font-size:13px"><strong style="color:var(--white)">Japón</strong></span>
        <span class="analyzed-badge" style="margin-left:auto">✓ Detallado</span>
      </div>
      <div style="display:flex;align-items:center;gap:1rem;padding:.75rem 1rem;background:var(--card);border-radius:8px;border-left:3px solid var(--border)">
        <span style="font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--muted);min-width:80px">15 May</span>
        <span><img class="flag-svg" src="assets/flags/tun.svg" alt="Túnez" loading="lazy"></span><span style="font-size:13px"><strong style="color:var(--white)">Túnez</strong></span>
        <span class="analyzed-badge" style="margin-left:auto">✓ Detallado</span>
      </div>`;
const NEW_15 =
`      <div style="display:flex;align-items:center;gap:1rem;padding:.75rem 1rem;background:var(--card);border-radius:8px;border-left:3px solid var(--border)">
        <span style="font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--muted);min-width:80px">15 May</span>
        <span><img class="flag-svg" src="assets/flags/bel.svg" alt="Bélgica" loading="lazy"> <img class="flag-svg" src="assets/flags/civ.svg" alt="Costa de Marfil" loading="lazy"> <img class="flag-svg" src="assets/flags/hti.svg" alt="Haití" loading="lazy"> <img class="flag-svg" src="assets/flags/jpn.svg" alt="Japón" loading="lazy"> <img class="flag-svg" src="assets/flags/tun.svg" alt="Túnez" loading="lazy"></span><span style="font-size:13px"><strong style="color:var(--white)">Bélgica · Costa de Marfil · Haití · Japón · Túnez</strong></span>
        <span class="analyzed-badge" style="margin-left:auto">✓ Detallado</span>
      </div>`;
if (h.includes(OLD_15)) { h = h.replace(OLD_15, NEW_15); log.push('✓ Cronología 15 May: 3 entradas → 1'); }
else { log.push('✗ NOT FOUND: Cronología 15 May'); }

// 5b. Fusionar dos entradas del 18 May → una sola
const OLD_18 =
`      <div style="display:flex;align-items:center;gap:1rem;padding:.75rem 1rem;background:var(--card);border-radius:8px;border-left:3px solid var(--border)">
        <span style="font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--muted);min-width:80px">18 May</span>
        <span><img class="flag-svg" src="assets/flags/aut.svg" alt="Austria" loading="lazy"> <img class="flag-svg" src="assets/flags/cod.svg" alt="RD Congo" loading="lazy"> <img class="flag-svg" src="assets/flags/cpv.svg" alt="Cabo Verde" loading="lazy"></span><span style="font-size:13px"><strong style="color:var(--white)">Austria · RD Congo · Cabo Verde</strong></span>
        <span class="analyzed-badge" style="margin-left:auto">✓ Detallado</span>
      </div>
      <div style="display:flex;align-items:center;gap:1rem;padding:.75rem 1rem;background:var(--card);border-radius:8px;border-left:3px solid var(--border)">
        <span style="font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--muted);min-width:80px">18 May</span>
        <img class="flag-svg" src="assets/flags/cuw.svg" alt="Curazao" loading="lazy"><span style="font-size:13px"><strong style="color:var(--white)">Curazao</strong></span>
        <span class="analyzed-badge" style="margin-left:auto">✓ Detallado</span>
      </div>`;
const NEW_18 =
`      <div style="display:flex;align-items:center;gap:1rem;padding:.75rem 1rem;background:var(--card);border-radius:8px;border-left:3px solid var(--border)">
        <span style="font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--muted);min-width:80px">18 May</span>
        <span><img class="flag-svg" src="assets/flags/aut.svg" alt="Austria" loading="lazy"> <img class="flag-svg" src="assets/flags/cod.svg" alt="RD Congo" loading="lazy"> <img class="flag-svg" src="assets/flags/cpv.svg" alt="Cabo Verde" loading="lazy"> <img class="flag-svg" src="assets/flags/cuw.svg" alt="Curazao" loading="lazy"></span><span style="font-size:13px"><strong style="color:var(--white)">Austria · RD Congo · Cabo Verde · Curazao</strong></span>
        <span class="analyzed-badge" style="margin-left:auto">✓ Detallado</span>
      </div>`;
if (h.includes(OLD_18)) { h = h.replace(OLD_18, NEW_18); log.push('✓ Cronología 18 May: 2 entradas → 1'); }
else { log.push('✗ NOT FOUND: Cronología 18 May'); }

// ── Guardar ──────────────────────────────────────────────────────────────────
const out = crlf ? h.replace(/\n/g, '\r\n') : h;
fs.writeFileSync('index.html', out, 'utf8');
console.log(log.join('\n'));
console.log('\n✓ index.html actualizado.');
