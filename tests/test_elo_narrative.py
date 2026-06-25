# -*- coding: utf-8 -*-
"""Tests de la narrativa v2 (scripts/elo_narrative.py) y su integración en el
seed de predicciones. Cubre las funciones puras (interpretación ELO, capa de
banquillo, pulido de texto) y propiedades del seed completo: unicidad,
longitud, ausencia de plantilla y de caracteres vetados."""
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import elo_narrative as en  # noqa: E402
import generate_predictions as gp  # noqa: E402
from export_to_supabase import parse_predictions_seed  # noqa: E402

BANNED_CHARS = (":", ";", "—")


# ── Fixtures ────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def seed_rows(tmp_path_factory):
    """Genera el seed completo en un directorio temporal y devuelve las filas
    parseadas (mismo patrón que test_generate_predictions_calendar)."""
    tmp_path = tmp_path_factory.mktemp("seed")
    strengths_path = tmp_path / "team_strength_snapshots.json"
    output_sql = tmp_path / "predictions_seed.sql"
    subprocess.run(
        [sys.executable, "scripts/build_team_strength.py", "--output", str(strengths_path)],
        cwd=REPO_ROOT, check=True, text=True, capture_output=True,
    )
    orig_strengths, orig_output = gp.STRENGTHS_FILE, gp.OUTPUT_SQL
    gp.STRENGTHS_FILE, gp.OUTPUT_SQL = strengths_path, output_sql
    try:
        gp.main()
    finally:
        gp.STRENGTHS_FILE, gp.OUTPUT_SQL = orig_strengths, orig_output
    return parse_predictions_seed(output_sql.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def teams_data():
    return json.loads((REPO_ROOT / "data" / "teams.json").read_text(encoding="utf-8"))


def _supersub_profile(delta=80.0):
    """bench_profile mínimo con un supersub en la rama de salto fuerte."""
    return {
        "team_code": "tst",
        "name": "Test",
        "supersub": {
            "name": "Jugador Prueba", "club": "Club X", "line": "attack",
            "elo": 1700.0, "delta": delta, "line_avg": 1600.0, "new_avg": 1660.0,
        },
        "bench_size": 7, "bench_top5_avg": 1500.0,
    }


# ── Funciones puras ──────────────────────────────────────────────────────────────

def test_expected_duel_pct_known_values():
    assert en.expected_duel_pct(0) == pytest.approx(50.0)
    assert en.expected_duel_pct(400) == pytest.approx(90.909, abs=0.01)
    assert en.expected_duel_pct(-400) == pytest.approx(9.091, abs=0.01)
    # monotonía creciente
    seq = [en.expected_duel_pct(g) for g in (-200, -50, 0, 50, 200)]
    assert seq == sorted(seq)


def test_gap_phrase_boundaries():
    assert en.gap_phrase(24) == "un cruce prácticamente parejo en roce de club"
    assert en.gap_phrase(25) == "una ventaja ligera"
    assert en.gap_phrase(59) == "una ventaja ligera"
    assert en.gap_phrase(60) == "una ventaja clara"
    assert en.gap_phrase(119) == "una ventaja clara"
    assert en.gap_phrase(120) == "un dominio esperado sobre el papel"
    assert en.gap_phrase(199) == "un dominio esperado sobre el papel"
    assert en.gap_phrase(200) == "una diferencia de categoría"


def test_polish_contractions_and_periods():
    assert en.polish("frente a el ataque rival") == "frente al ataque rival"
    assert en.polish("subir el nivel de el arquero") == "subir el nivel del arquero"
    assert en.polish("a favor de EE.UU..") == "a favor de EE.UU."
    # no toca nombres con punto interno ni contracciones ya correctas
    assert en.polish("EE.UU. enfrenta al ataque") == "EE.UU. enfrenta al ataque"
    # idempotente
    once = en.polish("de el mediocampo de el rival.")
    assert en.polish(once) == once == "del mediocampo del rival."


def test_pick_is_deterministic():
    opts = ["a", "b", "c", "d"]
    assert en.pick("m1", "salt", opts) == en.pick("m1", "salt", opts)
    # distinto match_id puede cambiar la variante; la función no usa RNG
    assert all(en.pick("m1", "s", opts) == en.pick("m1", "s", opts) for _ in range(5))


def test_bench_sentence_avoid_index_forces_distinct_variant():
    prof = _supersub_profile()
    text, idx = en.bench_sentence("grp-x", "Equipo", prof)
    assert idx is not None
    # forzar evitar su propio índice produce una variante distinta
    other_text, other_idx = en.bench_sentence("grp-x", "Equipo", prof, avoid_index=idx)
    assert other_idx != idx
    assert other_text != text


def test_bench_sentence_no_supersub_returns_fixed_note():
    text, idx = en.bench_sentence("grp-x", "Equipo", {"supersub": None})
    assert idx is None
    assert "no ofrece un salto" in text


# ── Capa de banquillo sobre datos reales ─────────────────────────────────────────

def test_build_bench_profiles_supersub_belongs_to_team_and_line(teams_data):
    profiles = en.build_bench_profiles(teams_data)
    assert profiles, "debe construir al menos un perfil de banca"
    by_id = {t["id"]: t for t in teams_data["teams"]}
    from xi_matchups import normalize_line
    for team_id, prof in profiles.items():
        sub = prof.get("supersub")
        if not sub:
            continue
        # el supersub es un suplente real del equipo, en la línea declarada
        bench = [
            p for p in by_id[team_id].get("players", [])
            if not p.get("titular") and p.get("elo") is not None
        ]
        match = next((p for p in bench if (p.get("name") or "Suplente") == sub["name"]), None)
        assert match is not None, f"{team_id}: supersub {sub['name']} no está en su banca"
        assert normalize_line(match.get("pos")) == sub["line"]


def test_build_bench_profiles_prioritizes_attacking_or_midfield_supersub():
    teams_data = {
        "teams": [
            {
                "id": "tst",
                "name": "Equipo Prueba",
                "players": [
                    {"name": "Arquero Titular", "pos": "GK", "elo": 1500, "titular": True},
                    {"name": "Defensa Titular", "pos": "DEF", "elo": 1500, "titular": True},
                    {"name": "Medio Titular", "pos": "MED", "elo": 1500, "titular": True},
                    {"name": "Delantero Titular", "pos": "DEL", "elo": 1500, "titular": True},
                    {"name": "Central Potente", "pos": "DEF", "elo": 1730, "titular": False, "club": "Club Fuerte"},
                    {"name": "Interior Cambio", "pos": "MED", "elo": 1600, "titular": False, "club": "Club Medio"},
                    {"name": "Extremo Cambio", "pos": "DEL", "elo": 1580, "titular": False, "club": "Club Ataque"},
                ],
            }
        ]
    }

    profile = en.build_bench_profiles(teams_data)["tst"]

    assert profile["supersub"]["name"] == "Interior Cambio"
    assert profile["supersub"]["line"] == "midfield"


# ── Propiedades del seed completo ────────────────────────────────────────────────

def test_seed_has_72_rows(seed_rows):
    assert len(seed_rows) == 72


def test_all_explanations_unique(seed_rows):
    explanations = [r["explanation"] for r in seed_rows]
    assert len(set(explanations)) == len(explanations)


def test_explanation_length_within_relaxed_bounds(seed_rows):
    for r in seed_rows:
        n = len(r["explanation"])
        assert 600 <= n <= 1400, f"{r['match_id']} longitud {n} fuera de rango"


def test_no_banned_chars_or_contraction_bugs(seed_rows):
    for r in seed_rows:
        for col in ("explanation", "team_a_context", "team_b_context"):
            text = r.get(col) or ""
            for ch in BANNED_CHARS:
                assert ch not in text, f"{r['match_id']} {col}: caracter vetado {ch!r}"
            assert " a el " not in text, f"{r['match_id']} {col}: contracción 'a el'"
            assert " de el " not in text, f"{r['match_id']} {col}: contracción 'de el'"
            assert ".." not in text, f"{r['match_id']} {col}: doble punto"


def test_not_a_fixed_template(seed_rows):
    """Anti-plantilla: el primer párrafo (lectura del cruce), con los números
    enmascarados, debe tener varias formas distintas. Si la narrativa regresara
    a una plantilla fija, todos los esqueletos colapsarían a uno solo."""
    skeletons = set()
    openings = set()
    for r in seed_rows:
        first_para = r["explanation"].split("\n\n")[0]
        masked = re.sub(r"\d+", "#", first_para)
        skeletons.add(masked)
        openings.add(masked.split(". ")[0])
    assert len(skeletons) >= 8, f"muy pocos esqueletos distintos: {len(skeletons)}"
    assert len(openings) >= 4, f"muy pocas aperturas distintas: {len(openings)}"


def test_seed_limits_repeated_editorial_transitions(seed_rows):
    joined = "\n".join(r["explanation"] for r in seed_rows)

    assert joined.count("El cruce que más desequilibra") <= 30
    assert joined.count("El partido también puede decidirse desde los cambios") <= 30


def test_seed_revulsives_do_not_focus_on_goalkeepers_or_defenders(seed_rows):
    forbidden = [
        "subir el nivel del arquero",
        "refrescar el arquero",
        "el arquero puede jugar",
        "subir el nivel de la defensa",
        "refrescar la defensa",
        "la defensa puede jugar",
    ]

    for row in seed_rows:
        text = " ".join(
            row.get(col) or ""
            for col in ("explanation", "team_a_context", "team_b_context")
        )
        lowered = text.lower()
        for phrase in forbidden:
            assert phrase not in lowered, f"{row['match_id']} usa revulsivo defensivo: {phrase}"


def test_seed_avoids_malformed_editorial_phrases(seed_rows):
    forbidden = [
        ",.",
        "Su el ",
        "Su la ",
        "activa el arquero",
        "protege el arquero",
    ]

    for row in seed_rows:
        text = " ".join(
            row.get(col) or ""
            for col in ("explanation", "team_a_context", "team_b_context")
        )
        for phrase in forbidden:
            assert phrase not in text, f"{row['match_id']} contiene frase editorial débil: {phrase}"


def test_seed_preserves_contextual_memory_for_specific_match(seed_rows):
    row = next(r for r in seed_rows if r["match_id"] == "grp-f-j1-ned-jpn")

    assert "Qatar 2022" in row["explanation"]
    assert "Alemania" in row["explanation"]
    assert "España" in row["explanation"]


def test_probability_paragraph_present(seed_rows):
    for r in seed_rows:
        assert "modelo ELO" in r["explanation"]
