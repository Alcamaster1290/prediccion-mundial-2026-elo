#!/usr/bin/env python3
"""Builds a local team content coverage manifest for the private admin monitor."""

import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ASSET_ALIASES = {
    "jpn": "jap",
    "cuw": "cur",
}
SECTION_BY_CODE = {
    "ger": "alemania",
    "aut": "austria",
    "bel": "belgica",
    "bih": "bosnia",
    "bra": "brasil",
    "cpv": "cabo-verde",
    "col": "colombia",
    "kor": "corea",
    "civ": "costa-marfil",
    "cuw": "curazao",
    "sco": "escocia",
    "esp": "espana",
    "usa": "estados-unidos",
    "fra": "francia",
    "hti": "haiti",
    "eng": "inglaterra",
    "jpn": "japon",
    "nor": "noruega",
    "nzl": "nueva-zelanda",
    "por": "portugal",
    "cod": "rd-congo",
    "swe": "suecia",
    "sui": "suiza",
    "tun": "tunez",
}


def load_json(path):
    return json.loads((REPO_ROOT / path).read_text(encoding="utf-8"))


def asset_codes(folder, pattern):
    return {path.name.split(pattern, 1)[0] for path in (REPO_ROOT / folder).glob(f"*{pattern}*")}


def player_asset_codes():
    codes = set()
    for path in (REPO_ROOT / "assets/players").glob("*-*"):
        if path.is_file():
            codes.add(path.name.split("-", 1)[0])
    return codes


def build_manifest():
    groups = load_json("data/groups.json")["groups"]
    teams_data = load_json("data/teams.json")
    analyzed = {team["id"]: team for team in teams_data.get("teams", [])}
    html = (REPO_ROOT / "index.html").read_text(encoding="utf-8")

    flags = {path.stem for path in (REPO_ROOT / "assets/flags").glob("*.svg")}
    xi_images = asset_codes("assets/xi", "-xi.")
    star_images = player_asset_codes()
    list_png = asset_codes("assets/lists", "-list.")
    list_txt = {path.name.split("-list.", 1)[0] for path in (REPO_ROOT / "assets/lists").glob("*-list.txt")}

    teams = []
    for group in groups:
        for code in group["teams"]:
            asset_code = ASSET_ALIASES.get(code, code)
            analyzed_team = analyzed.get(code)
            section_id = SECTION_BY_CODE.get(code)
            html_section = bool(section_id and re.search(rf'id="{re.escape(section_id)}"', html))
            players = analyzed_team.get("players", []) if analyzed_team else []
            titulars = sum(1 for player in players if player.get("titular"))
            player_elos = sum(1 for player in players if player.get("elo") is not None)

            assets = {
                "flag": code in flags,
                "xi_image": asset_code in xi_images,
                "star_image": asset_code in star_images,
                "list_png": asset_code in list_png,
                "list_txt": asset_code in list_txt,
            }
            local = {
                "analysis_json": analyzed_team is not None,
                "html_section": html_section,
                "players_json": len(players) >= 26,
                "starter_json": titulars >= 11,
                "player_elo_json_rows": player_elos,
            }

            local_missing = []
            for key, value in assets.items():
                if not value:
                    local_missing.append(key)
            for key in ("analysis_json", "html_section", "players_json", "starter_json"):
                if not local[key]:
                    local_missing.append(key)

            teams.append({
                "team_code": code,
                "asset_code": asset_code,
                "name": analyzed_team.get("name") if analyzed_team else None,
                "group_id": group["id"],
                "section_id": section_id,
                "source": teams_data.get("meta", {}).get("source_analysis") if analyzed_team else None,
                "assets": assets,
                "local": local,
                "local_missing": local_missing,
            })

    return {
        "meta": {
            "version": "1.0",
            "updated": "2026-06-04",
            "total_teams": len(teams),
            "source_analysis": teams_data.get("meta", {}).get("source_analysis"),
            "notes": "Generated from data/groups.json, data/teams.json, index.html, and assets folders.",
        },
        "teams": teams,
    }


def main():
    output = REPO_ROOT / "data/team-content-manifest.json"
    manifest = build_manifest()
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output.relative_to(REPO_ROOT)} with {manifest['meta']['total_teams']} teams")


if __name__ == "__main__":
    main()
