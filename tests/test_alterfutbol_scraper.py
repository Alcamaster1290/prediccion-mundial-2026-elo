from scripts.scrape_alterfutbol_news import (
    build_article_entry,
    build_source_manifest,
    extract_tactical_info_from_article,
    extract_players_from_article,
    normalize_country_name,
    resolve_output_path,
)


def test_extract_players_accepts_comma_age_club_format():
    html = """
    <article>
      <h2>Lista completa</h2>
      <h3>Arqueros</h3>
      <ul>
        <li>Alisson (33 años, Liverpool)</li>
      </ul>
      <h3>Defensores</h3>
      <ul>
        <li>Marquinhos (32 años, PSG)</li>
      </ul>
    </article>
    """

    players = extract_players_from_article(html)

    assert players == [
        {
            "number": None,
            "pos": "GK",
            "name": "Alisson",
            "age": 33,
            "club": "Liverpool",
            "country": None,
            "elo": None,
            "titular": False,
        },
        {
            "number": None,
            "pos": "DF",
            "name": "Marquinhos",
            "age": 32,
            "club": "PSG",
            "country": None,
            "elo": None,
            "titular": False,
        },
    ]


def test_extract_players_accepts_dash_after_age_format():
    html = """
    <article>
      <h2>La lista completa de convocados</h2>
      <p>Arqueros:</p>
      <ul>
        <li>Gregor Kobel (28 años) – Borussia Dortmund</li>
      </ul>
      <p>Volantes:</p>
      <ul>
        <li>Granit Xhaka (33 años) – Sunderland</li>
      </ul>
    </article>
    """

    players = extract_players_from_article(html)

    assert players == [
        {
            "number": None,
            "pos": "GK",
            "name": "Gregor Kobel",
            "age": 28,
            "club": "Borussia Dortmund",
            "country": None,
            "elo": None,
            "titular": False,
        },
        {
            "number": None,
            "pos": "MF",
            "name": "Granit Xhaka",
            "age": 33,
            "club": "Sunderland",
            "country": None,
            "elo": None,
            "titular": False,
        },
    ]


def test_extract_players_accepts_age_without_years_word():
    html = """
    <article>
      <h3>Arqueros</h3>
      <ul>
        <li>Guillermo Ochoa (40, AEL Limassol)</li>
      </ul>
    </article>
    """

    players = extract_players_from_article(html)

    assert players == [
        {
            "number": None,
            "pos": "GK",
            "name": "Guillermo Ochoa",
            "age": 40,
            "club": "AEL Limassol",
            "country": None,
            "elo": None,
            "titular": False,
        }
    ]


def test_extract_players_prefers_elementor_post_content_over_related_articles():
    html = """
    <html>
      <body>
        <article><h3>También te puede interesar</h3><li>Artículo relacionado</li></article>
        <div class="elementor-widget-theme-post-content">
          <h3>Arqueros</h3>
          <ul>
            <li>Raúl Rangel (26, Chivas Guadalajara)</li>
          </ul>
        </div>
      </body>
    </html>
    """

    players = extract_players_from_article(html)

    assert players == [
        {
            "number": None,
            "pos": "GK",
            "name": "Raúl Rangel",
            "age": 26,
            "club": "Chivas Guadalajara",
            "country": None,
            "elo": None,
            "titular": False,
        }
    ]


def test_normalize_country_name_handles_accents_and_common_variants():
    assert normalize_country_name("Corea del Sur") == "corea del sur"
    assert normalize_country_name("EE.UU.") == "estados unidos"
    assert normalize_country_name("Países Bajos") == "paises bajos"


def test_build_article_entry_records_source_images_and_complete_status():
    player_items = "\n".join(
        f"<li>Jugador {index} ({20 + index % 10} años, Club {index})</li>"
        for index in range(1, 27)
    )
    html = f"""
    <html>
      <head>
        <meta property="og:title" content="México anunció sus convocados">
        <meta property="article:published_time" content="2026-06-03T12:00:00+00:00">
        <meta property="og:image" content="https://example.test/mexico-equipo.jpg">
      </head>
      <body>
        <article>
          <h1>Los convocados de México</h1>
          <img src="/wp-content/uploads/2026/06/mexico-equipo.jpg" alt="equipo">
          <img src="/wp-content/uploads/2026/06/mexico-forma1.png" alt="formación">
          <h3>Arqueros</h3>
          <ul>{player_items}</ul>
        </article>
      </body>
    </html>
    """

    entry = build_article_entry(
        team_code="mex",
        article_html=html,
        url="https://www.alterfutbol.com/concacaf/mexico/test/",
    )

    assert entry["team_code"] == "mex"
    assert entry["url"] == "https://www.alterfutbol.com/concacaf/mexico/test/"
    assert entry["title"] == "México anunció sus convocados"
    assert entry["published_date"] == "2026-06-03"
    assert entry["featured_image"] == "https://example.test/mexico-equipo.jpg"
    assert entry["image_urls"] == [
        "https://www.alterfutbol.com/wp-content/uploads/2026/06/mexico-equipo.jpg",
        "https://www.alterfutbol.com/wp-content/uploads/2026/06/mexico-forma1.png",
    ]
    assert entry["formation_images"] == [
        "https://www.alterfutbol.com/wp-content/uploads/2026/06/mexico-forma1.png"
    ]
    assert len(entry["players"]) == 26
    assert entry["player_count"] == 26
    assert entry["status"] == "complete"


