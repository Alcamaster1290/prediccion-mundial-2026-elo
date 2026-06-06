#!/usr/bin/env python3
"""Scrape AlterFutbol source pages for WC 2026 squad data."""

import argparse
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


REPO_ROOT = Path(__file__).resolve().parents[1]
NEWS_URL = "https://www.alterfutbol.com/noticias/"
USER_AGENT = "mundial-2026-data-audit/1.0 (+https://www.alterfutbol.com/noticias/)"


COUNTRY_VARIANTS = {
    "ee uu": "estados unidos",
    "eeuu": "estados unidos",
    "usa": "estados unidos",
    "usmnt": "estados unidos",
    "paises bajos": "paises bajos",
    "rd congo": "republica democratica del congo",
}

TEAM_NAMES_ES = {
    "mex": "México",
    "zaf": "Sudáfrica",
    "kor": "Corea del Sur",
    "cze": "República Checa",
    "can": "Canadá",
    "bih": "Bosnia y Herzegovina",
    "qat": "Qatar",
    "sui": "Suiza",
    "bra": "Brasil",
    "mar": "Marruecos",
    "hti": "Haití",
    "sco": "Escocia",
    "usa": "Estados Unidos",
    "pry": "Paraguay",
    "aus": "Australia",
    "tur": "Turquía",
    "ger": "Alemania",
    "cuw": "Curazao",
    "civ": "Costa de Marfil",
    "ecu": "Ecuador",
    "ned": "Países Bajos",
    "jpn": "Japón",
    "swe": "Suecia",
    "tun": "Túnez",
    "bel": "Bélgica",
    "egy": "Egipto",
    "irn": "Irán",
    "nzl": "Nueva Zelanda",
    "esp": "España",
    "cpv": "Cabo Verde",
    "ksa": "Arabia Saudita",
    "ury": "Uruguay",
    "fra": "Francia",
    "sen": "Senegal",
    "irq": "Irak",
    "nor": "Noruega",
    "arg": "Argentina",
    "alg": "Argelia",
    "aut": "Austria",
    "jor": "Jordania",
    "por": "Portugal",
    "cod": "RD Congo",
    "uzb": "Uzbekistán",
    "col": "Colombia",
    "eng": "Inglaterra",
    "cro": "Croacia",
    "gha": "Ghana",
    "pan": "Panamá",
}

TEAM_ALIASES = {
    "mex": ("méxico", "mexico"),
    "zaf": ("sudáfrica", "sudafrica", "south africa"),
    "kor": ("corea del sur", "south korea"),
    "cze": ("república checa", "republica checa", "chequia", "czechia"),
    "can": ("canadá", "canada"),
    "bih": ("bosnia y herzegovina", "bosnia"),
    "qat": ("qatar",),
    "sui": ("suiza", "switzerland"),
    "bra": ("brasil", "brazil"),
    "mar": ("marruecos", "morocco"),
    "hti": ("haití", "haiti"),
    "sco": ("escocia", "scotland"),
    "usa": ("estados unidos", "ee uu", "eeuu", "usmnt", "united states"),
    "pry": ("paraguay",),
    "aus": ("australia",),
    "tur": ("turquía", "turquia", "turkey"),
    "ger": ("alemania", "germany"),
    "cuw": ("curazao", "curaçao", "curacao"),
    "civ": ("costa de marfil", "ivory coast"),
    "ecu": ("ecuador",),
    "ned": ("países bajos", "paises bajos", "netherlands"),
    "jpn": ("japón", "japon", "japan"),
    "swe": ("suecia", "sweden"),
    "tun": ("túnez", "tunez", "tunisia"),
    "bel": ("bélgica", "belgica", "belgium"),
    "egy": ("egipto", "egypt"),
    "irn": ("irán", "iran"),
    "nzl": ("nueva zelanda", "new zealand"),
    "esp": ("españa", "espana", "spain"),
    "cpv": ("cabo verde", "cape verde"),
    "ksa": ("arabia saudita", "arabia saudi", "saudi arabia"),
    "ury": ("uruguay",),
    "fra": ("francia", "france"),
    "sen": ("senegal",),
    "irq": ("irak", "iraq"),
    "nor": ("noruega", "norway"),
    "arg": ("argentina",),
    "alg": ("argelia", "algeria"),
    "aut": ("austria",),
    "jor": ("jordania", "jordan"),
    "por": ("portugal",),
    "cod": (
        "rd congo",
        "rd-congo",
        "republica democratica del congo",
        "república democrática del congo",
        "dr congo",
    ),
    "uzb": ("uzbekistán", "uzbekistan"),
    "col": ("colombia",),
    "eng": ("inglaterra", "england"),
    "cro": ("croacia", "croatia"),
    "gha": ("ghana",),
    "pan": ("panamá", "panama"),
}

