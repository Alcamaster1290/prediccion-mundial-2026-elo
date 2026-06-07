import json
import re
from html.parser import HTMLParser
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class SectionParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.team_sections = []

    def handle_starttag(self, tag, attrs):
        if tag != "div":
            return
        attr = dict(attrs)
        classes = set((attr.get("class") or "").split())
        if "team-section" in classes and attr.get("id"):
            self.team_sections.append(attr["id"])


def read_team_codes(index_html):
    match = re.search(r"var TEAM_CODES = \{(.*?)\};", index_html, re.S)
    assert match, "TEAM_CODES block missing"
    return dict(re.findall(r"'([^']+)'\s*:\s*'([^']+)'", match.group(1)))


def test_every_team_section_has_knockout_route_mapping():
    index_html = (REPO_ROOT / "index.html").read_text(encoding="utf-8")
    groups = json.loads((REPO_ROOT / "data" / "groups.json").read_text(encoding="utf-8"))
    all_team_codes = {code for group in groups["groups"] for code in group["teams"]}

    parser = SectionParser()
    parser.feed(index_html)
    team_codes = read_team_codes(index_html)

    missing = sorted(set(parser.team_sections) - set(team_codes))
    assert missing == []

    unknown_codes = sorted(set(team_codes.values()) - all_team_codes)
    assert unknown_codes == []


def test_best_third_slot_parser_keeps_every_group_option():
    index_html = (REPO_ROOT / "index.html").read_text(encoding="utf-8")

    assert "var third = clean.match(/^3[^A-L]*([A-L](?:\\/[A-L])*)$/);" in index_html
    assert "var third = clean.match(/^3\\D+([A-L](?:\\/[A-L])*)$/);" not in index_html

    third_labels = re.findall(r"(?:homeLabel|awayLabel):'([^']*3\.[^']*)'", index_html)
    parsed_groups = set()
    for label in third_labels:
        clean = label.replace("Grupo ", "").replace("Ã‚", "")
        match = re.match(r"^3[^A-L]*([A-L](?:/[A-L])*)$", clean)
        assert match, label
        parsed_groups.update(match.group(1).split("/"))

    assert parsed_groups == set("ABCDEFGHIJKL")
