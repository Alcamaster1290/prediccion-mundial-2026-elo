#!/usr/bin/env python3
"""Render source-backed team sections into index.html.

The static page keeps editorial team sections in HTML. This script adds the
source-backed AlterFutbol teams that already have complete squad, XI and
tactical data in data/teams.json.
"""

import argparse
import html
import json
import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup

try:
    from scripts.scrape_alterfutbol_news import (
        USER_AGENT,
        article_content_root,
        normalize_country_name,
        normalize_text,
    )
except ModuleNotFoundError:
    from scrape_alterfutbol_news import (
        USER_AGENT,
        article_content_root,
        normalize_country_name,
        normalize_text,
    )


REPO_ROOT = Path(__file__).resolve().parents[1]

SECTION_BY_CODE = {
    "mex": "mexico",
    "zaf": "sudafrica",
    "kor": "corea",
    "cze": "chequia",
    "can": "canada",
    "bih": "bosnia",
    "qat": "qatar",
    "sui": "suiza",
    "bra": "brasil",
    "mar": "marruecos",
    "hti": "haiti",
    "sco": "escocia",
    "ger": "alemania",
    "cuw": "curazao",
    "civ": "costa-marfil",
    "ecu": "ecuador",
    "ned": "paises-bajos",
    "jpn": "japon",
    "swe": "suecia",
    "tun": "tunez",
    "bel": "belgica",
    "egy": "egipto",
    "irn": "iran",
    "nzl": "nueva-zelanda",
    "esp": "espana",
    "cpv": "cabo-verde",
    "ksa": "arabia-saudita",
    "ury": "uruguay",
    "fra": "francia",
    "sen": "senegal",
    "irq": "irak",
    "nor": "noruega",
    "arg": "argentina",
    "alg": "argelia",
    "aut": "austria",
    "jor": "jordania",
    "por": "portugal",
    "cod": "rd-congo",
    "uzb": "uzbekistan",
    "col": "colombia",
    "eng": "inglaterra",
    "cro": "croacia",
    "gha": "ghana",
    "pan": "panama",
    "usa": "estados-unidos",
    "pry": "paraguay",
    "aus": "australia",
    "tur": "turquia",
}

HOSTS = {"mex", "can", "usa"}

TEAM_DISPLAY_NAMES = {
    "mex": "México",
    "zaf": "Sudáfrica",
    "kor": "Corea del Sur",
    "cze": "Chequia",
    "can": "Canadá",
    "bih": "Bosnia y Herzegovina",
    "qat": "Qatar",
    "sui": "Suiza",
    "bra": "Brasil",
    "mar": "Marruecos",
    "hti": "Haití",
    "sco": "Escocia",
    "ger": "Alemania",
    "cuw": "Curazao",
    "civ": "Costa de Marfil",
    "ecu": "Ecuador",
    "ned": "Países Bajos",
    "jpn": "Japón",
    "swe": "Suecia",
    "tun": "Túnez",
    "bel": "Bélgica",
    "egy": "Egipto",
    "irn": "Irán",
    "nzl": "Nueva Zelanda",
    "esp": "España",
    "cpv": "Cabo Verde",
    "ksa": "Arabia Saudita",
    "ury": "Uruguay",
    "fra": "Francia",
    "sen": "Senegal",
    "irq": "Irak",
    "nor": "Noruega",
    "arg": "Argentina",
    "alg": "Argelia",
    "aut": "Austria",
    "jor": "Jordania",
    "por": "Portugal",
    "cod": "RD Congo",
    "uzb": "Uzbekistán",
    "col": "Colombia",
    "eng": "Inglaterra",
    "cro": "Croacia",
    "gha": "Ghana",
    "pan": "Panamá",
    "usa": "EE.UU.",
    "pry": "Paraguay",
    "aus": "Australia",
    "tur": "Turquía",
}

GROUP_BORDER = {
    "A": "rgba(229,92,92,.3)",
    "B": "rgba(59,139,235,.3)",
    "C": "rgba(16,185,129,.3)",
    "D": "rgba(99,102,241,.3)",
    "E": "rgba(249,115,22,.3)",
    "F": "rgba(245,158,11,.3)",
    "G": "rgba(139,92,246,.3)",
    "H": "rgba(236,72,153,.3)",
    "I": "rgba(6,182,212,.3)",
    "J": "rgba(132,204,22,.3)",
    "K": "rgba(217,119,6,.3)",
    "L": "rgba(148,163,184,.3)",
}

