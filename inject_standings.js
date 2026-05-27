const fs = require('fs');
const raw = fs.readFileSync('index.html', 'utf8');
const crlf = raw.includes('\r\n');
let h = crlf ? raw.replace(/\r\n/g, '\n') : raw;
let log = [];

// ── CSS ──────────────────────────────────────────────────────────────────────
const CSS_ANCHOR = '  /* ─── HERO ─── */';
const STANDINGS_CSS =
`  /* ─── STANDINGS TABLE ─── */
  .standings-wrap {
    margin: 1.75rem 0 2rem;
    border-radius: 10px;
    border: 1px solid var(--border);
    overflow: hidden;
  }
  .standings-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13.5px;
  }
  .standings-table thead th {
    background: #0b0f1c;
    padding: .5rem .75rem;
    font-family: 'Barlow Condensed', sans-serif;
    font-weight: 700;
    font-size: 11px;
    letter-spacing: .07em;
    text-transform: uppercase;
    color: var(--muted);
    text-align: center;
    white-space: nowrap;
  }
  .standings-table thead th.st-team-hdr { text-align: left; min-width: 140px; }
  .standings-table thead th.st-pos-hdr  { width: 30px; }
  .standings-table thead th.st-pts-hdr  { color: var(--fg); }
  .standings-table td {
    padding: .52rem .75rem;
    border-bottom: 1px solid var(--border);
    text-align: center;
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
  }
  .standings-table tr:last-child td { border-bottom: none; }
  .standings-table tr:hover td { background: rgba(255,255,255,.025); }
  .st-pos-cell {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: var(--muted);
  }
  .st-team-cell { text-align: left !important; }
  .st-team-link { color: inherit; text-decoration: none; }
  .st-team-link:hover { color: var(--accent); }
  .st-pts { font-family: 'Barlow Condensed', sans-serif; font-weight: 900; font-size: 15px; color: var(--white); }
  /* Zone indicators */
  .st-qualify > td:first-child { border-left: 3px solid var(--grp-col, var(--accent)); }
  .st-third   > td:first-child { border-left: 3px solid rgba(245,158,11,.7); }
  /* Tiebreak accordion */
  .st-tiebreak {
    padding: .55rem 1rem;
    border-top: 1px solid var(--border);
    background: rgba(0,0,0,.18);
  }
  .st-tiebreak summary {
    cursor: pointer;
    font-size: 10.5px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: .07em;
    font-family: 'Barlow Condensed', sans-serif;
    font-weight: 700;
    user-select: none;
    list-style: none;
  }
  .st-tiebreak summary::-webkit-details-marker { display: none; }
  .st-tiebreak[open] summary { color: var(--fg); }
  .st-tiebreak-list {
    margin: .6rem 0 .3rem 1.3rem;
    font-size: 12px;
    color: var(--muted);
    line-height: 1.75;
  }
  .st-tiebreak-note {
    font-size: 11px;
    color: var(--muted);
    opacity: .7;
    margin: .35rem 0 .1rem;
    font-style: italic;
  }
  /* Legend */
  .standings-legend {
    display: flex;
    gap: 1.25rem;
    margin-top: .5rem;
    font-size: 11px;
    color: var(--muted);
    padding: 0 .25rem;
  }
  .st-legend-dot {
    display: inline-block;
    width: 7px; height: 7px;
    border-radius: 2px;
    margin-right: .35rem;
    vertical-align: middle;
  }
  @media (max-width: 600px) {
    .standings-table { font-size: 12px; }
    .standings-table thead th, .standings-table td { padding: .45rem .4rem; }
    .st-team-hdr, .st-team-cell { min-width: 110px; }
  }

`;

if (h.includes(CSS_ANCHOR)) {
  h = h.replace(CSS_ANCHOR, STANDINGS_CSS + CSS_ANCHOR);
  log.push('✓ CSS standings insertado');
} else {
  log.push('✗ NOT FOUND: CSS anchor');
}

