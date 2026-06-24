import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_prediction_cards_keep_editorial_outlook_and_numeric_model_outputs():
    premium_js = read("js/premium.js")
    body = re.search(
        r"function renderPredictionCard\(p\) \{(.*?)\n  function renderGhostCards",
        premium_js,
        flags=re.S,
    ).group(1)

    assert "renderEditorialOutlook(p, result)" in body
    assert "renderProbabilityBars(p, result)" in body
    assert "renderScorelines(p, result)" in body
    assert body.index("renderEditorialOutlook(p, result)") < body.index("renderProbabilityBars(p, result)")
    assert body.index("renderProbabilityBars(p, result)") < body.index("renderScorelines(p, result)")
    assert "prono-final-badge" not in body


def test_scoreline_renderer_shows_top_ten_and_marks_final_result():
    premium_js = read("js/premium.js")
    body = re.search(
        r"function renderScorelines\(p, result\) \{(.*?)\n  function renderEditorialOutlook",
        premium_js,
        flags=re.S,
    ).group(1)

    assert ".slice(0, 10)" in body
    assert "top10Hit" in body
    assert "prono-score-hit" in body
    assert "prono-score-check" in body
    assert "prono-score-final-miss" in body
    assert "prono-scores-final-note" not in body
    assert "Final" in body


def test_prediction_copy_promises_editorial_keys_percentages_and_scorelines():
    premium_js = read("js/premium.js")

    assert "jugador diferencial" in premium_js.lower()
    assert "Lectura editorial" in premium_js
    assert "porcentajes de victoria" in premium_js.lower()
    assert "10 resultados" in premium_js.lower()


def test_prediction_team_names_link_to_country_sections_responsively():
    premium_js = read("js/premium.js")
    index_html = read("index.html")
    body = re.search(
        r"function renderPredictionCard\(p\) \{(.*?)\n  function renderGhostCards",
        premium_js,
        flags=re.S,
    ).group(1)

    assert "TEAM_SECTION_BY_CODE" in premium_js
    assert "function renderTeamLink" in premium_js
    assert "href=\"#" in premium_js
    assert "renderTeamLink(codeA, nameA" in body
    assert "renderTeamLink(codeB, nameB" in body
    assert ".prono-team-link" in index_html
    assert "text-overflow: ellipsis" in index_html
