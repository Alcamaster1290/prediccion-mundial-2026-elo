# -*- coding: utf-8 -*-
"""
Rewrites data/groups.json with correct dates, times (UTC) and venues.
Fixes GROUP_D in index.html and updates the tz note.
All times from official FIFA schedule, all in EDT (UTC-4).
UTC = EDT + 4h. Store with FIFA-calendar date (EDT date).
"""
import json

# ── STADIUM ALIASES ────────────────────────────────────────────────────────────
AZTECA   = 'Estadio Azteca, Ciudad de México'
AKRON    = 'Estadio Akron, Guadalajara'
BBVA     = 'Estadio BBVA, Guadalupe'
BMO      = 'BMO Field, Toronto'
SOFI     = 'SoFi Stadium, Los Ángeles'
LEVIS    = "Levi's Stadium, Santa Clara"
METLIFE  = 'MetLife Stadium, East Rutherford'
GILLETTE = 'Gillette Stadium, Foxborough'
BCPLACE  = 'BC Place, Vancouver'
NRG      = 'NRG Stadium, Houston'
ATTSTAD  = 'AT&T Stadium, Arlington'
LINCOLN  = 'Lincoln Financial Field, Filadelfia'
MBSTD    = 'Mercedes-Benz Stadium, Atlanta'
LUMEN    = 'Lumen Field, Seattle'
HARDROCK = 'Hard Rock Stadium, Miami Gardens'
ARROWH   = 'Arrowhead Stadium, Kansas City'

