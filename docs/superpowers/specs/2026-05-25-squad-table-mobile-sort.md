# Spec: Squad table — datos completos + orden + mobile expandible

**Fecha:** 2026-05-25
**Scope:** `index.html` (CSS inline + JS inline). Sin dependencias externas.

---

## Problema

1. **Datos incompletos:** Costa de Marfil, Austria y RD Congo tienen 22 jugadores en lugar de 26.
2. **Orden arbitrario:** Los 26 convocados aparecen en orden del artículo de AlterFutbol, no por criterio de visualización.
3. **Mobile:** La tabla requiere rotar el teléfono para ver todas las columnas. El breakpoint ≤600px ya oculta columnas, pero no es suficiente.

---

## Cambios

### 1 — Jugadores faltantes (12 filas HTML)

Añadir al final del `<tbody>` de cada sección (el sort del paso 2 los reordenará):

#### Costa de Marfil
| # | Pos | Jugador | Edad | Club | País club | ELO | Titular |
|---|-----|---------|------|------|-----------|-----|---------|
| 23 | DEL | Elye Wahi | 23 | OGC Nice | Francia | lookup | — |
| 24 | DEL | Yan Diomandé | 19 | RB Leipzig | Alemania | 1698 | Sí |
| 25 | DEL | Ange-Yoan Bonny | 22 | Inter de Milán | Italia | 1876 | Sí |
| 26 | DEL | Oumar Diakité | 22 | Cercle Brugge | Bélgica | lookup | — |

#### Austria
| # | Pos | Jugador | Edad | Club | País club | ELO | Titular |
|---|-----|---------|------|------|-----------|-----|---------|
| 23 | MED | Alessandro Schöpf | 32 | Wolfsberger AC | Austria | N/D | — |
| 24 | DEL | Marko Arnautovic | 37 | Crvena Zvezda | Serbia | 1264 | Sí |
| 25 | DEL | Michael Gregoritsch | 32 | FC Augsburg | Alemania | 1526 | — |
| 26 | DEL | Sasa Kalajdzic | 28 | LASK Linz | Austria | N/D | — |

#### RD del Congo
| # | Pos | Jugador | Edad | Club | País club | ELO | Titular |
|---|-----|---------|------|------|-----------|-----|---------|
| 23 | DEL | Cédric Bakambu | 35 | Real Betis | España | 1661 | Sí |
| 24 | DEL | Yoane Wissa | 29 | Newcastle United | Inglaterra | 1736 | Sí |
| 25 | DEL | Fiston Kalala Mayele | 31 | Pyramids FC | Egipto | N/D | — |
| 26 | DEL | Simon Banza | 29 | Al-Jazira Club | EAU | N/D | — |

> ELO "lookup": buscar en worldclubratings.com durante implementación. Si el club no aparece → N/D.
> INSTRUCTIONS.md Tarea 2 y Tarea 1: actualizar filas de CIV, AUT y COD con conteos finales.

---

### 2 — Orden de filas: JS sort en DOMContentLoaded

Añadir un bloque JS inline (junto al bloque de ELO color coding, línea ~2909):

```js
// ── SQUAD TABLE SORT ─────────────────────────────────────────────────────
(function sortSquadTables() {
  var posOrder = { 'pos-gk': 0, 'pos-def': 1, 'pos-med': 2, 'pos-del': 3 };
  document.querySelectorAll('.squad-table tbody').forEach(function(tbody) {
    var rows = Array.from(tbody.querySelectorAll('tr'));
    rows.sort(function(a, b) {
      var pa = posOrder[a.querySelector('.pos-badge').className.split(' ').find(c => posOrder[c] !== undefined)] ?? 9;
      var pb = posOrder[b.querySelector('.pos-badge').className.split(' ').find(c => posOrder[c] !== undefined)] ?? 9;
      if (pa !== pb) return pa - pb;
      var ta = a.querySelector('.titl-yes') ? 0 : 1;
      var tb = b.querySelector('.titl-yes') ? 0 : 1;
      if (ta !== tb) return ta - tb;
      var ea = parseInt(a.querySelector('.elo-cell').textContent) || 0;
      var eb = parseInt(b.querySelector('.elo-cell').textContent) || 0;
      return eb - ea;
    });
    rows.forEach(function(r) { tbody.appendChild(r); });
  });
})();
```

**Criterio de orden:**
1. Posición: GK → DEF → MED → DEL
2. Titular: Sí primero, luego —
3. ELO del club: descendente; N/D (→ 0) al final de su grupo

**Aplica a todas las tablas** (18 actuales + futuras). Se ejecuta una vez al cargar.

---

### 3 — Mobile expandible: CSS + JS

#### CSS — reemplazar bloque `/* Squad table */` dentro de `@media (max-width: 600px)`

