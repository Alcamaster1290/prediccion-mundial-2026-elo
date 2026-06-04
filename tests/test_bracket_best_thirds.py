import subprocess
import textwrap


def test_bracket_uses_unique_projected_best_thirds():
    script = r"""
    const fs = require('fs');
    const vm = require('vm');

    const data = JSON.parse(fs.readFileSync('data/mc_results.json', 'utf8'));
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


def test_prediction_route_uses_unique_projected_best_thirds():
    script = r"""
    const fs = require('fs');
    const vm = require('vm');

    const data = JSON.parse(fs.readFileSync('data/mc_results.json', 'utf8'));
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
