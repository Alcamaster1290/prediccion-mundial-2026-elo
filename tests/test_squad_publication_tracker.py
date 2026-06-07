import json
from pathlib import Path


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
    assert "Arabia Saudita</strong></td><td>31 may</td>" in html
    assert "Uruguay</strong></td><td>31 may</td>" in html
    assert "Senegal</strong></td><td>1 jun</td>" in html
