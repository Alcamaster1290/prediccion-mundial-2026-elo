import subprocess
import sys
from pathlib import Path

from scripts.enrich_alterfutbol_xi_assets import enrich_teams_with_xi_assets


REPO_ROOT = Path(__file__).resolve().parents[1]


TACTICAL_HTML = """
<article>
  <h2>El esquema tactico y el XI ideal</h2>
  <p>El tecnico se inclino por el 4-3-3 para presionar alto.</p>
  <p>El equipo junta extremos abiertos y laterales profundos.</p>
  <h2>Lista completa</h2>
  <p>Arqueros:</p>
</article>
"""


def test_enrich_teams_downloads_missing_xi_and_adds_tactical_fields(tmp_path):
    teams_data = {
        "teams": [
            {
                "id": "mex",
                "name": "Mexico",
                "group": "A",
                "dt": "",
                "analyzed": False,
                "source_status": "squad_only",
                "players": [{"name": "Jugador", "titular": False}],
            }
        ]
    }
    sources = {
        "teams": [
            {
                "team_code": "mex",
                "url": "https://example.test/mexico/",
                "formation_images": ["https://example.test/mexico-xi.png"],
            }
        ]
    }

    enriched, report = enrich_teams_with_xi_assets(
        teams_data=teams_data,
        source_manifest=sources,
        xi_dir=tmp_path,
        fetch_article_html=lambda url: TACTICAL_HTML,
        download_image=lambda url: b"fake-png",
    )

    team = enriched["teams"][0]
    assert report["downloaded"] == ["mex"]
    assert (tmp_path / "mex-xi.png").read_bytes() == b"fake-png"
    assert team["scheme"] == "4-3-3"
    assert team["tactics"] == [
        "El tecnico se inclino por el 4-3-3 para presionar alto.",
        "El equipo junta extremos abiertos y laterales profundos.",
    ]
    assert team["xi_image"] == "assets/xi/mex-xi.png"
    assert team["xi_source_url"] == "https://example.test/mexico-xi.png"
    assert team["source_tactics_url"] == "https://example.test/mexico/"
    assert team["players"][0]["titular"] is False


def test_enrich_teams_preserves_existing_xi_without_overwrite(tmp_path):
    existing = tmp_path / "mar-xi.png"
    existing.write_bytes(b"existing")
    teams_data = {
        "teams": [
            {
                "id": "mar",
                "name": "Marruecos",
                "group": "C",
                "dt": "",
                "analyzed": False,
                "source_status": "squad_only",
                "players": [],
            }
        ]
    }
    sources = {
        "teams": [
            {
                "team_code": "mar",
                "url": "https://example.test/marruecos/",
                "formation_images": ["https://example.test/mar-xi.png"],
            }
        ]
    }

    enriched, report = enrich_teams_with_xi_assets(
        teams_data=teams_data,
        source_manifest=sources,
        xi_dir=tmp_path,
        fetch_article_html=lambda url: TACTICAL_HTML,
        download_image=lambda url: b"new",
        overwrite=False,
    )

    team = enriched["teams"][0]
    assert report["preserved"] == ["mar"]
    assert report["downloaded"] == []
    assert existing.read_bytes() == b"existing"
    assert team["xi_image"] == "assets/xi/mar-xi.png"
    assert team["scheme"] == "4-3-3"


def test_enrich_cli_can_run_as_script():
    result = subprocess.run(
        [sys.executable, "scripts/enrich_alterfutbol_xi_assets.py", "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Enrich squad-only teams" in result.stdout
