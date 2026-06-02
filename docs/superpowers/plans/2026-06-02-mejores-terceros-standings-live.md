# Mejores Terceros + Standings Live + KO Flags — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Mejores Terceros" table after the 12 group sections, drive all standings from Supabase in real time, and show rival flags in each team's "Ruta Posible" KO path cards.

**Architecture:** A new `js/standings.js` module reads `match_results` from Supabase, calculates group standings client-side, updates the existing static HTML tables, renders the best-thirds table, and re-renders KO paths with resolved flags. Default standings are seeded from the existing DOM so flags always show even before kick-off. Supabase Realtime triggers a full recalculation on every result update.

**Tech Stack:** Vanilla JS (ES5 style, matching existing codebase), Supabase JS v2 (already loaded via CDN), Node.js (seed script), Supabase MCP for migrations.

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `index.html` lines 4793–5186 | Modify | Extract 7 declarations from IIFE to global scope; add `.ko-path` clear at top of `renderTeamKOPaths()` |
| `index.html` CSS block | Modify | Add 4 CSS rules for mejores-terceros table |
| `index.html` after line 3849 | Modify | Insert `<section id="mejores-terceros">` HTML |
| `index.html` before `</body>` | Modify | Add `<script src="js/standings.js"></script>` |
| `js/standings.js` | Create | All live-standings logic |
| `data/knockout_matches.json` | Create | KO fixture data for seed script |
| `scripts/seed_matches.js` | Create | Node.js: populates `match_results` in Supabase |

---

## Task 1: Create Supabase `match_results` table

**Files:** Supabase migration via MCP

- [ ] **Step 1: Apply migration**

Use the Supabase MCP tool `apply_migration` with this SQL:

```sql
CREATE TABLE match_results (
  id            UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
  match_number  INTEGER     UNIQUE NOT NULL,
  phase         TEXT        NOT NULL,
  group_id      TEXT,
  home_team     TEXT,
  away_team     TEXT,
  home_goals    INTEGER,
  away_goals    INTEGER,
  home_label    TEXT,
  away_label    TEXT,
  kickoff_utc   TIMESTAMPTZ,
  stadium       TEXT,
  city          TEXT,
  updated_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_match_results_updated_at
  BEFORE UPDATE ON match_results
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

ALTER TABLE match_results ENABLE ROW LEVEL SECURITY;

CREATE POLICY "public read" ON match_results
  FOR SELECT USING (true);
```

- [ ] **Step 2: Verify table exists**

Run via `execute_sql`:
```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'match_results'
ORDER BY ordinal_position;
```

