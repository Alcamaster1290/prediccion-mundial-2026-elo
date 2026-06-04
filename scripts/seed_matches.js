// seed_matches.js — Run with: node scripts/seed_matches.js
// Requires: SUPABASE_URL and SUPABASE_SERVICE_KEY env vars
// npm install @supabase/supabase-js

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

  let allFixtures = [];
  groupsData.groups.forEach(function(g) {
    g.fixtures.forEach(function(f) {
      allFixtures.push(Object.assign({}, f, { group_id: g.id.toUpperCase() }));
    });
  });
  allFixtures.sort(function(a, b) {
    const da = a.date + 'T' + a.time;
    const db = b.date + 'T' + b.time;
    return da < db ? -1 : da > db ? 1 : 0;
  });

  allFixtures.forEach(function(f, i) {
    const matchNum = i + 1;
    const parts = f.venue ? f.venue.split(',') : [];
    const stadium = parts[0] ? parts[0].trim() : null;
    const city = parts[1] ? parts[1].trim() : null;
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
      stadium: stadium,
      city: city,
      status: 'scheduled'
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
      home_label: isR32 ? m.homeLabel : null,
      away_label: isR32 ? m.awayLabel : null,
      kickoff_utc: m.date + 'T' + m.time + ':00Z',
      stadium: m.venue || null,
      city: m.city || null,
      status: 'scheduled'
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
