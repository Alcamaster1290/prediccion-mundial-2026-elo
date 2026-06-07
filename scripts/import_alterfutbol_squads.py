#!/usr/bin/env python3
"""Import source-backed AlterFutbol squads into data/teams.json."""

import argparse
import copy
import html as html_lib
import json
import re
import unicodedata
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

CLUB_TRANSLITERATION = str.maketrans(
    {
        "ı": "i",
        "İ": "I",
        "ø": "o",
        "Ø": "O",
        "ł": "l",
        "Ł": "L",
        "đ": "d",
        "Đ": "D",
        "ð": "d",
        "Ð": "D",
        "þ": "th",
        "Þ": "Th",
        "æ": "ae",
        "Æ": "AE",
        "œ": "oe",
        "Œ": "OE",
        "ß": "ss",
    }
)

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
    "borussia m gladbach": "borussia monchengladbach",
    "b monchengladbach": "borussia monchengladbach",
    "gladbach": "borussia monchengladbach",
    "dortmund": "borussia dortmund",
    "stuttgart": "vfb stuttgart",
    "mainz 05": "fsv mainz 05",
    "fsv mainz": "fsv mainz 05",
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
    "bsc young boys": "young boys bern",
    "young boys": "young boys bern",
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
    "rennes": "stade rennes",
    "toulouse fc": "toulouse",
    "ogc nice": "ogc nizza",
    "nice": "ogc nizza",
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
    "wolverhampton": "wolverhampton wanderers",
    "wolves": "wolverhampton wanderers",
    "al ahli": "al ahli",
    "al ahli saudi": "al ahli",
    "al ahli saudi fc": "al ahli",
    "al ahly": "al ahly",
    "al ahly sc": "al ahly",
    "al hilal": "al hilal sfc",
    "al hilal sfc": "al hilal sfc",
    "al nassr": "al nassr riyadh",
    "al nassr fc": "al nassr riyadh",
    "al wakrah": "al wakra",
    "al wakrah sc": "al wakra",
    "al ittihad kalba": "ittihad kalba",
    "al ittihad kalba scc": "ittihad kalba",
    "al shamal": "shamal",
    "al shamal sc": "shamal",
    "al najmah": "al najma",
    "al najmah fc": "al najma",
    "baniyas": "bani yas",
    "fc baniyas": "bani yas",
    "pumas unam": "unam pumas",
    "sint truidense": "st truiden",
    "sint truidense vv": "st truiden",
    "sharjah": "al sharjah",
    "sharjah fc": "al sharjah",
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
    "atlético mineiro": "atletico-mg",
    "atletico mineiro": "atletico-mg",
    "leverkusen": "bayer leverkusen",
    "bayer 04 leverkusen": "bayer leverkusen",
    "hoffenheim": "tsg hoffenheim",
    "tsg 1899 hoffenheim": "tsg hoffenheim",
    "wolfsburg": "vfl wolfsburg",
    "hamburgo sv": "hsv",
    "st gallen": "st gallen",
    "pafos fc": "paphos",
    "pafos": "paphos",
    "friburgo": "freiburg",
    "sc friburgo": "freiburg",
    "newcastle": "newcastle united",
    "lyon": "olympique lyon",
    "pfc ludogorets": "ludogorez rasgrad",
    "ludogorets": "ludogorez rasgrad",
    "qarabag": "qarabag agdam",
    "lask linz": "lask",
    "lafc": "los angeles fc",
    "norwich city": "norwich",
    "swansea city": "swansea",
    "hull city": "hull",
    "leicester city": "leicester",
    "watford fc": "watford",
    "hannover 96": "hannover",
    "stoke city": "stoke",
    "middlesbrough fc": "middlesbrough",
    "coventry city": "coventry",
    "rkc waalwijk": "waalwijk",
    "derby county": "derby",
    "birmingham city": "birmingham",
    "barnsley fc": "barnsley",
    "karlsruher sc": "karlsruhe",
    "fortuna dusseldorf": "dusseldorf",
    "almere city": "almere",
    "almere city fc": "almere",
    "charlton athletic": "charlton",
    "ipswich town": "ipswich",
    "vvv venlo": "venlo",
    "beveren": "waasland beveren",
    "sk beveren": "waasland beveren",
    "stade reims": "reims",
    "stade de reims": "reims",
    "holstein kiel": "holstein",
    "ifk norrkoping": "norrkoping",
    "peterborough united": "peterboro",
    "gd chaves": "chaves",
    "hamburger sv": "hamburg",
    "racing santander": "santander",
    "agmk olmaliq": "fc agmk",
    "nancy lorraine": "nancy",
    "rotherham united": "rotherham",
    "luton town": "luton",
    "frosinone calcio": "frosinone",
    "fcv dender": "dender",
    "fcv dender eh": "dender",
    "chivas guadalajara": "cd guadalajara",
    "pakhtakor tashkent": "pakhtakor",
    "neftchi fergana": "neftchi fargona",
    "cd toluca": "deportivo toluca",
    "toluca": "deportivo toluca",
    "jeonbuk hyundai motors": "jeonbuk fc",
    "tigres uanl": "uanl tigres",
    "rijeka": "hnk rijeka",
    "atlanta united": "atlanta utd",
    "standard lieja": "standard luttich",
    "standard liège": "standard luttich",
    "deportivo saprissa": "saprissa",
    "jagiellonia": "jagiellonia bialystok",
    "kasimpasa": "kasimpasa istanbul",
    "kasimpasa sk": "kasimpasa istanbul",
    "botafogo": "botafogo rj",
    "dinamo samarqand": "din samarkand",
    "dinamo samarkand": "din samarkand",
    "polokwane city": "polokwane",
    "polokwane city fc": "polokwane",
    "daejeon hana citizen": "daejeon",
    "tatran presov": "presov",
    "fc tatran presov": "presov",
    "univ cluj": "universitatea cluj",
    "ferencvaros": "ferencvaros budapest",
    "ferencvaros tc": "ferencvaros budapest",
    "san lorenzo almagro": "san lorenzo",
    "san lorenzo de almagro": "san lorenzo",
    "independiente rivadavia": "ind rivadavia",
    "rb bragantino": "bragantino",
    "grazer ak 1902": "grazer ak",
    "leipzig": "rb leipzig",
    "apoel": "apoel nikosia",
    "kifisias": "kifisia",
    "ae kifisias": "kifisia",
    "ae kifisia": "kifisia",
    "liga quito": "ldu quito",
    "liga de quito": "ldu quito",
    "independiente valle": "ind valle",
    "independiente del valle": "ind valle",
    "royal antwerp": "royal antwerpen",
    "west ham": "west ham united",
    "etoile du sahel": "etoile sahel",
    "servette": "servette genf",
    "sporting lisboa": "sporting cp",
    "sporting de lisboa": "sporting cp",
    "el gouna": "el gounah",
    "aik": "aik stockholm",
    "twente": "twente enschede",
    "fc twente": "twente enschede",
    "malavan bandar anzali": "malavan",
    "sjk": "sjk seinajoki",
    "surkhon termiz": "termez surkhon",
    "shabab al ahli dubai": "al ahli dubai",
    "rostov": "rostow",
    "fk rostov": "rostow",
    "western sydney wanderers": "western sydney wanderers",
    "w sydney wanderers": "western sydney wanderers",
    "celta": "celta vigo",
    "rc celta": "celta vigo",
    "omonoia nicosia": "omonia nikosia",
    "akron tolyatti": "akron togliatti",
    "estudiantes la plata": "estudiantes",
    "estudiantes de la plata": "estudiantes",
    "real salt lake city": "real salt lake",
    "persib bandung": "persib",
    "port fc": "port mti",
    "pogon szczecin": "pogon stettin",
    "larissa": "larisa",
    "ael larissa": "larisa",
    "atletico nacional": "atl nacional",
    "atlas": "atlas guadalajara",
    "athletico paranaense": "athletico pr",
    "vasco da gama": "vasco",
    "cr vasco da gama": "vasco",
    "st patrick s athletic": "st patrick s",
    "pari nizhny novgorod": "pari nn",
    "academia puerto cabello": "puerto cabello",
    "deportivo la guaira": "la guaira",
    "ironi kiryat shmona": "kiryat shmona",
    "rcd espanyol": "espanyol barcelona",
    "espanyol": "espanyol barcelona",
    "fcsb": "fcsb bukarest",
    "zhejiang": "zhejiang professional",
    "zhejiang fc": "zhejiang professional",
    "idgir": "igdir",
    "idgir fk": "igdir",
}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_club_elo_sources(primary_path, supplement_paths=None):
    data = copy.deepcopy(load_json(primary_path))
    data.setdefault("clubs", [])
    for supplement_path in supplement_paths or []:
        path = Path(supplement_path)
        if not path.exists():
            continue
        supplement = load_json(path)
        data["clubs"].extend(supplement.get("clubs", []))
    return data


