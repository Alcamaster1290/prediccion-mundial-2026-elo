# -*- coding: utf-8 -*-
"""One-off audit: matches.json/groups.json `date` must be the stadium-local
(FIFA) calendar date of the kickoff instant stored in Supabase kickoff_utc.
`time` must be the UTC clock time. Usage: --report | --apply
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta

# UTC offsets June 2026 (DST in effect in US/Canada; Mexico has no DST)
CITY_OFFSET = {
    'Ciudad de México': -6, 'Guadalajara': -6, 'Guadalupe': -6,
    'Toronto': -4, 'East Rutherford': -4, 'Foxborough': -4,
    'Filadelfia': -4, 'Philadelphia': -4, 'Atlanta': -4, 'Miami Gardens': -4,
    'Houston': -5, 'Arlington': -5, 'Kansas City': -5,
    'Inglewood': -7, 'Santa Clara': -7, 'Vancouver': -7, 'Seattle': -7,
    'Los Ángeles': -7,
}

def venue_offset(venue):
    city = venue.split(',')[-1].strip()
    if city not in CITY_OFFSET:
        raise KeyError('Unknown city for venue: ' + venue)
    return CITY_OFFSET[city]

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
        utc_clock = ko.strftime('%H:%M')
        local = ko + timedelta(hours=venue_offset(m['venue']))
        fifa_date = local.strftime('%Y-%m-%d')
        issues = []
        if m['time'] != utc_clock:
            issues.append(f"time {m['time']} != UTC clock {utc_clock}")
        if m['date'] != fifa_date:
            issues.append(f"date {m['date']} != FIFA local {fifa_date} (local {local.strftime('%d-%b %H:%M')})")
        if issues:
            problems += 1
            print(f"P{m['match_number']:>2} {m['match_id']:<22} {m['venue'].split(',')[-1].strip():<16} " + '; '.join(issues))
            fix_by_pair[(m['home_team'], m['away_team'])] = (fifa_date, utc_clock)
            if apply_fixes:
                m['date'] = fifa_date
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
        print('Sin problemas: las 72 fechas coinciden con el dia local del estadio.')
    else:
        print(f"\n{problems} partidos con desfase (usa --apply para corregir)")

if __name__ == '__main__':
    main()
