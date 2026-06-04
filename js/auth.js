/**
 * auth.js — Autenticación Supabase para Mundial 2026 Predicciones
 * Expone: window.SupaAuth
 * Requiere: window.SUPABASE_URL, window.SUPABASE_ANON_KEY (de config.js)
 */
(function () {
  'use strict';

  var _client = null;

  function getClient() {
    if (!_client) {
      if (window.SupaData && window.SupaData.getClient) {
        _client = window.SupaData.getClient();
        if (_client) return _client;
      }
      if (!window.SUPABASE_URL || !window.SUPABASE_ANON_KEY ||
          window.SUPABASE_URL.includes('TU-PROYECTO')) {
        console.warn('[SupaAuth] config.js no configurado — modo demo activo');
        return null;
      }
      _client = window.supabase.createClient(
        window.SUPABASE_URL,
        window.SUPABASE_ANON_KEY
      );
    }
    return _client;
  }

  // ── Funciones de auth ────────────────────────────────────────

  async function getCurrentUser() {
    var c = getClient();
    if (!c) return null;
    var ref = await c.auth.getUser();
    return ref.data && ref.data.user ? ref.data.user : null;
  }

  async function getProfile(userId) {
    var c = getClient();
    if (!c || !userId) return null;
    var ref = await c.from('profiles').select('*').eq('id', userId).single();
    return ref.data || null;
  }

  async function signUp(email, password, fullName, country) {
    var c = getClient();
    if (!c) return { error: { message: 'Supabase no configurado' } };
    return await c.auth.signUp({
      email: email,
      password: password,
      options: { data: { full_name: fullName, country: country || '' } }
    });
  }

  async function signIn(email, password) {
    var c = getClient();
    if (!c) return { error: { message: 'Supabase no configurado' } };
    return await c.auth.signInWithPassword({ email: email, password: password });
  }

  async function signOut() {
    var c = getClient();
    if (!c) return;
    await c.auth.signOut();
  }

  // ── Modal de autenticación ───────────────────────────────────

  function openAuthModal(onSuccess, tab) {
    var overlay = document.getElementById('auth-modal-overlay');
    if (!overlay) return;
    overlay.classList.add('open');
    overlay.dataset.onSuccess = onSuccess || '';
    if (tab) setAuthTab(tab);
    document.getElementById('auth-modal-email').focus();
    document.getElementById('auth-error').textContent = '';
  }

  function closeAuthModal() {
    var overlay = document.getElementById('auth-modal-overlay');
    if (overlay) overlay.classList.remove('open');
  }

  function setAuthTab(tab) {
    var loginTab     = document.getElementById('auth-tab-login');
    var signupTab    = document.getElementById('auth-tab-signup');
    var nameField    = document.getElementById('auth-name-wrap');
    var countryField = document.getElementById('auth-country-wrap');
    var btnText      = document.getElementById('auth-submit-text');
    if (tab === 'login') {
      loginTab.classList.add('active');
      signupTab.classList.remove('active');
      nameField.style.display = 'none';
      if (countryField) countryField.style.display = 'none';
      btnText.textContent = 'Iniciar sesión';
    } else {
      signupTab.classList.add('active');
      loginTab.classList.remove('active');
      nameField.style.display = 'block';
      if (countryField) countryField.style.display = 'block';
      btnText.textContent = 'Crear cuenta';
    }
    document.getElementById('auth-error').textContent = '';
  }

  async function handleAuthSubmit(e) {
    e.preventDefault();
    var tab      = document.getElementById('auth-tab-signup').classList.contains('active')
                   ? 'signup' : 'login';
    var email    = document.getElementById('auth-modal-email').value.trim();
    var password = document.getElementById('auth-modal-password').value;
    var fullName = document.getElementById('auth-modal-name').value.trim();
    var countryEl = document.getElementById('auth-modal-country');
    var country  = countryEl ? countryEl.value : '';
    var errEl    = document.getElementById('auth-error');
    var btn      = document.getElementById('auth-submit-btn');

    if (!email || !password) {
      errEl.textContent = 'Completa email y contraseña.';
      return;
    }
    if (tab === 'signup' && password.length < 8) {
      errEl.textContent = 'La contraseña debe tener al menos 8 caracteres.';
      return;
    }

    btn.disabled = true;
    btn.textContent = tab === 'login' ? 'Entrando…' : 'Creando cuenta…';
    errEl.textContent = '';

    var result = tab === 'signup'
      ? await signUp(email, password, fullName, country)
      : await signIn(email, password);

    btn.disabled = false;
    btn.textContent = tab === 'login' ? 'Iniciar sesión' : 'Crear cuenta';

    if (result.error) {
      var msg = result.error.message || 'Error desconocido';
      if (msg.includes('Invalid login')) msg = 'Email o contraseña incorrectos.';
      if (msg.includes('already registered')) msg = 'Este email ya tiene cuenta. Inicia sesión.';
      errEl.textContent = msg;
      return;
    }

    if (tab === 'signup' && result.data && !result.data.session) {
      errEl.style.color = 'var(--yes)';
      errEl.textContent = 'Revisa tu email para confirmar tu cuenta.';
      return;
    }

    closeAuthModal();
    await refreshAuthState();
  }

  // ── Estado global de autenticación ───────────────────────────

  async function refreshAuthState() {
    var user    = await getCurrentUser();
    var profile = user ? await getProfile(user.id) : null;
    var isPrem  = profile && profile.is_premium;

    window.__authState = { user: user, isPremium: !!isPrem };

    updateNavAuthUI(user, isPrem);

    if (window.PremiumSection) {
      window.PremiumSection.onAuthChange(user, isPrem, profile);
    }
    if (window.PredicionesSection) {
      window.PredicionesSection.onAuthChange(user, isPrem, profile);
    }
    if (window.BracketSection) {
      window.BracketSection.setPremiumState(!!isPrem);
    }
  }

  function updateNavAuthUI(user, isPremium) {
    var joinBtn    = document.getElementById('join-btn');
    var userInfo   = document.getElementById('nav-user-info');
    if (!joinBtn) return;

    if (user) {
      joinBtn.style.display = 'none';
      if (userInfo) {
        userInfo.style.display = 'flex';
        var emailEl = document.getElementById('nav-user-email');
        if (emailEl) emailEl.textContent = user.email.split('@')[0];
        var premBadge = document.getElementById('nav-premium-badge');
        if (premBadge) premBadge.style.display = isPremium ? 'inline' : 'none';
      }
    } else {
      joinBtn.style.display = '';
      if (userInfo) userInfo.style.display = 'none';
    }
  }

  // ── Inicialización ───────────────────────────────────────────

  function init() {
    var c = getClient();
    if (!c) return;

    // Auth state change listener
    c.auth.onAuthStateChange(function (event, session) {
      refreshAuthState();
    });

    refreshAuthState();

    // Form submit
    var form = document.getElementById('auth-form');
    if (form) form.addEventListener('submit', handleAuthSubmit);

    // Tabs
    var tabLogin  = document.getElementById('auth-tab-login');
    var tabSignup = document.getElementById('auth-tab-signup');
    if (tabLogin)  tabLogin.addEventListener('click',  function() { setAuthTab('login'); });
    if (tabSignup) tabSignup.addEventListener('click',  function() { setAuthTab('signup'); });

    // Cerrar con overlay click
    var overlay = document.getElementById('auth-modal-overlay');
    if (overlay) overlay.addEventListener('click', function(e) {
      if (e.target === overlay) closeAuthModal();
    });

    // Sign out
    var signOutBtn = document.getElementById('nav-signout-btn');
    if (signOutBtn) signOutBtn.addEventListener('click', async function() {
      await signOut();
      refreshAuthState();
    });
  }

  // Exponer API pública
  window.SupaAuth = {
    getClient: getClient,
    getCurrentUser: getCurrentUser,
    getProfile: getProfile,
    signIn: signIn,
    signUp: signUp,
    signOut: signOut,
    openAuthModal: openAuthModal,
    closeAuthModal: closeAuthModal,
    setAuthTab: setAuthTab,
    refreshAuthState: refreshAuthState,
    init: init
  };

  // Auto-init cuando el DOM está listo
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
