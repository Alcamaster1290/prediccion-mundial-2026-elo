import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_prediction_cards_use_editorial_outlook_instead_of_numeric_blocks():
    premium_js = read("js/premium.js")
    body = re.search(
        r"function renderPredictionCard\(p\) \{(.*?)\n  function renderGhostCards",
        premium_js,
        flags=re.S,
    ).group(1)

    assert "renderEditorialOutlook(p, result)" in body
    assert "renderScorelines(p, result)" not in body
    assert "prono-probs" not in body
    assert "prono-prob-pct" not in body


def test_prediction_copy_promises_editorial_keys_and_player_differentials():
    premium_js = read("js/premium.js")

    assert "jugador diferencial" in premium_js.lower()
    assert "Lectura editorial" in premium_js
    assert "Probabilidad de victoria / empate / derrota" not in premium_js
    assert "Marcadores exactos más probables" not in premium_js
