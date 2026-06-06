#!/usr/bin/env python3
"""Download AlterFutbol XI images and enrich squad-only team records."""

import argparse
import json
from pathlib import Path

import requests

try:
    from scripts.scrape_alterfutbol_news import USER_AGENT, extract_tactical_info_from_article
except ModuleNotFoundError:
    from scrape_alterfutbol_news import USER_AGENT, extract_tactical_info_from_article


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def source_by_code(source_manifest):
    return {team["team_code"]: team for team in source_manifest.get("teams", [])}


def default_fetch_article_html(url):
    response = requests.get(url, timeout=30, headers={"User-Agent": USER_AGENT})
    response.raise_for_status()
    return response.text


def default_download_image(url):
    response = requests.get(url, timeout=30, headers={"User-Agent": USER_AGENT})
    response.raise_for_status()
    return response.content


def enrich_teams_with_xi_assets(
    teams_data,
    source_manifest,
    xi_dir,
    fetch_article_html,
    download_image,
    overwrite=False,
):
    xi_path = Path(xi_dir)
    xi_path.mkdir(parents=True, exist_ok=True)
    sources = source_by_code(source_manifest)
    report = {
        "downloaded": [],
        "preserved": [],
        "missing_source": [],
        "missing_formation": [],
        "fetch_error": [],
    }

    for team in teams_data.get("teams", []):
        if team.get("source_status") != "squad_only":
            continue
        code = team["id"]
        source = sources.get(code)
        if not source or not source.get("url"):
            report["missing_source"].append(code)
            continue

        formation_images = source.get("formation_images") or []
        if not formation_images:
            report["missing_formation"].append(code)
            continue

        asset_name = f"{code}-xi.png"
        asset_path = xi_path / asset_name
        if asset_path.exists() and not overwrite:
            report["preserved"].append(code)
        else:
            asset_path.write_bytes(download_image(formation_images[0]))
            report["downloaded"].append(code)

        try:
            article_html = fetch_article_html(source["url"])
            tactical_info = extract_tactical_info_from_article(article_html)
        except Exception as exc:
            tactical_info = {"scheme": None, "tactics": []}
            report["fetch_error"].append({"team_code": code, "error": str(exc)})

        team["scheme"] = tactical_info.get("scheme")
        team["tactics"] = tactical_info.get("tactics") or []
        team["xi_image"] = f"assets/xi/{asset_name}"
        team["xi_source_url"] = formation_images[0]
        team["source_tactics_url"] = source["url"]

        for player in team.get("players", []):
            player["titular"] = bool(player.get("titular", False))

    return teams_data, report


def main():
    parser = argparse.ArgumentParser(description="Enrich squad-only teams with XI image assets and tactical fields")
    parser.add_argument("--teams", default=str(REPO_ROOT / "data" / "teams.json"))
    parser.add_argument("--sources", default=str(REPO_ROOT / "data" / "alterfutbol_sources.json"))
    parser.add_argument("--xi-dir", default=str(REPO_ROOT / "assets" / "xi"))
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    teams_path = Path(args.teams)
    teams_data = load_json(teams_path)
    source_manifest = load_json(args.sources)
    enriched, report = enrich_teams_with_xi_assets(
        teams_data=teams_data,
        source_manifest=source_manifest,
        xi_dir=Path(args.xi_dir),
        fetch_article_html=default_fetch_article_html,
        download_image=default_download_image,
        overwrite=args.overwrite,
    )
    write_json(teams_path, enriched)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