// ── STANDINGS TABLE BUILDER ───────────────────────────────────────────────────
const TIEBREAK_HTML =
`      <details class="st-tiebreak">
        <summary>Criterios de desempate ▸</summary>
        <ol class="st-tiebreak-list">
          <li>Puntos en enfrentamiento directo entre equipos igualados</li>
          <li>Diferencia de goles en enfrentamiento directo</li>
          <li>Goles marcados en enfrentamiento directo</li>
          <li>Diferencia de goles en todos los partidos del grupo</li>
          <li>Goles marcados en todos los partidos del grupo</li>
          <li>Fair play: amarilla &minus;1&thinsp;pt &middot; roja directa &minus;4&thinsp;pts &middot; amarilla+roja &minus;5&thinsp;pts</li>
          <li>Ranking FIFA/Coca-Cola masculino (ediciones sucesivas hasta desempatar)</li>
        </ol>
        <p class="st-tiebreak-note">Sin sorteo — novedad respecto a Qatar 2022.</p>
      </details>`;

const LEGEND_HTML =
`    <div class="standings-legend">
      <span><span class="st-legend-dot" style="background:var(--grp-col,var(--accent))"></span>Clasificados a 32avos</span>
      <span><span class="st-legend-dot" style="background:rgba(245,158,11,.7)"></span>Posible clasificado (mejor 3.º)</span>
    </div>`;

function teamRow(pos, flag, name, href, zoneClass) {
  const cell = href
    ? `<a href="${href}" class="st-team-link"><img class="flag-svg" src="assets/flags/${flag}" alt="${name}" loading="lazy"> ${name}</a>`
    : `<img class="flag-svg" src="assets/flags/${flag}" alt="${name}" loading="lazy"> ${name}`;
  return `          <tr class="${zoneClass}">
            <td class="st-pos-cell">${pos}</td>
            <td class="st-team-cell">${cell}</td>
            <td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td>
            <td class="st-pts">0</td>
          </tr>`;
}

function standingsBlock(grpLetter, teams) {
  const rows = teams.map((t, i) => {
    const zone = i < 2 ? 'st-qualify' : i === 2 ? 'st-third' : '';
    return teamRow(i + 1, t.flag, t.name, t.href || null, zone);
  }).join('\n');
  return `
    <!-- ─── TABLA DE POSICIONES ─── -->
    <div class="standings-wrap" style="--grp-col:var(--grp-${grpLetter})">
      <table class="standings-table">
        <thead>
          <tr>
            <th class="st-pos-hdr">#</th>
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
        <tbody>
${rows}
        </tbody>
      </table>
${TIEBREAK_HTML}
    </div>
${LEGEND_HTML}
`;
}