def normalize_club_key(value):
    text = "" if value is None else str(value)
    text = html_lib.unescape(text)
    text = text.translate(CLUB_TRANSLITERATION)
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
        "1902",
        "ac",
        "afc",
        "ae",
        "ael",
        "as",
        "bc",
        "bsc",
        "c",
        "ca",
        "calcio",
        "cd",
        "cf",
        "club",
        "de",
        "del",
        "eh",
        "f",
        "fc",
        "fcv",
        "ff",
        "fk",
        "football",
        "futbol",
        "gd",
        "gnk",
        "hnk",
        "hsc",
        "if",
        "jk",
        "pfk",
        "pfc",
        "rc",
        "rcd",
        "rsc",
        "sc",
        "scc",
        "sco",
        "scu",
        "sk",
        "ss",
        "sv",
        "tc",
        "the",
        "us",
        "vv",
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
        unescaped_club = html_lib.unescape(str(club))
        elos.setdefault(club, elo)
        elos.setdefault(unescaped_club, elo)

        key = normalize_club_key(club)
        if key not in elos or elo > elos[key]:
            elos[key] = elo
    return elos


def lookup_club_elo(club, club_elos):
    if not club:
        return None
    key = normalize_club_key(club)
    aliases = {
        normalize_club_key(alias): normalize_club_key(target)
        for alias, target in CLUB_ELO_ALIASES.items()
    }
    alias = aliases.get(key)
    if alias in club_elos:
        return club_elos[alias]
    if club in club_elos:
        return club_elos[club]
    unescaped_club = html_lib.unescape(str(club))
    if unescaped_club in club_elos:
        return club_elos[unescaped_club]
    return club_elos.get(key)


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
    apply_club_elos_to_teams(merged, exact_elos, only_missing=False)
    return merged, added