POS_LABEL = {"DF": "DEF", "MF": "MED", "FW": "DEL"}
POS_CLASS = {"GK": "pos-gk", "DF": "pos-def", "DEF": "pos-def", "MF": "pos-med", "MED": "pos-med", "FW": "pos-del", "DEL": "pos-del"}
TEAM_CONTEXT_BADGES = {
    "mex": "3er Mundial en casa",
    "zaf": "Sundowns como base",
    "cze": "Kovář figura del repechaje",
    "can": "Co-sede · 3er Mundial",
    "qat": "Campeón Asia 2023",
    "mar": "Semifinalista Qatar 2022",
    "pry": "Regresa tras 16 años",
    "aus": "6° Mundial consecutivo",
    "tur": "Regresa tras 24 años",
    "ecu": "5° Mundial",
    "ned": "Finalista 3 veces",
    "egy": "Salah a 2 goles del récord",
    "irn": "4° Mundial consecutivo",
    "ury": "Muslera · 5° Mundial",
    "sen": "Campeón África 2021",
    "irq": "Regresa tras 40 años",
    "arg": "Campeona Qatar 2022",
    "alg": "Regresa tras 12 años",
    "uzb": "1° Mundial histórico",
    "cro": "Último Mundial de Modrić",
    "gha": "5° Mundial",
    "pan": "2° Mundial",
}
ABSENCE_LABEL_OVERRIDES = {
    "mex": [
        "Hirving “Chucky” Lozano (no convocado)",
        "César Huerta (duda física)",
        "Marcel Ruiz (lesionado)",
    ],
    "zaf": ["Modiba / Thapelo Morena (lesionados)"],
    "cze": [
        "Adam Hložek (lesionado)",
        "Tomáš Chorý / David Douděra (sanción)",
        "Christophe Kabongo / Pavel Bucha / Tomáš Ladra (no convocados)",
    ],
    "can": [
        "Lista marcada por lesiones (seguimiento)",
        "Corte final de seis jugadores (no convocados)",
        "Davies / Bombito / Laryea / Shaffelburg / De Fougerolles / Koné (duda física)",
    ],
    "qat": [
        "Delantero sin ritmo (lesionado)",
        "Titular con roja y lesión (duda física)",
    ],
    "mar": [
        "Youssef En-Nesyri (no convocado)",
        "Ait Boudlal (lesionado)",
    ],
    "pry": [
        "Exclusiones por lesión o decisión técnica (seguimiento)",
        "Adam Bareiro / Mathías Villasanti (lesionados)",
        "Decisión técnica (no convocado)",
    ],
    "aus": [
        "Volante del Middlesbrough (lesionado)",
        "Hayden Matthews / Nick D’Agostino / Patrick Yazbek (lesionados)",
        "Riley McGree (lesionado)",
    ],
    "tur": [
        "Reservas por posibles lesiones (seguimiento)",
        "Enes Ünal (lesionado)",
        "Atakan Karazor (no convocado)",
    ],
    "ecu": ["Leonardo Campana (lesionado)"],
    "ned": [
        "Xavi Simons / Jerdy Schouten (lesionados)",
        "Lateral del Liverpool (lesionado)",
        "Volante de Atalanta (no convocado)",
    ],
    "egy": [
        "Aqtai Abdallah (no convocado)",
        "Abdelmonem (duda física)",
        "Continuidad física (seguimiento)",
    ],
    "irn": [
        "Sardar Azmoun (marginado)",
        "Ali Gholizadeh (lesionado)",
    ],
    "ury": [
        "Luis Suárez (no convocado)",
        "Nández / Facundo Torres / Nicolás Fonseca / Luciano Rodríguez (no convocados)",
        "Atacante recuperado (seguimiento)",
    ],
    "sen": ["Kalidou Koulibaly (duda física)"],
    "irq": ["Arquero titular (recuperado)"],
    "arg": [
        "Marcos Senesi (no convocado)",
        "Lo Celso / Máximo Perrone (seguimiento)",
        "Garnacho / Soulé / Prestianni / Buendía (no convocados)",
    ],
    "alg": [
        "Ausencia por lesiones repetidas (no convocado)",
        "Ilan Kebbal (no convocado)",
        "Sanción por altercado (seguimiento)",
    ],
    "uzb": ["Aziz Ganiev (lesionado)"],
    "cro": [
        "Molestias recientes (duda física)",
        "Bruno Petković (lesionado)",
    ],
    "gha": [
        "Mohammed Kudus (lesionado)",
        "Mohammed Salisu (lesionado)",
    ],
    "pan": [
        "Kadir Barría (lesionado)",
        "Kadir Barría (recuperación)",
    ],
}
ABSENCE_PATTERNS = (
    "ausencia mas",
    "ausencia notable",
    "ausencias notable",
    "baja sensible",
    "bajas sensible",
    "baja mas",
    "bajas mas",
    "quedo afuera",
    "quedaron afuera",
    "queda afuera",
    "quedo fuera",
    "quedaron fuera",
    "fuera del mundial",
    "no fue convocado",
    "no fue convocada",
    "no fueron convocados",
    "no entro",
    "no entraron",
    "descartado",
    "descartada",
    "descartados",
    "descartadas",
    "marginado",
    "marginada",
    "marginados",
    "marginadas",
    "excluir",
    "excluido",
    "excluida",
    "lesion",
    "lesionado",
    "lesionada",
    "lesiones",
    "rotura",
    "molestia",
    "sancion",
)
ABSENCE_REJECT_PATTERNS = (
    "torneo continental",
    "copa africana",
    "rusia 2018",
    "caso byron castillo",
    "camino con tres puntos menos",
    "marcelo gallardo",
    "regreso tras superar",
)
DEDUP_TOKEN_STOPWORDS = {
    "afuera",
    "baja",
    "bajas",
    "carlos",
    "comentada",
    "comentadas",
    "copa",
    "descartado",
    "descartada",
    "despejada",
    "dolorosa",
    "enero",
    "equipo",
    "estrellas",
    "figura",
    "fuera",
    "jugador",
    "jugadores",
    "lesion",
    "lesiones",
    "mundial",
    "mohamed",
    "mohammed",
    "mundo",
    "negras",
    "notable",
    "notables",
    "queiroz",
    "temporada",
}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def h(value):
    return html.escape("" if value is None else str(value), quote=True)


def is_publishable_team(team):
    players = team.get("players") or []
    starter_count = sum(1 for player in players if player.get("titular") is True)
    return (
        len(players) >= 26
        and starter_count >= 11
        and bool(team.get("scheme"))
        and bool(team.get("xi_image"))
        and bool(team.get("tactics"))
    )


def has_public_profile(team):
    return bool(team.get("analyzed")) or is_publishable_team(team)


def has_absence_signal(text):
    key = normalize_country_name(text)
    return any(
        re.search(r"\b" + re.escape(normalize_country_name(pattern)), key)
        for pattern in ABSENCE_PATTERNS
    )


def is_noise_absence_note(text):
    key = normalize_country_name(text)
    return any(normalize_country_name(pattern) in key for pattern in ABSENCE_REJECT_PATTERNS)


def meaningful_tokens(text):
    tokens = set()
    for token in re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ']+", text):
        if not token[:1].isupper():
            continue
        key = normalize_country_name(token)
        if len(key) >= 5 and key not in DEDUP_TOKEN_STOPWORDS:
            tokens.add(key)
    return tokens


def trim_note(text, max_sentences=2, max_chars=460):
    text = normalize_text(text)
    sentences = re.split(r"(?<=[.!?])\s+", text)
    signal_sentences = [sentence for sentence in sentences if has_absence_signal(sentence)]
    clipped = " ".join((signal_sentences or sentences)[:max_sentences]).strip()
    if len(clipped) > max_chars:
        clipped = clipped[:max_chars].rsplit(" ", 1)[0].rstrip(".,;") + "."
    return clipped


