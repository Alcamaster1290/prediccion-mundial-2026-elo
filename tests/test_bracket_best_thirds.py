import subprocess
import textwrap


SYNTHETIC_MC_FIXTURE = r"""
    const groups = {
      A: ['mex', 'kor', 'cze', 'rsa'],
      B: ['can', 'mar', 'sui', 'qat'],
      C: ['bra', 'ecu', 'hai', 'sco'],
      D: ['usa', 'aus', 'par', 'tun'],
      E: ['esp', 'cro', 'irq', 'nzl'],
      F: ['ned', 'jpn', 'alg', 'pan'],
      G: ['bel', 'egy', 'irn', 'cur'],
      H: ['fra', 'sen', 'ksa', 'nor'],
      I: ['arg', 'aut', 'jor', 'gha'],
      J: ['eng', 'uru', 'uzb', 'tri'],
      K: ['ger', 'col', 'uae', 'cpv'],
      L: ['por', 'tur', 'civ', 'jam'],
    };

    function buildSyntheticData() {
      const data = { meta: { runs: 1000, version: 'test' }, teams: {}, terceros_table: [] };
      const groupKeys = Object.keys(groups);
      groupKeys.forEach((group, groupIndex) => {
        groups[group].forEach((code, teamIndex) => {
          data.teams[code] = {
            team_code: code,
            group: group,
            group_id: group,
            country_name: code.toUpperCase(),
            first_pct: teamIndex === 0 ? 74 - groupIndex : 5 + teamIndex,
            second_pct: teamIndex === 1 ? 68 - groupIndex : 4 + teamIndex,
            best_third_pct: teamIndex === 2 ? 60 - groupIndex : 1,
            qualified_pct: teamIndex < 2 ? 88 - groupIndex : (teamIndex === 2 ? 65 - groupIndex : 2),
            points_avg: 6 - teamIndex,
            gd_avg: 3 - teamIndex,
            goals_for_avg: 5 - teamIndex,
            points_pct: { '9': 10, '6': 40, '3': 30, '0': 20 },
          };
        });
        data.terceros_table.push({
          rank: groupIndex + 1,
          group: group,
          group_id: group,
          team_code: groups[group][2],
          country_name: groups[group][2].toUpperCase(),
          points_avg: 4.2 - groupIndex / 10,
          gd_avg: 0.5 - groupIndex / 10,
          goals_for_avg: 2.2 - groupIndex / 10,
          qualifies: groupIndex < 8,
          qualifies_pct: 79 - groupIndex,
        });
      });
      return data;
    }

    const data = buildSyntheticData();
"""