POSITION_BY_HEADING = (
    ("arquero", "GK"),
    ("portero", "GK"),
    ("defensor", "DF"),
    ("defensa", "DF"),
    ("mediocampista", "MF"),
    ("volante", "MF"),
    ("delantero", "FW"),
    ("atacante", "FW"),
)

TACTICAL_HEADING_TOKENS = (
    "esquema tactico",
    "analisis tactico",
    "xi ideal",
    "como juega",
)

TACTICAL_STOP_HEADING_TOKENS = (
    "lista",
    "convocados",
    "ausencias",
    "historia",
    "mejores jugadores",
    "arqueros",
    "defensores",
    "volantes",
    "delanteros",
)

SCHEME_RE = re.compile(r"\b[1-5](?:-[1-5]){2,4}\b")


def normalize_country_name(value):
    """Return a lowercase, accent-free country key for source matching."""
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return COUNTRY_VARIANTS.get(text, text)


def normalize_text(value):
    return re.sub(r"\s+", " ", value or "").strip()


def heading_to_position(text):
    key = normalize_country_name(text)
    for needle, pos in POSITION_BY_HEADING:
        if needle in key:
            return pos
    return None


def parse_player_line(text, pos):
    clean = normalize_text(text).strip("•-* ")
    patterns = (
        r"^(?P<name>.+?)\s*\((?P<age>\d{1,2})\s*años?,\s*(?P<club>[^)]+)\)",
        r"^(?P<name>.+?)\s*\((?P<age>\d{1,2}),\s*(?P<club>[^)]+)\)",
        r"^(?P<name>.+?)\s*\((?P<age>\d{1,2})\s*años?\)\s*[-–—]\s*(?P<club>.+)$",
    )
    for pattern in patterns:
        match = re.search(pattern, clean, flags=re.I)
        if not match:
            continue
        return {
            "number": None,
            "pos": pos,
            "name": normalize_text(match.group("name")),
            "age": int(match.group("age")),
            "club": normalize_text(match.group("club")),
            "country": None,
            "elo": None,
            "titular": False,
        }
    return None


def article_content_root(soup):
    return (
        soup.select_one(".elementor-widget-theme-post-content")
        or soup.select_one(".entry-content")
        or soup.find("article")
        or soup
    )


def extract_players_from_article(html):
    """Extract source-backed player rows from list sections in an article."""
    soup = BeautifulSoup(html, "html.parser")
    root = article_content_root(soup)
    players = []
    current_pos = None

    for node in root.find_all(["h2", "h3", "h4", "p", "li"]):
        text = normalize_text(node.get_text(" ", strip=True))
        if not text:
            continue
        pos = heading_to_position(text)
        if pos and node.name != "li":
            current_pos = pos
            continue
        if node.name == "li" and current_pos:
            player = parse_player_line(text, current_pos)
            if player:
                players.append(player)

    return players


def heading_matches_any(text, tokens):
    key = normalize_country_name(text)
    return any(token in key for token in tokens)


def extract_scheme(text):
    match = SCHEME_RE.search(text or "")
    return match.group(0) if match else None


