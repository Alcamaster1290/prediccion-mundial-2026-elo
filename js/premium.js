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

  function flag(code) {
    var name = NAMES[code] || code;
    return '<img class="flag-svg" src="assets/flags/' + code + '.svg" alt="' + name + '" loading="lazy">';
  }

  // ── Canje de código premium ─────────────────────────────────

  async function redeemCode(code) {
    var c = window.SupaAuth && window.SupaAuth.getClient();
    if (!c) return { success: false, message: 'Supabase no configurado.' };

    var ref = await c.rpc('redeem_premium_code', { input_code: code });
    if (ref.error) {
      return { success: false, message: ref.error.message || 'Error al canjear el código.' };
    }
    return ref.data || { success: false, message: 'Respuesta inesperada del servidor.' };
  }

  // ── Carga de predicciones desde Supabase ────────────────────

  async function loadPredictions() {
    var c = window.SupaAuth && window.SupaAuth.getClient();
    if (!c) {
      return loadMockPredictions();
    }
    var ref = await c
      .from('predictions')
      .select('*')
      .eq('published', true)
      .eq('is_premium', true)
      .order('group_code')
      .order('matchday');

    if (ref.error) {
      console.error('[PremiumSection] Error loading predictions:', ref.error);
      return [];
    }
    return ref.data || [];
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
      + '<button class="prono-join-btn" onclick="window.SupaAuth && window.SupaAuth.openAuthModal()">Únete — S/. 15 · $5</button>'
      + '</div>';
  }

  function renderPaymentModal(profile) {
    var el = document.getElementById('pronosticos-content');
    if (!el) return;
    el.innerHTML = '<div class="prono-payment">'
      + '<div class="prono-payment-icon">&#x1F4B3;</div>'
      + '<h3>Un paso más…</h3>'
      + '<p>Confirma tu pago para activar el acceso premium a todos los pronósticos.</p>'
      + '<div class="prono-payment-options">'
      + '  <div class="prono-pay-opt">'
      + '    <span class="prono-pay-method">Yape</span>'
      + '    <span class="prono-pay-amount">S/. 15 soles</span>'
      + '    <span class="prono-pay-phone">&#x1F4F1; Número en el email de bienvenida</span>'
      + '  </div>'
      + '  <div class="prono-pay-opt">'
      + '    <span class="prono-pay-method">PayPal</span>'
      + '    <span class="prono-pay-amount">$5 USD</span>'
      + '    <span class="prono-pay-phone">&#x1F4E7; alvarojohn1290@gmail.com</span>'
      + '  </div>'
      + '</div>'
      + '<p class="prono-pay-note">Una vez confirmado el pago, te enviaremos un código de activación a <strong>'
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

  async function renderActive(predictions) {
    var el = document.getElementById('pronosticos-content');
    if (!el) return;

    if (!predictions || predictions.length === 0) {
      el.innerHTML = '<div class="prono-empty">'
        + '<span class="prono-premium-badge">&#x2705; Acceso Premium Activo</span>'
        + '<p style="color:var(--muted);margin-top:1rem">Los pronósticos se publicarán a medida que se acerquen los partidos.</p>'
        + '</div>';
      return;
    }

    var byGroup = {};
    predictions.forEach(function(p) {
      if (!byGroup[p.group_code]) byGroup[p.group_code] = [];
      byGroup[p.group_code].push(p);
    });

    var html = '<div class="prono-active-header">'
      + '<span class="prono-premium-badge">&#x2705; Acceso Premium Activo</span>'
      + '</div>';

    Object.keys(byGroup).sort().forEach(function(grp) {
      html += '<div class="prono-group-block">'
        + '<div class="prono-group-title">Grupo ' + grp + '</div>';
      byGroup[grp].forEach(function(p) {
        html += renderPredictionCard(p);
      });
      html += '</div>';
    });

    el.innerHTML = html;
  }

  function renderPredictionCard(p) {
    var aWin  = parseFloat(p.team_a_win_probability) || 0;
    var draw  = parseFloat(p.draw_probability) || 0;
    var bWin  = parseFloat(p.team_b_win_probability) || 0;

    return '<div class="prono-card">'
      + '  <div class="prono-card-header">'
      + '    <span class="prono-matchday">J' + p.matchday + '</span>'
      + '    <div class="prono-teams">'
      + '      <div class="prono-team">' + flag(p.team_a) + '<span>' + (NAMES[p.team_a] || p.team_a) + '</span></div>'
      + '      <span class="prono-vs">vs</span>'
      + '      <div class="prono-team">' + flag(p.team_b) + '<span>' + (NAMES[p.team_b] || p.team_b) + '</span></div>'
      + '    </div>'
      + (p.global_tag ? '<span class="prono-global-tag">' + p.global_tag + '</span>' : '')
      + '  </div>'
      + '  <div class="prono-probs">'
      + '    <div class="prono-prob-row">'
      + '      <span class="prono-prob-label">' + (NAMES[p.team_a] || p.team_a) + '</span>'
      + '      <div class="prono-prob-bar-wrap"><div class="prono-prob-bar prono-bar-a" style="width:' + aWin + '%"></div></div>'
      + '      <span class="prono-prob-pct">' + aWin.toFixed(0) + '%</span>'
      + '    </div>'
      + '    <div class="prono-prob-row">'
      + '      <span class="prono-prob-label">Empate</span>'
      + '      <div class="prono-prob-bar-wrap"><div class="prono-prob-bar prono-bar-draw" style="width:' + draw + '%"></div></div>'
      + '      <span class="prono-prob-pct">' + draw.toFixed(0) + '%</span>'
      + '    </div>'
      + '    <div class="prono-prob-row">'
      + '      <span class="prono-prob-label">' + (NAMES[p.team_b] || p.team_b) + '</span>'
      + '      <div class="prono-prob-bar-wrap"><div class="prono-prob-bar prono-bar-b" style="width:' + bWin + '%"></div></div>'
      + '      <span class="prono-prob-pct">' + bWin.toFixed(0) + '%</span>'
      + '    </div>'
      + '  </div>'
      + (p.team_a_context || p.team_b_context
         ? '<div class="prono-contexts">'
           + (p.team_a_context ? '<div class="prono-ctx prono-ctx-a"><strong>' + (NAMES[p.team_a]||p.team_a) + ':</strong> ' + p.team_a_context + '</div>' : '')
           + (p.team_b_context ? '<div class="prono-ctx prono-ctx-b"><strong>' + (NAMES[p.team_b]||p.team_b) + ':</strong> ' + p.team_b_context + '</div>' : '')
           + '</div>'
         : '')
      + (p.explanation ? '<div class="prono-explanation">' + p.explanation + '</div>' : '')
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
      errEl.textContent = result.message;
      setTimeout(function() {
        window.SupaAuth && window.SupaAuth.refreshAuthState();
      }, 1200);
    } else {
      errEl.textContent = result.message;
    }
  }

  // ── Auth change callback (llamado desde auth.js) ─────────────

  async function onAuthChange(user, isPremium, profile) {
    if (!user) {
      renderLocked();
    } else if (!isPremium) {
      renderPaymentModal(profile);
    } else {
      var predictions = await loadPredictions();
      renderActive(predictions);
    }
  }

  // ── Init ────────────────────────────────────────────────────

  function init() {
    renderLocked();
  }

  window.PremiumSection = {
    init: init,
    onAuthChange: onAuthChange,
    submitCode: submitCode,
    loadPredictions: loadPredictions
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
