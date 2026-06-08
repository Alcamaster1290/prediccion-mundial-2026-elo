#!/usr/bin/env python3
"""generate_seed_sql.py -- Generates INSERT SQL files for Supabase seeding.

Outputs:
  data/seed_strengths.sql    -- team_strength_snapshots (48 rows)
  data/seed_players.sql      -- players (loaded teams x 26 players)
  data/seed_mc.sql           -- simulation_runs + simulation_group_standings

Run: python scripts/generate_seed_sql.py
"""
import json
import hashlib
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


def q(v):
    """Escape and quote a string, or return NULL."""
    if v is None:
        return 'NULL'
    return "'" + str(v).replace("'", "''") + "'"


def n(v):
    """Numeric or NULL."""
    return str(v) if v is not None else 'NULL'


def load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def gen_strengths(strengths_data, out_path):
    version = strengths_data.get('_version', '1.1')
    rows = []
    for code, t in strengths_data['teams'].items():
        rows.append(
            f"({q(code)},{q(version)},{n(t['elo_intl'])},{n(t.get('xi_blend'))},{n(t['strength_score'])},{q(t['method'])})"
        )

    sql = (
        "-- team_strength_snapshots\n"
        "TRUNCATE team_strength_snapshots RESTART IDENTITY CASCADE;\n"
        "INSERT INTO team_strength_snapshots (team_code,version,elo_intl,elo_club_avg,strength_score,method) VALUES\n"
        + ',\n'.join(rows)
        + ';\n'
    )
    out_path.write_text(sql, encoding='utf-8')
    print(f"  {len(rows)} rows -> {out_path.name}")


def gen_players(teams_data, out_path):
    version = '1.0'
    rows = []
    for team in teams_data.get('teams', []):
        code = team['id']
        for p in team.get('players', []):
            rows.append(
                f"({q(code)},{n(p.get('number'))},{q(p.get('pos'))},{q(p.get('name'))},{n(p.get('age'))},{q(p.get('club'))},{q(p.get('country'))},{n(p.get('elo'))},NULL,{str(bool(p.get('titular', False))).upper()},{q(version)})"
            )

    # Split into chunks of 200 to avoid SQL size limits
    chunk_size = 200
    chunks = [rows[i:i+chunk_size] for i in range(0, len(rows), chunk_size)]
    cols = "(team_code,shirt_number,pos,name,age,club,club_country,elo_club,elo_player,titular,version)"

    parts = ["-- players\nTRUNCATE players RESTART IDENTITY CASCADE;\n"]
    for chunk in chunks:
        parts.append(
            f"INSERT INTO players {cols} VALUES\n"
            + ',\n'.join(chunk)
            + ';\n'
        )

    out_path.write_text('\n'.join(parts), encoding='utf-8')
    print(f"  {len(rows)} rows ({len(chunks)} chunks) -> {out_path.name}")


def gen_mc(mc_data, out_path):
    runs = mc_data['runs']
    seed = mc_data.get('seed')
    version = mc_data.get('version', '1.1')
    scenario_name = mc_data.get('scenario_name', 'baseline')
    input_hash = hashlib.sha256(
        json.dumps(mc_data, sort_keys=True, separators=(',', ':')).encode('utf-8')
    ).hexdigest()

    run_rows = []
    for code, r in mc_data['teams'].items():
        points_pct = json.dumps(r.get('points_pct', {}), ensure_ascii=False, separators=(',', ':'))
        run_rows.append(
            f"({q(code)},{n(r['qualified_pct'])},{n(r['first_pct'])},{n(r['second_pct'])},{n(r['third_pct'])},{n(r.get('best_third_pct',0))},{n(r['fourth_pct'])},{q(points_pct)})"
        )

    terceros_rows = []
    for row in mc_data.get('terceros_table', []):
        group_id = row.get('group_id') or row.get('group')
        qualifies = str(bool(row.get('qualifies', False))).upper()
        terceros_rows.append(
            f"({n(row['rank'])},{q(group_id)},{q(row['team_code'])},{n(row['third_pct'])},{n(row['qualifies_pct'])},{n(row['avg_pts'])},{n(row['avg_gd'])},{n(row['avg_gf'])},{qualifies})"
        )

    sql = (
        "-- simulation_runs + simulation_group_standings + simulation_terceros_table\n"
        "TRUNCATE simulation_terceros_table RESTART IDENTITY CASCADE;\n"
        "TRUNCATE simulation_group_standings RESTART IDENTITY CASCADE;\n"
        "TRUNCATE simulation_runs RESTART IDENTITY CASCADE;\n"
        "\n"
        "WITH inserted_run AS (\n"
        "  INSERT INTO simulation_runs\n"
        "    (runs,seed,version,scenario_name,model_version,is_active,completed_at,input_hash)\n"
        f"  VALUES ({runs},{n(seed)},{q(version)},{q(scenario_name)},{q(version)},TRUE,NOW(),{q(input_hash)})\n"
        "  RETURNING id\n"
        "), inserted_standings AS (\n"
        "  INSERT INTO simulation_group_standings\n"
        "    (simulation_run,team_code,qualified_pct,first_pct,second_pct,third_pct,best_third_pct,fourth_pct,points_pct)\n"
        "  SELECT r.id, v.team_code, v.qualified_pct, v.first_pct, v.second_pct, v.third_pct, v.best_third_pct, v.fourth_pct, v.points_pct::jsonb\n"
        "  FROM inserted_run r,\n"
        "  (VALUES\n"
        + ',\n'.join(run_rows)
        + "\n  ) AS v(team_code,qualified_pct,first_pct,second_pct,third_pct,best_third_pct,fourth_pct,points_pct)\n"
        "  RETURNING 1\n"
        ")\n"
        "INSERT INTO simulation_terceros_table\n"
        "  (simulation_run,rank,group_id,team_code,third_pct,qualifies_pct,avg_pts,avg_gd,avg_gf,qualifies)\n"
        "SELECT r.id, v.rank, v.group_id, v.team_code, v.third_pct, v.qualifies_pct, v.avg_pts, v.avg_gd, v.avg_gf, v.qualifies\n"
        "FROM inserted_run r,\n"
        "(SELECT count(*) FROM inserted_standings) s,\n"
        "(VALUES\n"
        + ',\n'.join(terceros_rows)
        + "\n) AS v(rank,group_id,team_code,third_pct,qualifies_pct,avg_pts,avg_gd,avg_gf,qualifies);\n"
    )
    out_path.write_text(sql, encoding='utf-8')
    print(f"  {len(run_rows)} team rows + {len(terceros_rows)} terceros rows -> {out_path.name}")


def main():
    data_dir = REPO_ROOT / 'data'
    strengths_data = load(data_dir / 'team_strength_snapshots.json')
    teams_data     = load(data_dir / 'teams.json')
    mc_data        = load(data_dir / 'mc_results.json')

    print("Generating SQL seed files...")
    gen_strengths(strengths_data, data_dir / 'seed_strengths.sql')
    gen_players(teams_data,       data_dir / 'seed_players.sql')
    gen_mc(mc_data,               data_dir / 'seed_mc.sql')
    print("Done.")


if __name__ == '__main__':
    main()