def extract_tactical_info_from_article(html, max_paragraphs=3):
    """Extract tactical system and article-backed tactical paragraphs."""
    soup = BeautifulSoup(html, "html.parser")
    root = article_content_root(soup)
    tactics = []
    in_tactical_block = False

    for node in root.find_all(["h2", "h3", "h4", "p"]):
        text = normalize_text(node.get_text(" ", strip=True))
        if not text:
            continue

        if node.name in ("h2", "h3", "h4"):
            if heading_matches_any(text, TACTICAL_HEADING_TOKENS):
                in_tactical_block = True
                continue
            if in_tactical_block and heading_matches_any(text, TACTICAL_STOP_HEADING_TOKENS):
                break
            if in_tactical_block:
                break
            continue

        if in_tactical_block and node.name == "p":
            tactics.append(text)
            if len(tactics) >= max_paragraphs:
                break

    scheme = None
    for paragraph in tactics:
        scheme = extract_scheme(paragraph)
        if scheme:
            break

    return {
        "scheme": scheme,
        "tactics": tactics,
    }


def meta_content(soup, selector):
    tag = soup.select_one(selector)
    return normalize_text(tag.get("content")) if tag and tag.get("content") else None


def extract_published_date(soup):
    value = (
        meta_content(soup, 'meta[property="article:published_time"]')
        or meta_content(soup, 'meta[name="date"]')
    )
    if value:
        match = re.search(r"\d{4}-\d{2}-\d{2}", value)
        if match:
            return match.group(0)
    time_tag = soup.find("time")
    if time_tag:
        raw = time_tag.get("datetime") or time_tag.get_text(" ", strip=True)
        match = re.search(r"\d{4}-\d{2}-\d{2}", raw or "")
        if match:
            return match.group(0)
    return None


def is_formation_image(src, alt):
    key = normalize_country_name(f"{src} {alt}")
    return any(token in key for token in ("forma", "formacion", "alineacion", "xi ideal"))


def extract_article_images(soup, base_url):
    root = article_content_root(soup)
    image_urls = []
    formation_images = []
    seen = set()
    for image in root.find_all("img"):
        src = image.get("src") or image.get("data-src")
        if not src:
            continue
        absolute = urljoin(base_url, src)
        if absolute in seen:
            continue
        seen.add(absolute)
        image_urls.append(absolute)
        if is_formation_image(absolute, image.get("alt") or ""):
            formation_images.append(absolute)
    return image_urls, formation_images


def build_article_entry(team_code, article_html, url):
    """Build one traceable source record from an AlterFutbol article."""
    soup = BeautifulSoup(article_html, "html.parser")
    players = extract_players_from_article(article_html)
    tactical_info = extract_tactical_info_from_article(article_html)
    image_urls, formation_images = extract_article_images(soup, url)
    title = meta_content(soup, 'meta[property="og:title"]')
    if not title:
        heading = soup.find("h1")
        title = normalize_text(heading.get_text(" ", strip=True)) if heading else None

    player_count = len(players)
    if player_count == 26:
        status = "complete"
    elif player_count:
        status = "needs_manual_review"
    else:
        status = "article_only"

    return {
        "team_code": team_code,
        "url": url,
        "title": title,
        "published_date": extract_published_date(soup),
        "featured_image": meta_content(soup, 'meta[property="og:image"]'),
        "image_urls": image_urls,
        "formation_images": formation_images,
        "scheme": tactical_info["scheme"],
        "tactics": tactical_info["tactics"],
        "players": players,
        "player_count": player_count,
        "status": status,
    }


def looks_like_squad_article(title):
    key = normalize_country_name(title)
    has_tournament = "mundial" in key or "world cup" in key
    has_squad_signal = any(token in key for token in ("convocado", "convocados", "lista"))
    return has_tournament and has_squad_signal


def parse_news_listing(news_html, base_url=NEWS_URL):
    soup = BeautifulSoup(news_html, "html.parser")
    candidates = []
    seen = set()
    for anchor in soup.find_all("a", href=True):
        title = normalize_text(anchor.get_text(" ", strip=True))
        if not title or not looks_like_squad_article(title):
            continue
        url = urljoin(base_url, anchor["href"])
        if url in seen:
            continue
        seen.add(url)
        candidates.append({"title": title, "url": url})
    return candidates


