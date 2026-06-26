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
  var TEAM_SECTION_BY_CODE = {
    mex:'mexico', zaf:'sudafrica', kor:'corea', cze:'chequia',
    can:'canada', bih:'bosnia', qat:'qatar', sui:'suiza',
    bra:'brasil', mar:'marruecos', hti:'haiti', sco:'escocia',
    ger:'alemania', cuw:'curazao', civ:'costa-marfil', ecu:'ecuador',
    ned:'paises-bajos', jpn:'japon', swe:'suecia', tun:'tunez',
    bel:'belgica', egy:'egipto', irn:'iran', nzl:'nueva-zelanda',
    esp:'espana', cpv:'cabo-verde', ksa:'arabia-saudita', ury:'uruguay',
    fra:'francia', sen:'senegal', irq:'irak', nor:'noruega',
    arg:'argentina', alg:'argelia', aut:'austria', jor:'jordania',
    por:'portugal', cod:'rd-congo', uzb:'uzbekistan', col:'colombia',
    eng:'inglaterra', cro:'croacia', gha:'ghana', pan:'panama',
    usa:'estados-unidos', pry:'paraguay', aus:'australia', tur:'turquia'
  };
  var ACCESS_READY_MESSAGE = 'Todo desbloqueado. Ya puedes ver todas las predicciones.';
  // Último perfil conocido, para que el botón "Desbloquear todo" del preview
  // gratuito pueda abrir la pantalla de pago con el email correcto.
  var _lastProfile = null;

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

  function renderTeamLink(code, name, className) {
    var safeCode = safeTeamCode(code);
    var sectionId = TEAM_SECTION_BY_CODE[safeCode];
    var cls = className || 'prono-team-link';
    if (!sectionId) {
      return '<span class="' + escapeHtml(cls) + '">' + escapeHtml(name) + '</span>';
    }
    return '<a class="' + escapeHtml(cls) + '" href="#' + escapeHtml(sectionId) + '">' + escapeHtml(name) + '</a>';
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
      + '<p class="prono-lock-desc">Accede a una lectura editorial de cada partido con ELO de clubes, XI probable, porcentajes de victoria, 10 resultados probables y narrativa competitiva para los 72 partidos de la fase de grupos.</p>'
      + '<ul class="prono-lock-benefits">'
      + '  <li>&#x2714; Lectura editorial del favorito, rival incómodo y escenarios de partido</li>'
      + '  <li>&#x2714; Porcentajes de victoria, empate y derrota por partido</li>'
      + '  <li>&#x2714; 10 resultados más probables según la simulación</li>'
      + '  <li>&#x2714; Factor de jugador diferencial en equipos con talentos que alteran el plan</li>'
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
        + '<p class="pred-terceros-note">Lectura editorial, porcentajes de victoria, 10 resultados probables, jugador diferencial y explicación del pronóstico para la fase de grupos.</p>';
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

  // ── Preview gratuito: pronósticos de partidos ya jugados ────────
  // El RLS (28_predictions_free_finished.sql) entrega a anon/free solo las
  // predicciones cuyo partido está finished. Las mostramos desbloqueadas y
  // añadimos un upsell hacia el acceso completo.

  function renderUpsellBanner(user) {
    var cta = user
      ? '<button class="prono-join-btn" onclick="window.PremiumSection.showPayment()">Desbloquear los 72 + Monte Carlo</button>'
      : '<button class="prono-join-btn" onclick="window.SupaAuth && window.SupaAuth.openAuthModal()">Crear cuenta gratis</button>';
    return '<div class="prono-free-upsell">'
      + '<h3 class="prono-free-upsell-title">Desbloquea todos los pronósticos</h3>'
      + '<p class="prono-free-upsell-desc">Estás viendo gratis los pronósticos de los partidos ya jugados. '
      + 'Accede a los 72 partidos de la fase de grupos, la lectura editorial, los porcentajes de victoria y los 10 resultados de los próximos cruces '
      + 'y la simulación Monte Carlo de clasificación.</p>'
      + cta
      + '</div>';
  }

  function renderFreePreview(predictions, user) {
    var el = document.getElementById('pronosticos-content');
    if (!el) return;
    var intro = '<div class="prono-free-intro">'
      + '<span class="prono-free-badge">Gratis · partidos jugados</span>'
      + '<h3 class="prono-free-title">Pronósticos de partidos ya jugados</h3>'
      + '<p class="prono-free-desc">Lee la interpretación editorial, los porcentajes de victoria, los 10 resultados probables, el jugador diferencial y el análisis '
      + 'de los partidos que ya se disputaron, y compáralos con el resultado real.</p>'
      + '</div>';
    var cards = renderActiveContent(predictions, {
      includeTitle: false,
      includeBadge: false,
      embedded: false
    });
    el.innerHTML = intro + cards + renderUpsellBanner(user);
  }

  function showPayment() {
    renderPaymentModal(_lastProfile);
  }

  function formatPct(value) {
    var pct = pctValue(value);
    return pct.toFixed(1).replace(/\.0$/, '') + '%';
  }

  function renderProbabilityBars(p, result) {
    var codeA = safeTeamCode(p.team_a);
    var codeB = safeTeamCode(p.team_b);
    var nameA = teamName(codeA || p.team_a);
    var nameB = teamName(codeB || p.team_b);
    var aWin = pctValue(p.team_a_win_probability);
    var draw = pctValue(p.draw_probability);
    var bWin = pctValue(p.team_b_win_probability);

    return '<div class="prono-probs">'
      + '<span class="prono-probs-label">Porcentajes de victoria</span>'
      + renderProbabilityRow(renderTeamLink(codeA, nameA, 'prono-team-link prono-prob-team-link'), aWin, 'prono-bar-a')
      + renderProbabilityRow('Empate', draw, 'prono-bar-draw')
      + renderProbabilityRow(renderTeamLink(codeB, nameB, 'prono-team-link prono-prob-team-link'), bWin, 'prono-bar-b')
      + '</div>';
  }

  function renderProbabilityRow(labelHtml, value, barClass) {
    return '<div class="prono-prob-row">'
      + '<span class="prono-prob-label">' + labelHtml + '</span>'
      + '<div class="prono-prob-bar-wrap"><div class="prono-prob-bar ' + barClass + '" style="width:' + value + '%"></div></div>'
      + '<span class="prono-prob-pct">' + formatPct(value) + '</span>'
      + '</div>';
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
    var scorelines = parseScorelines(p.top_scorelines).slice(0, 10);
    if (!scorelines.length && !result) return '';

    var top10Hit = !!(result && scorelines.some(function(item) {
      return String(item.score) === result.score;
    }));

    var html = '<div class="prono-scores">'
      + '<div class="prono-scores-head">'
      + '<span class="prono-scores-label">10 resultados más probables</span>'
      + '</div>'
      + '<div class="prono-scores-chips">';

    scorelines.forEach(function(item) {
      var pctText = formatPct(item.pct);
      var isHit = !!(result && String(item.score) === result.score);
      html += '<span class="prono-score-chip' + (isHit ? ' prono-score-hit' : '') + '">'
        + (isHit ? '<span class="prono-score-check">&#x2714;</span>' : '')
        + '<strong>' + escapeHtml(item.score) + '</strong>'
        + '<small>' + pctText + '</small>'
        + '</span>';
    });

    if (result && !top10Hit) {
      html += '<span class="prono-score-chip prono-score-final-miss">'
        + '<span class="prono-score-final-label">Final</span>'
        + '<strong>' + escapeHtml(result.score) + '</strong>'
        + '</span>';
    }

    html += '</div></div>';
    return html;
  }

  function renderEditorialOutlook(p, result) {
    var text = selectEditorialOutlook(p);
    if (!text) return '';

    return '<div class="prono-editorial-outlook">'
      + '<span class="prono-editorial-label">Lectura editorial</span>'
      + '<p>' + escapeHtml(text) + '</p>'
      + '</div>';
  }

  function predictionParagraphs(text) {
    return String(text || '')
      .split(/\n{2,}/)
      .map(function(para) { return para.trim(); })
      .filter(Boolean);
  }

  function selectEditorialOutlook(p) {
    var paragraphs = predictionParagraphs(p && p.explanation);
    if (paragraphs.length) return paragraphs[0];

    var contexts = [
      p && p.team_a_context,
      p && p.team_b_context
    ].map(function(text) { return String(text || '').trim(); }).filter(Boolean);
    return contexts.length ? contexts[0] : '';
  }

  function renderPredictionExplanation(p) {
    var paragraphs = predictionParagraphs(p && p.explanation).slice(1);
    if (!paragraphs.length) return '';
    return '<div class="prono-explanation">'
      + paragraphs.map(function(para) {
          return '<p class="prono-explanation-p">' + escapeHtml(para) + '</p>';
        }).join('')
      + '</div>';
  }

  function renderPredictionCard(p) {
    var codeA = safeTeamCode(p.team_a);
    var codeB = safeTeamCode(p.team_b);
    var nameA = teamName(codeA || p.team_a);
    var nameB = teamName(codeB || p.team_b);
    var result = findFinalResult(p);
    // Ancla navegable por partido: los fixtures de equipo saltan aquí
    // mediante handleFixtureClick(match_id).
    var anchorId = String(p.match_id || '').toLowerCase().replace(/[^a-z0-9-]/g, '');

    return '<div class="prono-card"' + (anchorId ? ' id="prono-' + anchorId + '"' : '') + '>'
      + '  <div class="prono-card-header">'
      + '    <span class="prono-matchday">J' + escapeHtml(p.matchday) + '</span>'
      + '    <div class="prono-teams">'
      + '      <div class="prono-team">' + flag(codeA) + renderTeamLink(codeA, nameA, 'prono-team-link prono-team-link-main') + '</div>'
      + '      <span class="prono-vs">vs</span>'
      + '      <div class="prono-team">' + flag(codeB) + renderTeamLink(codeB, nameB, 'prono-team-link prono-team-link-main') + '</div>'
      + '    </div>'
      + (p.global_tag ? '<span class="prono-global-tag">' + escapeHtml(p.global_tag) + '</span>' : '')
      + '  </div>'
      + renderEditorialOutlook(p, result)
      + renderProbabilityBars(p, result)
      + renderScorelines(p, result)
      + (p.team_a_context || p.team_b_context
         ? '<div class="prono-contexts">'
           + (p.team_a_context ? '<div class="prono-ctx prono-ctx-a"><strong>' + renderTeamLink(codeA, nameA, 'prono-team-link prono-ctx-team-link') + ':</strong> ' + escapeHtml(p.team_a_context) + '</div>' : '')
           + (p.team_b_context ? '<div class="prono-ctx prono-ctx-b"><strong>' + renderTeamLink(codeB, nameB, 'prono-team-link prono-ctx-team-link') + ':</strong> ' + escapeHtml(p.team_b_context) + '</div>' : '')
           + '</div>'
         : '')
      + renderPredictionExplanation(p)
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
    _lastProfile = profile || null;

    if (isPremium) {
      var predictions = await loadPredictions();
      if (predictions === null) {
        renderDataError();
        return;
      }
      renderActive(predictions);
      return;
    }

    // Free (anon o logueado sin premium): el RLS solo devuelve los partidos
    // ya jugados. Si hay alguno, lo mostramos desbloqueado + upsell; si no,
    // caemos al teaser (anon) o a la pantalla de pago (logueado).
    var freePreds = await loadPredictions();
    if (freePreds && freePreds.length) {
      renderFreePreview(freePreds, user);
    } else if (!user) {
      renderLocked();
    } else {
      renderPaymentModal(profile);
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
    showPayment: showPayment,
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
