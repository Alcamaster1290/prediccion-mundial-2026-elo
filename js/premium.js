/**
 * premium.js — Sección Premium "Pronósticos Fase de Grupos"
 * Expone: window.PremiumSection
 * Requiere: window.SupaAuth (auth.js)
 */
(function () {
  'use strict';

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
  var ACCESS_READY_MESSAGE = 'Todo desbloqueado. Ya puedes ver todas las predicciones.';

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

  function teamName(code) {
    return NAMES[code] || String(code || '').toUpperCase();
  }

  function flag(code) {
    var safeCode = safeTeamCode(code);
    if (!safeCode) return '';
    var name = teamName(safeCode);
    return '<img class="flag-svg" src="assets/flags/' + safeCode + '.svg" alt="' + escapeHtml(name) + '" loading="lazy">';
  }

  function pctValue(value) {
    var n = parseFloat(value);
    if (isNaN(n)) return 0;
    return Math.max(0, Math.min(100, n));
  }

  function hasStandaloneContainer() {
    return !!document.getElementById('pronosticos-content');
  }

  function isLocalDev() {
    if (window.SupaData && window.SupaData.isLocalDev) return window.SupaData.isLocalDev();
    var host = window.location && window.location.hostname;
    var protocol = window.location && window.location.protocol;
    return protocol === 'file:' || host === 'localhost' || host === '127.0.0.1';
  }

  // ── Canje de código premium ─────────────────────────────────

  async function redeemCode(code) {
    if (window.SupaData && window.SupaData.redeemPremiumCode) {
      return await window.SupaData.redeemPremiumCode(code);
    }
    var c = window.SupaAuth && window.SupaAuth.getClient();
    if (!c) return { success: false, message: 'Supabase no configurado.' };

    var ref = await c.rpc('redeem_premium_code', { input_code: code });
    if (ref.error) {
      return { success: false, message: ref.error.message || 'Error al canjear el código.' };
    }
    return ref.data || { success: false, message: 'Respuesta inesperada del servidor.' };
  }

  function accessMessage(message, fallback) {
    var text = message ? String(message) : '';
    if (/premium/i.test(text)) return fallback;
    return text || fallback;
  }

  // ── Carga de predicciones desde Supabase ────────────────────

  async function loadPredictions() {
    var predictions;
    if (window.SupaData && window.SupaData.loadPredictions) {
      predictions = await window.SupaData.loadPredictions();
    } else {
      var c = window.SupaAuth && window.SupaAuth.getClient();
      if (!c) {
        predictions = isLocalDev() ? await loadMockPredictions() : null;
      } else {
        var ref = await c
          .from('predictions')
          .select('*')
          .eq('published', true)
          .eq('is_premium', true)
          .order('group_code')
          .order('matchday');

        if (ref.error) {
          console.error('[PremiumSection] Error loading predictions:', ref.error);
          predictions = null;
        } else {
          predictions = ref.data || [];
        }
      }
    }
    await loadFinishedResults();
    return predictions;
  }

  // ── Resultados reales (match_results finished) ──────────────
  // En fase de grupos cada par de equipos juega una sola vez,
  // así que el par ordenado identifica el partido.

  var _resultsByPair = null;

  function pairKey(a, b) {
    return [a, b].sort().join('|');
  }

  async function loadFinishedResults() {
    if (_resultsByPair) return _resultsByPair;
    var rows = null;
    if (window.SupaData && window.SupaData.loadMatchResults) {
      try { rows = await window.SupaData.loadMatchResults(); } catch (e) { rows = null; }
    }
    _resultsByPair = {};
    (rows || []).forEach(function(row) {
      if (!row || row.phase !== 'group' || row.status !== 'finished') return;
      if (row.home_goals == null || row.away_goals == null) return;
      var home = safeTeamCode(row.home_team);
      var away = safeTeamCode(row.away_team);
      if (!home || !away) return;
      _resultsByPair[pairKey(home, away)] = row;
    });
    return _resultsByPair;
  }

  function findFinalResult(p) {
    if (!_resultsByPair) return null;
    var codeA = safeTeamCode(p.team_a);
    var codeB = safeTeamCode(p.team_b);
    if (!codeA || !codeB) return null;
    var row = _resultsByPair[pairKey(codeA, codeB)];
    if (!row) return null;
    var goalsA = row.home_team === codeA ? row.home_goals : row.away_goals;
    var goalsB = row.home_team === codeA ? row.away_goals : row.home_goals;
    return {
      score: goalsA + '-' + goalsB,
      outcome: goalsA > goalsB ? 'a' : (goalsA < goalsB ? 'b' : 'draw')
    };
  }

  async function loadMockPredictions() {
    try {
      var r = await fetch('data/predictions.mock.json');
      var d = await r.json();
      return d.predictions || [];
    } catch (e) {
      return [];
    }
  }

  // ── Render de la sección ────────────────────────────────────

  function renderLocked() {
    var el = document.getElementById('pronosticos-content');
    if (!el) return;
    el.innerHTML = '<div class="prono-locked">'
      + '<div class="prono-lock-icon">&#x1F512;</div>'
      + '<h3 class="prono-lock-title">Pronósticos detallados por partido</h3>'
      + '<p class="prono-lock-desc">Accede a probabilidades calculadas con ELO de clubes, XI probable, contexto de grupo y narrativa competitiva para los 72 partidos de la fase de grupos.</p>'
      + '<ul class="prono-lock-benefits">'
      + '  <li>&#x2714; Probabilidad de victoria / empate / derrota por partido</li>'
      + '  <li>&#x2714; Marcadores exactos más probables con su probabilidad</li>'
      + '  <li>&#x2714; Contexto táctico y análisis de cada equipo</li>'
      + '  <li>&#x2714; Etiqueta global del partido (favorito, duelo parejo, etc.)</li>'
      + '  <li>&#x2714; Explicación del pronóstico en texto</li>'
      + '  <li>&#x2714; Actualizado conforme avanza el torneo</li>'
      + '</ul>'
      + '<div class="prono-lock-model">'
      + '  <span class="prono-model-label">Modelo basado en</span>'
      + '  ELO ponderado del XI · ELO de banca · Orden de partidos · Presión clasificatoria · Riesgo de rotación'
      + '</div>'
      + renderGhostCards(3)
      + '<button class="prono-join-btn" onclick="window.SupaAuth && window.SupaAuth.openAuthModal()">Crear cuenta</button>'
      + '</div>';
  }

  function renderConfigError() {
    var el = document.getElementById('pronosticos-content');
    if (!el) return;
    el.innerHTML = '<div class="prono-locked">'
      + '<h3 class="prono-lock-title">Pronósticos no disponibles</h3>'
      + '<p class="prono-lock-desc">La conexión con Supabase no está configurada. En producción esta sección no carga datos locales ni mocks.</p>'
      + '</div>';
  }

  function renderDataError() {
    var el = document.getElementById('pronosticos-content');
    if (!el) return;
    el.innerHTML = '<div class="prono-empty">'
      + '<span class="prono-premium-badge">&#x2705; Todo desbloqueado</span>'
      + '<p style="color:var(--muted);margin-top:1rem">No pudimos cargar los pronósticos desde Supabase. Revisa la configuración o las políticas RLS.</p>'
      + '</div>';
  }

  function renderPaymentModal(profile) {
    var el = document.getElementById('pronosticos-content');
    if (!el) return;
    el.innerHTML = '<div class="prono-payment">'
      + '<div class="prono-payment-icon">&#x1F4B3;</div>'
      + '<h3>Un paso más…</h3>'
      + '<p>Elige cómo completar tu acceso y escanea el QR.</p>'
      + '<div class="prono-pay-tabs">'
      + '  <button class="prono-pay-tab active" id="prono-tab-yape" onclick="window.PremiumSection.showQR(\'yape\')">'
      + '    &#x1F1F5;&#x1F1EA; Yape<span class="prono-pay-tab-amount">S/. 15</span>'
      + '  </button>'
      + '  <button class="prono-pay-tab" id="prono-tab-paypal" onclick="window.PremiumSection.showQR(\'paypal\')">'
      + '    &#x1F310; PayPal<span class="prono-pay-tab-amount">$5 USD</span>'
      + '  </button>'
      + '</div>'
      + '<div class="prono-qr-panel" id="prono-qr-yape">'
      + '  <img src="assets/yape-qr.jpeg" alt="QR Yape" class="prono-qr-img">'
      + '</div>'
      + '<div class="prono-qr-panel" id="prono-qr-paypal" style="display:none">'
      + '  <img src="assets/paypal-qr.jpeg" alt="QR PayPal" class="prono-qr-img">'
      + '</div>'
      + '<p class="prono-pay-note">Una vez realizado el pago, te enviamos un código de activación a <strong>'
      +   (profile && profile.email ? profile.email : 'tu email') + '</strong>.</p>'
      + '<div class="prono-code-form">'
      + '  <label class="prono-code-label" for="prono-code-input">Ingresa tu código de activación</label>'
      + '  <div class="prono-code-row">'
      + '    <input id="prono-code-input" class="prono-code-input" type="text" placeholder="XXXX-XXXX-XXXX" autocomplete="off" autocapitalize="characters">'
      + '    <button id="prono-code-submit" class="prono-code-btn" onclick="window.PremiumSection.submitCode()">Activar</button>'
      + '  </div>'
      + '  <div id="prono-code-error" class="prono-code-error"></div>'
      + '</div>'
      + '</div>';
  }

  function showQR(method) {
    var yapePanel  = document.getElementById('prono-qr-yape');
    var paypalPanel = document.getElementById('prono-qr-paypal');
    var yapeTab    = document.getElementById('prono-tab-yape');
    var paypalTab  = document.getElementById('prono-tab-paypal');
    if (!yapePanel || !paypalPanel) return;
    var isYape = (method === 'yape');
    yapePanel.style.display   = isYape ? '' : 'none';
    paypalPanel.style.display = isYape ? 'none' : '';
    yapeTab.classList.toggle('active', isYape);
    paypalTab.classList.toggle('active', !isYape);
  }

  function renderActiveContent(predictions, options) {
    options = options || {};
    var includeTitle = options.includeTitle !== false;
    var includeBadge = options.includeBadge === true;
    var isEmbedded = options.embedded === true;
    var html = '<section class="' + (isEmbedded ? 'pred-pronosticos-block' : 'prono-active-block') + '">';

    if (includeTitle) {
      html += '<h3 class="pred-subsection-title">Pronósticos Fase de Grupos</h3>'
        + '<p class="pred-terceros-note">Probabilidades por partido, contexto táctico y explicación del pronóstico para la fase de grupos.</p>';
    }

    if (includeBadge) {
      html += '<div class="prono-active-header">'
        + '<span class="prono-premium-badge">&#x2705; Todo desbloqueado</span>'
        + '</div>';
    }

    if (!predictions || predictions.length === 0) {
      html += '<div class="prono-empty">'
        + '<p style="color:var(--muted);margin-top:1rem">Los pronósticos se publicarán a medida que se acerquen los partidos.</p>'
        + '</div></section>';
      return html;
    }

    var byGroup = {};
    predictions.forEach(function(p) {
      if (!byGroup[p.group_code]) byGroup[p.group_code] = [];
      byGroup[p.group_code].push(p);
    });

    Object.keys(byGroup).sort().forEach(function(grp) {
      html += '<div class="prono-group-block">'
        + '<div class="prono-group-title">Grupo ' + escapeHtml(grp) + '</div>';
      if (typeof options.renderGroupExtra === 'function') {
        // Contenido extra por grupo (p. ej. tabla de probabilidades MC)
        html += options.renderGroupExtra(grp) || '';
      }
      byGroup[grp].forEach(function(p) {
        html += renderPredictionCard(p);
      });
      html += '</div>';
    });

    html += '</section>';
    return html;
  }

  async function renderActive(predictions) {
    var el = document.getElementById('pronosticos-content');
    if (!el) return;

    el.innerHTML = renderActiveContent(predictions, {
      includeTitle: false,
      includeBadge: true,
      embedded: false
    });
  }

  function parseScorelines(raw) {
    var list = raw;
    if (typeof list === 'string') {
      try { list = JSON.parse(list); } catch (e) { return []; }
    }
    if (!Array.isArray(list)) return [];
    return list.filter(function(item) {
      return item && /^\d{1,2}-\d{1,2}$/.test(String(item.score || '')) && parseFloat(item.pct) > 0;
    });
  }

  function renderScorelines(p, result) {
    var scorelines = parseScorelines(p.top_scorelines);
    if (!scorelines.length) return '';
    var html = '<div class="prono-scores">'
      + '<span class="prono-scores-label">Marcadores más probables</span>'
      + '<div class="prono-scores-chips">';
    var hitFound = false;
    scorelines.forEach(function(item, index) {
      var pct = parseFloat(item.pct);
      var pctText = pct.toFixed(1).replace(/\.0$/, '') + '%';
      var isHit = !!(result && String(item.score) === result.score);
      if (isHit) hitFound = true;
      html += '<span class="prono-score-chip' + (index === 0 ? ' prono-score-top' : '') + (isHit ? ' prono-score-hit' : '') + '">'
        + (isHit ? '<span class="prono-score-check">&#x2714;</span>' : '')
        + '<strong>' + escapeHtml(item.score) + '</strong>'
        + '<small>' + pctText + '</small>'
        + '</span>';
    });
    if (result && !hitFound) {
      // El marcador real no estaba en el top-5: se muestra igual como chip final
      html += '<span class="prono-score-chip prono-score-hit">'
        + '<span class="prono-score-check">&#x2714;</span>'
        + '<strong>' + escapeHtml(result.score) + '</strong>'
        + '<small>real</small>'
        + '</span>';
    }
    html += '</div></div>';
    return html;
  }

  function renderPredictionCard(p) {
    var codeA = safeTeamCode(p.team_a);
    var codeB = safeTeamCode(p.team_b);
    var nameA = teamName(codeA || p.team_a);
    var nameB = teamName(codeB || p.team_b);
    var aWin  = pctValue(p.team_a_win_probability);
    var draw  = pctValue(p.draw_probability);
    var bWin  = pctValue(p.team_b_win_probability);
    var result = findFinalResult(p);
    var hitA    = !!(result && result.outcome === 'a');
    var hitDraw = !!(result && result.outcome === 'draw');
    var hitB    = !!(result && result.outcome === 'b');
    var check   = ' <span class="prono-hit-check">&#x2714;</span>';
    // Ancla navegable por partido: los fixtures de equipo saltan aquí
    // mediante handleFixtureClick(match_id).
    var anchorId = String(p.match_id || '').toLowerCase().replace(/[^a-z0-9-]/g, '');

    return '<div class="prono-card"' + (anchorId ? ' id="prono-' + anchorId + '"' : '') + '>'
      + '  <div class="prono-card-header">'
      + '    <span class="prono-matchday">J' + escapeHtml(p.matchday) + '</span>'
      + '    <div class="prono-teams">'
      + '      <div class="prono-team">' + flag(codeA) + '<span>' + escapeHtml(nameA) + '</span></div>'
      + '      <span class="prono-vs">vs</span>'
      + '      <div class="prono-team">' + flag(codeB) + '<span>' + escapeHtml(nameB) + '</span></div>'
      + '    </div>'
      + (result ? '<span class="prono-final-badge">&#x2714; Final ' + escapeHtml(result.score) + '</span>' : '')
      + (p.global_tag ? '<span class="prono-global-tag">' + escapeHtml(p.global_tag) + '</span>' : '')
      + '  </div>'
      + '  <div class="prono-probs">'
      + '    <div class="prono-prob-row' + (hitA ? ' prono-prob-hit' : '') + '">'
      + '      <span class="prono-prob-label">' + escapeHtml(nameA) + '</span>'
      + '      <div class="prono-prob-bar-wrap"><div class="prono-prob-bar prono-bar-a" style="width:' + aWin + '%"></div></div>'
      + '      <span class="prono-prob-pct">' + aWin.toFixed(0) + '%' + (hitA ? check : '') + '</span>'
      + '    </div>'
      + '    <div class="prono-prob-row' + (hitDraw ? ' prono-prob-hit' : '') + '">'
      + '      <span class="prono-prob-label">Empate</span>'
      + '      <div class="prono-prob-bar-wrap"><div class="prono-prob-bar prono-bar-draw" style="width:' + draw + '%"></div></div>'
      + '      <span class="prono-prob-pct">' + draw.toFixed(0) + '%' + (hitDraw ? check : '') + '</span>'
      + '    </div>'
      + '    <div class="prono-prob-row' + (hitB ? ' prono-prob-hit' : '') + '">'
      + '      <span class="prono-prob-label">' + escapeHtml(nameB) + '</span>'
      + '      <div class="prono-prob-bar-wrap"><div class="prono-prob-bar prono-bar-b" style="width:' + bWin + '%"></div></div>'
      + '      <span class="prono-prob-pct">' + bWin.toFixed(0) + '%' + (hitB ? check : '') + '</span>'
      + '    </div>'
      + '  </div>'
      + renderScorelines(p, result)
      + (p.team_a_context || p.team_b_context
         ? '<div class="prono-contexts">'
           + (p.team_a_context ? '<div class="prono-ctx prono-ctx-a"><strong>' + escapeHtml(nameA) + ':</strong> ' + escapeHtml(p.team_a_context) + '</div>' : '')
           + (p.team_b_context ? '<div class="prono-ctx prono-ctx-b"><strong>' + escapeHtml(nameB) + ':</strong> ' + escapeHtml(p.team_b_context) + '</div>' : '')
           + '</div>'
         : '')
      + (p.explanation
         ? '<div class="prono-explanation">'
           + p.explanation.split('\n\n').map(function (para) {
               return '<p class="prono-explanation-p">' + escapeHtml(para) + '</p>';
             }).join('')
           + '</div>'
         : '')
      + '</div>';
  }

  function renderGhostCards(n) {
    var html = '<div class="prono-ghost-cards">';
    for (var i = 0; i < n; i++) {
      html += '<div class="prono-ghost-card">'
        + '<div class="prono-ghost-header"></div>'
        + '<div class="prono-ghost-bars"></div>'
        + '<div class="prono-ghost-text"></div>'
        + '</div>';
    }
    html += '</div>';
    return html;
  }

  // ── Envío de código ─────────────────────────────────────────

  async function submitCode() {
    var input   = document.getElementById('prono-code-input');
    var errEl   = document.getElementById('prono-code-error');
    var btn     = document.getElementById('prono-code-submit');
    if (!input || !errEl) return;

    var code = input.value.trim();
    if (!code) {
      errEl.textContent = 'Ingresa el código que recibiste por email.';
      return;
    }

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
      setTimeout(function() {
        window.SupaAuth && window.SupaAuth.refreshAuthState();
      }, 1200);
    } else {
      errEl.textContent = accessMessage(result.message, 'No pudimos completar el acceso. Revisa el código e inténtalo de nuevo.');
    }
  }

  // ── Auth change callback (llamado desde auth.js) ─────────────

  async function onAuthChange(user, isPremium, profile) {
    if (!hasStandaloneContainer()) return;

    if (!user) {
      renderLocked();
    } else if (!isPremium) {
      renderPaymentModal(profile);
    } else {
      var predictions = await loadPredictions();
      if (predictions === null) {
        renderDataError();
        return;
      }
      renderActive(predictions);
    }
  }

  // ── Init ────────────────────────────────────────────────────

  function init() {
    if (!hasStandaloneContainer()) return;
    if (window.__supabaseConfigError && !isLocalDev()) {
      renderConfigError();
      return;
    }
    renderLocked();
  }

  window.PremiumSection = {
    init: init,
    onAuthChange: onAuthChange,
    submitCode: submitCode,
    loadPredictions: loadPredictions,
    renderActiveContent: renderActiveContent,
    renderConfigError: renderConfigError,
    renderDataError: renderDataError,
    showQR: showQR,
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