// ── GROUP DATA ────────────────────────────────────────────────────────────────
const groups = [
  {
    letter: 'a',
    teams: [
      { flag: 'mex.svg', name: 'México' },
      { flag: 'zaf.svg', name: 'Sudáfrica' },
      { flag: 'kor.svg', name: 'Corea del Sur', href: '#corea' },
      { flag: 'cze.svg', name: 'Chequia' },
    ],
    anchor: '    </div>\n    \n    <!-- ─── COREA DEL SUR ─── -->\n    \n    <!-- ─── COREA DEL SUR ─── -->',
  },
  {
    letter: 'b',
    teams: [
      { flag: 'can.svg', name: 'Canadá' },
      { flag: 'bih.svg', name: 'Bosnia y Herz.', href: '#bosnia' },
      { flag: 'qat.svg', name: 'Qatar' },
      { flag: 'sui.svg', name: 'Suiza', href: '#suiza' },
    ],
    anchor: '    </div>\n    \n    <!-- ─── BOSNIA Y HERZEGOVINA ─── -->',
  },
  {
    letter: 'c',
    teams: [
      { flag: 'bra.svg', name: 'Brasil', href: '#brasil' },
      { flag: 'mar.svg', name: 'Marruecos' },
      { flag: 'hti.svg', name: 'Haití', href: '#haiti' },
      { flag: 'sco.svg', name: 'Escocia', href: '#escocia' },
    ],
    anchor: '    </div>\n    \n    <!-- ─── BRASIL ─── -->',
  },
  {
    letter: 'e',
    teams: [
      { flag: 'ger.svg', name: 'Alemania', href: '#alemania' },
      { flag: 'civ.svg', name: 'Costa de Marfil', href: '#costa-marfil' },
      { flag: 'ecu.svg', name: 'Ecuador' },
      { flag: 'cuw.svg', name: 'Curazao', href: '#curazao' },
    ],
    anchor: '    </div>\n    \n    <!-- ─── COSTA DE MARFIL ─── -->',
  },
  {
    letter: 'f',
    teams: [
      { flag: 'ned.svg', name: 'Países Bajos' },
      { flag: 'jpn.svg', name: 'Japón', href: '#japon' },
      { flag: 'swe.svg', name: 'Suecia', href: '#suecia' },
      { flag: 'tun.svg', name: 'Túnez', href: '#tunez' },
    ],
    anchor: '    </div>\n    \n    <!-- ─── SUECIA ─── -->',
  },
  {
    letter: 'g',
    teams: [
      { flag: 'bel.svg', name: 'Bélgica', href: '#belgica' },
      { flag: 'egy.svg', name: 'Egipto' },
      { flag: 'irn.svg', name: 'Irán' },
      { flag: 'nzl.svg', name: 'Nueva Zelanda', href: '#nueva-zelanda' },
    ],
    anchor: '    </div>\n    \n    <!-- ─── BÉLGICA ─── -->',
  },
  {
    letter: 'h',
    teams: [
      { flag: 'esp.svg', name: 'España' },
      { flag: 'ury.svg', name: 'Uruguay' },
      { flag: 'ksa.svg', name: 'Arabia Saudita' },
      { flag: 'cpv.svg', name: 'Cabo Verde', href: '#cabo-verde' },
    ],
    anchor: '    </div>\n    \n    <!-- ─── CABO VERDE ─── -->',
  },
  {
    letter: 'i',
    teams: [
      { flag: 'fra.svg', name: 'Francia', href: '#francia' },
      { flag: 'nor.svg', name: 'Noruega', href: '#noruega' },
      { flag: 'sen.svg', name: 'Senegal' },
      { flag: 'irq.svg', name: 'Irak' },
    ],
    anchor: '    </div>\n    \n    <!-- ─── FRANCIA ─── -->',
  },
  {
    letter: 'j',
    teams: [
      { flag: 'arg.svg', name: 'Argentina' },
      { flag: 'aut.svg', name: 'Austria', href: '#austria' },
      { flag: 'alg.svg', name: 'Argelia' },
      { flag: 'jor.svg', name: 'Jordania' },
    ],
    anchor: '    </div>\n    \n    <!-- ─── AUSTRIA ─── -->',
  },
  {
    letter: 'k',
    teams: [
      { flag: 'por.svg', name: 'Portugal', href: '#portugal' },
      { flag: 'col.svg', name: 'Colombia' },
      { flag: 'cod.svg', name: 'RD del Congo', href: '#rd-congo' },
      { flag: 'uzb.svg', name: 'Uzbekistán' },
    ],
    anchor: '    </div>\n    \n    <!-- ─── PORTUGAL ─── -->',
  },
  {
    letter: 'l',
    teams: [
      { flag: 'eng.svg', name: 'Inglaterra', href: '#inglaterra' },
      { flag: 'cro.svg', name: 'Croacia' },
      { flag: 'gha.svg', name: 'Ghana' },
      { flag: 'pan.svg', name: 'Panamá' },
    ],
    anchor: '    </div>\n    \n    <!-- ─── INGLATERRA ─── -->',
  },
];

// ── INJECT ────────────────────────────────────────────────────────────────────
groups.forEach(function(g) {
  const block = standingsBlock(g.letter, g.teams);
  const replacement = block + '\n    <!-- ─── ' + g.anchor.split('<!-- ─── ')[1];
  if (h.includes(g.anchor)) {
    h = h.replace(g.anchor, replacement);
    log.push('✓ Grupo ' + g.letter.toUpperCase() + ': tabla inyectada');
  } else {
    log.push('✗ NOT FOUND: Grupo ' + g.letter.toUpperCase());
  }
});

// ── GUARDAR ───────────────────────────────────────────────────────────────────
const out = crlf ? h.replace(/\n/g, '\r\n') : h;
fs.writeFileSync('index.html', out, 'utf8');
console.log(log.join('\n'));
console.log('\n✓ index.html actualizado.');