def match_team_code(candidate, valid_codes):
    haystack = normalize_country_name(f"{candidate.get('title')} {candidate.get('url')}")
    padded = f" {haystack} "
    for code in valid_codes:
        aliases = sorted(TEAM_ALIASES.get(code, ()), key=len, reverse=True)
        for alias in aliases:
            normalized = normalize_country_name(alias)
            if f" {normalized} " in padded:
                return code
    return None


def build_source_manifest(groups_data, news_pages, fetch_article_html):
    group_by_code = {}
    ordered_codes = []
    for group in groups_data.get("groups", []):
        for code in group.get("teams", []):
            ordered_codes.append(code)
            group_by_code[code] = group.get("id")

    valid_codes = set(ordered_codes)
    candidates = []
    for page in news_pages:
        candidates.extend(parse_news_listing(page))

    article_by_code = {}
    for candidate in candidates:
        code = match_team_code(candidate, valid_codes)
        if code and code not in article_by_code:
            article_by_code[code] = candidate

    teams = []
    for code in ordered_codes:
        candidate = article_by_code.get(code)
        if not candidate:
            teams.append({
                "team_code": code,
                "name": TEAM_NAMES_ES.get(code, code.upper()),
                "group_id": group_by_code.get(code),
                "url": None,
                "title": None,
                "published_date": None,
                "featured_image": None,
                "image_urls": [],
                "formation_images": [],
                "players": [],
                "player_count": 0,
                "status": "missing_article",
            })
            continue

        try:
            article_html = fetch_article_html(candidate["url"])
            entry = build_article_entry(code, article_html, candidate["url"])
        except Exception as exc:
            entry = {
                "team_code": code,
                "url": candidate["url"],
                "title": candidate["title"],
                "published_date": None,
                "featured_image": None,
                "image_urls": [],
                "formation_images": [],
                "players": [],
                "player_count": 0,
                "status": "fetch_error",
                "error": str(exc),
            }
        entry.setdefault("title", candidate["title"])
        entry["name"] = TEAM_NAMES_ES.get(code, code.upper())
        entry["group_id"] = group_by_code.get(code)
        teams.append(entry)

    statuses = {}
    for team in teams:
        statuses[team["status"]] = statuses.get(team["status"], 0) + 1

    return {
        "meta": {
            "source": "AlterFutbol noticias",
            "source_url": NEWS_URL,
            "total_teams": len(teams),
            "statuses": statuses,
            "notes": (
                "Generated only from direct article links found in AlterFutbol "
                "noticias pages. Player rows are kept only when parsed from article text."
            ),
        },
        "teams": teams,
    }


def news_page_url(page):
    if page == 1:
        return NEWS_URL
    return urljoin(NEWS_URL, f"page/{page}/")


def fetch_url(session, url):
    response = session.get(url, timeout=30)
    response.raise_for_status()
    return response.text


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def resolve_output_path(path):
    output = Path(path)
    return output if output.is_absolute() else REPO_ROOT / output


def main():
    parser = argparse.ArgumentParser(description="Scrape AlterFutbol WC 2026 squad sources")
    parser.add_argument("--max-pages", type=int, default=30)
    parser.add_argument("--output", default=str(REPO_ROOT / "data" / "alterfutbol_sources.json"))
    args = parser.parse_args()

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    news_pages = []
    for page in range(1, args.max_pages + 1):
        url = news_page_url(page)
        try:
            news_pages.append(fetch_url(session, url))
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 404:
                break
            raise

    groups_data = load_json(REPO_ROOT / "data" / "groups.json")
    manifest = build_source_manifest(
        groups_data=groups_data,
        news_pages=news_pages,
        fetch_article_html=lambda url: fetch_url(session, url),
    )

    output = resolve_output_path(args.output)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output.relative_to(REPO_ROOT)} with {manifest['meta']['total_teams']} teams")
    print(json.dumps(manifest["meta"]["statuses"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
