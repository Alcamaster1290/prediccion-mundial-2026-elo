# AlterFutbol Data Quality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scrape AlterFutbol noticias, document traceable article/image sources, and populate only source-backed team data for the app/Supabase seed flow.

**Architecture:** Add a small scraper/parser that creates a source manifest from AlterFutbol article pages, then use that manifest to update existing README files and append squad-only teams to `data/teams.json` only when the article yields exactly 26 players. Derived manifest/SQL files are regenerated from existing scripts; no live Supabase write is performed.

**Tech Stack:** Python 3.13, `requests`, `beautifulsoup4`, JSON data files, existing Supabase seed/export scripts.

---

### Task 1: Scraper Contract

**Files:**
- Create: `tests/test_alterfutbol_scraper.py`
- Create: `scripts/scrape_alterfutbol_news.py`
- Modify: `requirements.txt`

- [ ] **Step 1: Write failing parser tests**

Create `tests/test_alterfutbol_scraper.py` with tests for both source formats and country normalization.

- [ ] **Step 2: Run test to verify RED**

Run: `python -m pytest tests/test_alterfutbol_scraper.py -q`

Expected: FAIL because `scripts.scrape_alterfutbol_news` does not exist.

- [ ] **Step 3: Implement minimal parser and dependency declarations**

Add `requests>=2.31` and `beautifulsoup4>=4.12` to `requirements.txt`. Create `scripts/scrape_alterfutbol_news.py` with `normalize_country_name()` and `extract_players_from_article()` using BeautifulSoup and explicit positional heading mapping.

- [ ] **Step 4: Run test to verify GREEN**

Run: `python -m pytest tests/test_alterfutbol_scraper.py -q`

Expected: PASS.

### Task 2: Source Manifest Generation

**Files:**
- Modify: `tests/test_alterfutbol_scraper.py`
- Modify: `scripts/scrape_alterfutbol_news.py`
- Generate: `data/alterfutbol_sources.json`

- [ ] **Step 1: Add failing manifest test**

Extend `tests/test_alterfutbol_scraper.py` with a fixture that proves one article row includes `team_code`, `url`, `title`, `published_date`, `featured_image`, `image_urls`, `formation_images`, `players`, and `status`.

- [ ] **Step 2: Run test to verify RED**

Run: `python -m pytest tests/test_alterfutbol_scraper.py -q`

Expected: FAIL because manifest assembly is missing.

- [ ] **Step 3: Implement manifest builder**

Implement paginated news scraping from `https://www.alterfutbol.com/noticias/`, country-code mapping from `data/groups.json`, article parsing, and JSON output. Mark teams as `complete` only when the player list has 26 rows; mark `article_only`, `missing_article`, or `needs_manual_review` otherwise.

- [ ] **Step 4: Generate source manifest**

Run: `python scripts/scrape_alterfutbol_news.py --max-pages 30 --output data/alterfutbol_sources.json`

Expected: JSON with 48 team rows, direct AlterFutbol URLs for found articles, and no fabricated players.

### Task 3: README Source Audit

**Files:**
- Modify: `assets/players/README.txt`
- Modify: `assets/xi/README.txt`

- [ ] **Step 1: Update existing README files**

Use `data/alterfutbol_sources.json` and actual asset files to correct counts, file extensions, legacy asset codes, direct article URLs, image source URLs, and missing-source notes.

- [ ] **Step 2: Verify README consistency**

Run: `python scripts/build_team_content_manifest.py`

Expected: manifest generation succeeds and `mar-xi.png` / `pan-xi.png` are treated as existing local assets.

### Task 4: Reliable Squad Data

**Files:**
- Modify: `data/teams.json`
- Regenerate: `data/seed_players.sql`
- Regenerate: `data/team-content-manifest.json`

- [ ] **Step 1: Add squad-only teams from complete source articles**

Append missing teams from `data/alterfutbol_sources.json` only where `status == "complete"` and `players` has 26 rows. Set `analyzed` to `false`, `source_url` to the article URL, `source_status` to `squad_only`, `titular` to `false`, and `elo` to `null` unless an exact existing club ELO match is available.

- [ ] **Step 2: Regenerate local derived data**

Run `python scripts/build_team_content_manifest.py` and `python scripts/generate_seed_sql.py`.

Expected: `data/team-content-manifest.json` and `data/seed_players.sql` reflect the larger source-backed player set.

### Task 5: Verification

**Files:**
- Validate: all touched files

- [ ] **Step 1: Run data validation**

Run: `python scripts/validate_data.py`

Expected: PASS or only pre-existing documented warnings.

- [ ] **Step 2: Run test suite**

Run: `python -m pytest -q`

Expected: PASS.

- [ ] **Step 3: Review diff**

Run: `git diff --stat` and inspect key data diffs for accidental generated/fabricated content.
