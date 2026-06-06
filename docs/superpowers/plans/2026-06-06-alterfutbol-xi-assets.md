# AlterFutbol XI Assets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Download source-backed XI formation images for squad-only teams and enrich their team records with tactical system and tactics text from AlterFutbol articles.

**Architecture:** Extend the existing scraper with deterministic article-content extraction for `scheme` and `tactics`, then add an enrichment script that reads `data/alterfutbol_sources.json`, downloads `formation_images[0]` to `assets/xi/{code}-xi.png`, and updates only source-backed fields in `data/teams.json`. The script does not mark `players[].titular`; starter marking stays for the later image-reading/manual-validation phase.

**Tech Stack:** Python 3.13, requests, BeautifulSoup, existing JSON data files and content manifest.

---

### Task 1: Parser Contract

**Files:**
- Modify: `tests/test_alterfutbol_scraper.py`
- Modify: `scripts/scrape_alterfutbol_news.py`

- [ ] **Step 1: Write failing tests for tactical extraction**

Add tests that assert `extract_tactical_info_from_article()` returns a scheme such as `4-3-3` and the paragraphs under the tactical/XI heading.

- [ ] **Step 2: Run focused tests**

Run: `python -m pytest tests/test_alterfutbol_scraper.py -q`

Expected: FAIL because the tactical extractor does not exist.

- [ ] **Step 3: Implement minimal tactical extractor**

Add helper functions that select the real article content root, locate tactical headings, collect following paragraphs until the next heading, and extract the first tactical system pattern.

- [ ] **Step 4: Verify focused tests**

Run: `python -m pytest tests/test_alterfutbol_scraper.py -q`

Expected: PASS.

### Task 2: Enrichment Contract

**Files:**
- Create: `tests/test_enrich_alterfutbol_xi_assets.py`
- Create: `scripts/enrich_alterfutbol_xi_assets.py`

- [ ] **Step 1: Write failing enrichment tests**

Test that a squad-only team receives `scheme`, `tactics`, `xi_image`, `xi_source_url`, and `source_tactics_url`, while existing XI files are not overwritten unless explicitly requested.

- [ ] **Step 2: Run focused tests**

Run: `python -m pytest tests/test_enrich_alterfutbol_xi_assets.py -q`

Expected: FAIL because the enrichment module does not exist.

- [ ] **Step 3: Implement enrichment module**

Use injected download/fetch functions for testability; the CLI uses requests to fetch article HTML and image bytes.

- [ ] **Step 4: Verify focused tests**

Run: `python -m pytest tests/test_enrich_alterfutbol_xi_assets.py -q`

Expected: PASS.

### Task 3: Apply Data and Asset Changes

**Files:**
- Modify: `data/teams.json`
- Create: `assets/xi/{code}-xi.png` for missing squad-only XI images
- Modify: `assets/xi/README.txt`
- Regenerate: `data/team-content-manifest.json`

- [ ] **Step 1: Run enrichment script**

Run: `python scripts/enrich_alterfutbol_xi_assets.py`

Expected: Missing XI images downloaded, existing `mar-xi.png` and `pan-xi.png` preserved, squad-only records enriched with source-backed tactical fields.

- [ ] **Step 2: Regenerate manifest**

Run: `python scripts/build_team_content_manifest.py`

Expected: `xi_image` local asset coverage improves for the squad-only teams.

- [ ] **Step 3: Update README**

Update `assets/xi/README.txt` with the new local files and clarify that titular marking will be handled after image review.

### Task 4: Verification

**Files:**
- Validate all touched files.

- [ ] **Step 1: Run data validation**

Run: `python scripts/validate_data.py`

Expected: PASS with only existing `match_context` warnings.

- [ ] **Step 2: Run test suite**

Run: `python -m pytest -q`

Expected: PASS.