Expected: 14 columns listed (id, match_number, phase, group_id, home_team, away_team, home_goals, away_goals, home_label, away_label, kickoff_utc, stadium, city, updated_at).

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat: create match_results table in Supabase"
```

---

## Task 2: Create `data/knockout_matches.json`

**Files:**
- Create: `data/knockout_matches.json`

This JSON mirrors the `KNOCKOUT_MATCHES` array already in `index.html` so the seed script can consume it without parsing HTML.

- [ ] **Step 1: Create the file**

Create `data/knockout_matches.json` with this exact content:

```json
[
  {"phase":"r32","matchNum":73,"date":"2026-06-28","time":"19:00","homeLabel":"2.° Grupo A","awayLabel":"2.° Grupo B","venue":"SoFi Stadium","city":"Los Ángeles"},
  {"phase":"r32","matchNum":74,"date":"2026-06-29","time":"20:30","homeLabel":"1.° Grupo E","awayLabel":"3.° A/B/C/D/F","venue":"Gillette Stadium","city":"Foxborough"},
  {"phase":"r32","matchNum":75,"date":"2026-06-29","time":"01:00","homeLabel":"1.° Grupo F","awayLabel":"2.° Grupo C","venue":"Estadio BBVA","city":"Guadalupe"},
  {"phase":"r32","matchNum":76,"date":"2026-06-29","time":"17:00","homeLabel":"1.° Grupo C","awayLabel":"2.° Grupo F","venue":"NRG Stadium","city":"Houston"},
  {"phase":"r32","matchNum":77,"date":"2026-06-30","time":"21:00","homeLabel":"1.° Grupo I","awayLabel":"3.° C/D/F/G/H","venue":"MetLife Stadium","city":"East Rutherford"},
  {"phase":"r32","matchNum":78,"date":"2026-06-30","time":"17:00","homeLabel":"2.° Grupo E","awayLabel":"2.° Grupo I","venue":"AT&T Stadium","city":"Arlington"},
  {"phase":"r32","matchNum":79,"date":"2026-06-30","time":"01:00","homeLabel":"1.° Grupo A","awayLabel":"3.° C/E/F/H/I","venue":"Estadio Azteca","city":"Ciudad de México"},
  {"phase":"r32","matchNum":80,"date":"2026-07-01","time":"16:00","homeLabel":"1.° Grupo L","awayLabel":"3.° E/H/I/J/K","venue":"Mercedes-Benz Stadium","city":"Atlanta"},
  {"phase":"r32","matchNum":81,"date":"2026-07-01","time":"00:00","homeLabel":"1.° Grupo D","awayLabel":"3.° B/E/F/I/J","venue":"Levi's Stadium","city":"Santa Clara"},
  {"phase":"r32","matchNum":82,"date":"2026-07-01","time":"20:00","homeLabel":"1.° Grupo G","awayLabel":"3.° A/E/H/I/J","venue":"Lumen Field","city":"Seattle"},
  {"phase":"r32","matchNum":83,"date":"2026-07-02","time":"23:00","homeLabel":"2.° Grupo K","awayLabel":"2.° Grupo L","venue":"BMO Field","city":"Toronto"},
  {"phase":"r32","matchNum":84,"date":"2026-07-02","time":"19:00","homeLabel":"1.° Grupo H","awayLabel":"2.° Grupo J","venue":"SoFi Stadium","city":"Los Ángeles"},
  {"phase":"r32","matchNum":85,"date":"2026-07-02","time":"03:00","homeLabel":"1.° Grupo B","awayLabel":"3.° E/F/G/I/J","venue":"BC Place","city":"Vancouver"},
  {"phase":"r32","matchNum":86,"date":"2026-07-03","time":"22:00","homeLabel":"1.° Grupo J","awayLabel":"2.° Grupo H","venue":"Hard Rock Stadium","city":"Miami Gardens"},
  {"phase":"r32","matchNum":87,"date":"2026-07-03","time":"01:30","homeLabel":"1.° Grupo K","awayLabel":"3.° D/E/I/J/L","venue":"Arrowhead Stadium","city":"Kansas City"},
  {"phase":"r32","matchNum":88,"date":"2026-07-03","time":"18:00","homeLabel":"2.° Grupo D","awayLabel":"2.° Grupo G","venue":"AT&T Stadium","city":"Arlington"},
  {"phase":"r16","matchNum":89,"date":"2026-07-04","time":"21:00","homeLabel":"Ganador Partido 74","awayLabel":"Ganador Partido 77","venue":"Lincoln Financial Field","city":"Filadelfia"},
  {"phase":"r16","matchNum":90,"date":"2026-07-04","time":"17:00","homeLabel":"Ganador Partido 73","awayLabel":"Ganador Partido 75","venue":"NRG Stadium","city":"Houston"},
  {"phase":"r16","matchNum":91,"date":"2026-07-05","time":"20:00","homeLabel":"Ganador Partido 76","awayLabel":"Ganador Partido 78","venue":"MetLife Stadium","city":"East Rutherford"},
  {"phase":"r16","matchNum":92,"date":"2026-07-05","time":"00:00","homeLabel":"Ganador Partido 79","awayLabel":"Ganador Partido 80","venue":"Estadio Azteca","city":"Ciudad de México"},
  {"phase":"r16","matchNum":93,"date":"2026-07-06","time":"19:00","homeLabel":"Ganador Partido 83","awayLabel":"Ganador Partido 84","venue":"AT&T Stadium","city":"Arlington"},
  {"phase":"r16","matchNum":94,"date":"2026-07-06","time":"00:00","homeLabel":"Ganador Partido 81","awayLabel":"Ganador Partido 82","venue":"Lumen Field","city":"Seattle"},
  {"phase":"r16","matchNum":95,"date":"2026-07-07","time":"16:00","homeLabel":"Ganador Partido 86","awayLabel":"Ganador Partido 88","venue":"Mercedes-Benz Stadium","city":"Atlanta"},
  {"phase":"r16","matchNum":96,"date":"2026-07-07","time":"20:00","homeLabel":"Ganador Partido 85","awayLabel":"Ganador Partido 87","venue":"BC Place","city":"Vancouver"},
  {"phase":"qf","matchNum":97,"date":"2026-07-09","time":"20:00","homeLabel":"Ganador Partido 89","awayLabel":"Ganador Partido 90","venue":"Gillette Stadium","city":"Foxborough"},
  {"phase":"qf","matchNum":98,"date":"2026-07-10","time":"19:00","homeLabel":"Ganador Partido 93","awayLabel":"Ganador Partido 94","venue":"SoFi Stadium","city":"Los Ángeles"},
  {"phase":"qf","matchNum":99,"date":"2026-07-11","time":"21:00","homeLabel":"Ganador Partido 91","awayLabel":"Ganador Partido 92","venue":"Hard Rock Stadium","city":"Miami Gardens"},
  {"phase":"qf","matchNum":100,"date":"2026-07-11","time":"01:00","homeLabel":"Ganador Partido 95","awayLabel":"Ganador Partido 96","venue":"Arrowhead Stadium","city":"Kansas City"},
  {"phase":"sf","matchNum":101,"date":"2026-07-14","time":"19:00","homeLabel":"Ganador Partido 97","awayLabel":"Ganador Partido 98","venue":"AT&T Stadium","city":"Arlington"},
  {"phase":"sf","matchNum":102,"date":"2026-07-15","time":"19:00","homeLabel":"Ganador Partido 99","awayLabel":"Ganador Partido 100","venue":"Mercedes-Benz Stadium","city":"Atlanta"},
  {"phase":"tp","matchNum":103,"date":"2026-07-18","time":"21:00","homeLabel":"Perdedor Partido 101","awayLabel":"Perdedor Partido 102","venue":"Hard Rock Stadium","city":"Miami Gardens"},
  {"phase":"final","matchNum":104,"date":"2026-07-19","time":"19:00","homeLabel":"Ganador Partido 101","awayLabel":"Ganador Partido 102","venue":"MetLife Stadium","city":"East Rutherford"}
]
```

- [ ] **Step 2: Commit**

```bash
git add data/knockout_matches.json
git commit -m "feat: add knockout_matches.json for seed script"
```

---

## Task 3: Create `scripts/seed_matches.js`

**Files:**
- Create: `scripts/seed_matches.js`

Seeds all 104 matches. Run once. Uses `@supabase/supabase-js` via npx or after `npm install @supabase/supabase-js`.

- [ ] **Step 1: Create `scripts/seed_matches.js`**

```javascript
// seed_matches.js — Run with: node scripts/seed_matches.js
// Requires: SUPABASE_URL and SUPABASE_SERVICE_KEY env vars
// npm install @supabase/supabase-js  (or npx --yes)

