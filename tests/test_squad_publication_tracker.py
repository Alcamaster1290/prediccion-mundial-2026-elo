import json
from pathlib import Path

from bs4 import BeautifulSoup


REPO_ROOT = Path(__file__).resolve().parents[1]
TRACKER_PATH = REPO_ROOT / "data" / "squad_publication_tracker.json"
INDEX_PATH = REPO_ROOT / "index.html"


EXPECTED_DATES = {
    "usa": "2026-05-26",
    "mar": "2026-05-26",
    "pan": "2026-05-26",
    "zaf": "2026-05-27",
    "ned": "2026-05-27",
    "arg": "2026-05-28",
    "can": "2026-05-29",
    "egy": "2026-05-29",
    "alg": "2026-05-31",
    "cze": "2026-05-31",
    "ksa": "2026-05-31",
    "ecu": "2026-05-31",
    "mex": "2026-05-31",
    "ury": "2026-05-31",
    "irn": "2026-06-01",
    "irq": "2026-06-01",
    "aus": "2026-06-01",
    "qat": "2026-06-01",
    "cro": "2026-06-01",
    "gha": "2026-06-01",
    "pry": "2026-06-01",
    "sen": "2026-06-01",
}


def test_squad_publication_tracker_matches_manual_dates():
    tracker = json.loads(TRACKER_PATH.read_text(encoding="utf-8"))
    rows = {row["team_code"]: row for row in tracker["teams"]}

    assert tracker["meta"]["total_published"] == 22
    assert set(rows) == set(EXPECTED_DATES)
    assert {code: rows[code]["published_date"] for code in rows} == EXPECTED_DATES
    assert rows["ksa"]["name"] == "Arabia Saudita"
    assert rows["ury"]["name"] == "Uruguay"


def test_index_tracker_renders_publication_dates():
    html = INDEX_PATH.read_text(encoding="utf-8")

    assert "22 selecciones con fecha de convocatoria registrada" in html
    assert "26 pendientes de fecha registrada" in html
    assert "<!-- Fechas de publicación de convocatorias -->" not in html
    assert "Cronología de anuncios" in html
    assert "31 May</span>" in html
    assert "Arabia Saudita" in html
    assert "Uruguay" in html
    assert "Senegal" in html


def test_index_tracker_uses_current_profile_totals():
    html = INDEX_PATH.read_text(encoding="utf-8")

    assert "46 perfiles publicados" in html
    assert "2 pendientes de perfil fuenteado" in html
    assert "24 con análisis completo" not in html


def test_rendered_starters_have_club_elo_in_team_tables():
    soup = BeautifulSoup(INDEX_PATH.read_text(encoding="utf-8"), "html.parser")

    missing = []
    for section in soup.select(".team-section"):
        section_id = section.get("id")
        for row in section.select(".squad-table tbody tr"):
            if not row.select_one(".titl-yes"):
                continue
            elo = row.select_one(".elo-cell")
            name = row.select_one(".player-name")
            if not elo or "elo-nd" in (elo.get("class") or []) or elo.get_text(strip=True) == "N/D":
                missing.append(f"{section_id}:{name.get_text(strip=True) if name else 'unknown'}")

    assert missing == []


def test_tracker_team_table_lists_all_teams_with_current_status():
    soup = BeautifulSoup(INDEX_PATH.read_text(encoding="utf-8"), "html.parser")
    tracker = soup.find(id="tracker")

    rows = tracker.select(".tracker-squad tbody tr")
    tracker_text = tracker.get_text(" ", strip=True)

    assert len(rows) == 48
    assert "Arabia Saudita" in tracker_text
    assert "31 May" in tracker_text
    assert "Jordania" in tracker_text
    assert "Pendiente perfil" in tracker_text
