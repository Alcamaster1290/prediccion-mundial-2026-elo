import sys
from pathlib import Path

from bs4 import BeautifulSoup


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
    assert "3er Mundial en casa" in section
    assert "Perfil fuenteado" not in section
    assert '<span class="absence-name">' in section
    assert '<span class="absence-reason">Hirving Lozano quedo fuera de la nomina final.</span>' in section
    assert "XI Probable" in section
    assert "squad-table" in section
    assert "dt_source" not in section


def test_published_absence_cards_use_name_reason_format():
    html = (Path(__file__).resolve().parents[1] / "index.html").read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    missing = []
    for h4 in soup.select("h4"):
        if h4.get_text(" ", strip=True) != "Ausencias notables":
            continue
        card = h4.find_parent(class_="info-card")
        if not card:
            continue
        for index, item in enumerate(card.select(".absence-list li"), start=1):
            if not item.select_one(".absence-name") or not item.select_one(".absence-reason"):
                team = item.find_parent(class_="team-section")
                missing.append(f"{team.get('id') if team else 'unknown'}:{index}")

    assert missing == []
    assert "Dudas y novedades" not in html
    assert "Perfil fuenteado" not in html


def test_generated_team_pills_use_contextual_badges():
    html = (Path(__file__).resolve().parents[1] / "index.html").read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    missing = []
    for code, badge in render_team_sections.TEAM_CONTEXT_BADGES.items():
        section_id = render_team_sections.SECTION_BY_CODE[code]
        section = soup.find(id=section_id)
        if not section:
            missing.append(f"{section_id}:missing-section")
            continue
        pills = [pill.get_text(" ", strip=True) for pill in section.select(".team-pills .team-pill")]
        if badge not in pills:
            missing.append(f"{section_id}:{badge}")

    assert missing == []