const { createClient } = require('@supabase/supabase-js');
const fs = require('fs');
const path = require('path');

const SUPABASE_URL = process.env.SUPABASE_URL || 'https://hqgrgcvtzzsjmjjqqqjf.supabase.co';
const SUPABASE_SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY;

if (!SUPABASE_SERVICE_KEY) {
  console.error('Set SUPABASE_SERVICE_KEY env var (service_role key from Supabase dashboard)');
  process.exit(1);
}

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);

// Team display names (matches NAMES object in index.html)
const NAMES = {
  mex:'México', zaf:'Sudáfrica', kor:'Corea del Sur', cze:'Chequia',
  can:'Canadá', bih:'Bosnia', qat:'Qatar', sui:'Suiza',
  bra:'Brasil', mar:'Marruecos', hti:'Haití', sco:'Escocia',
  ger:'Alemania', cuw:'Curazao', civ:'Costa de Marfil', ecu:'Ecuador',
  ned:'Países Bajos', jpn:'Japón', swe:'Suecia', tun:'Túnez',
  bel:'Bélgica', egy:'Egipto', irn:'Irán', nzl:'Nueva Zelanda',
  esp:'España', cpv:'Cabo Verde', ksa:'Arabia Saudita', ury:'Uruguay',
  fra:'Francia', sen:'Senegal', irq:'Irak', nor:'Noruega',
  arg:'Argentina', alg:'Argelia', aut:'Austria', jor:'Jordania',
  por:'Portugal', cod:'RD Congo', uzb:'Uzbekistán', col:'Colombia',
  eng:'Inglaterra', cro:'Croacia', gha:'Ghana', pan:'Panamá',
  usa:'EE.UU.', pry:'Paraguay', aus:'Australia', tur:'Turquía'
};

async function seed() {
  const rows = [];

  // ── GROUP MATCHES (P1–P72) ─────────────────────────────────────────────────
  const groupsPath = path.join(__dirname, '../data/groups.json');
  const groupsData = JSON.parse(fs.readFileSync(groupsPath, 'utf8'));

  // Collect all fixtures and sort by date+time to assign match numbers
  let allFixtures = [];
  groupsData.groups.forEach(function(g) {
    g.fixtures.forEach(function(f) {
      allFixtures.push(Object.assign({}, f, { group_id: g.id.toLowerCase() }));
    });
  });
  allFixtures.sort(function(a, b) {
    const da = a.date + 'T' + a.time;
    const db = b.date + 'T' + b.time;
    return da < db ? -1 : da > db ? 1 : 0;
  });

  allFixtures.forEach(function(f, i) {
    const matchNum = i + 1;
    const cityFromVenue = f.venue ? f.venue.split(',').pop().trim() : '';
    rows.push({
      match_number: matchNum,
      phase: 'group',
      group_id: f.group_id,
      home_team: f.home,
      away_team: f.away,
      home_goals: null,
      away_goals: null,
      home_label: NAMES[f.home] || f.home,
      away_label: NAMES[f.away] || f.away,
      kickoff_utc: f.date + 'T' + f.time + ':00Z',
      stadium: f.venue ? f.venue.split(',')[0].trim() : null,
      city: cityFromVenue || null
    });
  });

  // ── KO MATCHES (P73–P104) ──────────────────────────────────────────────────
  const koPath = path.join(__dirname, '../data/knockout_matches.json');
  const koData = JSON.parse(fs.readFileSync(koPath, 'utf8'));

  koData.forEach(function(m) {
    const isR32 = m.phase === 'r32';
    rows.push({
      match_number: m.matchNum,
      phase: m.phase,
      group_id: null,
      home_team: null,
      away_team: null,
      home_goals: null,
      away_goals: null,
      // 16avos: keep bracket labels; octavos+: null (just match name)
      home_label: isR32 ? m.homeLabel : null,
      away_label: isR32 ? m.awayLabel : null,
      kickoff_utc: m.date + 'T' + m.time + ':00Z',
      stadium: m.venue || null,
      city: m.city || null
    });
  });

  // ── UPSERT ─────────────────────────────────────────────────────────────────
  console.log('Inserting', rows.length, 'matches...');
  const { error } = await supabase
    .from('match_results')
    .upsert(rows, { onConflict: 'match_number' });

  if (error) {
    console.error('Upsert error:', error.message);
    process.exit(1);
  }
  console.log('Done! Seeded', rows.length, 'matches.');
}

