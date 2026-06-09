/**
 * predicciones.js — Sección Premium "Predicciones Monte Carlo"
 * Expone: window.PredicionesSection
 * Requiere: window.SupaAuth (auth.js)
 */
(function () {
  'use strict';

  var GROUP_TEAMS = {
    A: ['mex','zaf','kor','cze'], B: ['can','bih','qat','sui'],
    C: ['bra','mar','hti','sco'], D: ['usa','pry','aus','tur'],
    E: ['ger','cuw','civ','ecu'], F: ['ned','jpn','swe','tun'],
    G: ['bel','egy','irn','nzl'], H: ['esp','cpv','ksa','ury'],
    I: ['fra','sen','irq','nor'], J: ['arg','alg','aut','jor'],
    K: ['por','cod','uzb','col'], L: ['eng','cro','gha','pan'],
  };
  var GROUP_ORDER = ['A','B','C','D','E','F','G','H','I','J','K','L'];
  var POINT_TOTALS = ['0','1','2','3','4','5','6','7','9'];
  var ACCESS_READY_MESSAGE = 'Todo desbloqueado. Ya puedes ver todas las predicciones.';

  /* reverse map: team_code → group letter */
  var TEAM_GROUP = {};
  Object.keys(GROUP_TEAMS).forEach(function (g) {
    GROUP_TEAMS[g].forEach(function (code) { TEAM_GROUP[code] = g; });
  });

  var R32 = [
    {num:73, home:{t:'2',g:'A'}, away:{t:'2',g:'B'}},
    {num:74, home:{t:'1',g:'E'}, away:{t:'3',gs:['A','B','C','D','F']}},
    {num:75, home:{t:'1',g:'F'}, away:{t:'2',g:'C'}},
    {num:76, home:{t:'1',g:'C'}, away:{t:'2',g:'F'}},
    {num:77, home:{t:'1',g:'I'}, away:{t:'3',gs:['C','D','F','G','H']}},
    {num:78, home:{t:'2',g:'E'}, away:{t:'2',g:'I'}},
    {num:79, home:{t:'1',g:'A'}, away:{t:'3',gs:['C','E','F','H','I']}},
    {num:80, home:{t:'1',g:'L'}, away:{t:'3',gs:['E','H','I','J','K']}},
    {num:81, home:{t:'1',g:'D'}, away:{t:'3',gs:['B','E','F','I','J']}},
    {num:82, home:{t:'1',g:'G'}, away:{t:'3',gs:['A','E','H','I','J']}},
    {num:83, home:{t:'2',g:'K'}, away:{t:'2',g:'L'}},
    {num:84, home:{t:'1',g:'H'}, away:{t:'2',g:'J'}},
    {num:85, home:{t:'1',g:'B'}, away:{t:'3',gs:['E','F','G','I','J']}},
    {num:86, home:{t:'1',g:'J'}, away:{t:'2',g:'H'}},
    {num:87, home:{t:'1',g:'K'}, away:{t:'3',gs:['D','E','I','J','L']}},
    {num:88, home:{t:'2',g:'D'}, away:{t:'2',g:'G'}},
  ];

  var NAMES = {
    mex:'México', zaf:'Sudáfrica', kor:'Corea del Sur', cze:'Chequia',
    can:'Canadá', bih:'Bosnia', qat:'Qatar', sui:'Suiza',
    bra:'Brasil', mar:'Marruecos', hti:'Haití', sco:'Escocia',
    ger:'Alemania', cuw:'Curazao', civ:'Costa de Marfil', ecu:'Ecuador',
    ned:'Países Bajos', jpn:'Japón', swe:'Suecia', tun:'Túnez',
    bel:'Bélgica', egy:'Egipto', irn:'Irán', nzl:'Nueva Zelanda',
    esp:'España', cpv:'Cabo Verde', ksa:'Arabia Saudita', ury:'Uruguay',
    fra:'Francia', sen:'Senegal', irq:'Irak', nor:'Noruega',
    arg:'Argentina', alg:'Argelia', aut:'Austria', jor:'Jordania',
    por:'Portugal', cod:'RD Congo', uzb:'Uzbekistán', col:'Colombia',
    eng:'Inglaterra', cro:'Croacia', gha:'Ghana', pan:'Panamá',
    usa:'EE.UU.', pry:'Paraguay', aus:'Australia', tur:'Turquía'
  };

  function flag(code) {
    var name = NAMES[code] || code;
    return '<img class="flag-svg" src="assets/flags/' + code + '.svg" alt="' + name + '" loading="lazy">';
  }

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function safeTeamCode(code) {
    var value = String(code || '').toLowerCase();
    return /^[a-z0-9]{3}$/.test(value) ? value : '';
  }

  function modelFlag(code, name) {
    var safeCode = safeTeamCode(code);
    if (!safeCode) return '';
    return '<img class="flag-svg" src="assets/flags/' + safeCode + '.svg" alt="' + escapeHtml(name || safeCode) + '" loading="lazy">';
  }

  // ── Carga de datos desde Supabase ────────────────────────────

  async function loadSimulationData() {
    if (window.SupaData && window.SupaData.loadSimulationData) {
      return await window.SupaData.loadSimulationData();
    }
    var c = window.SupaAuth && window.SupaAuth.getClient();
    if (!c) return null;

    var runRef = await c
      .from('simulation_runs')
      .select('*')
      .eq('is_active', true)
      .order('created_at', { ascending: false })
      .limit(1)
      .single();
    if (runRef.error || !runRef.data) return null;
    var runId = runRef.data.id;

    var standRef = await c
      .from('simulation_group_standings')
      .select('*')
      .eq('simulation_run', runId);
    if (standRef.error) return null;

    var terRef = await c
      .from('simulation_terceros_table')
      .select('*')
      .eq('simulation_run', runId)
      .order('rank');

    var terceros = terRef.error ? [] : (terRef.data || []);
    terceros = terceros.map(function(row) {
      if (!row.group_id && row.group) row.group_id = row.group;
      return row;
    });

    return {
      run:      runRef.data,
      standings: standRef.data || [],
      terceros:  terceros,
    };
  }

  // ── Ghost table para blur preview ────────────────────────────

  async function loadEloModelExplainer() {
    var c = window.SupaAuth && window.SupaAuth.getClient();
    if (!c) return null;

    try {
      var ref = await c.rpc('get_elo_model_explainer');
      if (ref.error || !ref.data || ref.data.success === false) return null;
      return ref.data;
    } catch (e) {
      return null;
    }
  }

  async function loadEmbeddedPronosticos() {
    if (!window.PremiumSection || !window.PremiumSection.loadPredictions) return [];
    try {
      return await window.PremiumSection.loadPredictions();
    } catch (e) {
      return [];
    }
  }

  function renderEmbeddedPronosticos(predictions) {
    if (!window.PremiumSection || !window.PremiumSection.renderActiveContent) return '';
    return window.PremiumSection.renderActiveContent(predictions, {
      embedded: true,
      includeTitle: true,
      includeBadge: false
    });
  }

  function renderGhostTable() {
    var html = '<div class="pred-ghost-rows">';
    for (var i = 0; i < 6; i++) {
      html += '<div class="pred-ghost-row"><div></div><div></div><div></div><div></div></div>';
    }
    html += '</div>';
    return html;
  }

  function pctNumber(value) {
    var n = parseFloat(value);
    return isNaN(n) ? 0 : n;
  }

  function formatPct(value) {
    var n = pctNumber(value);
    var rounded = Math.round(n * 10) / 10;
    if (Math.abs(rounded - Math.round(rounded)) < 0.05) return String(Math.round(rounded));
    return rounded.toFixed(1);
  }

  function pctText(value) {
    return formatPct(value) + '%';
  }

  function qualifyClass(value) {
    var q = pctNumber(value);
    return q >= 99 ? 'pred-q-100' : q >= 70 ? 'pred-q-high' : q >= 40 ? 'pred-q-mid' : 'pred-q-low';
  }

  function groupColor(group) {
    return 'var(--grp-' + String(group).toLowerCase() + ')';
  }

  function getPointsData(row) {
    var raw = row && row.points_pct ? row.points_pct : {};
    if (typeof raw === 'string') {
      try { raw = JSON.parse(raw); } catch (e) { raw = {}; }
    }

    var values = {};
    var hasData = false;
    POINT_TOTALS.forEach(function(points) {
      var n = pctNumber(raw[points]);
      values[points] = n;
      if (n > 0) hasData = true;
    });

    return { values: values, hasData: hasData };
  }

  function topPointsBucket(pointsData) {
    if (!pointsData || !pointsData.hasData) return null;
    var best = { points: POINT_TOTALS[0], pct: -1 };
    POINT_TOTALS.forEach(function(points) {
      var value = pointsData.values[points] || 0;
      if (value > best.pct || (value === best.pct && parseInt(points, 10) > parseInt(best.points, 10))) {
        best = { points: points, pct: value };
      }
    });
    return best;
  }

  function formatModelValue(value, decimals) {
    var n = parseFloat(value);
    if (isNaN(n)) return '-';
    var digits = typeof decimals === 'number' ? decimals : 1;
    return n.toLocaleString('es-PE', {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits
    });
  }

  function eloTierClass(tier) {
    if (tier === 'xi_blend_ready') return 'pred-elo-status-ready';
    if (tier === 'needs_player_elo') return 'pred-elo-status-needs';
    return 'pred-elo-status-base';
  }

  function renderEloModelExplainer(payload) {
    if (!payload || !payload.success) {
      return '<section class="pred-elo-model pred-elo-model-empty">'
        + '<div class="pred-elo-copy">'
        + '<span class="pred-elo-kicker">Modelo ELO</span>'
        + '<h3>Calculo de fuerza por seleccion</h3>'
        + '<p>La explicacion del modelo se carga desde Supabase para usuarios con acceso completo. Las probabilidades de la simulacion siguen disponibles abajo.</p>'
        + '</div>'
        + '</section>';
    }

    var summary = payload.summary || {};
    var model = payload.model || {};
    var teams = Array.isArray(payload.teams) ? payload.teams : [];
    var readyTeams = teams.filter(function(team) {
      return team.coverage_tier === 'xi_blend_ready';
    }).slice(0, 8);
    var avgXiBlend = model.avg_xi_blend;
    var avgXiBlendText = formatModelValue(avgXiBlend, 1);
    var clubAdjWeight = model.club_adj_weight == null ? 0.35 : model.club_adj_weight;
    var clubAdjWeightText = formatModelValue(clubAdjWeight, 2);
    var ratingDate = model.rating_date ? ' (' + escapeHtml(model.rating_date) + ')' : '';
    var sourceText = 'ELO internacional: ' + escapeHtml(model.elo_source || 'international-football.net')
      + ratingDate
      + '; ELO clubes: ' + escapeHtml(model.club_elo_source || 'worldclubratings.com') + '.';
    var baseGoals = model.base_goals_per_team == null ? 1.25 : parseFloat(model.base_goals_per_team);
    var totalGoalsText = isNaN(baseGoals) ? '-' : formatModelValue(baseGoals * 2, 1);
    var eloScale = model.elo_scale == null ? 400 : model.elo_scale;
    var eloScaleText = formatModelValue(eloScale, 0);
    var calibrationText = '';
    if (model.elo_lambda_scale != null) {
      calibrationText += ' &middot; escala goles ' + formatModelValue(model.elo_lambda_scale, 0);
    }
    if (model.draw_bias != null) {
      calibrationText += ' &middot; ajuste empate ' + formatModelValue(model.draw_bias, 2);
    }
    var xiMatchupWeight = model.xi_matchup_weight == null ? 0.2 : model.xi_matchup_weight;
    var xiMatchupWeightText = formatModelValue(xiMatchupWeight, 2);
    var probabilityFormula = model.probability_formula || 'ELO expected-score -> Poisson; fixed 2 * base_goals_per_team expected goals split by team strength';

    var html = '<section class="pred-elo-model">'
      + '<div class="pred-elo-copy">'
      + '<span class="pred-elo-kicker">Modelo ELO</span>'
      + '<h3>Como se calcula la fuerza de cada seleccion</h3>'
      + '<p>El punto de partida es el ELO internacional. Cuando el XI titular tiene muestra suficiente de ELO de clubes, la fuerza se ajusta contra el promedio global del XI. Luego esa fuerza se transforma en probabilidades con una curva ELO y Poisson sin inflar el total esperado de goles.</p>'
      + '<div class="pred-elo-formula">'
      + '<span>Fuerza seleccion</span>'
      + '<code>ELO internacional + (XI blend - ' + avgXiBlendText + ') x ' + clubAdjWeightText + '</code>'
      + '</div>'
      + '<div class="pred-elo-formula">'
      + '<span>promedio XI actual</span>'
      + '<code>' + avgXiBlendText + ' &middot; peso clubes ' + clubAdjWeightText + '</code>'
      + '</div>'
      + '<div class="pred-elo-formula">'
      + '<span>Probabilidad partido</span>'
      + '<code>' + escapeHtml(probabilityFormula) + ' &middot; total goles ' + totalGoalsText + ' &middot; escala ELO ' + eloScaleText + calibrationText + '</code>'
      + '</div>'
      + '<div class="pred-elo-formula">'
      + '<span>matchup XI</span>'
      + '<code>ataque vs defensa, medio vs medio, defensa vs ataque &middot; peso ' + xiMatchupWeightText + '</code>'
      + '</div>'
      + '<p>Snapshot actual: ' + formatModelValue(summary.xi_blend_ready, 0) + ' selecciones usan ajuste por XI titular; ' + formatModelValue(summary.needs_player_elo, 0) + ' necesitan mas ELOs de jugadores; ' + formatModelValue(summary.elo_intl_only, 0) + ' quedan con base internacional. ' + sourceText + '</p>'
      + '</div>'
      + '<div class="pred-elo-metrics" aria-label="Resumen de cobertura del modelo">'
      + '<div><strong>' + formatModelValue(summary.xi_blend_ready, 0) + '</strong><span>Listos para XI</span></div>'
      + '<div><strong>' + formatModelValue(summary.needs_player_elo, 0) + '</strong><span>Faltan ELOs</span></div>'
      + '<div><strong>' + formatModelValue(summary.elo_intl_only, 0) + '</strong><span>Base internacional</span></div>'
      + '</div>';

    if (readyTeams.length) {
      html += '<div class="pred-elo-ready-strip" aria-label="Equipos con mejor cobertura">'
        + '<span>Mejor cobertura</span>';
      readyTeams.forEach(function(team) {
        var code = safeTeamCode(team.team_code);
        var name = team.name || NAMES[code] || String(code || '').toUpperCase();
        html += '<div class="pred-elo-ready-team">'
          + modelFlag(code, name)
          + '<span>' + escapeHtml(name) + '</span>'
          + '<small>' + formatModelValue(team.starter_elo_rows, 0) + '/11</small>'
          + '</div>';
      });
      html += '</div>';
    }

    html += '<div class="pred-table-wrap pred-elo-team-wrap">'
      + '<table class="pred-table pred-elo-team-table">'
      + '<thead><tr>'
      + '<th>Equipo</th><th>Estado</th><th>XI con ELO</th><th>ELO int.</th><th>XI blend</th><th>Score</th><th>Uso</th>'
      + '</tr></thead><tbody>';

    teams.forEach(function(team) {
      var code = safeTeamCode(team.team_code);
      var name = team.name || NAMES[code] || String(code || '').toUpperCase();
      var method = team.strength_method === 'xi_blend_adj' ? 'Hibrido' : 'Base';
      html += '<tr>'
        + '<td class="pred-team-cell">' + modelFlag(code, name) + '<span>' + escapeHtml(name) + '</span><span class="pred-group-badge">' + escapeHtml(team.group_id || TEAM_GROUP[code] || '?') + '</span></td>'
        + '<td><span class="pred-elo-status ' + eloTierClass(team.coverage_tier) + '">' + escapeHtml(team.coverage_label || 'Base internacional') + '</span></td>'
        + '<td class="pred-mono">' + formatModelValue(team.starter_elo_rows, 0) + '/11</td>'
        + '<td class="pred-mono">' + formatModelValue(team.elo_intl, 0) + '</td>'
        + '<td class="pred-mono">' + formatModelValue(team.xi_blend, 1) + '</td>'
        + '<td class="pred-mono">' + formatModelValue(team.strength_score, 1) + '</td>'
        + '<td>' + method + '</td>'
        + '</tr>';
    });

    html += '</tbody></table></div>'
      + '<p class="pred-elo-footnote">Listo para XI significa que el modelo ya tiene muestra suficiente de titulares con ELO para ajustar la base internacional. Los faltantes se iran refinando sin romper la simulacion.</p>'
      + '</section>';

    return html;
  }

  function renderGroupProbabilityTables(data) {
    var byCode = {};
    data.standings.forEach(function(row) {
      byCode[row.team_code] = row;
    });

    var html = '<h3 class="pred-subsection-title">Probabilidades por Grupo</h3>'
      + '<div class="pred-group-prob-grid">';

    GROUP_ORDER.forEach(function(group) {
      var rows = (GROUP_TEAMS[group] || []).map(function(code) {
        return byCode[code];
      }).filter(Boolean);
      if (!rows.length) return;

      rows.sort(function(a, b) {
        var qDiff = pctNumber(b.qualified_pct) - pctNumber(a.qualified_pct);
        if (qDiff !== 0) return qDiff;
        var fDiff = pctNumber(b.first_pct) - pctNumber(a.first_pct);
        if (fDiff !== 0) return fDiff;
        return GROUP_TEAMS[group].indexOf(a.team_code) - GROUP_TEAMS[group].indexOf(b.team_code);
      });

      html += '<section class="pred-group-prob" style="--grp-col:' + groupColor(group) + '">'
        + '<div class="pred-group-prob-title"><span>Grupo ' + group + '</span></div>'
        + '<div class="standings-wrap pred-points-wrap">'
        + '<table class="standings-table pred-points-table">'
        + '<thead><tr>'
        + '<th class="st-pos-hdr">#</th>'
        + '<th class="st-team-hdr">Equipo</th>'
        + '<th>Clasif.</th>'
        + '<th class="st-pts-hdr">PTS prob.</th>';

      POINT_TOTALS.forEach(function(points) {
        html += '<th title="' + points + ' puntos">' + points + '</th>';
      });

      html += '</tr></thead><tbody>';

      rows.forEach(function(row, index) {
        var pointsData = getPointsData(row);
        var topPoints = topPointsBucket(pointsData);
        var rowClass = index < 2 ? 'st-qualify' : (index === 2 ? 'st-third' : '');
        var bestLabel = topPoints
          ? '<span class="pred-points-main">' + topPoints.points + ' pts</span><span class="pred-points-pct">' + pctText(topPoints.pct) + '</span>'
          : '<span class="pred-points-empty">-</span>';

        html += '<tr class="' + rowClass + '">'
          + '<td class="st-pos-cell">' + (index + 1) + '</td>'
          + '<td class="st-team-cell">' + flag(row.team_code) + ' ' + (NAMES[row.team_code] || row.team_code.toUpperCase()) + '</td>'
          + '<td><span class="pred-q-badge ' + qualifyClass(row.qualified_pct) + '">' + pctText(row.qualified_pct) + '</span></td>'
          + '<td class="pred-points-best">' + bestLabel + '</td>';

        POINT_TOTALS.forEach(function(points) {
          var value = pointsData.values[points] || 0;
          var isTop = topPoints && points === topPoints.points;
          html += '<td class="pred-point-pct' + (isTop ? ' pred-point-top' : '') + '">' + (pointsData.hasData ? pctText(value) : '-') + '</td>';
        });

        html += '</tr>';
      });

      html += '</tbody></table></div></section>';
    });

    html += '</div>';
    return html;
  }

  // ── Estados de render ────────────────────────────────────────

  function setLockVisible(visible) {
    var lockEl = document.getElementById('pred-header-lock');
    if (lockEl) lockEl.style.display = visible ? '' : 'none';
  }

  function renderLocked() {
    var el = document.getElementById('predicciones-content');
    if (!el) return;
    setLockVisible(true);
    el.innerHTML = '<div class="pred-locked">'
      + '<div class="pred-lock-icon">&#x1F512;</div>'
      + '<h3 class="pred-lock-title">Simulación Monte Carlo — Fase de Grupos</h3>'
      + '<p class="pred-lock-desc">Accede a las probabilidades de clasificación calculadas con 10,000 simulaciones de la fase de grupos, usando un modelo ELO híbrido que combina el ranking internacional con el ELO de clubes del XI titular.</p>'
      + '<ul class="pred-lock-benefits">'
      + '  <li>&#x2714; Probabilidad de clasificación por equipo (48 selecciones)</li>'
      + '  <li>&#x2714; Proyección de la tabla de mejores terceros (12 grupos)</li>'
      + '  <li>&#x2714; Desglose por posición: 1°, 2°, mejor 3°, eliminado</li>'
      + '  <li>&#x2714; 10,000 escenarios · Modelo ELO híbrido · Poisson por goles</li>'
      + '</ul>'
      + renderGhostTable()
      + '<button class="pred-join-btn" onclick="window.SupaAuth && window.SupaAuth.openAuthModal()">Crear cuenta</button>'
      + '</div>';
  }

  function renderConfigError() {
    var el = document.getElementById('predicciones-content');
    if (!el) return;
    setLockVisible(true);
    el.innerHTML = '<div class="pred-locked">'
      + '<h3 class="pred-lock-title">Predicciones no disponibles</h3>'
      + '<p class="pred-lock-desc">La conexión con Supabase no está configurada. En producción esta sección no carga resultados locales ni mocks.</p>'
      + '</div>';
  }

  function renderDataError() {
    var el = document.getElementById('predicciones-content');
    if (!el) return;
    setLockVisible(false);
    el.innerHTML = '<div class="pred-empty">'
      + '<span class="pred-premium-badge">&#x2705; Todo desbloqueado</span>'
      + '<p style="color:var(--muted);margin-top:1rem">No pudimos cargar la simulación desde Supabase. Revisa la configuración, el run activo o las políticas RLS.</p>'
      + '</div>';
  }

  function renderPaywall(profile) {
    var el = document.getElementById('predicciones-content');
    if (!el) return;
    setLockVisible(true);
    el.innerHTML = '<div class="pred-payment">'
      + '<div class="pred-payment-icon">&#x1F4B3;</div>'
      + '<h3>Un paso más…</h3>'
      + '<p>Elige cómo completar tu acceso y escanea el QR.</p>'
      + '<div class="pred-pay-tabs">'
      + '  <button class="pred-pay-tab active" id="pred-tab-yape" onclick="window.PredicionesSection.showQR(\'yape\')">'
      + '    &#x1F1F5;&#x1F1EA; Yape<span class="pred-pay-tab-amount">S/. 15</span>'
      + '  </button>'
      + '  <button class="pred-pay-tab" id="pred-tab-paypal" onclick="window.PredicionesSection.showQR(\'paypal\')">'
      + '    &#x1F310; PayPal<span class="pred-pay-tab-amount">$5 USD</span>'
      + '  </button>'
      + '</div>'
      + '<div class="pred-qr-panel" id="pred-qr-yape">'
      + '  <img src="assets/yape-qr.jpeg" alt="QR Yape" class="pred-qr-img">'
      + '</div>'
      + '<div class="pred-qr-panel" id="pred-qr-paypal" style="display:none">'
      + '  <img src="assets/paypal-qr.jpeg" alt="QR PayPal" class="pred-qr-img">'
      + '</div>'
      + '<p class="pred-pay-note">Una vez realizado el pago, te enviamos un código de activación a <strong>'
      +   (profile && profile.email ? profile.email : 'tu email') + '</strong>.</p>'
      + '<div class="pred-code-form">'
      + '  <label class="pred-code-label" for="pred-code-input">Ingresa tu código de activación</label>'
      + '  <div class="pred-code-row">'
      + '    <input id="pred-code-input" class="pred-code-input" type="text" placeholder="XXXX-XXXX-XXXX" autocomplete="off" autocapitalize="characters">'
      + '    <button id="pred-code-submit" class="pred-code-btn" onclick="window.PredicionesSection.submitCode()">Activar</button>'
      + '  </div>'
      + '  <div id="pred-code-error" class="pred-code-error"></div>'
      + '</div>'
      + '</div>';
  }

  function showQR(method) {
    var yapePanel   = document.getElementById('pred-qr-yape');
    var paypalPanel = document.getElementById('pred-qr-paypal');
    var yapeTab     = document.getElementById('pred-tab-yape');
    var paypalTab   = document.getElementById('pred-tab-paypal');
    if (!yapePanel || !paypalPanel) return;
    var isYape = (method === 'yape');
    yapePanel.style.display   = isYape ? '' : 'none';
    paypalPanel.style.display = isYape ? 'none' : '';
    yapeTab.classList.toggle('active', isYape);
    paypalTab.classList.toggle('active', !isYape);
  }

  function renderRutaPosible(data) {
    // Build code->row index
    var byCode = {};
    data.standings.forEach(function(t) { byCode[t.team_code] = t; });

    // Build group->terceros index
    var tercByGroup = {};
    (data.terceros || []).forEach(function(r) {
      var group = String(r.group_id || r.group || '').toUpperCase();
      if (!group) return;
      r.group_id = group;
      tercByGroup[group] = r;
    });

    function thirdCandidateScore(candidate) {
      var rank = parseInt(candidate.rank, 10) || 99;
      var qualifiedScore = candidate.qualifies ? 10000 : 0;
      return qualifiedScore + (100 - rank) + (parseFloat(candidate.qualifies_pct) || 0) / 1000;
    }

    function buildThirdAssignments() {
      var slots = [];
      R32.forEach(function(m) {
        if (m.home.t === '3') slots.push({ key: m.num + ':home', slot: m.home });
        if (m.away.t === '3') slots.push({ key: m.num + ':away', slot: m.away });
      });

      slots.forEach(function(item) {
        item.candidates = item.slot.gs.map(function(group) {
          var row = tercByGroup[group];
          if (!row) return null;
          return {
            group: group,
            code: row.team_code,
            pct: parseFloat(row.qualifies_pct) || 0,
            rank: parseInt(row.rank, 10) || 99,
            qualifies: row.qualifies === true || row.qualifies === 'true'
          };
        }).filter(Boolean).sort(function(a, b) {
          return thirdCandidateScore(b) - thirdCandidateScore(a);
        });
      });

      var best = null;
      var bestScore = -Infinity;

      function search(index, usedGroups, assignment, score) {
        if (index === slots.length) {
          if (score > bestScore) {
            bestScore = score;
            best = Object.assign({}, assignment);
          }
          return;
        }

        var item = slots[index];
        item.candidates.forEach(function(candidate) {
          if (usedGroups[candidate.group]) return;
          usedGroups[candidate.group] = true;
          assignment[item.key] = candidate;
          search(index + 1, usedGroups, assignment, score + thirdCandidateScore(candidate));
          delete assignment[item.key];
          delete usedGroups[candidate.group];
        });
      }

      search(0, {}, {}, 0);
      return best || {};
    }

    var thirdAssignments = buildThirdAssignments();

    function getTeamForSlot(slot, slotKey) {
      if (slot.t === '3') {
        var third = thirdAssignments[slotKey];
        return third ? {
          code: third.code,
          pct: third.pct,
          slotLabel: 'Mejor 3. Grupo ' + third.group
        } : null;
      }
      // For 1st or 2nd: pick team in that group with highest first_pct or second_pct
      var field = slot.t === '1' ? 'first_pct' : 'second_pct';
      var codes = GROUP_TEAMS[slot.g] || [];
      var best = null;
      codes.forEach(function(code) {
        var t = byCode[code];
        if (!t) return;
        if (!best || parseFloat(t[field]) > parseFloat(best[field])) best = t;
      });
      return best ? { code: best.team_code, pct: parseFloat(best[field]) } : null;
    }

    function slotLabel(slot) {
      if (slot.t === '3') return '3.° ' + slot.gs.join('/');
      return slot.t + '.° Grupo ' + slot.g;
    }

    function renderSlot(slot, team) {
      var label = team && team.slotLabel ? team.slotLabel : slotLabel(slot);
      var teamHtml = team
        ? (flag(team.code) + '<span>' + (NAMES[team.code] || team.code.toUpperCase()) + '</span>')
        : '<span class="pred-slot-tbd">Por definir</span>';
      var pctHtml = team ? '<span class="pred-r32-pct">' + team.pct.toFixed(1) + '%</span>' : '';
      return '<div class="pred-r32-slot">'
        + '<span class="pred-r32-pos">' + label + '</span>'
        + '<div class="pred-r32-team">' + teamHtml + '</div>'
        + pctHtml
        + '</div>';
    }

    var html = '<h3 class="pred-subsection-title">Ruta Posible — Octavos de Final</h3>'
      + '<p class="pred-terceros-note">Equipos proyectados en cada cruce según las 10,000 simulaciones. El % indica la probabilidad de ocupar esa posición.</p>'
      + '<div class="pred-r32-grid">';

    R32.forEach(function(m) {
      var homeTeam = getTeamForSlot(m.home, m.num + ':home');
      var awayTeam = getTeamForSlot(m.away, m.num + ':away');
      html += '<div class="pred-r32-card">'
        + '<span class="pred-r32-num">P' + m.num + '</span>'
        + renderSlot(m.home, homeTeam)
        + '<span class="pred-r32-vs">vs</span>'
        + renderSlot(m.away, awayTeam)
        + '</div>';
    });

    html += '</div>';
    return html;
  }

  async function renderActive() {
    var el = document.getElementById('predicciones-content');
    if (!el) return;
    setLockVisible(false);

    el.innerHTML = '<div class="pred-loading">Cargando datos de simulación…</div>';

    var data = await loadSimulationData();
    var eloModel = await loadEloModelExplainer();
    var pronosticos = await loadEmbeddedPronosticos();

    if (!data) {
      renderDataError();
      return;
    }

    if (!data.standings.length) {
      el.innerHTML = '<div class="pred-empty">'
        + '<span class="pred-premium-badge">&#x2705; Todo desbloqueado</span>'
        + '<p style="color:var(--muted);margin-top:1rem">No hay resultados de simulación publicados para el run activo.</p>'
        + '</div>';
      return;
    }

    var runsLabel = data.run
      ? (parseInt(data.run.runs, 10).toLocaleString('es-PE') + ' simulaciones')
      : '';

    var html = '<div class="pred-active-header">'
      + '<span class="pred-premium-badge">&#x2705; Todo desbloqueado</span>'
      + (runsLabel ? '<span class="pred-model-note">' + runsLabel + ' &nbsp;·&nbsp; Monte Carlo &nbsp;·&nbsp; ELO híbrido</span>' : '')
      + '</div>';

    html += renderEloModelExplainer(eloModel);
    html += renderGroupProbabilityTables(data);
    html += renderEmbeddedPronosticos(pronosticos);

    // — Tabla 1: Probabilidades de clasificación —
    html += '<h3 class="pred-subsection-title">Probabilidad de Clasificación</h3>';
    html += '<p class="pred-terceros-note">Haz clic en un equipo para ver el desglose de posiciones.</p>';
    html += '<div class="pred-table-wrap"><table class="pred-table" id="pred-standings-table">'
      + '<thead><tr>'
      + '<th>Equipo</th><th>Gr.</th><th>Clasif.</th><th>1°</th><th>2°</th><th>Mejor 3°</th><th>Eliminado</th>'
      + '</tr></thead><tbody>';

    var sorted = data.standings.slice().sort(function (a, b) {
      return parseFloat(b.qualified_pct) - parseFloat(a.qualified_pct);
    });

    sorted.forEach(function (t) {
      var q    = parseFloat(t.qualified_pct);
      var f    = parseFloat(t.first_pct);
      var s    = parseFloat(t.second_pct);
      var b3   = parseFloat(t.best_third_pct);
      var out  = parseFloat(t.fourth_pct);
      var grp  = TEAM_GROUP[t.team_code] || '?';
      var qClass = q >= 99 ? 'pred-q-100' : q >= 70 ? 'pred-q-high' : q >= 40 ? 'pred-q-mid' : 'pred-q-low';
      /* bar widths — clamp tiny values so segments remain visible */
      var bF = Math.max(f > 0 ? Math.max(f, 1) : 0, 0);
      var bS = Math.max(s > 0 ? Math.max(s, 1) : 0, 0);
      var bB = Math.max(b3 > 0 ? Math.max(b3, 1) : 0, 0);
      var bO = Math.max(out > 0 ? Math.max(out, 1) : 0, 0);
      var detail = '<tr class="pred-detail-row" id="pred-detail-' + t.team_code + '" style="display:none">'
        + '<td colspan="7" class="pred-detail-cell">'
        + '<div class="pred-detail">'
        + '<div class="pred-bar">'
        + (bF ? '<div class="pred-bar-seg pred-bar-1" style="width:' + bF + '%"><span>' + f + '%</span></div>' : '')
        + (bS ? '<div class="pred-bar-seg pred-bar-2" style="width:' + bS + '%"><span>' + s + '%</span></div>' : '')
        + (bB ? '<div class="pred-bar-seg pred-bar-3" style="width:' + bB + '%"><span>' + b3 + '%</span></div>' : '')
        + (bO ? '<div class="pred-bar-seg pred-bar-out" style="width:' + bO + '%"><span>' + out + '%</span></div>' : '')
        + '</div>'
        + '<div class="pred-detail-legend">'
        + '<span class="pred-dl pred-dl-1">1° Grupo</span>'
        + '<span class="pred-dl pred-dl-2">2° Grupo</span>'
        + '<span class="pred-dl pred-dl-3">Mejor 3°</span>'
        + '<span class="pred-dl pred-dl-out">Eliminado</span>'
        + '</div>'
        + '</div></td></tr>';
      html += '<tr class="pred-row-clickable" data-code="' + t.team_code + '">'
        + '<td class="pred-team-cell">' + flag(t.team_code) + '<span>' + (NAMES[t.team_code] || t.team_code.toUpperCase()) + '</span>'
        + '<span class="pred-row-caret">▾</span></td>'
        + '<td><span class="pred-group-badge">' + grp + '</span></td>'
        + '<td><span class="pred-q-badge ' + qClass + '">' + t.qualified_pct + '%</span></td>'
        + '<td>' + t.first_pct + '%</td>'
        + '<td>' + t.second_pct + '%</td>'
        + '<td>' + t.best_third_pct + '%</td>'
        + '<td>' + t.fourth_pct + '%</td>'
        + '</tr>'
        + detail;
    });
    html += '</tbody></table></div>';

    // — Tabla 2: Proyección mejores terceros —
    if (data.terceros && data.terceros.length) {
      html += '<h3 class="pred-subsection-title">Proyección Mejores Terceros</h3>';
      html += '<p class="pred-terceros-note">Los 8 mejores terceros de 12 grupos avanzan a octavos. La fila representa el slot de tercer lugar del grupo; el equipo mostrado es el tercero más frecuente. Criterio actual: PTS prom. &gt; DG prom. &gt; GF prom.</p>';
      html += '<div class="pred-table-wrap"><table class="pred-table">'
        + '<thead><tr>'
        + '<th>#</th><th>Grupo</th><th>Equipo</th><th>3° más frecuente</th>'
        + '<th>Pts prom.</th><th>DG prom.</th><th>GF prom.</th><th>Clasif.%</th>'
        + '</tr></thead><tbody>';

      data.terceros.forEach(function (row) {
        var rowClass = row.qualifies ? 'pred-row-qualifies' : '';
        var gdSign = parseFloat(row.avg_gd) >= 0 ? '+' : '';
        html += '<tr class="' + rowClass + '">'
          + '<td class="pred-rank-cell">' + row.rank + (row.qualifies ? ' <span class="pred-q-dot"></span>' : '') + '</td>'
          + '<td><span class="pred-group-badge">' + row.group_id + '</span></td>'
          + '<td class="pred-team-cell">' + flag(row.team_code) + '<span>' + (NAMES[row.team_code] || row.team_code.toUpperCase()) + '</span></td>'
          + '<td>' + row.third_pct + '%</td>'
          + '<td class="pred-mono">' + row.avg_pts + '</td>'
          + '<td class="pred-mono">' + gdSign + row.avg_gd + '</td>'
          + '<td class="pred-mono">' + row.avg_gf + '</td>'
          + '<td><span class="pred-clasif-pct">' + row.qualifies_pct + '%</span></td>'
          + '</tr>';
      });
      html += '</tbody></table></div>';
      html += renderRutaPosible(data);
    }

    el.innerHTML = html;

    /* ── Row expand / collapse ── */
    var table = document.getElementById('pred-standings-table');
    if (table) {
      var openCode = null;
      table.addEventListener('click', function (e) {
        var row = e.target.closest('tr.pred-row-clickable');
        if (!row) return;
        var code = row.getAttribute('data-code');
        var detail = document.getElementById('pred-detail-' + code);
        if (!detail) return;
        var isOpen = detail.style.display !== 'none';
        /* close any open row first */
        if (openCode && openCode !== code) {
          var prev = document.getElementById('pred-detail-' + openCode);
          var prevRow = table.querySelector('tr[data-code="' + openCode + '"]');
          if (prev) prev.style.display = 'none';
          if (prevRow) prevRow.classList.remove('pred-row-open');
        }
        detail.style.display = isOpen ? 'none' : '';
        row.classList.toggle('pred-row-open', !isOpen);
        openCode = isOpen ? null : code;
      });
    }
  }

  // ── Canje de código ──────────────────────────────────────────

  async function redeemCode(code) {
    if (window.SupaData && window.SupaData.redeemPremiumCode) {
      return await window.SupaData.redeemPremiumCode(code);
    }
    var c = window.SupaAuth && window.SupaAuth.getClient();
    if (!c) return { success: false, message: 'Supabase no configurado.' };
    var ref = await c.rpc('redeem_premium_code', { input_code: code });
    if (ref.error) return { success: false, message: ref.error.message || 'Error al canjear el código.' };
    return ref.data || { success: false, message: 'Respuesta inesperada del servidor.' };
  }

  function accessMessage(message, fallback) {
    var text = message ? String(message) : '';
    if (/premium/i.test(text)) return fallback;
    return text || fallback;
  }

  async function submitCode() {
    var input = document.getElementById('pred-code-input');
    var errEl = document.getElementById('pred-code-error');
    var btn   = document.getElementById('pred-code-submit');
    if (!input || !errEl) return;
    var code = input.value.trim();
    if (!code) { errEl.textContent = 'Ingresa el código que recibiste por email.'; return; }
    btn.disabled = true;
    btn.textContent = 'Verificando…';
    errEl.textContent = '';
    errEl.style.color = '';
    var result = await redeemCode(code);
    btn.disabled = false;
    btn.textContent = 'Activar';
    if (result.success) {
      errEl.style.color = 'var(--yes)';
      errEl.textContent = ACCESS_READY_MESSAGE;
      setTimeout(function () { window.SupaAuth && window.SupaAuth.refreshAuthState(); }, 1200);
    } else {
      errEl.textContent = accessMessage(result.message, 'No pudimos completar el acceso. Revisa el código e inténtalo de nuevo.');
    }
  }

  // ── Auth change callback ─────────────────────────────────────

  async function onAuthChange(user, isPremium, profile) {
    if (!user) {
      renderLocked();
    } else if (!isPremium) {
      renderPaywall(profile);
    } else {
      await renderActive();
    }
  }

  // ── Init ─────────────────────────────────────────────────────

  function init() {
    if (window.__supabaseConfigError && !(window.SupaData && window.SupaData.isLocalDev && window.SupaData.isLocalDev())) {
      renderConfigError();
      return;
    }
    renderLocked();
  }

  window.PredicionesSection = {
    init:         init,
    onAuthChange: onAuthChange,
    submitCode:   submitCode,
    showQR:       showQR,
    renderConfigError: renderConfigError,
    renderDataError: renderDataError,
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
