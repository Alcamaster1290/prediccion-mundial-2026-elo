/**
 * bracket.js — Llave Eliminatoria Mundial 2026
 * Renderiza el bracket de 32 equipos con conectores CSS (Approach C).
 * El win% (qualified_pct de fase de grupos) es premium-gate.
 * Expone: window.BracketSection
 */
(function () {
  'use strict';

  /* ── Datos de grupos ── */
  var GROUP_TEAMS = {
    A:['mex','zaf','kor','cze'], B:['can','bih','qat','sui'],
    C:['bra','mar','hti','sco'], D:['usa','pry','aus','tur'],
    E:['ger','cuw','civ','ecu'], F:['ned','jpn','swe','tun'],
    G:['bel','egy','irn','nzl'], H:['esp','cpv','ksa','ury'],
    I:['fra','sen','irq','nor'], J:['arg','alg','aut','jor'],
    K:['por','cod','uzb','col'], L:['eng','cro','gha','pan'],
  };
  var NAMES = {
    mex:'México',   zaf:'Sudáfrica',  kor:'Corea del Sur',cze:'Chequia',
    can:'Canadá',   bih:'Bosnia',     qat:'Qatar',        sui:'Suiza',
    bra:'Brasil',   mar:'Marruecos',  hti:'Haití',        sco:'Escocia',
    usa:'EE.UU.',   pry:'Paraguay',   aus:'Australia',    tur:'Turquía',
    ger:'Alemania', cuw:'Curazao',    civ:'C. de Marfil', ecu:'Ecuador',
    ned:'P.Bajos',  jpn:'Japón',      swe:'Suecia',       tun:'Túnez',
    bel:'Bélgica',  egy:'Egipto',     irn:'Irán',         nzl:'N.Zelanda',
    esp:'España',   cpv:'Cabo Verde', ksa:'A.Saudita',    ury:'Uruguay',
    fra:'Francia',  sen:'Senegal',    irq:'Irak',         nor:'Noruega',
    arg:'Argentina',alg:'Argelia',    aut:'Austria',      jor:'Jordania',
    por:'Portugal', cod:'RD Congo',   uzb:'Uzbekistán',   col:'Colombia',
    eng:'Inglaterra',cro:'Croacia',   gha:'Ghana',        pan:'Panamá',
  };

  /* ── Estructura del bracket ──
     Cada slot: { slot: 'pos:group|W:num', label: 'texto visible' }
     Pairs = dos matches que alimentan el mismo match de la siguiente ronda. */
  var STRUCTURE = {
    left: {
      r32: [
        [{num:74,h:{s:'1:E',l:'1.° E'},a:{s:'3:A/B/C/D/F',l:'Mejor 3.°'}},
         {num:77,h:{s:'1:I',l:'1.° I'},a:{s:'3:C/D/F/G/H',l:'Mejor 3.°'}}],
        [{num:73,h:{s:'2:A',l:'2.° A'},a:{s:'2:B',l:'2.° B'}},
         {num:75,h:{s:'1:F',l:'1.° F'},a:{s:'2:C',l:'2.° C'}}],
        [{num:83,h:{s:'2:K',l:'2.° K'},a:{s:'2:L',l:'2.° L'}},
         {num:84,h:{s:'1:H',l:'1.° H'},a:{s:'2:J',l:'2.° J'}}],
        [{num:81,h:{s:'1:D',l:'1.° D'},a:{s:'3:B/E/F/I/J',l:'Mejor 3.°'}},
         {num:82,h:{s:'1:G',l:'1.° G'},a:{s:'3:A/E/H/I/J',l:'Mejor 3.°'}}],
      ],
      r16: [
        [{num:89,h:{s:'W:74',l:'G. P.74'},a:{s:'W:77',l:'G. P.77'}},
         {num:90,h:{s:'W:73',l:'G. P.73'},a:{s:'W:75',l:'G. P.75'}}],
        [{num:93,h:{s:'W:83',l:'G. P.83'},a:{s:'W:84',l:'G. P.84'}},
         {num:94,h:{s:'W:81',l:'G. P.81'},a:{s:'W:82',l:'G. P.82'}}],
      ],
      qf: [
        [{num:97,h:{s:'W:89',l:'G. P.89'},a:{s:'W:90',l:'G. P.90'}},
         {num:98,h:{s:'W:93',l:'G. P.93'},a:{s:'W:94',l:'G. P.94'}}],
      ],
      sf: [{num:101,h:{s:'W:97',l:'G. P.97'},a:{s:'W:98',l:'G. P.98'}}],
    },
    final: {num:104,h:{s:'W:101',l:'G. P.101'},a:{s:'W:102',l:'G. P.102'}},
    right: {
      sf: [{num:102,h:{s:'W:99',l:'G. P.99'},a:{s:'W:100',l:'G. P.100'}}],
      qf: [
        [{num:99, h:{s:'W:91',l:'G. P.91'},a:{s:'W:92',l:'G. P.92'}},
         {num:100,h:{s:'W:95',l:'G. P.95'},a:{s:'W:96',l:'G. P.96'}}],
      ],
      r16: [
        [{num:91,h:{s:'W:76',l:'G. P.76'},a:{s:'W:78',l:'G. P.78'}},
         {num:92,h:{s:'W:79',l:'G. P.79'},a:{s:'W:80',l:'G. P.80'}}],
        [{num:95,h:{s:'W:86',l:'G. P.86'},a:{s:'W:88',l:'G. P.88'}},
         {num:96,h:{s:'W:85',l:'G. P.85'},a:{s:'W:87',l:'G. P.87'}}],
      ],
      r32: [
        [{num:76,h:{s:'1:C',l:'1.° C'},a:{s:'2:F',l:'2.° F'}},
         {num:78,h:{s:'2:E',l:'2.° E'},a:{s:'2:I',l:'2.° I'}}],
        [{num:79,h:{s:'1:A',l:'1.° A'},a:{s:'3:C/E/F/H/I',l:'Mejor 3.°'}},
         {num:80,h:{s:'1:L',l:'1.° L'},a:{s:'3:E/H/I/J/K',l:'Mejor 3.°'}}],
        [{num:86,h:{s:'1:J',l:'1.° J'},a:{s:'2:H',l:'2.° H'}},
         {num:88,h:{s:'2:D',l:'2.° D'},a:{s:'2:G',l:'2.° G'}}],
        [{num:85,h:{s:'1:B',l:'1.° B'},a:{s:'3:E/F/G/I/J',l:'Mejor 3.°'}},
         {num:87,h:{s:'1:K',l:'1.° K'},a:{s:'3:D/E/I/J/L',l:'Mejor 3.°'}}],
      ],
    },
    third: {num:103,h:{s:'L:101',l:'Perdedor P.101'},a:{s:'L:102',l:'Perdedor P.102'}},
  };

  /* ── Build team-by-position map ── */
  var teamsByGroup = {};

  function buildTeamsByGroup(mc) {
    Object.keys(GROUP_TEAMS).forEach(function (g) {
      var teams = GROUP_TEAMS[g];
      var top = function (key) {
        return teams.slice().sort(function (a, b) {
          return ((mc[b] || {})[key] || 0) - ((mc[a] || {})[key] || 0);
        })[0];
      };
      teamsByGroup[g] = { 1: top('first_pct'), 2: top('second_pct'), 3: top('best_third_pct') };
    });
  }

  function getBestThird(groupsStr, mc) {
    var best = null, bestPct = -1;
    groupsStr.split('/').forEach(function (g) {
      var t = (teamsByGroup[g] || {})[3];
      if (!t) return;
      var p = (mc[t] || {}).best_third_pct || 0;
      if (p > bestPct) { bestPct = p; best = t; }
    });
    return best;
  }

  function resolveSlot(slotCode, mc) {
    var parts = slotCode.split(':'), pos = parts[0], val = parts[1];
    if (pos === 'W' || pos === 'L') return null;
    if (pos === '1' || pos === '2') return (teamsByGroup[val] || {})[+pos] || null;
    if (pos === '3') return getBestThird(val, mc);
    return null;
  }

  /* ── HTML rendering ── */
  function slot(slotCode, label, mc) {
    var code = mc ? resolveSlot(slotCode, mc) : null;
    var isTbd = !code;
    var name  = code ? (NAMES[code] || code.toUpperCase()) : label;
    var pct   = (code && mc && mc[code]) ? (mc[code].qualified_pct || 0).toFixed(1) + '%' : '—';
    var flag  = code
      ? '<img class="bk-flag" src="assets/flags/' + code + '.svg" alt="' + (NAMES[code] || code) + '" loading="lazy">'
      : '<span class="bk-flag-ph"></span>';
    return '<div class="bk-slot' + (isTbd ? ' bk-slot--tbd' : '') + '" data-slot="' + slotCode + '">'
      + flag
      + '<div class="bk-slot-info">'
      + '<span class="bk-slot-name">' + name + '</span>'
      + '<span class="bk-slot-tag">' + label + '</span>'
      + '</div>'
      + '<span class="bk-pct">' + pct + '</span>'
      + '</div>';
  }

  function match(m, mc, isFinal) {
    return '<div class="bk-match' + (isFinal ? ' bk-match--final' : '') + '" data-match="' + m.num + '">'
      + '<div class="bk-match-num">P.' + m.num + '</div>'
      + slot(m.h.s, m.h.l, mc)
      + slot(m.a.s, m.a.l, mc)
      + '</div>';
  }

  function renderPairs(pairs, mc) {
    return pairs.map(function (pair) {
      return '<div class="bk-pair">' + pair.map(function (m) { return match(m, mc); }).join('') + '</div>';
    }).join('');
  }

  function renderCol(roundClass, labelText, pairs, mc) {
    return '<div class="bk-col-wrap">'
      + '<div class="bk-round-label">' + labelText + '</div>'
      + '<div class="bk-col ' + roundClass + '">'
      + renderPairs(pairs, mc)
      + '</div></div>';
  }

  function renderSingle(roundClass, labelText, m, mc, isFinal) {
    return '<div class="bk-col-wrap">'
      + '<div class="bk-round-label">' + labelText + '</div>'
      + '<div class="bk-col ' + roundClass + '">'
      + '<div class="bk-pair">'
      + match(m, mc, isFinal)
      + '</div></div></div>';
  }

  function renderThird(m, mc) {
    var h = m.h, a = m.a;
    return '<div class="bk-third-wrap">'
      + '<div class="bk-third-label">3.er Puesto · P.103 · 18 Jul</div>'
      + '<div class="bk-third-match">'
      + '<div class="bk-slot bk-slot--tbd" data-slot="' + h.s + '">'
      + '<span class="bk-slot-info"><span class="bk-slot-name">' + h.l + '</span></span></div>'
      + '<span style="color:var(--muted);font-size:12px;padding:0 4px">vs</span>'
      + '<div class="bk-slot bk-slot--tbd" data-slot="' + a.s + '">'
      + '<span class="bk-slot-info"><span class="bk-slot-name">' + a.l + '</span></span></div>'
      + '</div></div>';
  }

  function renderBracket(mc) {
    var S = STRUCTURE;
    var spc = '<div class="bk-spc"></div>';
    var spcF = '<div class="bk-spc bk-spc-final"></div>';

    var left =
      '<div class="bk-side bk-side-l">'
      + renderCol('bk-col-r32',  '16avos de Final', S.left.r32, mc)
      + spc
      + renderCol('bk-col-r16',  'Octavos de Final', S.left.r16, mc)
      + spc
      + renderCol('bk-col-qf',   'Cuartos de Final', S.left.qf, mc)
      + spc
      + renderSingle('bk-col-sf','Semifinal', S.left.sf[0], mc)
      + spcF
      + '</div>';

    var final_ =
      '<div class="bk-col-wrap">'
      + '<div class="bk-round-label">&#x1F3C6; Final</div>'
      + '<div class="bk-col bk-col-final">'
      + '<div class="bk-pair">'
      + match(S.final, mc, true)
      + '</div></div></div>';

    var right =
      '<div class="bk-side bk-side-r">'
      + spcF
      + renderSingle('bk-col-sf','Semifinal', S.right.sf[0], mc)
      + spc
      + renderCol('bk-col-qf',   'Cuartos de Final', S.right.qf, mc)
      + spc
      + renderCol('bk-col-r16',  'Octavos de Final', S.right.r16, mc)
      + spc
      + renderCol('bk-col-r32',  '16avos de Final', S.right.r32, mc)
      + '</div>';

    return left + final_ + right;
  }

  /* ── Premium gate ── */
  function setPremiumState(isPremium) {
    var el = document.getElementById('bracket-inner');
    if (el) el.classList.toggle('bk-locked', !isPremium);
    var note = document.getElementById('bk-premium-note');
    if (note) note.style.display = isPremium ? 'none' : '';
  }

  /* ── Init ── */
  function init() {
    var inner = document.getElementById('bracket-inner');
    if (!inner) return;

    // Render static structure first (no mc data yet)
    inner.innerHTML = renderBracket(null);
    inner.classList.add('bk-locked');

    fetch('data/mc_results.json')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var mc = data.teams || data;
        buildTeamsByGroup(mc);
        inner.innerHTML = renderBracket(mc);
      })
      .catch(function () { /* labels remain as-is */ });
  }

  window.BracketSection = { init: init, setPremiumState: setPremiumState };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