seed().catch(function(e) { console.error(e); process.exit(1); });
```

- [ ] **Step 2: Install `@supabase/supabase-js` for the seed script**

```bash
npm install @supabase/supabase-js
```

- [ ] **Step 3: Commit**

```bash
git add scripts/seed_matches.js package.json package-lock.json
git commit -m "feat: add seed script for match_results"
```

---

## Task 4: Run seed script

**Files:** Supabase `match_results` table

- [ ] **Step 1: Run the seed script**

Replace `<YOUR_SERVICE_KEY>` with the `service_role` key from your Supabase project dashboard (Settings → API).

```bash
$env:SUPABASE_SERVICE_KEY="<YOUR_SERVICE_KEY>"
node scripts/seed_matches.js
```

Expected output:
```
Inserting 104 matches...
Done! Seeded 104 matches.
```

- [ ] **Step 2: Verify via MCP**

Run via `execute_sql`:
```sql
SELECT phase, COUNT(*) as cnt FROM match_results GROUP BY phase ORDER BY phase;
```

Expected:
```
final  | 1
group  | 72
qf     | 4
r16    | 8
r32    | 16
sf     | 2
tp     | 1
```

- [ ] **Step 3: Spot-check a group match and a KO match**

```sql
SELECT match_number, phase, group_id, home_team, away_team, home_label, away_label, stadium, city
FROM match_results
WHERE match_number IN (1, 73, 81, 104)
ORDER BY match_number;
```

Expected: P1 has `group_id='a'`, `home_team='mex'`, `home_label='México'`. P73 has `phase='r32'`, `home_label='2.° Grupo A'`, `home_team=null`. P104 has `phase='final'`, `home_label=null`.

---

## Task 5: Extract IIFE globals in `index.html`

**Files:**
- Modify: `index.html` lines 4793–5186

The goal is to move 7 declarations from inside the IIFE to the line immediately before it (line 4792), making them globally accessible to `standings.js`.

- [ ] **Step 1: Cut `PHASE_LABELS` and `PHASE_COLORS` from IIFE and place before it**

Current (inside IIFE at lines 4810–4811):
```javascript
    var PHASE_LABELS = {R32:'16avos',R16:'Octavos',QF:'Cuartos',SF:'Semifinal',TP:'3er Puesto',F:'Final'};
    var PHASE_COLORS = {R32:'#f97316',R16:'#f59e0b',QF:'#a855f7',SF:'#3b82f6',TP:'#64748b',F:'#ffd700'};
