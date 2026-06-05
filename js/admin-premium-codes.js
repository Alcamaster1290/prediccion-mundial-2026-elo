(function () {
  'use strict';

  var client = null;
  var currentCode = '';
  var teamContentRows = [];
  var els = {};
  var TEAM_MANIFEST_URL = '../data/team-content-manifest.json';
  var MISSING_LABELS = {
    advanced_profile: 'perfil avanzado',
    analysis_json: 'analisis local',
    flag: 'bandera',
    html_section: 'pagina',
    list_png: 'lista imagen',
    list_txt: 'texto fuente',
    player_elo: 'ELO jugadores',
    players: 'plantel DB',
    players_json: 'plantel local',
    predictions: 'predicciones',
    profile: 'perfil',
    simulation: 'simulacion',
    star_image: 'foto figura',
    starters: 'titulares DB',
    starter_json: 'titulares local',
    strength: 'modelo',
    xi_image: 'XI'
  };

  function byId(id) {
    return document.getElementById(id);
  }

  function bindElements() {
    els.loading = byId('admin-premium-loading');
    els.auth = byId('admin-premium-auth');
    els.denied = byId('admin-premium-denied');
    els.app = byId('admin-premium-app');
    els.userbar = byId('admin-premium-userbar');
    els.userEmail = byId('admin-premium-user-email');
    els.signout = byId('admin-premium-signout');
    els.loginForm = byId('admin-premium-login-form');
    els.loginEmail = byId('admin-premium-email');
    els.loginPassword = byId('admin-premium-password');
    els.loginButton = byId('admin-premium-login-button');
    els.loginStatus = byId('admin-premium-login-status');
    els.createForm = byId('admin-premium-create-form');
    els.createNotes = byId('admin-premium-notes');
    els.createButton = byId('admin-premium-create-button');
    els.createStatus = byId('admin-premium-create-status');
    els.result = byId('admin-premium-result');
    els.codeOutput = byId('admin-premium-code-output');
    els.copyButton = byId('admin-premium-copy-button');
    els.refresh = byId('admin-premium-refresh');
    els.listStatus = byId('admin-premium-list-status');
    els.rows = byId('admin-premium-code-rows');
    els.empty = byId('admin-premium-empty');
    els.contentStatus = byId('admin-content-status');
    els.contentRefresh = byId('admin-content-refresh');
    els.contentStatusText = byId('admin-content-status-text');
    els.simulationStatus = byId('admin-simulation-status');
    els.realResultsStatus = byId('admin-real-results-status');
    els.predictionsStatus = byId('admin-predictions-status');
    els.teamContentStatus = byId('admin-team-content-status');
    els.teamContentRefresh = byId('admin-team-content-refresh');
    els.teamContentStatusText = byId('admin-team-content-status-text');
    els.teamSummary = byId('admin-team-summary');
    els.teamRows = byId('admin-team-status-rows');
    els.teamEmpty = byId('admin-team-empty');
    els.teamSearch = byId('admin-team-search');
    els.teamGroupFilter = byId('admin-team-group-filter');
    els.teamMissingFilter = byId('admin-team-missing-filter');
  }

  function getClient() {
    if (client) return client;
    if (!window.supabase || !window.SUPABASE_URL || !window.SUPABASE_ANON_KEY) {
      throw new Error('Supabase no esta configurado.');
    }
    client = window.supabase.createClient(window.SUPABASE_URL, window.SUPABASE_ANON_KEY, {
      auth: { detectSessionInUrl: true }
    });
    return client;
  }

  function showOnly(section) {
    [els.loading, els.auth, els.denied, els.app].forEach(function (el) {
      if (el) el.classList.add('hidden');
    });
    if (section) section.classList.remove('hidden');
  }

  function setUserbar(user) {
    if (!els.userbar) return;
    if (user && user.email) {
      els.userEmail.textContent = user.email;
      els.userbar.classList.remove('hidden');
    } else {
      els.userEmail.textContent = '';
      els.userbar.classList.add('hidden');
    }
  }

  function setStatus(el, message, tone) {
    if (!el) return;
    el.textContent = message || '';
    el.classList.remove('error', 'ok');
    if (tone) el.classList.add(tone);
  }

  function setBusy(button, busy, label) {
    if (!button) return;
    button.disabled = !!busy;
    if (label) button.textContent = label;
  }

  function normalizeError(error) {
    if (!error) return 'Operacion no completada.';
    if (error.message && /invalid login/i.test(error.message)) {
      return 'No se pudo iniciar sesion con esas credenciales.';
    }
    return error.message || 'Operacion no completada.';
  }

  function validateNotes() {
    var notes = (els.createNotes.value || '').trim();
    if (notes.length > 500) {
      return { error: 'Las notas no pueden superar 500 caracteres.' };
    }
    return { notes: notes || null };
  }

  function formatDate(value) {
    if (!value) return '-';
    var date = new Date(value);
    if (Number.isNaN(date.getTime())) return '-';
    return new Intl.DateTimeFormat('es-PE', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    }).format(date);
  }

  async function fetchJson(url) {
    var response = await fetch(url, { cache: 'no-store' });
    if (!response.ok) throw new Error('HTTP ' + response.status + ' cargando ' + url);
    return await response.json();
  }

  function clearRows() {
    while (els.rows.firstChild) {
      els.rows.removeChild(els.rows.firstChild);
    }
  }

  function cell(text) {
    var td = document.createElement('td');
    td.textContent = text == null || text === '' ? '-' : String(text);
    return td;
  }

  function statusCell(row) {
    var td = document.createElement('td');
    var badge = document.createElement('span');
    badge.className = row.is_used ? 'badge used' : 'badge open';
    badge.textContent = row.is_used ? 'Usado' : 'Disponible';
    td.appendChild(badge);
    return td;
  }

  function userLabel(row) {
    if (row.used_by_name && row.used_by_email) {
      return row.used_by_name + ' - ' + row.used_by_email;
    }
    return row.used_by_email || row.used_by;
  }

  function renderRows(rows) {
    clearRows();
    if (!rows || rows.length === 0) {
      els.empty.classList.remove('hidden');
      return;
    }
    els.empty.classList.add('hidden');
    rows.forEach(function (row) {
      var tr = document.createElement('tr');
      tr.appendChild(statusCell(row));
      tr.appendChild(cell(formatDate(row.created_at)));
      tr.appendChild(cell(formatDate(row.used_at)));
      tr.appendChild(cell(userLabel(row)));
      tr.appendChild(cell(row.notes));
      els.rows.appendChild(tr);
    });
  }

  function valueOrDash(value) {
    return value == null || value === '' ? '-' : String(value);
  }

  function integerText(value) {
    var number = Number(value || 0);
    return Number.isFinite(number) ? number.toLocaleString('es-PE') : '0';
  }

  function clearList(el) {
    while (el && el.firstChild) {
      el.removeChild(el.firstChild);
    }
  }

  function appendMetric(list, label, value) {
    if (!list) return;
    var dt = document.createElement('dt');
    var dd = document.createElement('dd');
    dt.textContent = label;
    dd.textContent = valueOrDash(value);
    list.appendChild(dt);
    list.appendChild(dd);
  }

  function uniqueList(values) {
    var seen = {};
    var result = [];
    (values || []).forEach(function (value) {
      if (!value || seen[value]) return;
      seen[value] = true;
      result.push(value);
    });
    return result;
  }

  function groupSortValue(row) {
    return row.group_id || 'Z';
  }

  function missingLabel(key) {
    return MISSING_LABELS[key] || key;
  }

  function appendBadge(container, text, tone) {
    if (!container) return;
    var badge = document.createElement('span');
    badge.className = 'mini-badge' + (tone ? ' ' + tone : '');
    badge.textContent = text;
    container.appendChild(badge);
  }

  function clearElement(el) {
    while (el && el.firstChild) {
      el.removeChild(el.firstChild);
    }
  }

  function renderContentStatus(status) {
    var simulation = status && status.simulation ? status.simulation : {};
    var real = status && status.real_results ? status.real_results : {};
    var predictions = status && status.published_predictions ? status.published_predictions : {};

    clearList(els.simulationStatus);
    clearList(els.realResultsStatus);
    clearList(els.predictionsStatus);

    appendMetric(els.simulationStatus, 'Escenario', simulation.scenario_name);
    appendMetric(els.simulationStatus, 'Corridas', integerText(simulation.runs));
    appendMetric(els.simulationStatus, 'Tablas equipo', integerText(simulation.standings_rows_for_latest));
    appendMetric(els.simulationStatus, 'Mejores terceros', integerText(simulation.terceros_rows_for_latest));
    appendMetric(els.simulationStatus, 'Ultima carga', formatDate(simulation.completed_at || simulation.created_at));

    appendMetric(els.realResultsStatus, 'Partidos', integerText(real.total_matches));
    appendMetric(els.realResultsStatus, 'Fase grupos', integerText(real.group_matches));
    appendMetric(els.realResultsStatus, 'Con resultado', integerText(real.loaded_results));
    appendMetric(els.realResultsStatus, 'En vivo', integerText(real.live_matches));
    appendMetric(els.realResultsStatus, 'Ultima actualizacion', formatDate(real.last_updated_at));

    appendMetric(els.predictionsStatus, 'Publicados', integerText(predictions.published));
    appendMetric(els.predictionsStatus, 'Borradores', integerText(predictions.drafts));
    appendMetric(els.predictionsStatus, 'Total', integerText(predictions.total));
    appendMetric(els.predictionsStatus, 'Ultima edicion', formatDate(predictions.last_updated_at || predictions.last_created_at));
  }

  async function loadContentStatus() {
    setStatus(els.contentStatusText, 'Cargando estado de datos...', '');
    var ref = await getClient().rpc('admin_get_content_status');
    if (ref.error) {
      setStatus(els.contentStatusText, normalizeError(ref.error), 'error');
      return;
    }
    if (!ref.data || ref.data.success !== true) {
      setStatus(els.contentStatusText, ref.data && ref.data.message ? ref.data.message : 'No se pudo cargar el estado.', 'error');
      return;
    }
    renderContentStatus(ref.data);
    setStatus(els.contentStatusText, 'Estado actualizado.', 'ok');
  }

  async function loadLocalTeamManifest() {
    try {
      return await fetchJson(TEAM_MANIFEST_URL);
    } catch (error) {
      return { meta: { total_teams: 0 }, teams: [] };
    }
  }

  function mergeTeamContentStatus(remoteStatus, localManifest) {
    var localByCode = {};
    var remoteTeams = remoteStatus && remoteStatus.teams ? remoteStatus.teams : [];
    var localTeams = localManifest && localManifest.teams ? localManifest.teams : [];

    localTeams.forEach(function (team) {
      localByCode[team.team_code] = team;
    });

    return remoteTeams.map(function (remote) {
      var local = localByCode[remote.team_code] || {};
      var assets = local.assets || {};
      var localState = local.local || {};
      var dbMissing = remote.db_missing || [];
      var localMissing = local.local_missing || [];
      var missing = uniqueList(dbMissing.concat(localMissing));
      return {
        team_code: remote.team_code,
        asset_code: local.asset_code || remote.team_code,
        name: local.name || remote.name || remote.team_code.toUpperCase(),
        remote_name: remote.name || '',
        group_id: remote.group_id || local.group_id || '',
        player_rows: remote.player_rows || 0,
        starter_rows: remote.starter_rows || 0,
        player_elo_rows: remote.player_elo_rows || 0,
        strength_score: remote.strength_score,
        strength_method: remote.strength_method || '',
        profile_published: !!remote.profile_published,
        has_premium_profile: !!remote.has_premium_profile,
        simulation_rows: remote.simulation_rows || 0,
        published_prediction_rows: remote.published_prediction_rows || 0,
        assets: assets,
        local: localState,
        db_missing: dbMissing,
        local_missing: localMissing,
        missing: missing
      };
    }).sort(function (a, b) {
      if (groupSortValue(a) !== groupSortValue(b)) return groupSortValue(a).localeCompare(groupSortValue(b));
      return a.team_code.localeCompare(b.team_code);
    });
  }

  function appendSummaryPill(label, value) {
    var pill = document.createElement('span');
    pill.className = 'summary-pill';
    pill.textContent = label + ': ' + value;
    els.teamSummary.appendChild(pill);
  }

  function renderTeamSummary(remoteSummary) {
    var summary = remoteSummary || {};
    var total = teamContentRows.length || summary.total_teams || 0;
    var completeAll = teamContentRows.filter(function (row) { return row.missing.length === 0; }).length;
    var localAnalyzed = teamContentRows.filter(function (row) { return row.local && row.local.analysis_json; }).length;
    var xiImages = teamContentRows.filter(function (row) { return row.assets && row.assets.xi_image; }).length;
    var listTexts = teamContentRows.filter(function (row) { return row.assets && row.assets.list_txt; }).length;

    clearElement(els.teamSummary);
    appendSummaryPill('Equipos', integerText(total));
    appendSummaryPill('Planteles DB', integerText(summary.teams_with_players));
    appendSummaryPill('Perfiles', integerText(summary.teams_with_profiles));
    appendSummaryPill('Modelo', integerText(summary.teams_with_strength));
    appendSummaryPill('Analisis local', integerText(localAnalyzed));
    appendSummaryPill('XI assets', integerText(xiImages));
    appendSummaryPill('Textos fuente', integerText(listTexts));
    appendSummaryPill('Completos', integerText(completeAll));
  }

  function makeTeamCell(row) {
    var td = document.createElement('td');
    td.className = 'team-name-cell';
    var strong = document.createElement('strong');
    var span = document.createElement('span');
    strong.textContent = row.name;
    span.textContent = row.team_code.toUpperCase() + ' · Grupo ' + row.group_id;
    td.appendChild(strong);
    td.appendChild(span);
    return td;
  }

  function makeModelCell(row) {
    var td = document.createElement('td');
    appendBadge(td, row.strength_score ? 'score ' + Number(row.strength_score).toFixed(1) : 'sin score', row.strength_score ? 'ok' : 'miss');
    appendBadge(td, row.strength_method === 'xi_blend_adj' ? 'XI blend' : 'ELO int.', row.strength_method ? 'ok' : 'miss');
    appendBadge(td, row.simulation_rows > 0 ? 'sim' : 'sin sim', row.simulation_rows > 0 ? 'ok' : 'miss');
    appendBadge(td, row.published_prediction_rows >= 3 ? 'pred' : 'pred incompleta', row.published_prediction_rows >= 3 ? 'ok' : 'miss');
    return td;
  }

  function makeSquadCell(row) {
    var td = document.createElement('td');
    appendBadge(td, row.player_rows + '/26', row.player_rows >= 26 ? 'ok' : 'miss');
    appendBadge(td, row.starter_rows + '/11 titulares', row.starter_rows >= 11 ? 'ok' : 'miss');
    appendBadge(td, row.player_elo_rows + ' ELO', row.player_elo_rows >= 11 ? 'ok' : 'warn');
    return td;
  }

  function makeContentCell(row) {
    var td = document.createElement('td');
    appendBadge(td, row.profile_published ? 'perfil' : 'sin perfil', row.profile_published ? 'ok' : 'miss');
    appendBadge(td, row.has_premium_profile ? 'avanzado' : 'sin avanzado', row.has_premium_profile ? 'ok' : 'miss');
    appendBadge(td, row.local && row.local.analysis_json ? 'analysis' : 'sin analysis', row.local && row.local.analysis_json ? 'ok' : 'miss');
    appendBadge(td, row.local && row.local.html_section ? 'pagina' : 'sin pagina', row.local && row.local.html_section ? 'ok' : 'miss');
    return td;
  }

  function makeAssetsCell(row) {
    var td = document.createElement('td');
    var assets = row.assets || {};
    appendBadge(td, assets.flag ? 'flag' : 'sin flag', assets.flag ? 'ok' : 'miss');
    appendBadge(td, assets.xi_image ? 'XI' : 'sin XI', assets.xi_image ? 'ok' : 'miss');
    appendBadge(td, assets.star_image ? 'figura' : 'sin figura', assets.star_image ? 'ok' : 'miss');
    appendBadge(td, assets.list_png ? 'lista img' : 'sin lista img', assets.list_png ? 'ok' : 'miss');
    appendBadge(td, assets.list_txt ? 'texto' : 'sin texto', assets.list_txt ? 'ok' : 'miss');
    return td;
  }

  function makeMissingCell(row) {
    var td = document.createElement('td');
    td.className = 'missing-list';
    if (!row.missing || row.missing.length === 0) {
      appendBadge(td, 'completo', 'ok');
      return td;
    }
    row.missing.forEach(function (key) {
      appendBadge(td, missingLabel(key), 'miss');
    });
    return td;
  }

  function rowMatchesFilters(row) {
    var group = els.teamGroupFilter ? els.teamGroupFilter.value : '';
    var onlyMissing = els.teamMissingFilter ? els.teamMissingFilter.checked : false;
    var query = els.teamSearch ? (els.teamSearch.value || '').trim().toLowerCase() : '';
    if (group && row.group_id !== group) return false;
    if (onlyMissing && (!row.missing || row.missing.length === 0)) return false;
    if (!query) return true;
    var haystack = [
      row.team_code,
      row.asset_code,
      row.name,
      row.remote_name,
      row.group_id
    ].concat(row.missing.map(missingLabel)).join(' ').toLowerCase();
    return haystack.indexOf(query) !== -1;
  }

  function renderTeamContentRows() {
    clearElement(els.teamRows);
    var rows = teamContentRows.filter(rowMatchesFilters);
    if (!rows.length) {
      els.teamEmpty.classList.remove('hidden');
      return;
    }
    els.teamEmpty.classList.add('hidden');
    rows.forEach(function (row) {
      var tr = document.createElement('tr');
      tr.appendChild(makeTeamCell(row));
      tr.appendChild(makeModelCell(row));
      tr.appendChild(makeSquadCell(row));
      tr.appendChild(makeContentCell(row));
      tr.appendChild(makeAssetsCell(row));
      tr.appendChild(makeMissingCell(row));
      els.teamRows.appendChild(tr);
    });
  }

  async function loadTeamContentStatus() {
    setStatus(els.teamContentStatusText, 'Cargando cobertura por equipo...', '');
    var refs = await Promise.all([
      getClient().rpc('admin_get_team_data_status'),
      loadLocalTeamManifest()
    ]);
    var remoteRef = refs[0];
    var localManifest = refs[1];
    if (remoteRef.error) {
      setStatus(els.teamContentStatusText, normalizeError(remoteRef.error), 'error');
      return;
    }
    if (!remoteRef.data || remoteRef.data.success !== true) {
      setStatus(els.teamContentStatusText, remoteRef.data && remoteRef.data.message ? remoteRef.data.message : 'No se pudo cargar la cobertura.', 'error');
      return;
    }
    teamContentRows = mergeTeamContentStatus(remoteRef.data, localManifest);
    renderTeamSummary(remoteRef.data.summary || {});
    renderTeamContentRows();
    setStatus(els.teamContentStatusText, 'Cobertura actualizada.', 'ok');
  }

  async function loadCodes() {
    setStatus(els.listStatus, 'Cargando codigos...', '');
    var ref = await getClient().rpc('admin_list_premium_codes');
    if (ref.error) {
      setStatus(els.listStatus, normalizeError(ref.error), 'error');
      renderRows([]);
      return;
    }
    renderRows(ref.data || []);
    setStatus(els.listStatus, 'Ultimos 100 codigos cargados.', 'ok');
  }

  async function verifyAccess() {
    showOnly(els.loading);
    var c = getClient();
    var sessionRef = await c.auth.getSession();
    if (sessionRef.error || !sessionRef.data || !sessionRef.data.session) {
      setUserbar(null);
      showOnly(els.auth);
      return;
    }

    var userRef = await c.auth.getUser();
    var user = userRef.data && userRef.data.user ? userRef.data.user : null;
    setUserbar(user);

    var roleRef = await c.rpc('has_staff_role', { required_role: 'admin' });
    if (roleRef.error || roleRef.data !== true) {
      showOnly(els.denied);
      return;
    }

    showOnly(els.app);
    await loadCodes();
    await loadContentStatus();
    await loadTeamContentStatus();
  }

  async function handleLogin(event) {
    event.preventDefault();
    var email = (els.loginEmail.value || '').trim();
    var password = els.loginPassword.value || '';
    if (!email || email.length > 254 || !password) {
      setStatus(els.loginStatus, 'Completa email y password.', 'error');
      return;
    }

    setBusy(els.loginButton, true, 'Entrando...');
    setStatus(els.loginStatus, '', '');
    var ref = await getClient().auth.signInWithPassword({ email: email, password: password });
    setBusy(els.loginButton, false, 'Iniciar sesion');
    if (ref.error) {
      setStatus(els.loginStatus, normalizeError(ref.error), 'error');
      return;
    }
    els.loginPassword.value = '';
    await verifyAccess();
  }

  async function handleCreate(event) {
    event.preventDefault();
    var result = validateNotes();
    if (result.error) {
      setStatus(els.createStatus, result.error, 'error');
      return;
    }

    setBusy(els.createButton, true, 'Generando...');
    setStatus(els.createStatus, '', '');
    els.result.classList.add('hidden');
    els.codeOutput.textContent = '';
    currentCode = '';

    var ref = await getClient().rpc('admin_create_premium_code', { input_notes: result.notes });
    setBusy(els.createButton, false, 'Generar codigo');

    if (ref.error) {
      setStatus(els.createStatus, normalizeError(ref.error), 'error');
      return;
    }
    if (!ref.data || ref.data.success !== true || !ref.data.code) {
      setStatus(els.createStatus, ref.data && ref.data.message ? ref.data.message : 'No se genero codigo.', 'error');
      return;
    }

    currentCode = String(ref.data.code);
    els.codeOutput.textContent = currentCode;
    els.result.classList.remove('hidden');
    els.createNotes.value = '';
    setStatus(els.createStatus, ref.data.message || 'Codigo generado.', 'ok');
    await loadCodes();
  }

  async function handleCopy() {
    if (!currentCode) {
      setStatus(els.createStatus, 'No hay codigo para copiar.', 'error');
      return;
    }
    try {
      await navigator.clipboard.writeText(currentCode);
      setStatus(els.createStatus, 'Codigo copiado.', 'ok');
    } catch (error) {
      setStatus(els.createStatus, 'No se pudo copiar automaticamente.', 'error');
    }
  }

  async function handleSignout() {
    await getClient().auth.signOut();
    currentCode = '';
    setUserbar(null);
    showOnly(els.auth);
  }

  function init() {
    bindElements();
    els.loginForm.addEventListener('submit', handleLogin);
    els.createForm.addEventListener('submit', handleCreate);
    els.copyButton.addEventListener('click', handleCopy);
    els.refresh.addEventListener('click', loadCodes);
    els.contentRefresh.addEventListener('click', loadContentStatus);
    els.teamContentRefresh.addEventListener('click', loadTeamContentStatus);
    els.teamSearch.addEventListener('input', renderTeamContentRows);
    els.teamGroupFilter.addEventListener('change', renderTeamContentRows);
    els.teamMissingFilter.addEventListener('change', renderTeamContentRows);
    els.signout.addEventListener('click', handleSignout);
    getClient().auth.onAuthStateChange(function () {
      verifyAccess();
    });
    verifyAccess();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