def main():
    parser = argparse.ArgumentParser(description="Import complete AlterFutbol squads into teams.json")
    parser.add_argument("--teams", default=str(REPO_ROOT / "data" / "teams.json"))
    parser.add_argument("--sources", default=str(REPO_ROOT / "data" / "alterfutbol_sources.json"))
    parser.add_argument("--groups", default=str(REPO_ROOT / "data" / "groups.json"))
    parser.add_argument("--club-elo", default=str(REPO_ROOT / "data" / "club_elo.json"))
    parser.add_argument(
        "--club-elo-supplement",
        action="append",
        default=[
            str(REPO_ROOT / "data" / "club_elo_flerosport_supplement.json"),
            str(REPO_ROOT / "data" / "club_elo_elofootball_supplement.json"),
        ],
    )
    args = parser.parse_args()

    teams_path = Path(args.teams)
    teams_data = load_json(teams_path)
    source_manifest = load_json(args.sources)
    groups_data = load_json(args.groups)
    exact_elos = club_elo_map(load_club_elo_sources(args.club_elo, args.club_elo_supplement))

    merged, added = merge_squad_only_teams(teams_data, source_manifest, groups_data, exact_elos)
    teams_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Added {len(added)} squad-only teams: {', '.join(added) if added else 'none'}")
    print(f"teams.json now has {len(merged['teams'])} teams with squads")


if __name__ == "__main__":
    main()
