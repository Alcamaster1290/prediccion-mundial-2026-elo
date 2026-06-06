import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import render_team_sections  # noqa: E402


def test_absence_extractor_prefers_signal_sentence_and_rejects_historical_noise():
    html = """
    <article>
      <h2>Ausencias notables</h2>
      <p>Contexto general del equipo sin valor de baja. La baja mas dolorosa fue por lesion: Leonardo Campana quedo afuera.</p>
      <p>En octubre de 2024, Ghana quedo afuera del torneo continental por primera vez en veinte anos.</p>
    </article>
    """

    notes = render_team_sections.extract_absence_notes_from_html(html)

    assert notes == ["La baja mas dolorosa fue por lesion: Leonardo Campana quedo afuera."]


def test_generated_team_section_hides_dt_source_and_contains_required_blocks():
    section = render_team_sections.render_team_section(
        {
            "id": "mex",
            "name": "Mexico",
            "group": "A",
            "dt": "Javier Aguirre",
            "dt_source": "xi_image",
            "scheme": "4-3-3",
            "xi_image": "assets/xi/mex-xi.png",
            "source_url": "https://example.test/mexico",
            "tactics": ["Presiona alto y ataca por bandas."],
            "absences": ["Hirving Lozano quedo fuera de la nomina final."],
            "players": [
                {
                    "pos": "FW",
                    "name": f"Player {index}",
                    "age": 25,
                    "club": "Club",
                    "country": "Pais",
                    "elo": 1500,
                    "titular": index <= 11,
                }
                for index in range(1, 27)
            ],
        }
    )

    assert 'id="mexico"' in section
    assert "Sistema de juego" in section
    assert "Ausencias notables" in section
    assert "XI Probable" in section
    assert "squad-table" in section
    assert "dt_source" not in section