def extract_absence_notes_from_html(article_html, max_items=3):
    soup = BeautifulSoup(article_html, "html.parser")
    root = article_content_root(soup)
    block_notes = []
    fallback_notes = []
    in_absence_block = False

    for node in root.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
        text = normalize_text(node.get_text(" ", strip=True))
        if not text or "pic.twitter.com" in text:
            continue

        if node.name in ("h1", "h2", "h3", "h4"):
            key = normalize_country_name(text)
            if "ausencia" in key or "baja" in key or "duda" in key:
                in_absence_block = True
                continue
            if in_absence_block:
                break
            continue

        if has_absence_signal(text):
            note = trim_note(text)
            if is_noise_absence_note(note):
                continue
            if in_absence_block:
                block_notes.append(note)
            else:
                fallback_notes.append(note)

    notes = block_notes or fallback_notes
    deduped = []
    seen = set()
    token_sets = []
    for note in notes:
        key = normalize_country_name(note)
        if key in seen:
            continue
        tokens = meaningful_tokens(note)
        if tokens and any(tokens & previous_tokens for previous_tokens in token_sets):
            continue
        seen.add(key)
        token_sets.append(tokens)
        deduped.append(note)
        if len(deduped) >= max_items:
            break
    return deduped


def fetch_absences_for_team(team):
    url = team.get("source_url")
    if not url:
        return []
    response = requests.get(url, timeout=30, headers={"User-Agent": USER_AGENT})
    response.raise_for_status()
    return extract_absence_notes_from_html(response.text)


def enrich_team_records(teams_data, fetch_absences=False):
    updated_absences = []
    published = []
    for team in teams_data.get("teams", []):
        if fetch_absences and team.get("source_status") == "squad_only" and team.get("source_url"):
            notes = fetch_absences_for_team(team)
            team["absences"] = notes
            team["absences_source"] = "alterfutbol_article"
            team["absences_source_url"] = team.get("source_url")
            updated_absences.append(team["id"])

        if team.get("source_status") == "squad_only" and is_publishable_team(team):
            team["analyzed"] = True
            published.append(team["id"])

    meta = teams_data.setdefault("meta", {})
    meta["updated"] = "2026-06-06"
    meta["total_teams_analyzed"] = sum(1 for team in teams_data.get("teams", []) if team.get("analyzed"))
    meta["total_teams_with_squads"] = sum(1 for team in teams_data.get("teams", []) if team.get("players"))

    return {"updated_absences": updated_absences, "published": published}