```

Replace those two lines with nothing (delete them from inside the IIFE), and add them as global `var` declarations in the script block, just before `(function() {` at line 4793.

Find the comment line before the IIFE (line 4792: `// ── CALENDAR ──────────...`) and insert after it:

```javascript
  var PHASE_LABELS = {R32:'16avos',R16:'Octavos',QF:'Cuartos',SF:'Semifinal',TP:'3er Puesto',F:'Final'};
  var PHASE_COLORS = {R32:'#f97316',R16:'#f59e0b',QF:'#a855f7',SF:'#3b82f6',TP:'#64748b',F:'#ffd700'};
  var KNOCKOUT_MATCHES = [
    // 16avos de Final (28 jun – 3 jul)
    {phase:'R32',matchNum:73,date:'2026-06-28',time:'19:00',homeLabel:'2.° Grupo A',awayLabel:'2.° Grupo B',venue:'SoFi Stadium, Los Ángeles'},
    {phase:'R32',matchNum:74,date:'2026-06-29',time:'20:30',homeLabel:'1.° Grupo E',awayLabel:'3.° A/B/C/D/F',venue:'Gillette Stadium, Foxborough'},
    {phase:'R32',matchNum:75,date:'2026-06-29',time:'01:00',homeLabel:'1.° Grupo F',awayLabel:'2.° Grupo C',venue:'Estadio BBVA, Guadalupe'},
    {phase:'R32',matchNum:76,date:'2026-06-29',time:'17:00',homeLabel:'1.° Grupo C',awayLabel:'2.° Grupo F',venue:'NRG Stadium, Houston'},
    {phase:'R32',matchNum:77,date:'2026-06-30',time:'21:00',homeLabel:'1.° Grupo I',awayLabel:'3.° C/D/F/G/H',venue:'MetLife Stadium, East Rutherford'},
    {phase:'R32',matchNum:78,date:'2026-06-30',time:'17:00',homeLabel:'2.° Grupo E',awayLabel:'2.° Grupo I',venue:'AT&T Stadium, Arlington'},
    {phase:'R32',matchNum:79,date:'2026-06-30',time:'01:00',homeLabel:'1.° Grupo A',awayLabel:'3.° C/E/F/H/I',venue:'Estadio Azteca, Ciudad de México'},
    {phase:'R32',matchNum:80,date:'2026-07-01',time:'16:00',homeLabel:'1.° Grupo L',awayLabel:'3.° E/H/I/J/K',venue:'Mercedes-Benz Stadium, Atlanta'},
    {phase:'R32',matchNum:81,date:'2026-07-01',time:'00:00',homeLabel:'1.° Grupo D',awayLabel:'3.° B/E/F/I/J',venue:"Levi's Stadium, Santa Clara"},
    {phase:'R32',matchNum:82,date:'2026-07-01',time:'20:00',homeLabel:'1.° Grupo G',awayLabel:'3.° A/E/H/I/J',venue:'Lumen Field, Seattle'},
    {phase:'R32',matchNum:83,date:'2026-07-02',time:'23:00',homeLabel:'2.° Grupo K',awayLabel:'2.° Grupo L',venue:'BMO Field, Toronto'},
    {phase:'R32',matchNum:84,date:'2026-07-02',time:'19:00',homeLabel:'1.° Grupo H',awayLabel:'2.° Grupo J',venue:'SoFi Stadium, Los Ángeles'},
    {phase:'R32',matchNum:85,date:'2026-07-02',time:'03:00',homeLabel:'1.° Grupo B',awayLabel:'3.° E/F/G/I/J',venue:'BC Place, Vancouver'},
    {phase:'R32',matchNum:86,date:'2026-07-03',time:'22:00',homeLabel:'1.° Grupo J',awayLabel:'2.° Grupo H',venue:'Hard Rock Stadium, Miami Gardens'},
    {phase:'R32',matchNum:87,date:'2026-07-03',time:'01:30',homeLabel:'1.° Grupo K',awayLabel:'3.° D/E/I/J/L',venue:'Arrowhead Stadium, Kansas City'},
    {phase:'R32',matchNum:88,date:'2026-07-03',time:'18:00',homeLabel:'2.° Grupo D',awayLabel:'2.° Grupo G',venue:'AT&T Stadium, Arlington'},
    // Octavos de Final (4-7 jul)
    {phase:'R16',matchNum:89,date:'2026-07-04',time:'21:00',homeLabel:'Ganador Partido 74',awayLabel:'Ganador Partido 77',venue:'Lincoln Financial Field, Filadelfia'},
    {phase:'R16',matchNum:90,date:'2026-07-04',time:'17:00',homeLabel:'Ganador Partido 73',awayLabel:'Ganador Partido 75',venue:'NRG Stadium, Houston'},
    {phase:'R16',matchNum:91,date:'2026-07-05',time:'20:00',homeLabel:'Ganador Partido 76',awayLabel:'Ganador Partido 78',venue:'MetLife Stadium, East Rutherford'},
    {phase:'R16',matchNum:92,date:'2026-07-05',time:'00:00',homeLabel:'Ganador Partido 79',awayLabel:'Ganador Partido 80',venue:'Estadio Azteca, Ciudad de México'},
    {phase:'R16',matchNum:93,date:'2026-07-06',time:'19:00',homeLabel:'Ganador Partido 83',awayLabel:'Ganador Partido 84',venue:'AT&T Stadium, Arlington'},
    {phase:'R16',matchNum:94,date:'2026-07-06',time:'00:00',homeLabel:'Ganador Partido 81',awayLabel:'Ganador Partido 82',venue:'Lumen Field, Seattle'},
    {phase:'R16',matchNum:95,date:'2026-07-07',time:'16:00',homeLabel:'Ganador Partido 86',awayLabel:'Ganador Partido 88',venue:'Mercedes-Benz Stadium, Atlanta'},
    {phase:'R16',matchNum:96,date:'2026-07-07',time:'20:00',homeLabel:'Ganador Partido 85',awayLabel:'Ganador Partido 87',venue:'BC Place, Vancouver'},
    // Cuartos de Final (9-11 jul)
    {phase:'QF',matchNum:97,date:'2026-07-09',time:'20:00',homeLabel:'Ganador Partido 89',awayLabel:'Ganador Partido 90',venue:'Gillette Stadium, Foxborough'},
    {phase:'QF',matchNum:98,date:'2026-07-10',time:'19:00',homeLabel:'Ganador Partido 93',awayLabel:'Ganador Partido 94',venue:'SoFi Stadium, Los Ángeles'},
    {phase:'QF',matchNum:99,date:'2026-07-11',time:'21:00',homeLabel:'Ganador Partido 91',awayLabel:'Ganador Partido 92',venue:'Hard Rock Stadium, Miami Gardens'},
    {phase:'QF',matchNum:100,date:'2026-07-11',time:'01:00',homeLabel:'Ganador Partido 95',awayLabel:'Ganador Partido 96',venue:'Arrowhead Stadium, Kansas City'},
    // Semifinales (14-15 jul)
    {phase:'SF',matchNum:101,date:'2026-07-14',time:'19:00',homeLabel:'Ganador Partido 97',awayLabel:'Ganador Partido 98',venue:'AT&T Stadium, Arlington'},
    {phase:'SF',matchNum:102,date:'2026-07-15',time:'19:00',homeLabel:'Ganador Partido 99',awayLabel:'Ganador Partido 100',venue:'Mercedes-Benz Stadium, Atlanta'},
    // Tercer Puesto (18 jul)
    {phase:'TP',matchNum:103,date:'2026-07-18',time:'21:00',homeLabel:'Per. Partido 101',awayLabel:'Per. Partido 102',venue:'Hard Rock Stadium, Miami Gardens'},
    // Final (19 jul)
    {phase:'F',matchNum:104,date:'2026-07-19',time:'19:00',homeLabel:'Ganador Partido 101',awayLabel:'Ganador Partido 102',venue:'MetLife Stadium, East Rutherford'}
  ];
```

Then delete these same declarations from inside the IIFE (lines 4810–4851).

- [ ] **Step 2: Extract `labelDate()` from IIFE to global scope**

Current inside IIFE (lines 4862–4867):
```javascript
    function labelDate(dateStr) {
      // dateStr = YYYY-MM-DD; treat as local date (no time, no tz shift)
      var parts = dateStr.split('-');
      var d = new Date(parseInt(parts[0]), parseInt(parts[1])-1, parseInt(parts[2]));
      return DAYS_ES[d.getDay()] + ' ' + d.getDate() + ' ' + MONTHS_ES[d.getMonth()];
    }
```

This function uses `DAYS_ES` and `MONTHS_ES` which are local to the IIFE (lines 4808–4809). Two options:
- Also extract `DAYS_ES` and `MONTHS_ES` to global scope (simplest)
- Or copy them into `labelDate`'s own scope

Use the simplest: also move `DAYS_ES` and `MONTHS_ES` (lines 4808–4809) and `labelDate` to the global script block (before the IIFE). Then delete them from inside the IIFE.

New global declarations to add (alongside PHASE_LABELS, PHASE_COLORS, KNOCKOUT_MATCHES):
```javascript
  var DAYS_ES = ['Dom','Lun','Mar','Mié','Jue','Vie','Sáb'];
  var MONTHS_ES = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'];
  function labelDate(dateStr) {
    var parts = dateStr.split('-');
    var d = new Date(parseInt(parts[0]), parseInt(parts[1])-1, parseInt(parts[2]));
    return DAYS_ES[d.getDay()] + ' ' + d.getDate() + ' ' + MONTHS_ES[d.getMonth()];
  }
```

Delete `DAYS_ES`, `MONTHS_ES`, and `labelDate` from inside the IIFE.

- [ ] **Step 3: Extract `TEAM_CODES`, `TEAM_KO_PATH`, `TEAM_KO_3RD` from IIFE to global scope**

Move lines 4941–4951 (`TEAM_CODES`), 4998–5044 (`TEAM_KO_PATH`), and 5045–5067 (`TEAM_KO_3RD`) to the global script block before the IIFE.

Remove the `var` keyword from the IIFE versions (they'll become references to the globals) — actually just delete them from inside the IIFE entirely, since they're now declared globally.

- [ ] **Step 4: Extract `renderTeamKOPaths()` from IIFE to global scope; modify `koCard()` inside it**

Move lines 5069–5139 (`renderTeamKOPaths()`) to the global script block (after `labelDate`, before the IIFE).

**While moving, apply two changes:**

**Change A** — Add a clear at the top of `renderTeamKOPaths()` to prevent duplicate render on re-call:
```javascript
  function renderTeamKOPaths() {
    // Clear existing KO paths (idempotent re-render)
    document.querySelectorAll('.ko-path').forEach(function(el) { el.remove(); });

    var koByNum = {};
    KNOCKOUT_MATCHES.forEach(function(m) { koByNum[m.matchNum] = m; });
    // ... rest of function unchanged ...
```

**Change B** — In `koCard()` (nested inside `renderTeamKOPaths`), replace the `ko-card-opp` line:

Old:
```javascript
    + '<div class="ko-card-opp">vs ' + opp + '</div>'
```

New (calls `resolveOpponent` from standings.js — safe because standings.js is loaded before this runs):
```javascript
    + '<div class="ko-card-opp">vs ' + (function() {
        var r = (typeof resolveOpponent === 'function') ? resolveOpponent(opp) : null;
        if (!r) return opp;
        return '<img class="flag-svg" src="' + r.flagSrc + '" style="height:14px;vertical-align:middle;margin-right:.3rem">'
          + '<strong>' + r.name + '</strong>'
          + '<span style="opacity:.6;font-size:11px;margin-left:.3rem">(' + opp + ')</span>';
      })() + '</div>'
```

- [ ] **Step 5: Verify the page still loads correctly**

Open `index.html` in a browser (via a local server if needed — `npx serve .` or `python -m http.server`). Check:
- The group standings tables render (all zeros, same as before)
- The team KO path sections render (no duplicate `.ko-path` divs)
- No JS console errors

- [ ] **Step 6: Commit**

```bash
git add index.html
git commit -m "refactor: extract IIFE globals for standings live integration"
```

---

## Task 6: Add CSS for mejores-terceros table

**Files:**
- Modify: `index.html` CSS block (inside `<style>`)

- [ ] **Step 1: Find the standings CSS block and add 4 rules after it**

Search for `.st-thirds-cutline` — it doesn't exist yet. Search for `.st-third > td:first-child` (the existing rule, around line 312) and add the new rules immediately after the existing standings rules:

```css
/* Mejores terceros table rows */
.st-third-qualify > td:first-child { border-left: 3px solid rgba(245,158,11,.7); }
.st-third-out > td:first-child     { border-left: 3px solid rgba(100,116,139,.3); }
.st-third-out td                   { color: var(--muted); }
.st-thirds-cutline > td            { border-top: 1px dashed rgba(245,158,11,.4); }
```

- [ ] **Step 2: Commit**

```bash
git add index.html
git commit -m "feat: add CSS for mejores-terceros table rows"
```

---

## Task 7: Insert mejores-terceros HTML into `index.html`

**Files:**
- Modify: `index.html` after line 3849

Insert after `</section>` that closes `section#grupo-l` (line 3849) and before `<!-- ═══════ TRACKER DE CONVOCATORIAS ═══════ -->` (line 3850).

- [ ] **Step 1: Insert the new section**

```html
<!-- ═══════ MEJORES TERCEROS ═══════ -->
<section id="mejores-terceros">
  <div class="container">
    <div class="group-section-header" style="margin-bottom:1.5rem">
      <div class="group-big-label" style="color:rgba(245,158,11,.08);font-size:6rem;line-height:1">3°</div>
      <div class="group-section-info">
        <h2>Mejores Terceros</h2>
        <div style="color:var(--muted);font-size:14px;margin-top:.4rem">
          8 de los 12 terceros clasifican a 16avos de final · ordenados por criterios FIFA
        </div>
      </div>
    </div>

    <div class="standings-wrap" style="--grp-col:rgba(245,158,11,.7)">
      <table class="standings-table">
        <thead>
          <tr>
            <th class="st-pos-hdr">#</th>
            <th style="font-size:12px;padding:.4rem .5rem;text-align:center">Grp</th>
            <th class="st-team-hdr">Equipo</th>
            <th title="Partidos jugados">PJ</th>
            <th title="Ganados">PG</th>
            <th title="Empates">PE</th>
            <th title="Derrotas">PP</th>
            <th title="Goles a favor">GF</th>
            <th title="Goles en contra">GC</th>
            <th title="Diferencia de goles">DG</th>
            <th class="st-pts-hdr" title="Puntos">PTS</th>
          </tr>
        </thead>
        <tbody id="best-thirds-tbody">
        </tbody>
      </table>
    </div>

    <div class="standings-legend" style="margin-top:.75rem">
      <span><span class="st-legend-dot" style="background:rgba(245,158,11,.7)"></span>Clasifican (8 mejores)</span>
      <span><span class="st-legend-dot" style="background:rgba(100,116,139,.3)"></span>Eliminados</span>
    </div>

    <details class="st-tiebreak" style="margin-top:1rem">
      <summary>Criterios de ordenamiento para mejores terceros ▸</summary>
      <ol class="st-tiebreak-list">
        <li>Puntos totales en fase de grupos</li>
        <li>Diferencia de goles en todos los partidos del grupo</li>
        <li>Goles marcados en todos los partidos del grupo</li>
        <li>Fair play (−1 amarilla · −4 roja directa · −5 amarilla+roja)</li>
        <li>Ranking FIFA/Coca-Cola</li>
      </ol>
    </details>
  </div>
</section>
```

- [ ] **Step 2: Open the page and verify the section renders** (empty tbody is fine at this point)

- [ ] **Step 3: Commit**

```bash
git add index.html
git commit -m "feat: insert mejores-terceros section HTML"
```

---

## Task 8: Create `js/standings.js`

**Files:**
- Create: `js/standings.js`

- [ ] **Step 1: Create the file with full content**

```javascript
// standings.js — Live standings from Supabase, best-thirds table, KO path flags
// Requires: SUPABASE_URL, SUPABASE_ANON_KEY (config.js), window.supabase (CDN),
//           KNOCKOUT_MATCHES, TEAM_CODES, TEAM_KO_PATH, TEAM_KO_3RD, renderTeamKOPaths (index.html globals)

(function () {
  'use strict';

  // ── GROUP COMPOSITION ──────────────────────────────────────────────────────
  // Matches data/groups.json team order (used for default standings init)
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
  // Lower number = better rank
  var FIFA_RANK = {
    arg:1, fra:2, eng:3, bra:4, bel:5, por:6, ned:7, esp:8, ger:9, ury:10,
    col:11, usa:12, nor:13, mex:14, jpn:15, mor:16, cro:17, sen:18, sui:19,
    aut:20, kor:21, tur:22, aus:23, ecu:24, sco:25, irn:26, egy:27, mar:28,
    tun:29, can:30, swe:31, hti:32, cze:33, qat:34, irq:35, nor:13, cpv:36,
    ksa:37, cod:38, alg:39, bih:40, gha:41, zaf:42, uzb:43, jor:44,
    nzl:45, cuw:46, pry:47, pan:48
  };

  // ── CURRENT_STANDINGS global ───────────────────────────────────────────────
  // { 'a': [{code, name, flagSrc, group, PJ, PG, PE, PP, GF, GC, DG, PTS}, ...], ... }
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
  // Reads the current HTML standing tables (all zeros pre-tournament).
  // Sets CURRENT_STANDINGS so flags are always resolvable from day 1.
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
  // results: array of match_results rows for this group from Supabase
  // Returns: 4-item array sorted by FIFA criteria
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

      if (hg > ag)      { stats[h].PG++; stats[h].PTS += 3; stats[a].PP++; }
      else if (hg === ag){ stats[h].PE++; stats[h].PTS++;    stats[a].PE++; stats[a].PTS++; }
      else              { stats[a].PG++; stats[a].PTS += 3; stats[h].PP++; }
    });

    // Merge stats into existing team objects (preserves flagSrc, name, etc.)
    var existing = window.CURRENT_STANDINGS[gid] || [];
    var ranked = teamCodes.map(function (code) {
      var base = existing.filter(function (t) { return t.code === code; })[0] || {
        code: code, name: code,
        flagSrc: 'assets/flags/' + code + '.svg',
        group: gid.toUpperCase()
      };
      return Object.assign({}, base, stats[code] || {PJ:0,PG:0,PE:0,PP:0,GF:0,GC:0,DG:0,PTS:0});
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
  // Reorders <tr> rows and updates stat cells without rebuilding team cells.
  function updateStandingsTable(gid, ranked) {
    var section = document.getElementById('grupo-' + gid);
    if (!section) return;
    var tbody = section.querySelector('.standings-table tbody');
    if (!tbody) return;

    // Build code → row map
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

      tbody.appendChild(row); // moves row to end, reordering naturally
    });
  }

  // ── RESOLVE OPPONENT FLAG FROM TEXT ───────────────────────────────────────
  // Resolves "1.° Grupo A", "2.° Grupo B" → {flagSrc, name, code}
  // Returns null for multi-group patterns ("3.° C/E/F/H/I") or unknown.
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
      // No client (config not set) — just render defaults
      renderBestThirds(collectBestThirds());
      if (typeof renderTeamKOPaths === 'function') renderTeamKOPaths();
      return;
    }

    try {
      var ref = await client.from('match_results').select('*').eq('phase', 'group');
      var data = ref.data || [];

      if (data.length > 0) {
        // Group by group_id
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
```

- [ ] **Step 2: Commit**

```bash
git add js/standings.js
git commit -m "feat: standings.js — live standings, best thirds, KO flags"
```

---

## Task 9: Wire `standings.js` into `index.html`

**Files:**
- Modify: `index.html` before `</body>`

- [ ] **Step 1: Find where other JS files are loaded**

Search for `<script src="js/auth.js">` in index.html and note its line. The standings script must be added **after** `config.js` and `auth.js` (so `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and `window.supabase` CDN are already available).

- [ ] **Step 2: Add the script tag**

After the last `<script src="js/...">` tag (but before `</body>`), add:

```html
<script src="js/standings.js"></script>
```

- [ ] **Step 3: Commit**

```bash
git add index.html
git commit -m "feat: load standings.js in index.html"
```

---

## Task 10: End-to-end verification

**Files:** None modified — observation only

- [ ] **Step 1: Open the page and check the mejores-terceros section**

Open the page locally (`npx serve .` then visit `http://localhost:3000`).

Expected behavior:
- Scroll past Grupo L — a "Mejores Terceros" section appears with a table of 12 rows
- All 12 third-place teams are listed (one per group A–L), sorted initially by FIFA rank (since all PTS=0, DG=0, GF=0)
- Top 8 rows have orange left border (`.st-third-qualify`)
- Row 9 has a dashed top border (`.st-thirds-cutline`)
- Bottom 4 rows are grayed out (`.st-third-out`)
- No JS console errors

- [ ] **Step 2: Check KO path flags**

Navigate to any analyzed team section (e.g. `#estados-unidos`). In the "Ruta Eliminatoria Posible" cards:
- Cards showing `"1.° Grupo D"`, `"2.° Grupo B"`, etc. should now show a flag image + bold team name + faded bracket label in parentheses
- Cards showing `"3.° E/F/G/I/J"` or `"Ganador Partido 73"` should show only the text (no flag — expected, these can't be resolved pre-tournament)

- [ ] **Step 3: Simulate a live result via Supabase dashboard**

In the Supabase Table Editor, find match_number=1 (México vs Sudáfrica) and set `home_goals=2`, `away_goals=0`.

Without refreshing the page, within a few seconds:
- Group A standings should update: México 3pts (+2), Sudáfrica 0pts
- The mejores-terceros table should reorder (Corea del Sur or Chequia as 3rd of group A with 0pts, DG=0)
- The KO path flags for México-section should update if position changed

If realtime doesn't fire in <5s, manually refresh and verify standings update from Supabase on page load.

- [ ] **Step 4: Reset the test result**

```sql
UPDATE match_results SET home_goals = NULL, away_goals = NULL WHERE match_number = 1;
```

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat: mejores-terceros + standings live + KO path flags — complete"
```

---

## Self-Review Checklist

**Spec coverage:**
- ✓ Task 1: Supabase schema with all columns including home_label/away_label
- ✓ Task 2+3+4: Seed script for 104 matches (72 group + 16 r32 with labels + 16 KO without labels)
- ✓ Task 5: IIFE extraction of all 7 globals + renderTeamKOPaths + koCard flag injection
- ✓ Task 6: CSS for st-third-qualify, st-third-out, st-thirds-cutline
- ✓ Task 7: mejores-terceros HTML after grupo-l
- ✓ Task 8: standings.js with initDefaultStandings, calcGroupStandings, updateStandingsTable, resolveOpponent, collectBestThirds, renderBestThirds, loadAndRender, subscribeRealtime
- ✓ Task 9: script tag wired in
- ✓ Task 10: end-to-end test with live Supabase result simulation

**Type/name consistency check:**
- `resolveOpponent` declared as `window.resolveOpponent` in standings.js, referenced in `koCard()` as `resolveOpponent` — ✓ (window-scoped globals are accessible as bare names)
- `renderTeamKOPaths` called from `loadAndRender` as `renderTeamKOPaths()` — ✓ (extracted to global scope in Task 5)
- `CURRENT_STANDINGS` set as `window.CURRENT_STANDINGS` in standings.js — ✓
- `collectBestThirds()` returns array with `.classified` boolean — used correctly in `renderBestThirds` — ✓
- `updateStandingsTable(gid, ranked)` called with lowercase gid — `document.getElementById('grupo-' + gid)` expects lowercase — ✓
