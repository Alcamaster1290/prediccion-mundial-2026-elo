#!/usr/bin/env python3
"""Import source-backed AlterFutbol squads into data/teams.json."""

import argparse
import copy
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def club_elo_map(club_elo_data):
    return {row["club"]: row["elo"] for row in club_elo_data.get("clubs", [])}


def group_order(groups_data):
    order = {}
    for group_index, group in enumerate(groups_data.get("groups", [])):
        for draw_index, code in enumerate(group.get("teams", [])):
            order[code] = (group.get("id") or "Z", draw_index, group_index)
    return order


def normalize_source_player(player, exact_elos):
    row = {
        "number": player.get("number"),
        "pos": player.get("pos"),
        "name": player.get("name"),
        "age": player.get("age"),
        "club": player.get("club"),
        "country": player.get("country"),
        "elo": player.get("elo"),
        "titular": False,
    }
    if row["elo"] is None and row["club"] in exact_elos:
        row["elo"] = exact_elos[row["club"]]
    return row


def build_squad_only_team(source_team, exact_elos):
    players = [
        normalize_source_player(player, exact_elos)
        for player in source_team.get("players", [])
    ]
    return {
        "id": source_team["team_code"],
        "name": source_team.get("name") or source_team["team_code"].upper(),
        "group": source_team.get("group_id"),
        "dt": "",
        "analyzed": False,
        "source_url": source_team.get("url"),
        "source_title": source_team.get("title"),
        "source_published_date": source_team.get("published_date"),
        "source_status": "squad_only",
        "players": players,
    }


def merge_squad_only_teams(teams_data, source_manifest, groups_data, exact_elos):
    merged = copy.deepcopy(teams_data)
    existing = {team["id"]: team for team in merged.get("teams", [])}
    added = []

    for source_team in source_manifest.get("teams", []):
        code = source_team.get("team_code")
        if code in existing:
            continue
        if source_team.get("status") != "complete":
            continue
        if len(source_team.get("players", [])) != 26:
            continue
        existing[code] = build_squad_only_team(source_team, exact_elos)
        added.append(code)

    order = group_order(groups_data)
    merged["teams"] = sorted(
        existing.values(),
        key=lambda team: order.get(team["id"], ("Z", 99, 99)),
    )
    meta = merged.setdefault("meta", {})
    meta["updated"] = "2026-06-06"
    meta["total_teams_analyzed"] = sum(1 for team in merged["teams"] if team.get("analyzed"))
    meta["total_teams_with_squads"] = len(merged["teams"])
    meta["source_squads"] = "AlterFutbol noticias; see data/alterfutbol_sources.json"
    return merged, added


def main():
    parser = argparse.ArgumentParser(description="Import complete AlterFutbol squads into teams.json")
    parser.add_argument("--teams", default=str(REPO_ROOT / "data" / "teams.json"))
    parser.add_argument("--sources", default=str(REPO_ROOT / "data" / "alterfutbol_sources.json"))
    parser.add_argument("--groups", default=str(REPO_ROOT / "data" / "groups.json"))
    parser.add_argument("--club-elo", default=str(REPO_ROOT / "data" / "club_elo.json"))
    args = parser.parse_args()

    teams_path = Path(args.teams)
    teams_data = load_json(teams_path)
    source_manifest = load_json(args.sources)
    groups_data = load_json(args.groups)
    exact_elos = club_elo_map(load_json(args.club_elo))

    merged, added = merge_squad_only_teams(teams_data, source_manifest, groups_data, exact_elos)
    teams_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Added {len(added)} squad-only teams: {', '.join(added) if added else 'none'}")
    print(f"teams.json now has {len(merged['teams'])} teams with squads")


if __name__ == "__main__":
    main()
