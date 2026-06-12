from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_user_visible_copy_does_not_brand_access_as_premium():
    public_copy = "\n".join(
        read(path)
        for path in [
            "index.html",
            "auth/callback.html",
            "js/premium.js",
            "js/predicciones.js",
            "admin/premium-codes.html",
        ]
    )

    forbidden_phrases = [
        ">Premium<",
        "★ Premium",
        "solo Premium",
        "usuarios <strong style=\"color:var(--gold)\">Premium</strong>",
        "Activa tu acceso Premium",
        "Acceso Premium Activo",
        "Acceso Premium Activado",
        "Premium codes",
        "premium codes",
        " - premium",
    ]

    for phrase in forbidden_phrases:
        assert phrase not in public_copy


def test_access_layers_use_clear_non_premium_language():
    index_html = read("index.html")
    callback_html = read("auth/callback.html")
    prono_js = read("js/premium.js")
    pred_js = read("js/predicciones.js")
    admin_html = read("admin/premium-codes.html")

    assert ">Completo</span>" in index_html
    assert "Win% con acceso completo" in index_html
    assert "se desbloquea con acceso completo" in index_html
    assert "Completa tu acceso" in callback_html
    assert "Todo desbloqueado" in callback_html
    assert "Crear cuenta" in prono_js
    assert "Crear cuenta" in pred_js
    assert "Todo desbloqueado" in prono_js
    assert "Todo desbloqueado" in pred_js
    assert "Codigos de acceso" in admin_html


def test_prediction_nav_lock_is_stateful():
    index_html = read("index.html")
    auth_js = read("js/auth.js")

    assert "Predicciones &#x1F512;" not in index_html
    assert 'id="nav-pred-lock"' in index_html
    assert "navPredLock.style.display = hasFullAccess ? 'none' : ''" in auth_js


def test_code_redemption_does_not_render_backend_premium_wording():
    redemption_files = [
        read("auth/callback.html"),
        read("js/premium.js"),
        read("js/predicciones.js"),
    ]

    for source in redemption_files:
        assert "errEl.textContent = result.message" not in source
        assert "Todo desbloqueado. Ya puedes ver todas las predicciones." in source


def test_premium_local_mocks_are_dev_only():
    supa_data = read("js/supa-data.js")
    premium_js = read("js/premium.js")
    auth_js = read("js/auth.js")

    assert "function isLocalDev()" in supa_data
    assert "if (!localUrl || !isLocalDev()) return null;" in supa_data
    assert "isLocalDev() ? await loadMockPredictions() : null" in premium_js
    assert "window.__supabaseConfigError = true" in auth_js
