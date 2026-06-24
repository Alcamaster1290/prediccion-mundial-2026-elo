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
