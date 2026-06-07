#!/usr/bin/env python3
"""Refresh data/club_elo.json from World Club Ratings' full Elo table."""

import argparse
import html as html_lib
import json
import re
import ssl
from datetime import date
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_URL = "https://worldclubratings.com/rankings/elo_men/index.html"
RANK_TABLE_RE = re.compile(
    r"<script\b(?=[^>]*\bdata-for=[\"']rankdt[\"'])(?=[^>]*\btype=[\"']application/json[\"'])[^>]*>"
    r"(?P<payload>.*?)"
    r"</script>",
    re.IGNORECASE | re.DOTALL,
)


def parse_int(value):
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    text = re.sub(r"[^\d.-]+", "", str(value))
    if not text:
        raise ValueError(f"Expected numeric value, got {value!r}")
    return int(float(text))


def can_parse_int(value):
    try:
        parse_int(value)
    except ValueError:
        return False
    return True


def looks_like_columnar_table(table_data):
    if not (
        len(table_data) >= 5
        and all(isinstance(column, list) for column in table_data[:5])
    ):
        return False

    ranks = table_data[0]
    clubs = table_data[2]
    countries = table_data[3]
    elos = table_data[4]
    if not ranks or not clubs or not countries or not elos:
        return False
    if len({len(ranks), len(clubs), len(countries), len(elos)}) != 1:
        return False

    sample_size = min(5, len(ranks))
    return (
        all(can_parse_int(value) for value in ranks[:sample_size])
        and all(can_parse_int(value) for value in elos[:sample_size])
        and not can_parse_int(clubs[0])
    )


def parse_worldclubratings_html(html):
    match = RANK_TABLE_RE.search(html)
    if not match:
        raise ValueError("Could not find World Club Ratings rankdt JSON payload")

    payload = match.group("payload").strip()
    data = json.loads(payload)
    table_data = data.get("x", {}).get("data", [])
    clubs = []

    if looks_like_columnar_table(table_data):
        for rank, club, country, elo in zip(table_data[0], table_data[2], table_data[3], table_data[4]):
            club_name = html_lib.unescape(str(club)).strip()
            if not club_name:
                continue
            clubs.append(
                {
                    "rank": parse_int(rank),
                    "club": club_name,
                    "country": html_lib.unescape(str(country)).strip(),
                    "elo": parse_int(elo),
                }
            )
        return clubs

    rows = table_data
    for row in rows:
        if len(row) < 5:
            continue
        club_name = html_lib.unescape(str(row[2])).strip()
        if not club_name:
            continue
        clubs.append(
            {
                "rank": parse_int(row[0]),
                "club": club_name,
                "country": html_lib.unescape(str(row[3])).strip(),
                "elo": parse_int(row[4]),
            }
        )
    return clubs


def fetch_html(url, timeout=30):
    request = Request(
        url,
        headers={"User-Agent": "mundial-2026-elo-refresh/1.0"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read().decode(response.headers.get_content_charset() or "utf-8")
    except URLError:
        context = ssl._create_unverified_context()
        with urlopen(request, timeout=timeout, context=context) as response:
            return response.read().decode(response.headers.get_content_charset() or "utf-8")


def build_payload(clubs, source_url, snapshot):
    return {
        "meta": {
            "source": "worldclubratings.com",
            "source_url": source_url,
            "snapshot": snapshot,
            "total": len(clubs),
        },
        "clubs": clubs,
    }


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser(description="Refresh the full club Elo table")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--output", default=REPO_ROOT / "data" / "club_elo.json", type=Path)
    parser.add_argument("--snapshot", default=date.today().isoformat())
    args = parser.parse_args()

    html = fetch_html(args.url)
    clubs = parse_worldclubratings_html(html)
    payload = build_payload(clubs, args.url, args.snapshot)
    write_json(args.output, payload)
    print(f"Wrote {len(clubs)} clubs -> {args.output}")


if __name__ == "__main__":
    main()
