import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def read_index():
    return (REPO_ROOT / "index.html").read_text(encoding="utf-8")


def css_block(selector, html):
    pattern = re.compile(re.escape(selector) + r"\s*\{([^}]*)\}", re.S)
    match = pattern.search(html)
    assert match, f"CSS block not found: {selector}"
    return match.group(1)


def test_mobile_nav_stays_in_one_horizontal_row():
    html = read_index()
    mobile = html[html.index("MOBILE") :]

    nav_block = css_block("nav", mobile)
    assert "flex-wrap: nowrap" in nav_block
    assert "overflow-x: auto" in nav_block

    item_block = css_block("nav a, .grupos-nav-btn", mobile)
    assert "flex: 0 0 auto" in item_block


def test_join_and_prediction_paywalls_are_compact():
    html = read_index()

    assert "max-width: 360px" in css_block(".auth-modal", html)
    assert "max-width: 360px" in css_block(".pred-payment", html)
    assert "width: 150px" in css_block(".pred-qr-img", html)
    assert "max-width: 360px" in css_block(".prono-payment", html)
    assert "width: 150px" in css_block(".prono-qr-img", html)
