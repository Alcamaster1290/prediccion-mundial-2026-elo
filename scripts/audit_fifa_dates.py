# -*- coding: utf-8 -*-
"""Audit: matches.json/groups.json `date`+`time` must equal the UTC datetime
of the kickoff instant stored in Supabase kickoff_utc (canonical source).
The frontend converts to the timezone selected by the user at render time,
including the calendar day grouping. Usage: --report | --apply
"""
import json
import os
import sys
import urllib.request
from datetime import datetime


def fetch_kickoffs():
    url = os.environ['SUPABASE_URL'] + '/rest/v1/match_results?phase=eq.group&select=match_number,kickoff_utc&order=match_number'
    req = urllib.request.Request(url, headers={
        'apikey': os.environ['SUPABASE_SERVICE_KEY'],
        'Authorization': 'Bearer ' + os.environ['SUPABASE_SERVICE_KEY'],
    })
    with urllib.request.urlopen(req) as r:
        rows = json.load(r)
    return {row['match_number']: row['kickoff_utc'] for row in rows}


def main():
    apply_fixes = '--apply' in sys.argv
    kickoffs = fetch_kickoffs()
    matches = json.load(open('data/matches.json', encoding='utf-8'))
    groups = json.load(open('data/groups.json', encoding='utf-8'))

    fix_by_pair = {}
    problems = 0
    for m in matches:
        ko_raw = kickoffs.get(m['match_number'])
        if not ko_raw:
            print(f"P{m['match_number']} {m['match_id']}: SIN kickoff en Supabase")
            problems += 1
            continue
        ko = datetime.fromisoformat(ko_raw.replace('+00:00', ''))
        utc_date = ko.strftime('%Y-%m-%d')
        utc_clock = ko.strftime('%H:%M')
        issues = []
        if m['time'] != utc_clock:
            issues.append(f"time {m['time']} != UTC {utc_clock}")
        if m['date'] != utc_date:
            issues.append(f"date {m['date']} != UTC {utc_date}")
        if issues:
            problems += 1
            print(f"P{m['match_number']:>2} {m['match_id']:<22} " + '; '.join(issues))
            fix_by_pair[(m['home_team'], m['away_team'])] = (utc_date, utc_clock)
            if apply_fixes:
                m['date'] = utc_date
                m['time'] = utc_clock

    if apply_fixes and fix_by_pair:
        for g in groups['groups']:
            for f in g['fixtures']:
                key = (f['home'], f['away'])
                if key in fix_by_pair:
                    f['date'], f['time'] = fix_by_pair[key]
        with open('data/matches.json', 'w', encoding='utf-8') as fh:
            json.dump(matches, fh, ensure_ascii=False, indent=2)
        with open('data/groups.json', 'w', encoding='utf-8') as fh:
            json.dump(groups, fh, ensure_ascii=False, indent=2)
        print(f"\nAplicados {len(fix_by_pair)} arreglos en matches.json y groups.json")
    elif problems == 0:
        print('Sin problemas: las 72 fechas/horas coinciden con kickoff_utc (UTC).')
    else:
        print(f"\n{problems} partidos con desfase (usa --apply para corregir)")


if __name__ == '__main__':
    main()
