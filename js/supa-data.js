/**
 * supa-data.js - shared Supabase data helpers with local-dev fallback.
 * Exposes: window.SupaData
 */
(function () {
  'use strict';

  var _client = null;

  function isConfigured() {
    return !!(
      window.SUPABASE_URL &&
      window.SUPABASE_ANON_KEY &&
      !String(window.SUPABASE_URL).includes('TU-PROYECTO') &&
      window.supabase
    );
  }

  function isLocalDev() {
    var host = window.location && window.location.hostname;
    var protocol = window.location && window.location.protocol;
    return protocol === 'file:' || host === 'localhost' || host === '127.0.0.1';
  }

  function getClient() {
    if (_client) return _client;
    if (!isConfigured()) return null;
    _client = window.supabase.createClient(window.SUPABASE_URL, window.SUPABASE_ANON_KEY);
    return _client;
  }

  async function getSession(client) {
    if (!client || !client.auth || !client.auth.getSession) return null;
    try {
      var ref = await client.auth.getSession();
      return ref && ref.data ? ref.data.session : null;
    } catch (e) {
      return null;
    }
  }

  async function fetchJson(url) {
    var response = await fetch(url);
    if (!response.ok) throw new Error('HTTP ' + response.status + ' loading ' + url);
    return await response.json();
  }

  async function loadSupabaseOrLocal(remoteLoader, localUrl, normalizer) {
    var normalize = typeof normalizer === 'function' ? normalizer : function (value) { return value; };
    var client = getClient();

    if (client && typeof remoteLoader === 'function') {
      try {
        var remote = await remoteLoader(client);
        if (remote !== null && remote !== undefined) return normalize(remote, 'supabase');
      } catch (e) {
        console.warn('[SupaData] Supabase load failed:', e.message || e);
      }
    }

    if (!localUrl || !isLocalDev()) return null;
    try {
      return normalize(await fetchJson(localUrl), 'local');
    } catch (e2) {
      console.warn('[SupaData] Local fallback failed:', e2.message || e2);
      return null;
    }
  }

  async function redeemPremiumCode(code) {
    var client = getClient();
    if (!client) return { success: false, message: 'Supabase no configurado.' };
    var ref = await client.rpc('redeem_premium_code', { input_code: code });
    if (ref.error) return { success: false, message: ref.error.message || 'Error al canjear el codigo.' };
    return ref.data || { success: false, message: 'Respuesta inesperada del servidor.' };
  }

  async function loadPredictions() {
    return await loadSupabaseOrLocal(
      // Sin gate de sesión: anon y free también consultan. El RLS decide qué
      // filas vuelven — premium ve las 72; anon/free solo los partidos
      // finished (policy 28_predictions_free_finished.sql).
      async function (client) {
        var ref = await client
          .from('predictions')
          .select('*')
          .eq('published', true)
          .order('group_code')
          .order('matchday');
        if (ref.error) throw ref.error;
        return ref.data || [];
      },
      'data/predictions.mock.json',
      function (value, source) {
        return source === 'local' ? (value.predictions || []) : value;
      }
    );
  }

  async function loadSimulationData() {
    var client = getClient();
    if (!client) {
      if (!isLocalDev()) return null;
      try {
        return normalizeLocalSimulation(await fetchJson('data/mc_results.json'));
      } catch (e) {
        return null;
      }
    }

    var session = await getSession(client);
    if (session) {
      try {
        var premium = await loadPremiumSimulationData(client);
        if (premium && premium.standings && premium.standings.length) return premium;
      } catch (e1) {
        console.warn('[SupaData] Premium simulation load failed, falling back public:', e1.message || e1);
      }
    }

    return await loadPublicSimulationData();
  }

  async function loadPremiumSimulationData(client) {
    var runRef = await client
      .from('simulation_runs')
      .select('*')
      .eq('is_active', true)
      .order('created_at', { ascending: false })
      .limit(1)
      .single();
    if (runRef.error || !runRef.data) return null;

    var runId = runRef.data.id;
    var standRef = await client
      .from('simulation_group_standings')
      .select('*')
      .eq('simulation_run', runId);
    if (standRef.error) return null;

    var terRef = await client
      .from('simulation_terceros_table')
      .select('*')
      .eq('simulation_run', runId)
      .order('rank');

    return {
      run: runRef.data,
      standings: standRef.data || [],
      terceros: terRef.error ? [] : (terRef.data || []),
      source: 'premium'
    };
  }

  function pointsPct(points) {
    var values = {};
    ['0','1','2','3','4','5','6','7','9'].forEach(function(key) {
      values[key] = key === String(points) ? 100 : 0;
    });
    return values;
  }

  function normalizePublicSimulation(standingsRows, thirdRows, projection) {
    var classifiedThird = {};
    (thirdRows || []).forEach(function(row) {
      classifiedThird[row.team_code] = row.classified === true || row.classified === 'true';
    });

    var standings = (standingsRows || []).map(function(row) {
      var rank = parseInt(row.group_rank, 10);
      var isBestThird = rank === 3 && classifiedThird[row.team_code];
      return {
        team_code: row.team_code,
        qualified_pct: rank <= 2 || isBestThird ? 100 : 0,
        first_pct: rank === 1 ? 100 : 0,
        second_pct: rank === 2 ? 100 : 0,
        third_pct: rank === 3 ? 100 : 0,
        best_third_pct: isBestThird ? 100 : 0,
        fourth_pct: rank === 4 ? 100 : 0,
        points_pct: pointsPct(row.pts || 0)
      };
    });

    var terceros = (thirdRows || []).map(function(row) {
      return {
        rank: row.third_rank,
        group_id: row.group_id,
        team_code: row.team_code,
        third_pct: 100,
        qualifies_pct: row.classified ? 100 : 0,
        avg_pts: row.pts,
        avg_gd: row.dg,
        avg_gf: row.gf,
        qualifies: row.classified === true || row.classified === 'true'
      };
    });

    return {
      run: {
        id: 'public-final-groups',
        runs: 1,
        seed: null,
        version: 'final',
        public_final: true
      },
      standings: standings,
      terceros: terceros,
      bracket_projection: projection || null,
      source: 'public'
    };
  }

  function normalizeLocalSimulation(value) {
    if (!value) return null;
    var standings = [];
    Object.keys(value.teams || {}).forEach(function(code) {
      var row = Object.assign({ team_code: code }, value.teams[code]);
      standings.push(row);
    });
    var terceros = (value.terceros_table || []).map(function(row) {
      return Object.assign({ group_id: row.group_id || row.group }, row);
    });
    return {
      run: {
        id: 'local-mc',
        runs: value.runs || 0,
        seed: value.seed,
        version: value.version || 'local'
      },
      standings: standings,
      terceros: terceros,
      source: 'local'
    };
  }

  async function loadPublicSimulationData() {
    var client = getClient();
    if (!client) return null;
    try {
      var standingsRef = await client.rpc('get_group_standings');
      if (standingsRef.error) throw standingsRef.error;

      var thirdsRef = await client.rpc('get_best_thirds');
      if (thirdsRef.error) throw thirdsRef.error;

      var projectionRef = await client.rpc('get_bracket_projection');
      var projection = projectionRef.error ? null : (projectionRef.data || null);

      return normalizePublicSimulation(
        standingsRef.data || [],
        thirdsRef.data || [],
        projection
      );
    } catch (e) {
      console.warn('[SupaData] Public simulation load failed:', e.message || e);
      return null;
    }
  }

  async function loadSimulationTeams() {
    return await loadSupabaseOrLocal(
      async function () {
        var data = await loadSimulationData();
        if (!data || !data.standings || !data.standings.length) return null;
        var teams = {};
        data.standings.forEach(function (row) { teams[row.team_code] = row; });
        return teams;
      },
      'data/mc_results.json',
      function (value, source) {
        return source === 'local' ? (value.teams || value) : value;
      }
    );
  }

  async function loadMatchResults() {
    return await loadSupabaseOrLocal(
      async function (client) {
        var ref = await client
          .from('match_results')
          .select('match_number,phase,group_id,home_team,away_team,status,home_goals,away_goals')
          .eq('status', 'finished');
        if (ref.error) throw ref.error;
        return ref.data || [];
      },
      'data/match_results.mock.json',
      function (value, source) {
        return source === 'local' ? (value.results || []) : value;
      }
    );
  }

  async function loadGroupStandings() {
    var client = getClient();
    if (!client) return null;
    var ref = await client.rpc('get_group_standings');
    if (ref.error) return null;
    return ref.data || [];
  }

  window.SupaData = {
    getClient: getClient,
    isConfigured: isConfigured,
    loadSupabaseOrLocal: loadSupabaseOrLocal,
    isLocalDev: isLocalDev,
    redeemPremiumCode: redeemPremiumCode,
    loadPredictions: loadPredictions,
    loadMatchResults: loadMatchResults,
    loadPublicSimulationData: loadPublicSimulationData,
    loadSimulationData: loadSimulationData,
    loadSimulationTeams: loadSimulationTeams,
    loadGroupStandings: loadGroupStandings
  };
})();