def test_extract_tactical_info_from_article_reads_scheme_and_tactics_block():
    html = """
    <html>
      <body>
        <article><h2>Relacionado</h2><p>Texto externo con 5-4-1.</p></article>
        <div class="elementor-widget-theme-post-content">
          <h2>El esquema tactico y el XI ideal</h2>
          <p>El tecnico se inclino principalmente por el clasico 4-3-3, aunque alterno con variantes.</p>
          <p>El sistema busca cubrir cada zona del campo con orden y presion alta.</p>
          <h2>Lista completa de convocados</h2>
          <p>Arqueros:</p>
        </div>
      </body>
    </html>
    """

    info = extract_tactical_info_from_article(html)

    assert info["scheme"] == "4-3-3"
    assert info["tactics"] == [
        "El tecnico se inclino principalmente por el clasico 4-3-3, aunque alterno con variantes.",
        "El sistema busca cubrir cada zona del campo con orden y presion alta.",
    ]


def test_extract_tactical_info_from_article_handles_analysis_heading_variant():
    html = """
    <article>
      <h2>Analisis tactico y XI ideal</h2>
      <p>La estructura base oscila entre el 3-4-2-1 y el 4-2-3-1 segun el rival.</p>
      <h2>Las ausencias</h2>
      <p>Este parrafo ya no pertenece al bloque tactico.</p>
    </article>
    """

    info = extract_tactical_info_from_article(html)

    assert info["scheme"] == "3-4-2-1"
    assert info["tactics"] == [
        "La estructura base oscila entre el 3-4-2-1 y el 4-2-3-1 segun el rival."
    ]


def test_extract_tactical_info_from_article_limits_tactics_to_three_paragraphs():
    html = """
    <article>
      <h2>El esquema tactico y el XI ideal</h2>
      <p>El equipo parte de un 4-2-3-1 compacto.</p>
      <p>La presion se activa por bandas.</p>
      <p>El doble cinco sostiene las transiciones.</p>
      <p>Este cuarto parrafo describe un puesto especifico y debe quedar fuera.</p>
    </article>
    """

    info = extract_tactical_info_from_article(html)

    assert info["scheme"] == "4-2-3-1"
    assert info["tactics"] == [
        "El equipo parte de un 4-2-3-1 compacto.",
        "La presion se activa por bandas.",
        "El doble cinco sostiene las transiciones.",
    ]


def test_build_source_manifest_maps_listing_articles_and_marks_missing_teams():
    player_items = "\n".join(
        f"<li>Jugador {index} ({20 + index % 10} años, Club {index})</li>"
        for index in range(1, 27)
    )
    listing_html = """
    <main>
      <article>
        <a href="https://www.alterfutbol.com/concacaf/mexico/lista/">
          Los convocados de México al Mundial 2026: el análisis de la lista
        </a>
      </article>
    </main>
    """
    article_html = f"""
    <article>
      <h1>Los convocados de México</h1>
      <h3>Arqueros</h3>
      <ul>{player_items}</ul>
    </article>
    """

    manifest = build_source_manifest(
        groups_data={"groups": [{"id": "A", "teams": ["mex", "jor"]}]},
        news_pages=[listing_html],
        fetch_article_html=lambda url: article_html,
    )
    by_code = {team["team_code"]: team for team in manifest["teams"]}

    assert manifest["meta"]["total_teams"] == 2
    assert by_code["mex"]["status"] == "complete"
    assert by_code["mex"]["url"] == "https://www.alterfutbol.com/concacaf/mexico/lista/"
    assert by_code["mex"]["player_count"] == 26
    assert by_code["jor"]["status"] == "missing_article"
    assert by_code["jor"]["players"] == []


def test_resolve_output_path_makes_relative_paths_repo_local():
    output = resolve_output_path("data/alterfutbol_sources.json")

    assert output.is_absolute()
    assert output.name == "alterfutbol_sources.json"
    assert output.parent.name == "data"