def initials(name):
    letters = [part[0] for part in re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+", name or "")[:2]]
    return "".join(letters).upper() or "XI"


def elo_class(value):
    if value is None:
        return "elo-nd"
    try:
        rating = int(value)
    except (TypeError, ValueError):
        return "elo-nd"
    if rating >= 1650:
        return "elo-high"
    if rating >= 1400:
        return "elo-mid"
    return "elo-low"


def choose_featured_player(team):
    existing = team.get("star_player")
    if isinstance(existing, dict) and existing.get("name"):
        return existing

    players = team.get("players") or []
    pool = [player for player in players if player.get("titular")] or players
    with_elo = [player for player in pool if player.get("elo") is not None]
    player = max(with_elo or pool, key=lambda p: p.get("elo") or -1) if pool else {}
    return {
        "name": player.get("name") or "Jugador destacado",
        "club": player.get("club"),
        "elo": player.get("elo"),
        "image": None,
    }


def render_star_card(team):
    player = choose_featured_player(team)
    name = player.get("name") or "Jugador destacado"
    club = player.get("club") or "Club por confirmar"
    rating = player.get("elo")
    rating_text = f"ELO {rating}" if rating is not None else "ELO N/D"
    color = f"var(--grp-{team.get('group', 'a').lower()})"
    image = player.get("image")
    image_html = ""
    placeholder_style = ""
    if image:
        image_html = (
            f'<img src="{h(image)}" alt="{h(name)}" loading="lazy" '
            'onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'flex\'">'
        )
    else:
        placeholder_style = ' style="display:flex"'
    return f"""      <div class="star-card">
          <div class="star-img-wrap" style="--sc:{color}">
            {image_html}
            <div class="star-placeholder"{placeholder_style}>{h(initials(name))}</div>
          </div>
          <div class="star-info">
            <div class="star-label">Jugador destacado</div>
            <div class="star-name">{h(name)}</div>
            <div class="star-meta">{h(club)}</div>
            <span class="elo-cell {elo_class(rating)}" style="font-size:11px;font-family:'JetBrains Mono',monospace">{h(rating_text)}</span>
          </div>
        </div>"""


def absence_status_label(note):
    key = normalize_country_name(note)
    if "sancion" in key or "altercado" in key:
        return "sanción"
    if any(term in key for term in ("lesion", "rotura", "desgarro", "ligamento", "molestia", "sin ritmo")):
        return "duda física"
    if any(term in key for term in ("no convoc", "fuera", "afuera", "descart", "exclu", "margin", "corte")):
        return "no convocado"
    return "seguimiento"


def fallback_absence_label(note):
    key = normalize_country_name(note)
    if "decision tecnica" in key or "definicion" in key:
        return "Decisión técnica (no convocado)"
    if "reserva" in key:
        return "Reservas por posibles lesiones (seguimiento)"
    if "lesion" in key or "molestia" in key:
        return f"Situación física ({absence_status_label(note)})"
    if "corte" in key or "preseleccion" in key:
        return "Corte de lista (no convocado)"
    return f"Situación de lista ({absence_status_label(note)})"


def absence_label_for(team, index, note):
    labels = ABSENCE_LABEL_OVERRIDES.get(team.get("id"), [])
    if index < len(labels):
        return labels[index]
    return fallback_absence_label(note)


def render_absences(team):
    notes = team.get("absences") or []
    if not notes:
        notes = ["La fuente revisada no detalla ausencias puntuales en el bloque de convocatoria y análisis."]
    items = "\n".join(
        (
            f'            <li><span class="absence-name">{h(absence_label_for(team, index, note))}</span><br>'
            f'<span class="absence-reason">{h(note)}</span></li>'
        )
        for index, note in enumerate(notes[:3])
    )
    source_url = team.get("absences_source_url") or team.get("source_url")
    source_link = ""
    if source_url:
        source_link = (
            f'\n          <a href="{h(source_url)}" target="_blank" rel="noopener" '
            'style="display:inline-block;margin-top:.75rem;font-size:.72rem;color:var(--accent);text-decoration:none;opacity:.8">↗ Fuente AlterFutbol</a>'
        )
    return f"""        <div class="info-card">
          <h4>Ausencias notables</h4>
          <ul class="absence-list">
{items}
          </ul>{source_link}
        </div>"""


def team_context_badge(team):
    return TEAM_CONTEXT_BADGES.get(team.get("id")) or "Dato histórico"


def render_squad_table(team):
    rows = []
    for player in team.get("players") or []:
        raw_pos = player.get("pos") or ""
        pos = POS_LABEL.get(raw_pos, raw_pos)
        pos_cls = POS_CLASS.get(raw_pos, POS_CLASS.get(pos, ""))
        elo = player.get("elo")
        elo_text = str(elo) if elo is not None else "N/D"
        titular = player.get("titular") is True
        titular_cls = "titl-yes" if titular else "titl-no"
        titular_text = "Sí" if titular else "No"
        rows.append(
            "<tr>"
            f'<td><span class="pos-badge {pos_cls}">{h(pos)}</span></td>'
            f'<td class="player-name">{h(player.get("name"))}</td>'
            f'<td style="color:var(--muted)">{h(player.get("age") or "")}</td>'
            f'<td style="font-size:13px">{h(player.get("club") or "")}</td>'
            f'<td style="font-size:12px;color:var(--muted)">{h(player.get("country") or "")}</td>'
            f'<td class="elo-cell {elo_class(elo)}">{h(elo_text)}</td>'
            f'<td><span class="{titular_cls}">{titular_text}</span></td>'
            "</tr>"
        )
    return (
        '<div class="squad-wrap"><table class="squad-table"><thead><tr>'
        "<th>Pos</th><th>Jugador</th><th>Edad</th><th>Club</th><th>País</th><th>ELO</th><th>Titular</th>"
        "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
        '<div class="nd-note">ELO de clubes: <a href="http://worldclubratings.com/rankings/elo_men/" '
        'target="_blank" rel="noopener">worldclubratings.com/rankings/elo_men</a></div>'
    )


def render_team_section(team):
    code = team["id"]
    section_id = SECTION_BY_CODE[code]
    group = team.get("group") or ""
    scheme = team.get("scheme") or "Sistema por definir"
    tactics = team.get("tactics") or []
    tactic_text = tactics[0] if tactics else "Análisis táctico pendiente de fuente."
    source_url = team.get("source_tactics_url") or team.get("source_url")
    source_link = ""
    if source_url:
        source_link = (
            f'\n          <a href="{h(source_url)}" target="_blank" rel="noopener" '
            'style="display:inline-block;margin-top:.5rem;font-size:.72rem;color:var(--accent);text-decoration:none;opacity:.8">↗ Nota en AlterFutbol</a>'
        )
    return f"""
    <!-- ─── {h(team.get('name')).upper()} ─── -->
    <div class="team-section" id="{h(section_id)}">
      <div class="team-header">
        <div class="team-flag-big"><img src="assets/flags/{h(code)}.svg" alt="{h(team.get('name'))}" loading="lazy"></div>
        <div>
          <div class="team-name">{h(team.get('name'))}</div>
          <div class="team-sub">DT: {h(team.get('dt') or 'Por confirmar')} · Grupo {h(group)}</div>
          <div class="team-pills"><span class="team-pill" style="color:var(--accent);border-color:var(--accent)">{h(scheme)}</span><span class="team-pill" style="color:var(--grp-{h(group).lower()});border-color:var(--grp-{h(group).lower()})">Grupo {h(group)}</span><span class="team-pill" style="color:var(--gold);border-color:var(--gold)">{h(team_context_badge(team))}</span></div>
        </div>
{render_star_card(team)}
      </div>
      <div class="two-col">
        <div class="info-card">
          <h4>Sistema de juego</h4>
          <p class="tactic-prose">{h(tactic_text)}</p>{source_link}
        </div>
{render_absences(team)}
      </div>
      <div class="xi-img-wrap">
        <div class="xi-img-label">XI Probable · {h(team.get('name'))}</div>
        <img src="{h(team.get('xi_image'))}" alt="XI Ideal {h(team.get('name'))}" loading="lazy" class="xi-img">
      </div>
      {render_squad_table(team)}
    </div>"""


def find_squad_table_bounds(section_html):
    start = section_html.find('<div class="squad-wrap"><table class="squad-table">')
    if start == -1:
        return None
    table_end_marker = "</tbody></table></div>"
    table_end = section_html.find(table_end_marker, start)
    if table_end == -1:
        return None
    end = table_end + len(table_end_marker)
    note_start = section_html.find('<div class="nd-note">', end)
    if note_start == end:
        note_end = section_html.find("</div>", note_start)
        if note_end != -1:
            end = note_end + len("</div>")
    return start, end


def replace_existing_squad_tables(index_html, teams_by_code):
    for code, team in teams_by_code.items():
        if not team.get("players") or not has_public_profile(team):
            continue
        section_id = SECTION_BY_CODE.get(code)
        if not section_id:
            continue
        section_bounds = find_team_section_bounds(index_html, section_id)
        if not section_bounds:
            continue
        section_start, section_end = section_bounds
        section_html = index_html[section_start:section_end]
        table_bounds = find_squad_table_bounds(section_html)
        if not table_bounds:
            continue
        table_start, table_end = table_bounds
        updated_section = (
            section_html[:table_start]
            + render_squad_table(team)
            + section_html[table_end:]
        )
        index_html = index_html[:section_start] + updated_section + index_html[section_end:]
    return index_html


def render_pending_grid(codes, groups_data):
    if not codes:
        return ""
    names = team_names_from_groups(groups_data)
    cards = "".join(
        f'<div class="pending-card"><img class="flag-svg" src="assets/flags/{h(code)}.svg" alt="{h(names.get(code, code.upper()))}" loading="lazy"> {h(names.get(code, code.upper()))}<br><small style="font-size:11px;opacity:.6">Lista pendiente</small></div>'
        for code in codes
    )
    return (
        '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:1rem;margin-top:2rem">'
        + cards
        + "</div>"
    )


def team_names_from_groups(groups_data):
    names = {}
    for group in groups_data.get("groups", []):
        for code in group.get("teams", []):
            names[code] = TEAM_DISPLAY_NAMES.get(code, code.upper())
    return names


def render_group_cards(groups_data, teams_by_code):
    chunks = []
    for group in groups_data.get("groups", []):
        group_id = group["id"]
        border = GROUP_BORDER.get(group_id, "rgba(148,163,184,.3)")
        chunks.append(f'      <div class="group-card" style="border-color:{border}">')
        chunks.append(
            f'        <div class="group-label" style="color:var(--grp-{group_id.lower()})"><span class="group-dot" style="background:var(--grp-{group_id.lower()})"></span> Grupo {group_id}</div>'
        )
        chunks.append('        <ul class="group-teams">')
        for code in group.get("teams", []):
            team = teams_by_code.get(code)
            name = team.get("name") if team else TEAM_DISPLAY_NAMES.get(code, code.upper())
            flag = f'<img class="flag-svg" src="assets/flags/{h(code)}.svg" alt="{h(name)}" loading="lazy">'
            if team and SECTION_BY_CODE.get(code):
                label = f'<a href="#{h(SECTION_BY_CODE[code])}" class="group-team-link">{flag} {h(name)}</a>'
            else:
                label = f"{flag} {h(name)}"
            badges = []
            if code in HOSTS:
                badges.append('<span class="host-badge">LOCAL</span>')
            if team and has_public_profile(team):
                badges.append('<span class="analyzed-badge">✓</span>')
            chunks.append(f"          <li>{label} {' '.join(badges)}</li>")
        chunks.append("        </ul>")
        chunks.append("      </div>")
        chunks.append("")
    return "\n".join(chunks).rstrip()


def render_grupos_modal_body(groups_data, teams_by_code):
    chunks = []
    for group in groups_data.get("groups", []):
        group_id = group["id"]
        chunks.append(f"      <!-- {h(group_id)} -->")
        chunks.append('      <div class="gmod-group">')
        chunks.append(
            f'        <div class="gmod-group-header" style="background:{GROUP_BORDER.get(group_id, "rgba(148,163,184,.3)").replace(".3", ".1")};border-color:var(--grp-{group_id.lower()})"><span class="gmod-dot" style="background:var(--grp-{group_id.lower()})"></span>Grupo {h(group_id)}</div>'
        )
        for code in group.get("teams", []):
            team = teams_by_code.get(code)
            name = team.get("name") if team else TEAM_DISPLAY_NAMES.get(code, code.upper())
            flag = f'<img src="assets/flags/{h(code)}.svg" alt="">'
            if team and has_public_profile(team) and SECTION_BY_CODE.get(code):
                chunks.append(
                    f'        <a class="gmod-team has-analysis" data-name="{h(name)}" href="#{h(SECTION_BY_CODE[code])}">{flag}<span class="gmod-name">{h(name)}</span><span class="gmod-ana"></span></a>'
                )
            else:
                chunks.append(
                    f'        <div class="gmod-team" data-name="{h(name)}">{flag}<span class="gmod-name">{h(name)}</span></div>'
                )
        chunks.append("      </div>")
    chunks.append('      <div class="gmod-no-results" id="gmod-no-results">Sin resultados</div>')
    return "\n".join(chunks)


def replace_grupos_modal(index_html, groups_data, teams_by_code):
    marker = '    <div class="grupos-modal-body" id="grupos-modal-body">'
    body_start = index_html.index(marker)
    content_start = body_start + len(marker)
    body_end = index_html.index('    </div>\n    <div class="grupos-modal-footer">', content_start)
    replacement = "\n" + render_grupos_modal_body(groups_data, teams_by_code) + "\n"
    return index_html[:content_start] + replacement + index_html[body_end:]


def replace_groups_grid(index_html, groups_data, teams_by_code):
    section_start = index_html.index('<section id="grupos">')
    grid_start = index_html.index('    <div class="groups-grid">', section_start)
    content_start = grid_start + len('    <div class="groups-grid">')
    grid_end = index_html.index('    </div>\n    </div></div><!-- /section-body-inner /section-body grupos -->', content_start)
    replacement = "\n\n" + render_group_cards(groups_data, teams_by_code) + "\n\n"
    return index_html[:content_start] + replacement + index_html[grid_end:]


def replace_pending_grids(index_html, teams_by_code, groups_data):
    existing_sections = set(re.findall(r'<div class="team-section" id="([^"]+)"', index_html))
    pattern = re.compile(r'^    <div style="display:grid;grid-template-columns:repeat\(auto-fill,minmax\(220px,1fr\)\);gap:1rem;margin-top:2rem">.*pending-card.*</div>$', re.M)

    def replacement(match):
        line = match.group(0).strip()
        codes = re.findall(r'assets/flags/([a-z]{3})\.svg', line)
        sections = []
        pending = []
        for code in codes:
            team = teams_by_code.get(code)
            section_id = SECTION_BY_CODE.get(code)
            if team and section_id and section_id not in existing_sections and is_publishable_team(team):
                sections.append(render_team_section(team))
                existing_sections.add(section_id)
            else:
                pending.append(code)
        rendered_pending = render_pending_grid(pending, groups_data)
        parts = sections
        if rendered_pending:
            parts.append("    " + rendered_pending)
        return "\n".join(parts)

    return pattern.sub(replacement, index_html)


def find_team_section_bounds(index_html, section_id):
    marker = f'<div class="team-section" id="{section_id}">'
    div_start = index_html.find(marker)
    if div_start == -1:
        return None

    line_start = index_html.rfind("\n", 0, div_start) + 1
    previous_line_start = index_html.rfind("\n", 0, max(0, line_start - 1)) + 1
    previous_line = index_html[previous_line_start:line_start].strip()
    block_start = previous_line_start if previous_line.startswith("<!-- ───") else line_start

    depth = 0
    for match in re.finditer(r"</?div\b[^>]*>", index_html[div_start:]):
        token = match.group(0)
        if token.startswith("</"):
            depth -= 1
        else:
            depth += 1
        if depth == 0:
            block_end = div_start + match.end()
            if index_html[block_end:block_end + 1] == "\n":
                block_end += 1
            return block_start, block_end
    return None


def replace_existing_generated_sections(index_html, teams_by_code):
    for code, team in teams_by_code.items():
        if team.get("source_status") != "squad_only" or not is_publishable_team(team):
            continue
        section_id = SECTION_BY_CODE.get(code)
        if not section_id:
            continue
        bounds = find_team_section_bounds(index_html, section_id)
        if not bounds:
            continue
        start, end = bounds
        index_html = index_html[:start] + render_team_section(team).lstrip("\n") + "\n" + index_html[end:]
    return index_html


def replace_team_codes(index_html, teams_by_code):
    entries = []
    for code, section_id in SECTION_BY_CODE.items():
        if code in teams_by_code and has_public_profile(teams_by_code[code]):
            entries.append((section_id, code))
    lines = ["  var TEAM_CODES = {"]
    for index, (section_id, code) in enumerate(entries):
        comma = "," if index < len(entries) - 1 else ""
        lines.append(f"    '{section_id}': '{code}'{comma}")
    lines.append("  };")
    replacement = "\n".join(lines)
    return re.sub(r"  var TEAM_CODES = \{.*?\n  \};", replacement, index_html, flags=re.S)


def load_publication_tracker():
    path = REPO_ROOT / "data" / "squad_publication_tracker.json"
    if not path.exists():
        return {"meta": {"total_published": 0, "total_teams": 48}, "teams": []}
    return load_json(path)


def format_publication_date(value):
    month_labels = {"05": "May", "06": "Jun"}
    try:
        _, month, day = str(value).split("-")
    except ValueError:
        return str(value or "")
    return f"{int(day)} {month_labels.get(month, month)}"


def publication_tracker_rows_by_date(publication_tracker):
    rows_by_date = {}
    for row in publication_tracker.get("teams", []):
        rows_by_date.setdefault(row.get("published_date"), []).append(row)
    return rows_by_date


def render_tracker_summary(groups_data, teams_by_code, publication_tracker):
    total_teams = publication_tracker.get("meta", {}).get("total_teams", 48)
    dated_count = len(publication_tracker.get("teams", []))
    groups_with_dates = len({row.get("group_id") for row in publication_tracker.get("teams", []) if row.get("group_id")})
    published_profiles = 0
    for group in groups_data.get("groups", []):
        for code in group.get("teams", []):
            team = teams_by_code.get(code)
            if team and has_public_profile(team):
                published_profiles += 1
    pending_profiles = total_teams - published_profiles
    pending_dates = total_teams - dated_count
    return f"""    <p style="color:var(--muted);margin-bottom:2rem;font-size:14px">
      {dated_count} selecciones con fecha de convocatoria registrada entre el <strong style="color:var(--text)">26 mayo 2026</strong> y el <strong style="color:var(--text)">1 junio 2026</strong>. Hay {published_profiles} perfiles publicados y {pending_profiles} pendientes de perfil fuenteado; las fechas de convocatoria y el perfil analizado se gestionan como datos separados.
      Las marcadas con <span class="analyzed-badge">✓ Detallado</span> tienen análisis completo en este documento.
    </p>

    <!-- Resumen global -->
    <div class="format-grid" style="margin-bottom:3rem">
      <div class="fmt-card"><div class="fmt-num" style="color:var(--accent)">{dated_count}</div><div class="fmt-label">Convocatorias<br>con fecha registrada</div></div>
      <div class="fmt-card"><div class="fmt-num" style="color:var(--gold)">{groups_with_dates}</div><div class="fmt-label">Grupos con al menos<br>una fecha registrada</div></div>
      <div class="fmt-card"><div class="fmt-num" style="color:var(--red)">{pending_dates}</div><div class="fmt-label">{pending_dates} pendientes de fecha registrada</div></div>
      <div class="fmt-card"><div class="fmt-num" style="color:var(--accent)">{published_profiles}</div><div class="fmt-label">{published_profiles} perfiles publicados<br>{pending_profiles} pendientes de perfil fuenteado</div></div>
    </div>"""


def replace_tracker_summary_block(index_html, groups_data, teams_by_code, publication_tracker):
    header = '      <h2>Tracker de Convocatorias</h2>'
    header_pos = index_html.find(header)
    if header_pos == -1:
        return index_html
    start = index_html.find('    <p style="color:var(--muted);margin-bottom:2rem;font-size:14px">', header_pos)
    end = index_html.find("    <!-- Tabla tracker por grupo -->", start)
    if start == -1 or end == -1:
        return index_html
    return index_html[:start] + render_tracker_summary(groups_data, teams_by_code, publication_tracker) + "\n\n" + index_html[end:]


def render_publication_timeline(publication_tracker):
    chunks = [
        "    <!-- Timeline publicación -->",
        '    <h3 style="margin-top:3rem;margin-bottom:1.5rem">Cronología de anuncios</h3>',
        '    <div style="display:flex;flex-direction:column;gap:.5rem">',
    ]
    rows_by_date = publication_tracker_rows_by_date(publication_tracker)
    for index, (date_value, rows) in enumerate(rows_by_date.items()):
        border = "var(--accent)" if index in (0, len(rows_by_date) - 1) else "var(--border)"
        flags = " ".join(
            f'<img class="flag-svg" src="assets/flags/{h(row.get("team_code"))}.svg" alt="{h(row.get("name"))}" loading="lazy">'
            for row in rows
        )
        names = " · ".join(h(row.get("name")) for row in rows)
        chunks.extend(
            [
                f'      <div style="display:flex;align-items:center;gap:1rem;padding:.75rem 1rem;background:var(--card);border-radius:8px;border-left:3px solid {border}">',
                f'        <span style="font-family:\'JetBrains Mono\',monospace;font-size:11px;color:var(--muted);min-width:80px">{h(format_publication_date(date_value))}</span>',
                f'        <span>{flags}</span><span style="font-size:13px"><strong style="color:var(--white)">{names}</strong></span>',
                '        <span class="analyzed-badge" style="margin-left:auto">Convocatoria</span>',
                "      </div>",
            ]
        )
    chunks.append("    </div>")
    return "\n".join(chunks)


def replace_publication_timeline_block(index_html, publication_tracker):
    start = index_html.find("    <!-- Timeline publicación -->")
    end = index_html.find("    <!-- Selecciones pendientes por grupo -->", start)
    if start == -1 or end == -1:
        return index_html
    return index_html[:start] + render_publication_timeline(publication_tracker) + "\n\n" + index_html[end:]


def publication_date_by_code(publication_tracker):
    return {
        row.get("team_code"): format_publication_date(row.get("published_date"))
        for row in publication_tracker.get("teams", [])
    }


def tracker_status_html(team, date_label):
    date_html = f'<span style="display:block;margin-top:.25rem;font-size:11px;color:var(--muted)">{h(date_label)}</span>' if date_label else ""
    if team and has_public_profile(team):
        return f'<span class="analyzed-badge">✓ Detallado</span>{date_html}'
    if date_label:
        return f'<span class="team-pill tp-scheme" style="font-size:11px;padding:.1rem .5rem">Convocatoria</span>{date_html}<span style="display:block;margin-top:.25rem;font-size:11px;color:var(--muted)">Pendiente perfil</span>'
    return '<span style="font-size:12px;color:var(--muted)">Pendiente perfil</span>'


def tracker_team_name(code, team, names):
    return (team or {}).get("name") or names.get(code, code.upper())


def tracker_featured_name(team):
    if not team or not has_public_profile(team):
        return "Por definir"
    player = choose_featured_player(team)
    return player.get("name") or "Jugador destacado"


def render_tracker_profile_table(groups_data, teams_by_code, publication_tracker):
    names = team_names_from_groups(groups_data)
    dates = publication_date_by_code(publication_tracker)
    chunks = [
        "    <!-- Tabla tracker por grupo -->",
        '    <div class="squad-wrap tracker-squad">',
        '      <table class="squad-table">',
        "        <thead>",
        "          <tr>",
        "            <th>Grupo</th><th>Selección</th><th>DT</th><th>Sistema</th><th>Figura clave</th><th>Estado</th>",
        "          </tr>",
        "        </thead>",
        "        <tbody>",
    ]
    for group_index, group in enumerate(groups_data.get("groups", [])):
        group_id = group["id"]
        row_style = ' style="background:rgba(255,255,255,.02)"' if group_index % 2 == 0 else ""
        teams = group.get("teams", [])
        short_names = " · ".join(code.upper() for code in teams[:2]) + "<br>" + " · ".join(code.upper() for code in teams[2:])
        for team_index, code in enumerate(teams):
            team = teams_by_code.get(code)
            name = tracker_team_name(code, team, names)
            dt = (team or {}).get("dt") or "Por confirmar"
            scheme = (team or {}).get("scheme") or "Por definir"
            featured = tracker_featured_name(team)
            chunks.append(f"          <tr{row_style}>")
            if team_index == 0:
                chunks.append(
                    f'            <td rowspan="{len(teams)}"><strong style="color:var(--grp-{group_id.lower()})">{h(group_id)}</strong><br><span style="font-size:11px;color:var(--muted)">{short_names}</span></td>'
                )
            chunks.extend(
                [
                    f'            <td><img class="flag-svg" src="assets/flags/{h(code)}.svg" alt="{h(name)}" loading="lazy"> <strong class="player-name">{h(name)}</strong></td>',
                    f'            <td style="font-size:13px">{h(dt)}</td>',
                    f'            <td><span class="team-pill tp-scheme" style="font-size:11px;padding:.1rem .5rem">{h(scheme)}</span></td>',
                    f'            <td style="font-size:13px">{h(featured)}</td>',
                    f"            <td>{tracker_status_html(team, dates.get(code))}</td>",
                    "          </tr>",
                ]
            )
    chunks.extend(["        </tbody>", "      </table>", "    </div>"])
    return "\n".join(chunks)


def render_tracker_accordion(groups_data, teams_by_code, publication_tracker):
    names = team_names_from_groups(groups_data)
    dates = publication_date_by_code(publication_tracker)
    chunks = [
        "    <!-- Tracker accordion (mobile) -->",
        '    <div class="tracker-accordion">',
    ]
    for group in groups_data.get("groups", []):
        group_id = group["id"]
        team_codes = group.get("teams", [])
        chunks.extend(
            [
                f'      <div class="tacc-group" style="--gc:var(--grp-{group_id.lower()})">',
                '        <div class="tacc-group-header">',
                f'          <span class="tacc-group-letter">{h(group_id)}</span>',
                f'          <span class="tacc-group-teams">{" · ".join(h(code.upper()) for code in team_codes)}</span>',
                "        </div>",
            ]
        )
        for code in team_codes:
            team = teams_by_code.get(code)
            name = tracker_team_name(code, team, names)
            date_label = dates.get(code) or "Sin fecha registrada"
            status = "✓" if team and has_public_profile(team) else "Pendiente"
            dt = (team or {}).get("dt") or "Por confirmar"
            scheme = (team or {}).get("scheme") or "Por definir"
            featured = tracker_featured_name(team)
            chunks.extend(
                [
                    '        <details class="tacc-item">',
                    '          <summary class="tacc-summary">',
                    '            <div class="tacc-left">',
                    f'              <img class="flag-svg" src="assets/flags/{h(code)}.svg" alt="{h(name)}" loading="lazy">',
                    f"              <strong>{h(name)}</strong>",
                    f'              <span class="analyzed-badge">{h(status)}</span>',
                    "            </div>",
                    '            <span class="tacc-chevron">›</span>',
                    "          </summary>",
                    '          <div class="tacc-body">',
                    f'            <div class="tacc-field"><span class="tacc-label">DT</span><span>{h(dt)}</span></div>',
                    f'            <div class="tacc-field"><span class="tacc-label">Sistema</span><span class="team-pill tp-scheme">{h(scheme)}</span></div>',
                    f'            <div class="tacc-field tacc-full"><span class="tacc-label">Figura clave</span><span>{h(featured)}</span></div>',
                    f'            <div class="tacc-field tacc-full"><span class="tacc-label">Convocatoria</span><span>{h(date_label)}</span></div>',
                    "          </div>",
                    "        </details>",
                ]
            )
        chunks.append("      </div>")
    chunks.append("    </div>")
    return "\n".join(chunks)


def replace_tracker_profile_blocks(index_html, groups_data, teams_by_code, publication_tracker):
    start = index_html.find("    <!-- Tabla tracker por grupo -->")
    end = index_html.find("    <!-- Timeline publicación -->", start)
    if start == -1 or end == -1:
        return index_html
    replacement = (
        render_tracker_profile_table(groups_data, teams_by_code, publication_tracker)
        + "\n\n"
        + render_tracker_accordion(groups_data, teams_by_code, publication_tracker)
        + "\n\n"
    )
    return index_html[:start] + replacement + index_html[end:]


def render_pending_tracker(groups_data, teams_by_code):
    pending_by_group = []
    names = team_names_from_groups(groups_data)
    for group in groups_data.get("groups", []):
        pending_codes = [
            code
            for code in group.get("teams", [])
            if not (teams_by_code.get(code) and has_public_profile(teams_by_code[code]))
        ]
        if pending_codes:
            pending_by_group.append((group["id"], pending_codes))

    chunks = [
        "    <!-- Selecciones pendientes por grupo -->",
        '    <h3 style="margin-top:3rem;margin-bottom:1.5rem">Pendientes de perfil fuenteado</h3>',
    ]
    if not pending_by_group:
        chunks.append(
            '    <p style="font-size:13px;color:var(--muted)">Las 48 selecciones tienen perfil publicado con fuente local.</p>'
        )
        return "\n".join(chunks)

    chunks.extend(
        [
            '    <p style="font-size:13px;color:var(--muted);margin-top:-.75rem;margin-bottom:1.25rem">Estas selecciones pueden tener convocatoria registrada, pero aun no tienen articulo directo y lista confiable en AlterFutbol para publicar perfil completo.</p>',
            '    <div class="groups-grid" style="grid-template-columns:repeat(auto-fill,minmax(240px,1fr))">',
        ]
    )
    for group_id, codes in pending_by_group:
        border = GROUP_BORDER.get(group_id, "rgba(148,163,184,.3)")
        team_labels = " &middot; ".join(
            f'<img class="flag-svg" src="assets/flags/{h(code)}.svg" alt="{h(names.get(code, code.upper()))}" loading="lazy"> {h(names.get(code, code.upper()))}'
            for code in codes
        )
        suffix = "pendiente" if len(codes) == 1 else "pendientes"
        chunks.append(
            f'      <div class="group-card" style="border-color:{border}">'
            f'<div class="group-label" style="color:var(--grp-{group_id.lower()})">'
            f'<span class="group-dot" style="background:var(--grp-{group_id.lower()})"></span>'
            f'Grupo {h(group_id)} - {len(codes)} {suffix}</div>'
            f'<div style="font-size:13px;color:var(--muted)">{team_labels} '
            '<em style="font-size:11px">(sin perfil fuenteado)</em></div></div>'
        )
    chunks.append("    </div>")
    return "\n".join(chunks)


def replace_pending_tracker_block(index_html, groups_data, teams_by_code):
    start = index_html.find("    <!-- Selecciones pendientes por grupo -->")
    if start == -1:
        return index_html
    end_marker = "\n\n  </div>\n</section>\n\n<!-- FOOTER -->"
    end = index_html.find(end_marker, start)
    if end == -1:
        return index_html
    return index_html[:start] + render_pending_tracker(groups_data, teams_by_code) + index_html[end:]


def replace_footer_summary(index_html, teams_by_code):
    published = sum(1 for team in teams_by_code.values() if has_public_profile(team))
    pending = 48 - published
    summary = (
        f"Actualizado: 6 de junio de 2026 &nbsp;&middot;&nbsp; "
        f"Perfiles publicados: {published} selecciones &nbsp;&middot;&nbsp; "
        f"Pendientes: {pending} selecciones sin articulo directo confiable &nbsp;&middot;&nbsp; "
        "Fuente: AlterFutbol"
    )
    return re.sub(r"Actualizado: .*?</p>", summary + "</p>", index_html, count=1)


def render_index(index_html, teams_data, groups_data):
    teams_by_code = {team["id"]: team for team in teams_data.get("teams", [])}
    publication_tracker = load_publication_tracker()
    index_html = replace_grupos_modal(index_html, groups_data, teams_by_code)
    index_html = replace_groups_grid(index_html, groups_data, teams_by_code)
    index_html = replace_existing_generated_sections(index_html, teams_by_code)
    index_html = replace_existing_squad_tables(index_html, teams_by_code)
    index_html = replace_pending_grids(index_html, teams_by_code, groups_data)
    index_html = replace_team_codes(index_html, teams_by_code)
    index_html = replace_tracker_summary_block(index_html, groups_data, teams_by_code, publication_tracker)
    index_html = replace_tracker_profile_blocks(index_html, groups_data, teams_by_code, publication_tracker)
    index_html = replace_publication_timeline_block(index_html, publication_tracker)
    index_html = replace_pending_tracker_block(index_html, groups_data, teams_by_code)
    index_html = replace_footer_summary(index_html, teams_by_code)
    return index_html


def main():
    parser = argparse.ArgumentParser(description="Render source-backed team profiles into index.html")
    parser.add_argument("--teams", default=str(REPO_ROOT / "data" / "teams.json"))
    parser.add_argument("--groups", default=str(REPO_ROOT / "data" / "groups.json"))
    parser.add_argument("--index", default=str(REPO_ROOT / "index.html"))
    parser.add_argument("--fetch-absences", action="store_true")
    args = parser.parse_args()

    teams_path = Path(args.teams)
    index_path = Path(args.index)
    teams_data = load_json(teams_path)
    groups_data = load_json(args.groups)

    report = enrich_team_records(teams_data, fetch_absences=args.fetch_absences)
    write_json(teams_path, teams_data)

    rendered = render_index(index_path.read_text(encoding="utf-8"), teams_data, groups_data)
    index_path.write_text(rendered, encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
