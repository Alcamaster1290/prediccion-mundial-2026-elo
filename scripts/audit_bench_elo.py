# -*- coding: utf-8 -*-
"""Auditoría de ELO de banca antes de publicar narrativas con nombres.

Reporta por equipo los suplentes cuyo ELO de club supera el promedio del XI
titular (candidatos a supersub en la narrativa), los bloques de club repetido
y cualquier nombre o club con caracteres vetados por la guía de estilo.
Usage: python scripts/audit_bench_elo.py
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from xi_matchups import normalize_line

REPO_ROOT = Path(__file__).parent.parent
BANNED_CHARS = (':', ';', '—')


def main():
    teams = json.load(open(REPO_ROOT / 'data' / 'teams.json', encoding='utf-8'))['teams']
    style_issues = []
    for team in teams:
        players = team.get('players') or []
        starters = [p for p in players if p.get('titular') and p.get('elo') is not None]
        bench = [p for p in players if not p.get('titular') and p.get('elo') is not None]
        for p in players:
            for field in ('name', 'club'):
                value = str(p.get(field) or '')
                if any(ch in value for ch in BANNED_CHARS):
                    style_issues.append(f"{team['id']}: {field} con caracter vetado {value!r}")
        if not starters or not bench:
            continue
        xi_blend = sum(p['elo'] for p in starters) / len(starters)
        supersubs = sorted(
            (p for p in bench if p['elo'] > xi_blend),
            key=lambda p: -p['elo'],
        )
        club_blocks = Counter(p.get('club') for p in bench if p.get('club'))
        repeated = {club: n for club, n in club_blocks.items() if n >= 3}
        if supersubs or repeated:
            print(f"{team['id']} (XI blend {xi_blend:.1f})")
            for p in supersubs[:4]:
                line = normalize_line(p.get('pos')) or '?'
                print(f"   supersub {line:<8} {p.get('name'):<26} {p['elo']:>5}  {p.get('club','')}")
            for club, n in repeated.items():
                print(f"   bloque de club repetido en banca   {club} x{n}")
    if style_issues:
        print('\nProblemas de estilo en nombres/clubes')
        for issue in style_issues:
            print('   ' + issue)
    else:
        print('\nSin caracteres vetados en nombres ni clubes.')


if __name__ == '__main__':
    main()