# ── CORRECT GROUPS DATA ────────────────────────────────────────────────────────
GROUPS = [
  {
    "id": "A", "color": "#e55c5c",
    "teams": ["mex","zaf","kor","cze"],
    "fixtures": [
      {"jornada":1,"date":"2026-06-11","time":"19:00","home":"mex","away":"zaf","venue":AZTECA,"inaugural":True},
      {"jornada":1,"date":"2026-06-11","time":"02:00","home":"kor","away":"cze","venue":AKRON},
      {"jornada":2,"date":"2026-06-18","time":"16:00","home":"cze","away":"zaf","venue":MBSTD},
      {"jornada":2,"date":"2026-06-18","time":"01:00","home":"mex","away":"kor","venue":AKRON},
      {"jornada":3,"date":"2026-06-24","time":"01:00","home":"cze","away":"mex","simultaneous":True,"venue":AZTECA},
      {"jornada":3,"date":"2026-06-24","time":"01:00","home":"zaf","away":"kor","simultaneous":True,"venue":BBVA}
    ]
  },
  {
    "id": "B", "color": "#3b8beb",
    "teams": ["can","bih","qat","sui"],
    "fixtures": [
      {"jornada":1,"date":"2026-06-12","time":"19:00","home":"can","away":"bih","venue":BMO},
      {"jornada":1,"date":"2026-06-13","time":"19:00","home":"qat","away":"sui","venue":LEVIS},
      {"jornada":2,"date":"2026-06-18","time":"19:00","home":"sui","away":"bih","venue":SOFI},
      {"jornada":2,"date":"2026-06-18","time":"22:00","home":"can","away":"qat","venue":BCPLACE},
      {"jornada":3,"date":"2026-06-24","time":"19:00","home":"sui","away":"can","simultaneous":True,"venue":BCPLACE},
      {"jornada":3,"date":"2026-06-24","time":"19:00","home":"bih","away":"qat","simultaneous":True,"venue":LUMEN}
    ]
  },
  {
    "id": "C", "color": "#10b981",
    "teams": ["bra","mar","hti","sco"],
    "fixtures": [
      {"jornada":1,"date":"2026-06-13","time":"22:00","home":"bra","away":"mar","venue":METLIFE},
      {"jornada":1,"date":"2026-06-13","time":"01:00","home":"hti","away":"sco","venue":GILLETTE},
      {"jornada":2,"date":"2026-06-19","time":"22:00","home":"sco","away":"mar","venue":GILLETTE},
      {"jornada":2,"date":"2026-06-19","time":"01:00","home":"bra","away":"hti","venue":LINCOLN},
      {"jornada":3,"date":"2026-06-24","time":"22:00","home":"sco","away":"bra","simultaneous":True,"venue":HARDROCK},
      {"jornada":3,"date":"2026-06-24","time":"22:00","home":"mar","away":"hti","simultaneous":True,"venue":MBSTD}
    ]
  },
  {
    "id": "E", "color": "#f97316",
    "teams": ["ger","cuw","civ","ecu"],
    "fixtures": [
      {"jornada":1,"date":"2026-06-14","time":"17:00","home":"ger","away":"cuw","venue":NRG},
      {"jornada":1,"date":"2026-06-14","time":"23:00","home":"civ","away":"ecu","venue":LINCOLN},
      {"jornada":2,"date":"2026-06-20","time":"20:00","home":"ger","away":"civ","venue":BMO},
      {"jornada":2,"date":"2026-06-20","time":"02:00","home":"ecu","away":"cuw","venue":ARROWH},
      {"jornada":3,"date":"2026-06-25","time":"20:00","home":"ecu","away":"ger","simultaneous":True,"venue":METLIFE},
      {"jornada":3,"date":"2026-06-25","time":"20:00","home":"cuw","away":"civ","simultaneous":True,"venue":LINCOLN}
    ]
  },
  {
    "id": "F", "color": "#f59e0b",
    "teams": ["ned","jpn","swe","tun"],
    "fixtures": [
      {"jornada":1,"date":"2026-06-14","time":"20:00","home":"ned","away":"jpn","venue":ATTSTAD},
      {"jornada":1,"date":"2026-06-14","time":"02:00","home":"swe","away":"tun","venue":BBVA},
      {"jornada":2,"date":"2026-06-20","time":"17:00","home":"ned","away":"swe","venue":NRG},
      {"jornada":2,"date":"2026-06-20","time":"04:00","home":"tun","away":"jpn","venue":BBVA},
      {"jornada":3,"date":"2026-06-25","time":"23:00","home":"jpn","away":"swe","simultaneous":True,"venue":ATTSTAD},
      {"jornada":3,"date":"2026-06-25","time":"23:00","home":"tun","away":"ned","simultaneous":True,"venue":ARROWH}
    ]
  },
  {
    "id": "G", "color": "#8b5cf6",
    "teams": ["bel","egy","irn","nzl"],
    "fixtures": [
      {"jornada":1,"date":"2026-06-15","time":"19:00","home":"bel","away":"egy","venue":LUMEN},
      {"jornada":1,"date":"2026-06-15","time":"01:00","home":"irn","away":"nzl","venue":SOFI},
      {"jornada":2,"date":"2026-06-21","time":"19:00","home":"bel","away":"irn","venue":SOFI},
      {"jornada":2,"date":"2026-06-21","time":"01:00","home":"nzl","away":"egy","venue":BCPLACE},
      {"jornada":3,"date":"2026-06-26","time":"03:00","home":"egy","away":"irn","simultaneous":True,"venue":LUMEN},
      {"jornada":3,"date":"2026-06-26","time":"03:00","home":"nzl","away":"bel","simultaneous":True,"venue":BCPLACE}
    ]
  },
  {
    "id": "H", "color": "#ec4899",
    "teams": ["esp","cpv","ksa","ury"],
    "fixtures": [
      {"jornada":1,"date":"2026-06-15","time":"16:00","home":"esp","away":"cpv","venue":MBSTD},
      {"jornada":1,"date":"2026-06-15","time":"22:00","home":"ksa","away":"ury","venue":HARDROCK},
      {"jornada":2,"date":"2026-06-21","time":"16:00","home":"esp","away":"ksa","venue":MBSTD},
      {"jornada":2,"date":"2026-06-21","time":"22:00","home":"ury","away":"cpv","venue":HARDROCK},
      {"jornada":3,"date":"2026-06-26","time":"00:00","home":"cpv","away":"ksa","simultaneous":True,"venue":NRG},
      {"jornada":3,"date":"2026-06-26","time":"00:00","home":"ury","away":"esp","simultaneous":True,"venue":AKRON}
    ]
  },
  {
    "id": "I", "color": "#06b6d4",
    "teams": ["fra","sen","irq","nor"],
    "fixtures": [
      {"jornada":1,"date":"2026-06-16","time":"19:00","home":"fra","away":"sen","venue":METLIFE},
      {"jornada":1,"date":"2026-06-16","time":"22:00","home":"irq","away":"nor","venue":GILLETTE},
      {"jornada":2,"date":"2026-06-22","time":"21:00","home":"fra","away":"irq","venue":LINCOLN},
      {"jornada":2,"date":"2026-06-22","time":"00:00","home":"nor","away":"sen","venue":METLIFE},
      {"jornada":3,"date":"2026-06-26","time":"19:00","home":"nor","away":"fra","simultaneous":True,"venue":GILLETTE},
      {"jornada":3,"date":"2026-06-26","time":"19:00","home":"sen","away":"irq","simultaneous":True,"venue":BMO}
    ]
  },
  {
    "id": "J", "color": "#84cc16",
    "teams": ["arg","alg","aut","jor"],
    "fixtures": [
      {"jornada":1,"date":"2026-06-16","time":"01:00","home":"arg","away":"alg","venue":ARROWH},
      {"jornada":1,"date":"2026-06-16","time":"04:00","home":"aut","away":"jor","venue":LEVIS},
      {"jornada":2,"date":"2026-06-22","time":"17:00","home":"arg","away":"aut","venue":ATTSTAD},
      {"jornada":2,"date":"2026-06-22","time":"03:00","home":"jor","away":"alg","venue":LEVIS},
      {"jornada":3,"date":"2026-06-27","time":"02:00","home":"jor","away":"arg","simultaneous":True,"venue":ATTSTAD},
      {"jornada":3,"date":"2026-06-27","time":"02:00","home":"alg","away":"aut","simultaneous":True,"venue":ARROWH}
    ]
  },
  {
    "id": "K", "color": "#d97706",
    "teams": ["por","cod","uzb","col"],
    "fixtures": [
      {"jornada":1,"date":"2026-06-17","time":"17:00","home":"por","away":"cod","venue":NRG},
      {"jornada":1,"date":"2026-06-17","time":"02:00","home":"uzb","away":"col","venue":AZTECA},
      {"jornada":2,"date":"2026-06-23","time":"17:00","home":"por","away":"uzb","venue":NRG},
      {"jornada":2,"date":"2026-06-23","time":"02:00","home":"col","away":"cod","venue":AKRON},
      {"jornada":3,"date":"2026-06-27","time":"23:30","home":"col","away":"por","simultaneous":True,"venue":HARDROCK},
      {"jornada":3,"date":"2026-06-27","time":"23:30","home":"cod","away":"uzb","simultaneous":True,"venue":MBSTD}
    ]
  },
  {
    "id": "L", "color": "#94a3b8",
    "teams": ["eng","cro","gha","pan"],
    "fixtures": [
      {"jornada":1,"date":"2026-06-17","time":"20:00","home":"eng","away":"cro","venue":ATTSTAD},
      {"jornada":1,"date":"2026-06-17","time":"23:00","home":"gha","away":"pan","venue":BMO},
      {"jornada":2,"date":"2026-06-23","time":"20:00","home":"eng","away":"gha","venue":GILLETTE},
      {"jornada":2,"date":"2026-06-23","time":"23:00","home":"pan","away":"cro","venue":BMO},
      {"jornada":3,"date":"2026-06-27","time":"21:00","home":"pan","away":"eng","simultaneous":True,"venue":METLIFE},
      {"jornada":3,"date":"2026-06-27","time":"21:00","home":"cro","away":"gha","simultaneous":True,"venue":LINCOLN}
    ]
  }
]