```css
/* Squad table mobile: modo expandible */
.squad-wrap { border-radius: 8px; }
.squad-table { font-size: 13px; }

/* Ocultar cabeceras de columnas no visibles */
.squad-table thead th:nth-child(1),  /* # */
.squad-table thead th:nth-child(4),  /* Edad */
.squad-table thead th:nth-child(5),  /* Club */
.squad-table thead th:nth-child(6),  /* País */
.squad-table thead th:nth-child(7),  /* ELO */
.squad-table thead th:nth-child(8)   /* Titular */
{ display: none; }

/* Columna de chevron (9ª, inyectada por JS) */
.squad-table thead th:nth-child(9) { display: table-cell; width: 28px; }

/* Ocultar celdas de columnas no visibles */
.squad-table tbody td:nth-child(1),
.squad-table tbody td:nth-child(4),
.squad-table tbody td:nth-child(5),
.squad-table tbody td:nth-child(6),
.squad-table tbody td:nth-child(7),
.squad-table tbody td:nth-child(8)
{ display: none; }

/* Chevron TD inyectado */
.sq-chev {
  width: 28px; text-align: center; vertical-align: middle;
  color: var(--muted); font-size: 1rem; cursor: pointer;
  transition: transform .2s, color .2s;
  user-select: none;
}
.sq-open .sq-chev { transform: rotate(90deg); color: var(--accent); }

/* Fila de detalle expandida */
.sq-detail td {
  padding: .35rem .65rem .55rem 2rem;
  background: rgba(0,196,160,.04);
  border-bottom: 1px solid var(--border);
}
.sq-detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: .3rem .5rem;
}
.sq-detail-item .sq-dlabel {
  font-size: .58rem; text-transform: uppercase;
  letter-spacing: .06em; color: var(--muted); margin-bottom: .08rem;
}
.sq-detail-item .sq-dval { font-size: .75rem; color: var(--white); }
```

#### JS — añadir bloque tras el sort (dentro del mismo DOMContentLoaded o bloque `<script>`)

```js
// ── SQUAD TABLE MOBILE EXPAND ────────────────────────────────────────────
(function setupSquadExpand() {
  if (window.innerWidth > 600) return;

  document.querySelectorAll('.squad-table').forEach(function(tbl) {
    // Añadir th de chevron
    var th = tbl.querySelector('thead tr');
    if (th) th.insertAdjacentHTML('beforeend', '<th></th>');

    tbl.querySelectorAll('tbody tr').forEach(function(row) {
      // Añadir td de chevron
      row.insertAdjacentHTML('beforeend', '<td class="sq-chev">›</td>');

      row.addEventListener('click', function() {
        var isOpen = row.classList.contains('sq-open');
        // Cerrar cualquier fila abierta en esta tabla
        tbl.querySelectorAll('tr.sq-open').forEach(function(r) {
          r.classList.remove('sq-open');
          var d = r.nextElementSibling;
          if (d && d.classList.contains('sq-detail')) d.remove();
        });
        if (isOpen) return;

        // Leer datos de celdas ocultas
        var cells = row.querySelectorAll('td');
        var edad   = cells[3] ? cells[3].textContent.trim() : '';
        var club   = cells[4] ? cells[4].textContent.trim() : '';
        var pais   = cells[5] ? cells[5].textContent.trim() : '';
        var eloTd  = cells[6];
        var eloVal = eloTd ? eloTd.textContent.trim() : 'N/D';
        var eloClass = eloTd ? Array.from(eloTd.classList).find(c => c.startsWith('elo-')) || '' : '';
        var titl   = cells[7] ? cells[7].querySelector('.titl-yes') ? 'Sí' : '—' : '';
        var titlCls = titl === 'Sí' ? 'titl-yes' : 'titl-pending';

        row.classList.add('sq-open');
        row.insertAdjacentHTML('afterend',
          '<tr class="sq-detail"><td colspan="3">' +
          '<div class="sq-detail-grid">' +
            '<div class="sq-detail-item"><div class="sq-dlabel">Edad</div><div class="sq-dval">' + edad + '</div></div>' +
            '<div class="sq-detail-item"><div class="sq-dlabel">Club</div><div class="sq-dval">' + club + '</div></div>' +
            '<div class="sq-detail-item"><div class="sq-dlabel">País</div><div class="sq-dval">' + pais + '</div></div>' +
            '<div class="sq-detail-item"><div class="sq-dlabel">ELO</div><div class="sq-dval ' + eloClass + '">' + eloVal + '</div></div>' +
            '<div class="sq-detail-item"><div class="sq-dlabel">Titular</div><div class="sq-dval"><span class="' + titlCls + '">' + titl + '</span></div></div>' +
          '</div></td></tr>'
        );
      });
    });
  });
})();
```

**Comportamiento:**
- Solo se activa si `window.innerWidth ≤ 600` en el momento de carga.
- Una sola fila abierta por tabla a la vez; clic en la misma la cierra.
- Los datos del detalle se leen de las celdas ya existentes (no se duplican en el HTML).
- El sort del paso 2 ya corrió antes, así que el orden es correcto.

---

## Orden de implementación

1. Añadir 12 filas HTML (los 3 `<tbody>` de CIV / AUT / COD).
2. Actualizar INSTRUCTIONS.md (Tarea 1 y Tarea 2 para esos 3 equipos).
3. Añadir bloque JS de sort (línea ~2917, tras el ELO color coding).
4. Reemplazar CSS mobile de squad-table.
5. Añadir bloque JS de expand mobile.
6. Verificar en Playwright (375px): sort correcto, expand funciona, sin scroll horizontal.
7. Verificar en desktop (1280px): tabla sin cambios, sort aplicado.

---

## Archivos modificados

- `index.html` — CSS mobile squad + JS sort + JS expand + 12 filas HTML
- `claude/INSTRUCTIONS.md` — Tarea 1 (extensiones .webp) y Tarea 2 (CIV/AUT/COD counts)
