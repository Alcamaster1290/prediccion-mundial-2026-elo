import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.update_club_elo_from_worldclubratings import parse_worldclubratings_html  # noqa: E402


def test_parse_worldclubratings_html_extracts_embedded_rank_table():
    html = """
    <html>
      <script type="application/json" data-for="rankdt">
        {"x":{"data":[
          [1,"","Brighton &amp; Hove Albion","England",1680,"","+1"],
          [2,"","OGC Nizza","France","1384","","-2"]
        ]}}
      </script>
    </html>
    """

    clubs = parse_worldclubratings_html(html)

    assert clubs == [
        {"rank": 1, "club": "Brighton & Hove Albion", "country": "England", "elo": 1680},
        {"rank": 2, "club": "OGC Nizza", "country": "France", "elo": 1384},
    ]


def test_parse_worldclubratings_html_extracts_row_wise_table_with_many_clubs():
    html = """
    <html>
      <script type="application/json" data-for="rankdt">
        {"x":{"data":[
          [1,"","Brighton &amp; Hove Albion","England",1680,"","+1"],
          [2,"","OGC Nizza","France","1384","","-2"],
          [3,"","Milan","Italy",1688,"","+4"],
          [4,"","Arsenal","England",2106,"","0"],
          [5,"","Paris SG","France",2038,"","-1"]
        ]}}
      </script>
    </html>
    """

    clubs = parse_worldclubratings_html(html)

    assert clubs == [
        {"rank": 1, "club": "Brighton & Hove Albion", "country": "England", "elo": 1680},
        {"rank": 2, "club": "OGC Nizza", "country": "France", "elo": 1384},
        {"rank": 3, "club": "Milan", "country": "Italy", "elo": 1688},
        {"rank": 4, "club": "Arsenal", "country": "England", "elo": 2106},
        {"rank": 5, "club": "Paris SG", "country": "France", "elo": 2038},
    ]


def test_parse_worldclubratings_html_extracts_columnar_rank_table():
    html = """
    <script data-for="rankdt" type="application/json">
      {"x":{"data":[
        [1,2],
        [0,0],
        ["Brighton &amp; Hove Albion","OGC Nizza"],
        ["England","France"],
        [1680,"1384"],
        [0,0],
        ["id1","id2"]
      ]}}
    </script>
    """

    clubs = parse_worldclubratings_html(html)

    assert clubs == [
        {"rank": 1, "club": "Brighton & Hove Albion", "country": "England", "elo": 1680},
        {"rank": 2, "club": "OGC Nizza", "country": "France", "elo": 1384},
    ]


def test_parse_worldclubratings_html_skips_blank_clubs():
    html = """
    <script data-for="rankdt" type="application/json">
      {"x":{"data":[
        [1,2],
        [0,0],
        ["","OGC Nizza"],
        ["","France"],
        [1076,1384],
        [0,0],
        ["blank","id2"]
      ]}}
    </script>
    """

    clubs = parse_worldclubratings_html(html)

    assert clubs == [
        {"rank": 2, "club": "OGC Nizza", "country": "France", "elo": 1384},
    ]