with open('data/groups.json', 'r', encoding='utf-8') as f:
    orig = json.load(f)

orig['groups'] = GROUPS

with open('data/groups.json', 'w', encoding='utf-8') as f:
    json.dump(orig, f, ensure_ascii=False, indent=2)

print('OK groups.json rewritten with', sum(len(g['fixtures']) for g in GROUPS), 'fixtures')

# ── GROUP_D in index.html ──────────────────────────────────────────────────────
with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

changes = 0

old_gd = (
    "    var GROUP_D = {\n"
    "      id:'D', color:'#6366f1',\n"
    "      fixtures:[\n"
    "        {jornada:1,date:'2026-06-12',home:'usa',away:'pry',venue:'SoFi Stadium, Los Ángeles'},\n"
    "        {jornada:1,date:'2026-06-13',home:'aus',away:'tur',venue:'Por confirmar'},\n"
    "        {jornada:2,date:'2026-06-18',home:'usa',away:'aus',venue:'Por confirmar'},\n"
    "        {jornada:2,date:'2026-06-19',home:'tur',away:'pry',venue:'Por confirmar'},\n"
    "        {jornada:3,date:'2026-06-24',home:'usa',away:'tur',simultaneous:true,venue:'Por confirmar'},\n"
    "        {jornada:3,date:'2026-06-24',home:'pry',away:'aus',simultaneous:true,venue:'Por confirmar'}\n"
    "      ]\n"
    "    };"
)
new_gd = (
    "    var GROUP_D = {\n"
    "      id:'D', color:'#6366f1',\n"
    "      fixtures:[\n"
    "        {jornada:1,date:'2026-06-12',time:'01:00',home:'usa',away:'pry',venue:'SoFi Stadium, Los Ángeles'},\n"
    "        {jornada:1,date:'2026-06-13',time:'04:00',home:'aus',away:'tur',venue:'BC Place, Vancouver'},\n"
    "        {jornada:2,date:'2026-06-19',time:'19:00',home:'usa',away:'aus',venue:'Lumen Field, Seattle'},\n"
    "        {jornada:2,date:'2026-06-19',time:'04:00',home:'tur',away:'pry',venue:\"Levi's Stadium, Santa Clara\"},\n"
    "        {jornada:3,date:'2026-06-25',time:'02:00',home:'tur',away:'usa',simultaneous:true,venue:'SoFi Stadium, Los Ángeles'},\n"
    "        {jornada:3,date:'2026-06-25',time:'02:00',home:'pry',away:'aus',simultaneous:true,venue:\"Levi's Stadium, Santa Clara\"}\n"
    "      ]\n"
    "    };"
)
if old_gd in html:
    html = html.replace(old_gd, new_gd, 1)
    changes += 1
    print('OK GROUP_D updated in index.html')
else:
    print('FAIL GROUP_D not found')
    # Debug
    idx = html.find("var GROUP_D")
    if idx >= 0:
        print('  Found at index', idx, ':', repr(html[idx:idx+300]))

# ── TZ NOTE: remove "por confirmar" ───────────────────────────────────────────
old_note = "+ ' · Eliminatorias: horarios en UTC (conversión automática). Grupos: por confirmar.';"
new_note = "+ ' · Horarios en UTC. Conversión automática a la zona horaria seleccionada.';"
if old_note in html:
    html = html.replace(old_note, new_note, 1)
    changes += 1
    print('OK TZ note updated')
else:
    print('FAIL TZ note not found')

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f'Done - {changes}/2 index.html changes applied.')
