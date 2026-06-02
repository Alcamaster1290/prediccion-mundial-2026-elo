// standings.js — Live standings from Supabase, best-thirds table, KO path flags
// Requires: SUPABASE_URL, SUPABASE_ANON_KEY (config.js), window.supabase (CDN),
//           KNOCKOUT_MATCHES, TEAM_CODES, TEAM_KO_PATH, TEAM_KO_3RD, renderTeamKOPaths (index.html globals)

(function () {
  'use strict';

  // ── GROUP COMPOSITION ──────────────────────────────────────────────────────
  var GROUP_TEAMS = {
    a: ['mex','zaf','kor','cze'],
    b: ['can','bih','qat','sui'],
    c: ['bra','mar','hti','sco'],
    d: ['usa','pry','aus','tur'],
    e: ['ger','cuw','civ','ecu'],
    f: ['ned','jpn','swe','tun'],
    g: ['bel','egy','irn','nzl'],
    h: ['esp','cpv','ksa','ury'],
    i: ['fra','sen','irq','nor'],
    j: ['arg','alg','aut','jor'],
    k: ['por','cod','uzb','col'],
    l: ['eng','cro','gha','pan']
  };

  // ── FIFA RANKING (approx. June 2026, for final tiebreaker) ────────────────
  var FIFA_RANK = {
    arg:1, fra:2, eng:3, bra:4, bel:5, por:6, ned:7, esp:8, ger:9, ury:10,
    col:11, usa:12, nor:13, mex:14, jpn:15, mar:16, cro:17, sen:18, sui:19,
    aut:20, kor:21, tur:22, aus:23, ecu:24, sco:25, irn:26, egy:27,
    tun:28, can:29, swe:30, hti:31, cze:32, qat:33, irq:34, cpv:35,
    ksa:36, cod:37, alg:38, bih:39, gha:40, zaf:41, uzb:42, jor:43,
    nzl:44, cuw:45, pry:46, pan:47
  };

  // ── CURRENT_STANDINGS global ───────────────────────────────────────────────
  window.CURRENT_STANDINGS = {};

  // ── SUPABASE CLIENT ────────────────────────────────────────────────────────
  var _client = null;
  function getClient() {
    if (_client) return _client;
    if (!window.SUPABASE_URL || !window.SUPABASE_ANON_KEY) return null;
    if (!window.supabase) return null;
    _client = window.supabase.createClient(window.SUPABASE_URL, window.SUPABASE_ANON_KEY);
    return _client;
  }

  // ── INIT DEFAULT STANDINGS FROM DOM ───────────────────────────────────────
  function initDefaultStandings() {
    Object.keys(GROUP_TEAMS).forEach(function (gid) {
      var section = document.getElementById('grupo-' + gid);
      if (!section) return;
      var tbody = section.querySelector('.standings-table tbody');
      if (!tbody) return;
      var rows = Array.from(tbody.querySelectorAll('tr'));
      var teams = [];
      rows.forEach(function (row) {
        var cells = row.querySelectorAll('td');
        if (cells.length < 10) return;
        var img = cells[1].querySelector('img.flag-svg');
        if (!img) return;
        var flagSrc = img.getAttribute('src');
        var code = flagSrc.replace('assets/flags/', '').replace('.svg', '');
        var name = img.getAttribute('alt') || code;
        teams.push({
          code: code, name: name, flagSrc: flagSrc,
          group: gid.toUpperCase(),
          PJ: 0, PG: 0, PE: 0, PP: 0, GF: 0, GC: 0, DG: 0, PTS: 0
        });
      });
      window.CURRENT_STANDINGS[gid] = teams;
    });
  }

  // ── CALCULATE STANDINGS FOR ONE GROUP ─────────────────────────────────────
  function calcGroupStandings(gid, results) {
    var teamCodes = GROUP_TEAMS[gid] || [];
    var stats = {};
    teamCodes.forEach(function (code) {
      stats[code] = { PJ: 0, PG: 0, PE: 0, PP: 0, GF: 0, GC: 0, DG: 0, PTS: 0 };
    });

    results.forEach(function (m) {
      if (m.home_goals === null || m.away_goals === null) return;
      var hg = m.home_goals, ag = m.away_goals;
      var h = m.home_team, a = m.away_team;
      if (!h || !a) return;
      if (!stats[h]) stats[h] = { PJ: 0, PG: 0, PE: 0, PP: 0, GF: 0, GC: 0, DG: 0, PTS: 0 };
      if (!stats[a]) stats[a] = { PJ: 0, PG: 0, PE: 0, PP: 0, GF: 0, GC: 0, DG: 0, PTS: 0 };

      stats[h].PJ++; stats[a].PJ++;
      stats[h].GF += hg; stats[h].GC += ag;
      stats[a].GF += ag; stats[a].GC += hg;
      stats[h].DG = stats[h].GF - stats[h].GC;
      stats[a].DG = stats[a].GF - stats[a].GC;

      if (hg > ag)       { stats[h].PG++; stats[h].PTS += 3; stats[a].PP++; }
      else if (hg === ag) { stats[h].PE++; stats[h].PTS++;    stats[a].PE++; stats[a].PTS++; }
      else               { stats[a].PG++; stats[a].PTS += 3; stats[h].PP++; }
    });

    var existing = window.CURRENT_STANDINGS[gid] || [];
    var ranked = teamCodes.map(function (code) {
      var base = existing.filter(function (t) { return t.code === code; })[0] || {
        code: code, name: code,
        flagSrc: 'assets/flags/' + code + '.svg',
        group: gid.toUpperCase()
      };
      return Object.assign({}, base, stats[code] || { PJ:0,PG:0,PE:0,PP:0,GF:0,GC:0,DG:0,PTS:0 });
    });

    ranked.sort(function (a, b) {
      if (b.PTS !== a.PTS) return b.PTS - a.PTS;
      if (b.DG  !== a.DG)  return b.DG  - a.DG;
      if (b.GF  !== a.GF)  return b.GF  - a.GF;
      return (FIFA_RANK[a.code] || 200) - (FIFA_RANK[b.code] || 200);
    });

    return ranked;
  }

  // ── UPDATE HTML TABLE FOR ONE GROUP ───────────────────────────────────────
  function updateStandingsTable(gid, ranked) {
    var section = document.getElementById('grupo-' + gid);
    if (!section) return;
    var tbody = section.querySelector('.standings-table tbody');
    if (!tbody) return;

    var rowMap = {};
    Array.from(tbody.querySelectorAll('tr')).forEach(function (row) {
      var img = row.querySelector('img.flag-svg');
      if (!img) return;
      var code = img.getAttribute('src').replace('assets/flags/', '').replace('.svg', '');
      rowMap[code] = row;
    });

    ranked.forEach(function (team, i) {
      var row = rowMap[team.code];
      if (!row) return;
      var cells = row.querySelectorAll('td');
      if (cells.length < 10) return;

      cells[0].textContent = i + 1;
      cells[2].textContent = team.PJ;
      cells[3].textContent = team.PG;
      cells[4].textContent = team.PE;
      cells[5].textContent = team.PP;
      cells[6].textContent = team.GF;
      cells[7].textContent = team.GC;
      cells[8].textContent = team.DG > 0 ? '+' + team.DG : String(team.DG);
      cells[9].textContent = team.PTS;

      row.className = i < 2 ? 'st-qualify' : (i === 2 ? 'st-third' : '');

      tbody.appendChild(row);
    });
  }

  // ── RESOLVE OPPONENT FLAG FROM TEXT ───────────────────────────────────────
  window.resolveOpponent = function (oppText) {
    var m = oppText.match(/^(\d)\.°\s+Grupo\s+([A-L])$/i);
    if (!m) return null;
    var pos = parseInt(m[1], 10) - 1;
    var gid = m[2].toLowerCase();
    var standings = window.CURRENT_STANDINGS[gid];
    if (!standings || !standings[pos]) return null;
    return { flagSrc: standings[pos].flagSrc, name: standings[pos].name, code: standings[pos].code };
  };

  // ── COLLECT BEST THIRDS ───────────────────────────────────────────────────
  function collectBestThirds() {
    var thirds = [];
    ['a','b','c','d','e','f','g','h','i','j','k','l'].forEach(function (gid) {
      var s = window.CURRENT_STANDINGS[gid];
      if (!s || s.length < 3) return;
      thirds.push(Object.assign({}, s[2], { group: gid.toUpperCase() }));
    });

    thirds.sort(function (a, b) {
      if (b.PTS !== a.PTS) return b.PTS - a.PTS;
      if (b.DG  !== a.DG)  return b.DG  - a.DG;
      if (b.GF  !== a.GF)  return b.GF  - a.GF;
      return (FIFA_RANK[a.code] || 200) - (FIFA_RANK[b.code] || 200);
    });

    return thirds.map(function (t, i) {
      return Object.assign({}, t, { classified: i < 8 });
    });
  }

  // ── RENDER BEST-THIRDS TABLE ──────────────────────────────────────────────
  function renderBestThirds(thirds) {
    var tbody = document.getElementById('best-thirds-tbody');
    if (!tbody) return;
    var html = '';
    thirds.forEach(function (team, i) {
      var rowCls = (team.classified ? 'st-third-qualify' : 'st-third-out')
                 + (i === 8 ? ' st-thirds-cutline' : '');
      var dgStr = team.DG > 0 ? '+' + team.DG : String(team.DG);
      html += '<tr class="' + rowCls + '">'
        + '<td class="st-pos-cell">' + (i + 1) + '</td>'
        + '<td style="font-size:12px;color:var(--muted);text-align:center;font-family:\'Barlow Condensed\',sans-serif;font-weight:700">' + team.group + '</td>'
        + '<td class="st-team-cell"><img class="flag-svg" src="' + team.flagSrc + '" alt="' + team.name + '" loading="lazy"> ' + team.name + '</td>'
        + '<td>' + team.PJ + '</td>'
        + '<td>' + team.PG + '</td>'
        + '<td>' + team.PE + '</td>'
        + '<td>' + team.PP + '</td>'
        + '<td>' + team.GF + '</td>'
        + '<td>' + team.GC + '</td>'
        + '<td>' + dgStr + '</td>'
        + '<td class="st-pts">' + team.PTS + '</td>'
        + '</tr>';
    });
    tbody.innerHTML = html;
  }

  // ── LOAD FROM SUPABASE AND RENDER ─────────────────────────────────────────
  async function loadAndRender() {
    var client = getClient();
    if (!client) {
      renderBestThirds(collectBestThirds());
      if (typeof renderTeamKOPaths === 'function') renderTeamKOPaths();
      return;
    }

    try {
      var ref = await client.from('match_results').select('*').eq('phase', 'group');
      var data = ref.data || [];

      if (data.length > 0) {
        var byGroup = {};
        data.forEach(function (m) {
          var gid = (m.group_id || '').toLowerCase();
          if (!byGroup[gid]) byGroup[gid] = [];
          byGroup[gid].push(m);
        });

        Object.keys(byGroup).forEach(function (gid) {
          var ranked = calcGroupStandings(gid, byGroup[gid]);
          window.CURRENT_STANDINGS[gid] = ranked;
          updateStandingsTable(gid, ranked);
        });
      }
    } catch (e) {
      console.warn('[Standings] Supabase fetch error:', e.message || e);
    }

    renderBestThirds(collectBestThirds());
    if (typeof renderTeamKOPaths === 'function') renderTeamKOPaths();
  }

  // ── SUPABASE REALTIME ─────────────────────────────────────────────────────
  function subscribeRealtime() {
    var client = getClient();
    if (!client) return;
    client.channel('standings-live')
      .on('postgres_changes', {
        event: 'UPDATE', schema: 'public', table: 'match_results',
        filter: 'phase=eq.group'
      }, function () { loadAndRender(); })
      .subscribe();
  }

  // ── BOOT ──────────────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', function () {
    initDefaultStandings();
    loadAndRender();
    subscribeRealtime();
  });

})();