def test_bracket_uses_unique_projected_best_thirds():
    script = SYNTHETIC_MC_FIXTURE + r"""
    const fs = require('fs');
    const vm = require('vm');

    const inner = {
      _html: '',
      classList: { add() {}, toggle() {} },
      set innerHTML(value) { this._html = value; },
      get innerHTML() { return this._html; },
    };
    const document = {
      readyState: 'loading',
      addEventListener() {},
      getElementById(id) { return id === 'bracket-inner' ? inner : null; },
    };
    const window = {
      document,
      SupaData: {
        loadSimulationData: async () => data,
        loadSimulationTeams: async () => data.teams,
      },
    };

    vm.createContext({ console, document, window, Promise, setTimeout });
    vm.runInContext(fs.readFileSync('js/bracket.js', 'utf8'), vm.createContext({
      console,
      document,
      window,
      Promise,
      setTimeout,
    }));

    (async () => {
      window.BracketSection.init();
      window.BracketSection.setPremiumState(true);
      await new Promise(resolve => setTimeout(resolve, 25));

      const html = inner.innerHTML;
      const thirdSlots = [...html.matchAll(/data-slot="(3:[^"]+)">[\s\S]*?<img class="bk-flag" src="assets\/flags\/([^".]+)\.svg"[\s\S]*?<span class="bk-pct">([^<]+)<\/span>/g)]
        .map(match => ({ slot: match[1], code: match[2], pct: match[3] }));
      const projected = data.terceros_table
        .filter(row => row.qualifies)
        .map(row => ({ code: row.team_code, pct: `${Number(row.qualifies_pct).toFixed(1)}%` }));
      const projectedCodes = new Set(projected.map(row => row.code));
      const projectedPctByCode = new Map(projected.map(row => [row.code, row.pct]));
      const uniqueCodes = new Set(thirdSlots.map(row => row.code));

      if (thirdSlots.length !== 8) {
        throw new Error(`Expected 8 best-third slots, got ${thirdSlots.length}`);
      }
      if (uniqueCodes.size !== 8) {
        throw new Error(`Expected unique best-third teams, got ${JSON.stringify(thirdSlots)}`);
      }
      for (const row of thirdSlots) {
        if (!projectedCodes.has(row.code)) {
          throw new Error(`Unexpected best-third team ${row.code}`);
        }
        if (row.pct !== projectedPctByCode.get(row.code)) {
          throw new Error(`Expected ${row.code} to show ${projectedPctByCode.get(row.code)}, got ${row.pct}`);
        }
      }
    })().catch(error => {
      console.error(error.message);
      process.exit(1);
    });
    """
    result = subprocess.run(
        ["node", "-e", textwrap.dedent(script)],
        check=False,
        cwd=".",
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr


def test_bracket_slots_show_position_probability_not_general_qualification():
    script = SYNTHETIC_MC_FIXTURE + r"""
    const fs = require('fs');
    const vm = require('vm');

    const inner = {
      _html: '',
      classList: { add() {}, toggle() {} },
      set innerHTML(value) { this._html = value; },
      get innerHTML() { return this._html; },
    };
    const document = {
      readyState: 'loading',
      addEventListener() {},
      getElementById(id) { return id === 'bracket-inner' ? inner : null; },
    };
    const window = {
      document,
      SupaData: { loadSimulationData: async () => data },
    };

    vm.runInContext(fs.readFileSync('js/bracket.js', 'utf8'), vm.createContext({
      console,
      document,
      window,
      Promise,
      setTimeout,
    }));

    (async () => {
      window.BracketSection.init();
      window.BracketSection.setPremiumState(true);
      await new Promise(resolve => setTimeout(resolve, 25));

      const html = inner.innerHTML;
      const firstA = html.match(/data-slot="1:A">[\s\S]*?assets\/flags\/mex\.svg[\s\S]*?<span class="bk-pct">([^<]+)<\/span>/);
      const secondA = html.match(/data-slot="2:A">[\s\S]*?assets\/flags\/kor\.svg[\s\S]*?<span class="bk-pct">([^<]+)<\/span>/);
      if (!firstA || firstA[1] !== '74.0%') {
        throw new Error(`Expected 1:A to show first_pct 74.0%, got ${firstA && firstA[1]}`);
      }
      if (!secondA || secondA[1] !== '68.0%') {
        throw new Error(`Expected 2:A to show second_pct 68.0%, got ${secondA && secondA[1]}`);
      }
    })().catch(error => {
      console.error(error.message);
      process.exit(1);
    });
    """
    result = subprocess.run(
        ["node", "-e", textwrap.dedent(script)],
        check=False,
        cwd=".",
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr


def test_bracket_highlights_only_slots_clinched_at_one_hundred_percent():
    script = SYNTHETIC_MC_FIXTURE + r"""
    const fs = require('fs');
    const vm = require('vm');

    data.teams.mex.first_pct = 100;
    data.teams.kor.qualified_pct = 100;
    data.terceros_table[0].qualifies_pct = 100;

    const inner = {
      _html: '',
      classList: { add() {}, toggle() {} },
      set innerHTML(value) { this._html = value; },
      get innerHTML() { return this._html; },
    };
    const document = {
      readyState: 'loading',
      addEventListener() {},
      getElementById(id) { return id === 'bracket-inner' ? inner : null; },
    };
    const window = {
      document,
      SupaData: { loadSimulationData: async () => data },
    };

    vm.runInContext(fs.readFileSync('js/bracket.js', 'utf8'), vm.createContext({
      console,
      document,
      window,
      Promise,
      setTimeout,
    }));

    function slotMatch(html, slotCode, code) {
      const escapedSlot = slotCode.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      return html.match(new RegExp(
        '<div class="([^"]*)" data-slot="' + escapedSlot + '">[\\s\\S]*?'
        + 'assets\\/flags\\/' + code + '\\.svg[\\s\\S]*?'
        + '<span class="bk-pct">([^<]+)<\\/span>'
      ));
    }

    (async () => {
      window.BracketSection.init();
      window.BracketSection.setPremiumState(true);
      await new Promise(resolve => setTimeout(resolve, 25));

      const html = inner.innerHTML;
      const firstA = slotMatch(html, '1:A', 'mex');
      const secondA = slotMatch(html, '2:A', 'kor');
      const bestThirdA = html.match(/<div class="([^"]*)" data-slot="3:[^"]*">[\s\S]*?assets\/flags\/cze\.svg[\s\S]*?<span class="bk-pct">100\.0%<\/span>/);

      if (!firstA || !firstA[1].includes('bk-slot--clinched') || firstA[2] !== '100.0%') {
        throw new Error(`Expected 1:A to be clinched at 100.0%, got ${firstA && firstA.slice(1).join('|')}`);
      }
      if (!secondA || secondA[1].includes('bk-slot--clinched') || secondA[2] !== '68.0%') {
        throw new Error(`Expected 2:A not to be clinched from qualified_pct alone, got ${secondA && secondA.slice(1).join('|')}`);
      }
      if (!bestThirdA || !bestThirdA[1].includes('bk-slot--clinched')) {
        throw new Error(`Expected the 100.0% best-third slot to be clinched, got ${bestThirdA && bestThirdA[1]}`);
      }
    })().catch(error => {
      console.error(error.message);
      process.exit(1);
    });
    """
    result = subprocess.run(
        ["node", "-e", textwrap.dedent(script)],
        check=False,
        cwd=".",
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr


def test_bracket_uses_current_resolved_best_third_pairings():
    script = r"""
    const fs = require('fs');
    const vm = require('vm');
    const data = JSON.parse(fs.readFileSync('data/mc_results.json', 'utf8'));

    const inner = {
      _html: '',
      classList: { add() {}, remove() {}, toggle() {} },
      set innerHTML(value) { this._html = value; },
      get innerHTML() { return this._html; },
    };
    const note = { style: {} };
    const document = {
      readyState: 'loading',
      addEventListener() {},
      getElementById(id) {
        if (id === 'bracket-inner') return inner;
        if (id === 'bk-premium-note') return note;
        return null;
      },
    };
    const window = {
      document,
      SupaData: { loadSimulationData: async () => data },
    };

    vm.runInContext(fs.readFileSync('js/bracket.js', 'utf8'), vm.createContext({
      console,
      document,
      window,
      Promise,
      setTimeout,
      fetch: async () => ({ ok: false }),
    }));

    (async () => {
      window.BracketSection.init();
      window.BracketSection.setPremiumState(true);
      await new Promise(resolve => setTimeout(resolve, 25));

      const html = inner.innerHTML;
      const expected = [
        ['74', 'pry'],
        ['77', 'swe'],
        ['79', 'ecu'],
        ['82', 'sen'],
        ['85', 'alg'],
      ];
      for (const [matchNumber, code] of expected) {
        const pattern = new RegExp('data-match="' + matchNumber + '"[\\s\\S]*assets\\/flags\\/' + code + '\\.svg');
        if (!pattern.test(html)) {
          throw new Error(`Expected P${matchNumber} to include ${code}`);
        }
      }
    })().catch(error => {
      console.error(error.message);
      process.exit(1);
    });
    """
    result = subprocess.run(
        ["node", "-e", textwrap.dedent(script)],
        check=False,
        cwd=".",
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr


def test_bracket_shows_knockout_advance_percentages_from_round_of_16_onward():
    script = r"""
    const fs = require('fs');
    const vm = require('vm');
    const data = JSON.parse(fs.readFileSync('data/mc_results.json', 'utf8'));
    const finalPredictions = {
      matches: [
        {
          match_number: 89,
          phase: 'r16',
          home_team: 'ger',
          away_team: 'fra',
          advance_home_pct: 37.4,
          advance_away_pct: 62.6,
        },
      ],
    };

    const inner = {
      _html: '',
      classList: { add() {}, remove() {}, toggle() {} },
      set innerHTML(value) { this._html = value; },
      get innerHTML() { return this._html; },
    };
    const note = { style: {} };
    const document = {
      readyState: 'loading',
      addEventListener() {},
      getElementById(id) {
        if (id === 'bracket-inner') return inner;
        if (id === 'bk-premium-note') return note;
        return null;
      },
    };
    const window = {
      document,
      SupaData: { loadSimulationData: async () => data },
    };

    vm.runInContext(fs.readFileSync('js/bracket.js', 'utf8'), vm.createContext({
      console,
      document,
      window,
      Promise,
      setTimeout,
      fetch: async () => ({ ok: true, json: async () => finalPredictions }),
    }));

    (async () => {
      window.BracketSection.init();
      window.BracketSection.setPremiumState(true);
      await new Promise(resolve => setTimeout(resolve, 40));

      const html = inner.innerHTML;
      const match89 = html.match(/data-match="89"[\s\S]*?data-match="90"/);
      if (!match89) throw new Error('Expected P89 markup');
      const block = match89[0];
      if (!/assets\/flags\/ger\.svg[\s\S]*?<span class="bk-pct">37\.4%<\/span>/.test(block)) {
        throw new Error('Expected Germany advance percentage in P89');
      }
      if (!/assets\/flags\/fra\.svg[\s\S]*?<span class="bk-pct">62\.6%<\/span>/.test(block)) {
        throw new Error('Expected France advance percentage in P89');
      }
    })().catch(error => {
      console.error(error.message);
      process.exit(1);
    });
    """
    result = subprocess.run(
        ["node", "-e", textwrap.dedent(script)],
        check=False,
        cwd=".",
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr


def test_round_of_32_uses_match_percentages_and_highlights_actual_winner():
    script = r"""
    const fs = require('fs');
    const vm = require('vm');
    const data = JSON.parse(fs.readFileSync('data/mc_results.json', 'utf8'));
    const finalPredictions = {
      matches: [
        {
          match_number: 74,
          phase: 'r32',
          home_team: 'ger',
          away_team: 'pry',
          home_label: '1.° Grupo E',
          away_label: 'Mejor 3. Grupo D',
          advance_home_pct: 90.6,
          advance_away_pct: 9.4,
          actual_winner: 'pry',
        },
      ],
    };

    const inner = {
      _html: '',
      classList: { add() {}, remove() {}, toggle() {} },
      set innerHTML(value) { this._html = value; },
      get innerHTML() { return this._html; },
    };
    const note = { style: {} };
    const document = {
      readyState: 'loading',
      addEventListener() {},
      getElementById(id) {
        if (id === 'bracket-inner') return inner;
        if (id === 'bk-premium-note') return note;
        return null;
      },
    };
    const window = {
      document,
      SupaData: { loadSimulationData: async () => data },
    };

    vm.runInContext(fs.readFileSync('js/bracket.js', 'utf8'), vm.createContext({
      console,
      document,
      window,
      Promise,
      setTimeout,
      fetch: async () => ({ ok: true, json: async () => finalPredictions }),
    }));

    function slotMatch(block, slotCode, code) {
      const escapedSlot = slotCode.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      return block.match(new RegExp(
        '<div class="([^"]*)" data-slot="' + escapedSlot + '">[\\s\\S]*?'
        + 'assets\\/flags\\/' + code + '\\.svg[\\s\\S]*?'
        + '<span class="bk-pct">([^<]+)<\\/span>'
      ));
    }

    (async () => {
      window.BracketSection.init();
      window.BracketSection.setPremiumState(true);
      await new Promise(resolve => setTimeout(resolve, 40));

      const html = inner.innerHTML;
      const match74 = html.match(/data-match="74"[\s\S]*?data-match="77"/);
      if (!match74) throw new Error('Expected P74 markup');
      const block = match74[0];
      const germany = slotMatch(block, '1:E', 'ger');
      const paraguay = slotMatch(block, '3:A/B/C/D/F', 'pry');
      if (!germany || germany[2] !== '90.6%') {
        throw new Error(`Expected Germany match percentage 90.6%, got ${germany && germany[2]}`);
      }
      if (germany[1].includes('bk-slot--clinched')) {
        throw new Error('Germany should not be highlighted as advanced');
      }
      if (!paraguay || paraguay[2] !== '9.4%') {
        throw new Error(`Expected Paraguay match percentage 9.4%, got ${paraguay && paraguay[2]}`);
      }
      if (!paraguay[1].includes('bk-slot--clinched')) {
        throw new Error('Paraguay should be highlighted as actual winner');
      }
    })().catch(error => {
      console.error(error.message);
      process.exit(1);
    });
    """
    result = subprocess.run(
        ["node", "-e", textwrap.dedent(script)],
        check=False,
        cwd=".",
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr


def test_prediction_route_uses_unique_projected_best_thirds():
    script = SYNTHETIC_MC_FIXTURE + r"""
    const fs = require('fs');
    const vm = require('vm');

    const content = {
      _html: '',
      set innerHTML(value) { this._html = value; },
      get innerHTML() { return this._html; },
    };
    const lock = { style: {} };
    const document = {
      readyState: 'loading',
      addEventListener() {},
      getElementById(id) {
        if (id === 'predicciones-content') return content;
        if (id === 'pred-header-lock') return lock;
        return null;
      },
    };
    const window = {
      document,
      SupaData: {
        loadSimulationData: async () => ({
          run: data.meta || {},
              standings: Object.entries(data.teams).map(([team_code, row]) => ({ team_code, ...row })),
              terceros: data.terceros_table.map(row => ({ ...row, group_id: row.group })),
        }),
      },
    };

    vm.runInContext(fs.readFileSync('js/predicciones.js', 'utf8'), vm.createContext({
      console,
      document,
      window,
      Promise,
      setTimeout,
    }));

    (async () => {
      await window.PredicionesSection.onAuthChange({ id: 'user-1' }, true, { email: 'a@example.com' });

      const html = content.innerHTML;
      const thirdSlots = [...html.matchAll(/<div class="pred-r32-slot">\s*<span class="pred-r32-pos">(?:3\.|Mejor 3\.)[\s\S]*?assets\/flags\/([^".]+)\.svg[\s\S]*?<span class="pred-r32-pct">([^<]+)<\/span>/g)]
        .map(match => ({ code: match[1], pct: match[2] }));
      const projected = data.terceros_table
        .filter(row => row.qualifies)
        .map(row => ({ code: row.team_code, pct: `${Number(row.qualifies_pct).toFixed(1)}%` }));
      const projectedCodes = new Set(projected.map(row => row.code));
      const projectedPctByCode = new Map(projected.map(row => [row.code, row.pct]));
      const uniqueCodes = new Set(thirdSlots.map(row => row.code));

      if (thirdSlots.length !== 8) {
        throw new Error(`Expected 8 route best-third slots, got ${thirdSlots.length}`);
      }
      if (uniqueCodes.size !== 8) {
        throw new Error(`Expected unique route best-third teams, got ${JSON.stringify(thirdSlots)}`);
      }
      for (const row of thirdSlots) {
        if (!projectedCodes.has(row.code)) {
          throw new Error(`Unexpected route best-third team ${row.code}`);
        }
        if (row.pct !== projectedPctByCode.get(row.code)) {
          throw new Error(`Expected ${row.code} to show ${projectedPctByCode.get(row.code)}, got ${row.pct}`);
        }
      }
    })().catch(error => {
      console.error(error.message);
      process.exit(1);
    });
    """
    result = subprocess.run(
        ["node", "-e", textwrap.dedent(script)],
        check=False,
        cwd=".",
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
