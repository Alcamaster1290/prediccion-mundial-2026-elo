#!/usr/bin/env python3
"""serve_demo.py — Servidor local con modo Premium simulado.

Inyecta un script en index.html que:
  - Mockea window.SupaAuth.getClient() con datos de data/mc_results.json
  - Activa todas las secciones premium sin credenciales reales
  - Muestra usuario demo en la nav

Uso: python scripts/serve_demo.py [--port 8100]
"""
import argparse
import http.server
import os
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

INJECT = """
<script>
/* ── DEMO PREMIUM MODE ──────────────────────────────────────────── */
(function () {
  'use strict';

  var DEMO_USER    = { id: 'demo-user', email: 'demo@preview.local' };
  var DEMO_PROFILE = { id: 'demo-user', is_premium: true, email: 'demo@preview.local' };

  /* Build a mock Supabase-like client from local mc_results.json */
  function buildMockClient(mc) {
    var standings = Object.keys(mc.teams).map(function (code) {
      var t = mc.teams[code];
      return {
        team_code:      code,
        simulation_run: 'demo',
        qualified_pct:  t.qualified_pct,
        first_pct:      t.first_pct,
        second_pct:     t.second_pct,
        third_pct:      t.third_pct,
        best_third_pct: t.best_third_pct,
        fourth_pct:     t.fourth_pct,
        points_pct:     t.points_pct || {},
      };
    });

    var terceros = (mc.terceros_table || []).map(function (row) {
      return {
        simulation_run: 'demo',
        rank:           row.rank,
        group_id:       row.group,
        team_code:      row.team_code,
        third_pct:      row.third_pct,
        qualifies_pct:  row.qualifies_pct,
        avg_pts:        row.avg_pts,
        avg_gd:         row.avg_gd,
        avg_gf:         row.avg_gf,
        qualifies:      row.qualifies,
      };
    });

    var TABLES = {
      simulation_runs: [{ id: 'demo', runs: mc.runs, seed: mc.seed || 42,
                          created_at: new Date().toISOString(), version: '1.1' }],
      simulation_group_standings: standings,
      simulation_terceros_table: terceros,
    };

    function Builder(table) { this._t = table; }
    Builder.prototype.select  = function () { return this; };
    Builder.prototype.eq      = function () { return this; };
    Builder.prototype.order   = function () { return this; };
    Builder.prototype.limit   = function () { return this; };
    Builder.prototype.single  = function () {
      var rows = TABLES[this._t] || [];
      var row  = rows[0] || null;
      return Promise.resolve({ data: row, error: row ? null : { message: 'not found' } });
    };
    Builder.prototype.then = function (res, rej) {
      return Promise.resolve({ data: TABLES[this._t] || [], error: null }).then(res, rej);
    };

    return { from: function (table) { return new Builder(table); } };
  }

  function activatePremium(mockClient) {
    /* Override getClient so predicciones.js uses mock data */
    if (!window.SupaAuth) window.SupaAuth = {};
    window.SupaAuth.getClient = function () { return mockClient; };

    /* Bracket win% */
    if (window.BracketSection) window.BracketSection.setPremiumState(true);

    /* Predicciones section */
    if (window.PredicionesSection) {
      window.PredicionesSection.onAuthChange(DEMO_USER, true, DEMO_PROFILE);
    }

    /* Nav UI */
    var joinBtn = document.getElementById('join-btn');
    if (joinBtn) joinBtn.style.display = 'none';
    var navUser = document.getElementById('nav-user-info');
    if (navUser) {
      navUser.style.display = 'flex';
      navUser.innerHTML =
        '<span style="font-size:12px;color:var(--muted)">demo@preview.local</span>'
        + '<span style="font-size:11px;font-weight:700;color:var(--gold);margin-left:.4rem">★ Premium</span>';
    }
  }

  /* Fetch local mc data, then activate on load */
  fetch('data/mc_results.json')
    .then(function (r) { return r.json(); })
    .then(function (mc) {
      var mockClient = buildMockClient(mc);
      if (document.readyState === 'complete') {
        activatePremium(mockClient);
      } else {
        window.addEventListener('load', function () { activatePremium(mockClient); });
      }
    })
    .catch(function (e) { console.error('[Demo] No se pudo cargar mc_results.json', e); });
})();
</script>
</body>
"""

class DemoHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(REPO_ROOT), **kwargs)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        super().end_headers()

    def do_GET(self):
        if self.path in ('/', '/index.html'):
            self._serve_injected_index()
        else:
            super().do_GET()

    def _serve_injected_index(self):
        index = REPO_ROOT / 'index.html'
        content = index.read_bytes().decode('utf-8')
        content = content.replace('</body>', INJECT, 1)
        encoded = content.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, fmt, *args):
        pass  # silenciar logs de request


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8100)
    args = parser.parse_args()

    os.chdir(REPO_ROOT)
    server = http.server.HTTPServer(('127.0.0.1', args.port), DemoHandler)
    print(f'[Demo Premium] http://localhost:{args.port}/#bracket')
    print(f'[Demo Premium] http://localhost:{args.port}/#predicciones')
    print('Ctrl+C para detener.')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
