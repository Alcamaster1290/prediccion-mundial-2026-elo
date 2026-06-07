#!/usr/bin/env python3
"""Import source-backed AlterFutbol squads into data/teams.json."""

import argparse
import copy
import json
import re
import unicodedata
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

CLUB_ELO_ALIASES = {
    "ac milan": "ac mailand",
    "milan": "ac mailand",
    "inter": "inter mailand",
    "inter milan": "inter mailand",
    "inter de milan": "inter mailand",
    "bayern munich": "bayern munchen",
    "arsenal": "arsenal",
    "barcelona": "barcelona",
    "barcelona fc": "barcelona",
    "real madrid cf": "real madrid",
    "atletico de madrid": "atletico madrid",
    "paris saint germain": "psg",
    "liverpool": "liverpool",
    "chelsea": "chelsea",
    "chelsea fc": "chelsea",
    "tottenham": "tottenham hotspur",
    "aston villa fc": "aston villa",
    "manchester city fc": "manchester city",
    "manchester united fc": "manchester united",
    "newcastle united fc": "newcastle united",
    "juventus": "juventus turin",
    "juventus fc": "juventus turin",
    "ssc napoli": "ssc neapel",
    "napoli": "ssc neapel",
    "roma": "as rom",
    "as roma": "as rom",
    "lazio": "lazio rom",
    "atalanta": "atalanta bergamo",
    "atalanta bc": "atalanta bergamo",
    "brighton": "brighton hove albion",
    "brighton hove albion": "brighton hove albion",
    "real betis": "betis sevilla",
    "galatasaray": "galatasaray istanbul",
    "galatasaray sk": "galatasaray istanbul",
    "fenerbahce": "fenerbahce istanbul",
    "fenerbahce sk": "fenerbahce istanbul",
    "besiktas": "besiktas istanbul",
    "besiktas jk": "besiktas istanbul",
    "olympique de marsella": "olympique marseille",
    "olympique de marseille": "olympique marseille",
    "olympique lyonnais": "olympique lyon",
    "olympique de lyon": "olympique lyon",
    "losc lille": "osc lille",
    "lille": "osc lille",
    "slavia praga": "slavia prag",
    "sparta praga": "sparta prag",
    "viktoria plzen": "viktoria pilsen",
    "viktoria plzen 1911": "viktoria pilsen",
    "viktoria plzen": "viktoria pilsen",
    "fc copenhague": "kopenhagen",
    "fc copenhagen": "kopenhagen",
    "fc kopenhavn": "kopenhagen",
    "cr flamengo": "flamengo",
    "flamengo rj": "flamengo",
    "se palmeiras": "palmeiras",
    "palmeiras sp": "palmeiras",
    "red bull salzburg": "rb salzburg",
    "rb salzburg": "rb salzburg",
    "rsc union saint gilloise": "union saint gilloise",
    "club brujas": "brugge",
    "club brugge": "brugge",
    "genk": "krc genk",
    "rkc genk": "krc genk",
    "sc braga": "sporting braga",
    "braga": "sporting braga",
    "sporting": "sporting cp",
    "sc sporting": "sporting cp",
    "benfica": "benfica lissabon",
    "sl benfica": "benfica lissabon",
    "red star belgrade": "roter stern belgrad",
    "fk crvena zvezda": "roter stern belgrad",
    "shakhtar donetsk": "schachtar donezk",
    "dynamo kyiv": "dynamo kiew",
    "dynamo kiev": "dynamo kiew",
    "lokomotiv moskva": "lokomotive moskau",
    "dinamo moskva": "dynamo moskau",
    "dynamo moscu": "dynamo moskau",
    "spartak moscow": "spartak moskau",
    "fc zurich": "zurich",
    "feyenoord": "feyenoord rotterdam",
    "ajax": "ajax amsterdam",
    "afc ajax": "ajax amsterdam",
    "psv": "psv eindhoven",
    "celtic fc": "celtic glasgow",
    "rangers fc": "glasgow rangers",
    "heart of midlothian fc": "heart of midlothian",
    "olympiakos": "olympiakos piraus",
    "olympiakos piraeus": "olympiakos piraus",
    "aek atenas": "aek athen",
    "panathinaikos fc": "panathinaikos",
    "as monaco": "as monaco",
    "racing de estrasburgo": "racing strassburg",
    "rc estrasburgo": "racing strassburg",
    "rc strasbourg": "racing strassburg",
    "stade rennais": "stade rennes",
    "stade rennais fc": "stade rennes",
    "toulouse fc": "toulouse",
    "genoa cfc": "cfc genua",
    "ac genoa": "cfc genua",
    "udinese": "udinese calcio",
    "fiorentina": "ac florenz",
    "acf fiorentina": "ac florenz",
    "torino": "turin",
    "torino fc": "turin",
    "parma calcio 1913": "parma calcio",
    "venezia fc": "venezia",
    "venezia": "venezia",
    "sassuolo": "sassuolo calcio",
    "us sassuolo": "sassuolo calcio",
    "bologna fc 1909": "bologna",
    "bologna": "bologna",
    "cagliari": "cagliari calcio",
    "cagliari calcio": "cagliari calcio",
    "como": "como 1907",
    "como 1907": "como 1907",
    "al ahli": "al ahli",
    "al ahli saudi": "al ahli",
    "al ahli saudi fc": "al ahli",
    "al ahly": "al ahly",
    "al ahly sc": "al ahly",
    "al hilal": "al hilal sfc",
    "al hilal sfc": "al hilal sfc",
    "al nassr": "al nassr riyadh",
    "al nassr fc": "al nassr riyadh",
    "esperance tunis": "esperance tunis",
    "rs berkane": "berkane",
    "as far": "far rabat",
    "orlando pirates": "orlando",
    "mazembe": "mazembe",
    "raja casablanca": "raja casablanca",
    "simba sc": "simba",
    "young africans sc": "young africans",
    "nordsjaelland": "nordsjaelland",
    "nordsjaelland fc": "nordsjaelland",
    "midtjylland": "midtjylland",
    "fc midtjylland": "midtjylland",
    "villarreal": "villarreal",
    "villarreal cf": "villarreal",
    "fulham": "fulham",
    "fulham fc": "fulham",
    "everton": "everton",
    "everton fc": "everton",
    "sunderland": "sunderland",
    "sunderland afc": "sunderland",
    "bournemouth": "bournemouth",
    "athletic club": "athletic bilbao",
    "leverkusen": "bayer leverkusen",
    "bayer 04 leverkusen": "bayer leverkusen",
    "hoffenheim": "tsg hoffenheim",
    "tsg 1899 hoffenheim": "tsg hoffenheim",
    "wolfsburg": "vfl wolfsburg",
    "hamburgo sv": "hsv",
    "st gallen": "st gallen",
    "pafos fc": "paphos",
    "pafos": "paphos",
    "pfc ludogorets": "ludogorez rasgrad",
    "ludogorets": "ludogorez rasgrad",
    "qarabag": "qarabag agdam",
    "lask linz": "lask",
}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def normalize_club_key(value):
    text = "" if value is None else str(value)
    text = re.sub(r"[\U0001F1E6-\U0001F1FF]+", " ", text)
    text = "".join(
        char
        for char in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(char)
    )
    text = text.lower().replace("ß", "ss")
    text = text.replace("&", " ")
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    stopwords = {
        "1",
        "04",
        "1909",
        "1913",
        "ac",
        "afc",
        "as",
        "bc",
        "cd",
        "cf",
        "club",
        "de",
        "del",
        "fc",
        "fk",
        "football",
        "futbol",
        "jk",
        "pfc",
        "rc",
        "rsc",
        "sc",
        "sk",
        "ss",
        "sv",
        "the",
        "us",
    }
    tokens = [token for token in text.split() if token not in stopwords]
    return " ".join(tokens)


def club_elo_map(club_elo_data):
    elos = {}
    for row in club_elo_data.get("clubs", []):
        club = row.get("club")
        elo = row.get("elo")
        if not club or elo is None:
            continue
        elos[club] = elo
        elos[normalize_club_key(club)] = elo
    return elos


def lookup_club_elo(club, club_elos):
    if not club:
        return None
    if club in club_elos:
        return club_elos[club]
    key = normalize_club_key(club)
    aliases = {
        normalize_club_key(alias): normalize_club_key(target)
        for alias, target in CLUB_ELO_ALIASES.items()
    }
    alias = aliases.get(key, key)
    return club_elos.get(alias)


def apply_club_elos_to_teams(teams_data, club_elos, only_missing=True):
    updated = 0
    for team in teams_data.get("teams", []):
        for player in team.get("players") or []:
            if only_missing and player.get("elo") is not None:
                continue
            elo = lookup_club_elo(player.get("club"), club_elos)
            if elo is None:
                continue
            if player.get("elo") != elo:
                player["elo"] = elo
                updated += 1
    return updated


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
    if row["elo"] is None:
        row["elo"] = lookup_club_elo(row["club"], exact_elos)
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
    apply_club_elos_to_teams(merged, exact_elos)
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
