from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_group_match_predictions_are_embedded_in_predictions_flow():
    pred_js = read("js/predicciones.js")
    premium_js = read("js/premium.js")
    index_html = read("index.html")

    assert "renderEmbeddedPronosticos" in pred_js
    assert "loadEmbeddedPronosticos" in pred_js
    assert "renderActiveContent" in premium_js
    assert "pred-pronosticos-block" in premium_js

    group_tables = pred_js.index("html += renderGroupProbabilityTables(data);")
    embedded_pronosticos = pred_js.index("html += renderEmbeddedPronosticos")
    classification_table = pred_js.index("Probabilidad de Clasificaci")

    assert group_tables < embedded_pronosticos < classification_table

    assert '<section id="pronosticos"' not in index_html
    assert "document.getElementById('predicciones')" in index_html
