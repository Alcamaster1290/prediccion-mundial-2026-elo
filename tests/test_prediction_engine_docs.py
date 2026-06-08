from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_prediction_engine_docs_match_current_weight_schema():
    doc = read("docs/prediction-engine.md")
    readme = read("README.md")
    combined = doc + "\n" + readme

    assert "score = elo_intl + (xi_blend - avg_xi_blend) * club_adj_weight" in doc
    assert "xi_matchup_weight" in combined
    assert "base_goals_per_team" in combined
    assert "elo_scale" in combined
    assert "elo_intl_weight = 0.65" not in combined
    assert "xi_club_blend_weight = 0.35" not in combined
    assert "model_weights sum to 1.0" not in combined


def test_prediction_engine_docs_cover_supabase_public_and_premium_boundary():
    doc = read("docs/prediction-engine.md")

    assert "05_prediction_engine_schema.sql` creates a public-readable baseline" in doc
    assert "07_prediction_engine_rls_hardening.sql" in doc
    assert "08_security_advisors_hardening.sql" in doc
    assert "Public:" in doc
    assert "Premium:" in doc
