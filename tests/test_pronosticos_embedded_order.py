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

    # Las tablas de probabilidad por grupo van embebidas dentro de cada bloque
    # de Pronósticos (renderGroupExtra); la grilla separada queda solo como
    # fallback cuando no hay pronósticos publicados.
    assert "renderGroupExtra" in pred_js
    assert "renderGroupExtra" in premium_js
    assert "renderGroupProbabilityTable(" in pred_js
    assert "html += renderGroupProbabilityTables(data);" in pred_js  # fallback

    embedded_pronosticos = pred_js.index("html += renderEmbeddedPronosticos(pronosticos, data);")
    classification_table = pred_js.index("Probabilidad de Clasificaci")

    assert embedded_pronosticos < classification_table

    assert '<section id="pronosticos"' not in index_html
    assert "document.getElementById('predicciones')" in index_html
