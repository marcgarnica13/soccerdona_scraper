# soccerdonna_scraper — Plan 1: Player Backbone Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Scrapy project that scrapes soccerdonna.de's women's-football hierarchy (competitions → clubs → players → appearances) and emits JSON-Lines whose schema mirrors the transfermarkt-scraper exactly.

**Architecture:** Port transfermarkt-scraper's `BaseSpider` scaffolding and JSON-Lines/`parent`-linkage convention near-verbatim, then adapt URL/ID grammar and CSS selectors to soccerdonna. Spiders pipe to each other via `-a parents=<file>` or stdin. A synthetic `confederations` root keeps the pipe shape identical to TM.

**Tech Stack:** Python 3 (^3.9), Scrapy ^2.11, Poetry, inflection, python-dateutil, pytest (dev). Output = JSON-Lines to stdout.

**Spec:** `docs/superpowers/specs/2026-06-25-soccerdonna-scraper-design.md`

**Reference repo:** `/home/marc/Development/gemini/transfermarkt-scraper` (read freely for patterns).

---

## Conventions used in this plan

- **Package name:** `soccerdonna` (parallels TM's `tfmkt`).
- **Base URL:** `https://www.soccerdonna.de`. Stored hrefs include the `/en/...` prefix (e.g. `/en/fc-barcelona/startseite/verein_1132.html`).
- **Run spiders from the repo root** with Poetry: `poetry run scrapy crawl <name> ...`.
- **Sample-driven TDD:** soccerdonna's exact CSS selectors are unknown until you look at real HTML, and a single page can hide structural variation (lower-tier clubs, players with no national career, sparse stat tables). So **Task 1A collects the first 5 real pages of every type into `samples/pages/<type>/`** (plus guaranteed anchor pages) via a reproducible script. Each parser task then writes two kinds of tests against those samples: (a) a **structural-invariant test that iterates over all 5 samples** of that type and asserts required fields/types are present on each, and (b) an **anchor test that asserts concrete values** (listed inline, observed live on 2026-06-25) against one known page. You then adjust selectors until both pass. The assertions are fixed truth; only the selectors are unknown. Running the parser across 5 varied pages is what catches selector fragility a single fixture would miss.
- **Two `samples/` subdirs, kept distinct:** `samples/pages/` holds the raw **input** HTML the parsers read (the 5-of-each collection, committed so tests are offline/deterministic). `samples/output/` holds the JSON-Lines **output** the spiders produce (generated in Task 11). Don't conflate them.
- **Anchor data points** (observed live on 2026-06-25, use these in tests):
  - Spain women's first tier: competition code `ESP1`, slug `primera-division-femenina`, competition page `/en/primera-division-femenina/startseite/wettbewerb_ESP1.html`.
  - FC Barcelona: club id `1132`, page `/en/fc-barcelona/startseite/verein_1132.html`, squad `/en/fc-barcelona/kader/verein_1132.html`. Squad includes Alexia Putellas (`spieler_4824`) and Ewa Pajor (`spieler_22010`).
  - Gemma Font: player id `38461`, profile `/en/gemma-font/profil/spieler_38461.html`. DOB `23.10.1999`, position `Goalkeeper`, height `1,65`, nationality `Spain`, foot `right`, market value `€50,000`, name in native country `Gemma Font Oliveras`, contract until `30.06.2027`, current club FC Barcelona.
  - Performance data sub-page pattern: `/en/{name}/leistungsdaten/spieler_{id}.html`.

---

## File Structure

```
soccerdonna_scraper/
  scrapy.cfg                         # Scrapy project pointer
  pyproject.toml                     # Poetry deps + pytest config
  soccerdonna/
    __init__.py
    settings.py                      # Scrapy settings (politeness, jsonlines, cache)
    utils.py                         # ID-extraction + parsing helpers
    spiders/
      __init__.py
      common.py                      # BaseSpider: parent loading (stdin/file/gzip)
      common_comp_club.py            # BaseSpider subclass: season + URL building
      confederations.py              # synthetic root → index page
      competitions.py                # index → competitions (per country + international)
      clubs.py                       # competition → clubs + inline squad players
      clubs_by_url.py                # club URLs → clubs (bypass)
      players.py                     # clubs → player profiles + national career
      players_from_file.py           # player URLs → players (bypass)
      appearances.py                 # players → per-match appearance rows
  scripts/
    collect_samples.sh               # downloads first 5 real pages of each type
  tests/
    __init__.py
    conftest.py                      # sample-loading helpers (load_sample / iter_samples)
    test_utils.py
    test_confederations_spider.py
    test_competitions_spider.py
    test_clubs_spider.py
    test_players_spider.py
    test_appearances_spider.py
  samples/
    pages/                           # raw INPUT html the parsers read (committed)
      index/                         #   the competitions index page
      competition/                   #   5 competition pages (e.g. ESP1.html)
      club/                          #   5 squad/kader pages (e.g. verein_1132.html)
      player/                        #   5 player profiles (e.g. spieler_38461.html)
      appearance/                    #   5 performance-data pages (e.g. spieler_38461.html)
    output/                          # generated JSON-Lines OUTPUT per entity (Task 11)
  README.md
  DOCUMENTATION.md
  SCHEMA.md
  API_REFERENCE.md
```

Each file has one responsibility. `utils.py` holds pure functions (easy to unit-test offline). `common.py` holds parent-loading I/O. `common_comp_club.py` holds URL/season construction. Each spider holds only its own parse logic.

---

## Task 0: Repository scaffolding & tooling

**Files:**
- Create: `pyproject.toml`, `scrapy.cfg`, `soccerdonna/__init__.py`, `soccerdonna/spiders/__init__.py`, `tests/__init__.py`

- [ ] **Step 1: Initialize git**

Run:
```bash
cd /home/marc/Development/gemini/soccerdona_scraper
git init
```
Expected: `Initialized empty Git repository`.

- [ ] **Step 2: Create `pyproject.toml`**

```toml
[tool.poetry]
name = "soccerdonna-scraper"
version = "0.1.0"
description = "Collects women's football data from the soccerdonna.de website"
authors = ["Gemini Sports"]
packages = [{include = "soccerdonna"}]

[tool.poetry.dependencies]
python = "^3.9"
inflection = "^0.5.1"
Protego = "^0.2.1"
python-dateutil = "^2.8.2"
scrapy = "^2.11.0"

[tool.poetry.group.dev.dependencies]
pytest = "^8.0.0"

[tool.pytest.ini_options]
testpaths = ["tests"]

[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"
```

- [ ] **Step 3: Create `scrapy.cfg`**

```ini
[settings]
default = soccerdonna.settings

[deploy]
project = soccerdonna
```

- [ ] **Step 4: Create empty package markers**

Create these three empty files: `soccerdonna/__init__.py`, `soccerdonna/spiders/__init__.py`, `tests/__init__.py`.

- [ ] **Step 5: Create `.gitignore`**

```gitignore
.venv/
__pycache__/
*.pyc
httpcache/
.scrapy/
.pytest_cache/
*.egg-info/
```

- [ ] **Step 6: Install deps**

Run: `poetry install`
Expected: Poetry creates a venv and installs Scrapy + pytest without error.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "chore: scaffold soccerdonna scrapy project"
```

---

## Task 1: Scrapy settings

**Files:**
- Create: `soccerdonna/settings.py`

- [ ] **Step 1: Write `soccerdonna/settings.py`**

```python
# -*- coding: utf-8 -*-
BOT_NAME = 'soccerdonna'

SPIDER_MODULES = ['soccerdonna.spiders']
NEWSPIDER_MODULE = 'soccerdonna.spiders'

# Obey robots.txt rules
ROBOTSTXT_OBEY = True

# Identify ourselves honestly
USER_AGENT = 'soccerdonna-scraper (+https://github.com/gemini-sports; women-football research)'

FEED_FORMAT = 'jsonlines'
FEED_URI = 'stdout:'

# soccerdonna is a small site — crawl gently.
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1.0
AUTOTHROTTLE_MAX_DELAY = 10.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
DOWNLOAD_DELAY = 1.0
CONCURRENT_REQUESTS_PER_DOMAIN = 2

EXTENSIONS = {
    'scrapy.extensions.closespider.CloseSpider': 500
}
DOWNLOADER_MIDDLEWARES = {
    'scrapy.downloadermiddlewares.httpcache.HttpCacheMiddleware': 500
}

CLOSESPIDER_PAGECOUNT = 0
LOG_LEVEL = 'ERROR'

# HTTP cache (development aid)
HTTPCACHE_ENABLED = True
HTTPCACHE_DIR = 'httpcache'

REQUEST_FINGERPRINTER_IMPLEMENTATION = '2.7'
```

- [ ] **Step 2: Verify Scrapy sees the project**

Run: `poetry run scrapy list`
Expected: command succeeds and prints nothing yet (no spiders) — confirms settings import cleanly. (An ImportError here means a typo in settings.py.)

- [ ] **Step 3: Commit**

```bash
git add soccerdonna/settings.py
git commit -m "feat: add scrapy settings with autothrottle + jsonlines"
```

---

## Task 1A: Collect page samples (first 5 of each page type)

Download the first 5 real pages of every type the scraper will parse, into
`samples/pages/<type>/`, plus guaranteed anchor pages (ESP1, FC Barcelona,
Gemma Font) so the anchor tests are deterministic. These committed samples are
the offline inputs every parser test reads. A reproducible script means anyone
can refresh them.

**Files:**
- Create: `scripts/collect_samples.sh`, `tests/conftest.py`
- Create (output of the script): `samples/pages/{index,competition,club,player,appearance}/*.html`

- [ ] **Step 1: Write `scripts/collect_samples.sh`**

```bash
#!/usr/bin/env bash
# Collect the first 5 real pages of each soccerdonna page type into
# samples/pages/<type>/, plus guaranteed anchor pages. Idempotent; re-run to refresh.
set -euo pipefail

BASE='https://www.soccerdonna.de'
UA='soccerdonna-scraper (+research; women-football)'
INDEX='/en/2010/startseite/wettbewerbeDE.html'
OUT='samples/pages'

# Anchors we always want present (used by exact-value tests)
ANCHOR_COMP='/en/primera-division-femenina/startseite/wettbewerb_ESP1.html'
ANCHOR_CLUB='/en/fc-barcelona/kader/verein_1132.html'
ANCHOR_PLAYER='/en/gemma-font/profil/spieler_38461.html'

mkdir -p "$OUT"/{index,competition,club,player,appearance}
get() { curl -fsS -A "$UA" "$BASE$1" -o "$2"; echo "saved $2"; }

# pick first N hrefs matching a regex from a file, anchor first, de-duplicated
pick() { # <htmlfile> <regex> <anchor-href> <n>
  { echo "$3"; grep -oE "$2" "$1" || true; } | awk '!seen[$0]++' | head -n "$4"
}

# 1) Index page
get "$INDEX" "$OUT/index/wettbewerbeDE.html"

# 2) First 5 competitions (ESP1 anchored first). NOTE: index competition links
#    are mostly under /de/; normalize to /en/ so every downstream page and its
#    child links come back in English (verified: /en/ pages emit /en/ links).
mapfile -t COMPS < <(
  { echo "$ANCHOR_COMP";
    grep -oE '/(de|en)/[^"]*wettbewerb_[A-Za-z0-9]+\.html' "$OUT/index/wettbewerbeDE.html" \
      | sed 's#^/de/#/en/#'; } | awk '!seen[$0]++' | head -n 5)
for href in "${COMPS[@]}"; do
  code=$(echo "$href" | grep -oE 'wettbewerb_[A-Za-z0-9]+' | sed 's/wettbewerb_//')
  get "$href" "$OUT/competition/${code}.html"
done

# 3) First 5 clubs from those competition pages (Barcelona anchored first).
#    Convert /startseite/ club hrefs to their /kader/ squad page; force /en/.
CLUB_SRC=$(cat "$OUT"/competition/*.html)
mapfile -t CLUBS < <(printf '%s' "$CLUB_SRC" \
  | grep -oE '/(de|en)/[^"]*verein_[0-9]+\.html' \
  | sed -e 's#^/de/#/en/#' -e 's#/startseite/#/kader/#' \
  | { echo "$ANCHOR_CLUB"; cat; } | awk '!seen[$0]++' | head -n 5)
for href in "${CLUBS[@]}"; do
  id=$(echo "$href" | grep -oE 'verein_[0-9]+')
  get "$href" "$OUT/club/${id}.html"
done

# 4) First 5 players from those squad pages (Gemma Font anchored first); force /en/.
PLAYER_SRC=$(cat "$OUT"/club/*.html)
mapfile -t PLAYERS < <(printf '%s' "$PLAYER_SRC" \
  | grep -oE '/(de|en)/[^"]*spieler_[0-9]+\.html' \
  | sed 's#^/de/#/en/#' \
  | { echo "$ANCHOR_PLAYER"; cat; } | awk '!seen[$0]++' | head -n 5)
for href in "${PLAYERS[@]}"; do
  id=$(echo "$href" | grep -oE 'spieler_[0-9]+')
  get "$href" "$OUT/player/${id}.html"
  # 5) Matching performance-data (appearance) page for each player
  app_href=$(echo "$href" | sed 's#/profil/#/leistungsdaten/#')
  get "$app_href" "$OUT/appearance/${id}.html"
done

echo "Done. Sample counts:"
for d in index competition club player appearance; do
  echo "  $d: $(ls -1 "$OUT/$d" | wc -l)"
done
```

- [ ] **Step 2: Run the collector**

Run:
```bash
chmod +x scripts/collect_samples.sh
./scripts/collect_samples.sh
```
Expected: prints `saved ...` lines and a final count of `competition: 5`, `club: 5`,
`player: 5`, `appearance: 5`, `index: 1`. If a type collects fewer than 5
(e.g. the index regex misses links), inspect the index HTML and widen the regex
before continuing — the parser tasks depend on these samples.

- [ ] **Step 3: Confirm the anchors landed**

Run:
```bash
ls samples/pages/competition/ESP1.html \
   samples/pages/club/verein_1132.html \
   samples/pages/player/spieler_38461.html \
   samples/pages/appearance/spieler_38461.html
```
Expected: all four paths exist. (These back the exact-value tests.)

- [ ] **Step 4: Write `tests/conftest.py` (sample loaders)**

```python
import os
import glob
import pytest
from scrapy.http import HtmlResponse

SAMPLES = os.path.join(os.path.dirname(__file__), '..', 'samples', 'pages')
BASE = 'https://www.soccerdonna.de'


def _url_for(category, filename):
    """Best-effort reconstruct a plausible page URL from the sample filename."""
    stem = filename.replace('.html', '')
    if category == 'index':
        return f'{BASE}/en/2010/startseite/wettbewerbeDE.html'
    if category == 'competition':
        return f'{BASE}/en/x/startseite/wettbewerb_{stem}.html'
    if category == 'club':
        return f'{BASE}/en/x/kader/{stem}.html'
    if category == 'player':
        return f'{BASE}/en/x/profil/{stem}.html'
    if category == 'appearance':
        return f'{BASE}/en/x/leistungsdaten/{stem}.html'
    return f'{BASE}/en/{stem}.html'


def load_sample(category, filename):
    """Load one named sample as a Scrapy HtmlResponse."""
    path = os.path.join(SAMPLES, category, filename)
    with open(path, 'rb') as f:
        body = f.read()
    return HtmlResponse(url=_url_for(category, filename), body=body, encoding='utf-8')


def iter_samples(category):
    """Yield (filename, HtmlResponse) for every sample of a category."""
    for path in sorted(glob.glob(os.path.join(SAMPLES, category, '*.html'))):
        filename = os.path.basename(path)
        yield filename, load_sample(category, filename)


# Expose helpers as fixtures too, for convenience.
@pytest.fixture
def samples():
    return iter_samples
```

- [ ] **Step 5: Commit**

```bash
git add scripts/collect_samples.sh tests/conftest.py samples/pages/
git commit -m "test: collect 5 real page samples per type + sample loaders"
```

---

## Task 2: `utils.py` — ID extraction helpers (pure functions, full TDD)

soccerdonna IDs live in the `_{digits}.html` suffix and competition codes in `wettbewerb_{CODE}`. These are pure functions — fully testable offline.

**Files:**
- Create: `soccerdonna/utils.py`
- Test: `tests/test_utils.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_utils.py
from soccerdonna.utils import (
    extract_entity_id,
    extract_competition_code,
    parse_market_value,
    parse_date_de,
)


def test_extract_entity_id_from_player_href():
    assert extract_entity_id("/en/gemma-font/profil/spieler_38461.html") == "38461"


def test_extract_entity_id_from_club_href():
    assert extract_entity_id("/en/fc-barcelona/startseite/verein_1132.html") == "1132"


def test_extract_entity_id_returns_none_when_absent():
    assert extract_entity_id("/en/2010/startseite/wettbewerbeDE.html") is None


def test_extract_competition_code():
    href = "/en/primera-division-femenina/startseite/wettbewerb_ESP1.html"
    assert extract_competition_code(href) == "ESP1"


def test_parse_market_value_euros():
    assert parse_market_value("€50,000") == 50000


def test_parse_market_value_handles_blank():
    assert parse_market_value("-") is None
    assert parse_market_value("") is None
    assert parse_market_value(None) is None


def test_parse_date_de():
    # soccerdonna uses DD.MM.YYYY
    assert parse_date_de("23.10.1999") == "1999-10-23"


def test_parse_date_de_handles_blank():
    assert parse_date_de("") is None
    assert parse_date_de(None) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest tests/test_utils.py -v`
Expected: FAIL with `ImportError`/`ModuleNotFoundError` (utils functions not defined yet).

- [ ] **Step 3: Write `soccerdonna/utils.py`**

```python
import re
from datetime import datetime


def extract_entity_id(href: str) -> str | None:
    """Extract the numeric id from a soccerdonna href.

    soccerdonna encodes ids as a `_<digits>.html` suffix, e.g.
    `verein_1132.html`, `spieler_38461.html`, `spielbericht_153373.html`.
    Returns the digits as a string, or None if there is no id (e.g. the
    competitions index page).
    """
    if not href:
        return None
    match = re.search(r'_(\d+)\.html', href)
    return match.group(1) if match else None


def extract_competition_code(href: str) -> str | None:
    """Extract the competition code from a soccerdonna competition href.

    e.g. `/en/primera-division-femenina/startseite/wettbewerb_ESP1.html` -> `ESP1`.
    """
    if not href:
        return None
    match = re.search(r'wettbewerb_([A-Za-z0-9]+)\.html', href)
    return match.group(1) if match else None


def parse_market_value(value: str) -> int | None:
    """Parse a soccerdonna market value string like '€50,000' into an int (euros).

    Returns None for blank/placeholder values ('', '-', '?', None).
    """
    if not value:
        return None
    digits = re.sub(r'[^0-9]', '', value)
    return int(digits) if digits else None


def parse_date_de(value: str) -> str | None:
    """Convert a soccerdonna DD.MM.YYYY date into ISO YYYY-MM-DD.

    Returns None for blank input.
    """
    if not value:
        return None
    value = value.strip()
    try:
        return datetime.strptime(value, "%d.%m.%Y").strftime("%Y-%m-%d")
    except ValueError:
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `poetry run pytest tests/test_utils.py -v`
Expected: PASS (8 passed).

- [ ] **Step 5: Commit**

```bash
git add soccerdonna/utils.py tests/test_utils.py
git commit -m "feat: add id/value/date parsing utils with tests"
```

---

## Task 3: `common.py` — parent-loading BaseSpider (ported verbatim)

This is copied from TM with only `default_base_url` changed. It loads parent items from a file, gzip, or stdin and strips redundant nested `parent`.

**Files:**
- Create: `soccerdonna/spiders/common.py`

- [ ] **Step 1: Write `soccerdonna/spiders/common.py`**

```python
from io import BufferedReader
import scrapy
from scrapy import Request
import os, sys
import json
import gzip
import typing

default_base_url = 'https://www.soccerdonna.de'


def read_lines(file_name: str, reading_fn: typing.Callable[[str], BufferedReader]) -> typing.List[dict]:
    with reading_fn(file_name) as f:
        lines = f.readlines()
        parents = [json.loads(line) for line in lines]
    return parents


class BaseSpider(scrapy.Spider):
    def __init__(self, base_url=None, parents=None):
        if base_url is not None:
            self.base_url = base_url
        else:
            self.base_url = default_base_url

        # Determine whether the parents file is gzip compressed.
        if parents is not None:
            extension = parents.split(".")[-1]
            self.gzip_compressed = (extension == "gz") if extension else False
        else:
            self.gzip_compressed = False

        # Load parent objects either from a file, zipped file, or stdin.
        if parents is not None:
            if self.gzip_compressed:
                parents = read_lines(parents, gzip.open)
            else:
                parents = read_lines(parents, open)
        elif not sys.stdin.isatty():
            parents = [json.loads(line) for line in sys.stdin]
        else:
            parents = self.scrape_parents()

        # Second-level parents are redundant.
        for parent in parents:
            if parent.get('parent') is not None:
                del parent['parent']

        self.entrypoints = parents

    def scrape_parents(self):
        if not os.environ.get('SCRAPY_CHECK'):
            raise Exception("Backfilling is not yet supported, please provide a 'parents' file")
        else:
            return []

    def start_requests(self):
        applicable_items = []
        for item in self.entrypoints:
            item['seasoned_href'] = self.seasonize_entrypoin_href(item)
            applicable_items.append(item)

        return [
            Request(item['seasoned_href'], cb_kwargs={'parent': item})
            for item in applicable_items
        ]

    def seasonize_entrypoin_href(self, item):
        # Overridden in common_comp_club.BaseSpider; default is a plain join.
        return f"{self.base_url}{item['href']}"

    def safe_strip(self, word):
        return word.strip() if word else word
```

- [ ] **Step 2: Commit**

```bash
git add soccerdonna/spiders/common.py
git commit -m "feat: add parent-loading BaseSpider"
```

---

## Task 4: `common_comp_club.py` — season-aware URL building

soccerdonna's season URL grammar is one of the spec's flagged unknowns. **Before writing this file, verify the grammar against a real page** (Step 1). The implementation below is the working hypothesis; adjust the `seasonize_entrypoin_href` body to whatever the fixture proves.

**Files:**
- Create: `soccerdonna/spiders/common_comp_club.py`
- Test: `tests/test_competitions_spider.py` (season URL assertions added here, spider added in Task 6)

- [ ] **Step 1: Verify season grammar (manual, no code)**

Use the samples collected in Task 1A:
```bash
grep -oE 'saison_id[/=][0-9]+' samples/pages/club/verein_1132.html | head
grep -oE 'verein_[0-9]+(/saison_id/[0-9]+)?\.html' samples/pages/competition/ESP1.html | head
```
Look at how a non-current season is encoded on club/competition links. Note the exact pattern (path segment `/saison_id/{year}` vs query string vs none). Record it in a one-line comment at the top of the file you create in Step 2.

- [ ] **Step 2: Write `soccerdonna/spiders/common_comp_club.py`**

```python
from soccerdonna.spiders.common import BaseSpider as _BaseSpider, read_lines, default_base_url
import re


class BaseSpider(_BaseSpider):
    """BaseSpider that knows how to seasonize soccerdonna entrypoint URLs.

    `season` is an optional spider argument (`-a season=2024`). When unset, the
    site's default/current season is used (no season segment added).

    NOTE: confirm soccerdonna's season grammar against a real page (see plan
    Task 4 Step 1). The grammar below assumes a `/saison_id/{season}` path
    segment inserted before the `.html` suffix.
    """

    def __init__(self, season=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.season = season

    def seasonize_entrypoin_href(self, item):
        # Strip any existing season segment first, so re-runs are idempotent.
        base_href = re.sub(r'/saison_id/\d+', '', item['href'])

        if self.season:
            # Insert `/saison_id/{season}` before the `.html` suffix.
            seasoned = re.sub(r'\.html$', f'/saison_id/{self.season}.html', base_href)
            return f"{self.base_url}{seasoned}"

        return f"{self.base_url}{base_href}"
```

- [ ] **Step 3: Write the failing test**

```python
# tests/test_competitions_spider.py  (season-building portion)
from soccerdonna.spiders.competitions import CompetitionsSpider


def test_seasonize_without_season_is_plain_join():
    spider = CompetitionsSpider()
    item = {'type': 'competition',
            'href': '/en/primera-division-femenina/startseite/wettbewerb_ESP1.html'}
    url = spider.seasonize_entrypoin_href(item)
    assert url == ('https://www.soccerdonna.de'
                   '/en/primera-division-femenina/startseite/wettbewerb_ESP1.html')


def test_seasonize_with_season_inserts_segment():
    spider = CompetitionsSpider(season='2024')
    item = {'type': 'competition',
            'href': '/en/primera-division-femenina/startseite/wettbewerb_ESP1.html'}
    url = spider.seasonize_entrypoin_href(item)
    assert '/saison_id/2024' in url
    assert url.endswith('.html')
```

(This test can only run after Task 6 creates `competitions.py`. If executing strictly in order, write the test now and expect a collection error until Task 6; or move these two test functions to run alongside Task 6. Either way, the season grammar adjustment from Step 1 must keep `test_seasonize_with_season_inserts_segment` green.)

- [ ] **Step 4: Commit**

```bash
git add soccerdonna/spiders/common_comp_club.py
git commit -m "feat: add season-aware url building base spider"
```

---

## Task 5: `confederations` spider — synthetic root

soccerdonna has no confederations. Emit a single synthetic root pointing at the competitions index, carrying an honest `name`/`source` marker.

**Files:**
- Create: `soccerdonna/spiders/confederations.py`
- Test: `tests/test_confederations_spider.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_confederations_spider.py
from soccerdonna.spiders.confederations import ConfederationsSpider, INDEX_HREF


def test_scrape_parents_returns_root():
    spider = ConfederationsSpider()
    parents = spider.scrape_parents()
    assert parents == [{'type': 'root', 'href': ''}]


def test_parse_yields_single_synthetic_confederation():
    spider = ConfederationsSpider()
    results = list(spider.parse(response=None))
    assert len(results) == 1
    conf = results[0]
    assert conf['type'] == 'confederation'
    assert conf['href'] == INDEX_HREF
    assert conf['source'] == 'soccerdonna'
    assert conf['name'] == 'soccerdonna'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest tests/test_confederations_spider.py -v`
Expected: FAIL with `ModuleNotFoundError` (spider not defined).

- [ ] **Step 3: Write `soccerdonna/spiders/confederations.py`**

```python
from soccerdonna.spiders.common_comp_club import BaseSpider

# The competitions index. The leading path segment ("2010") is the site's
# index identifier, NOT a season — verify against the live site if coverage
# looks wrong. See spec section 7 (unknowns).
INDEX_HREF = '/en/2010/startseite/wettbewerbeDE.html'


class ConfederationsSpider(BaseSpider):
    name = 'confederations'

    def scrape_parents(self):
        return [{'type': 'root', 'href': ''}]

    def parse(self, response, **kwargs):
        yield {
            'type': 'confederation',
            'href': INDEX_HREF,
            'name': 'soccerdonna',
            'source': 'soccerdonna',
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `poetry run pytest tests/test_confederations_spider.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Smoke-test the real crawl**

Run: `poetry run scrapy crawl confederations`
Expected: one JSON line to stdout:
`{"type": "confederation", "href": "/en/2010/startseite/wettbewerbeDE.html", "name": "soccerdonna", "source": "soccerdonna"}`

- [ ] **Step 6: Commit**

```bash
git add soccerdonna/spiders/confederations.py tests/test_confederations_spider.py
git commit -m "feat: add synthetic-root confederations spider"
```

---

## Task 6: `competitions` spider — index → competitions

Parses the country-grouped index page. For each competition row, emit a `competition` item with `country_id`, `country_name`, `competition_code`, `competition_type`, `href`, and `parent`. Include the international section.

**Reference:** TM's `tfmkt/spiders/competitions.py` (`parse`/`parse_competitions`). soccerdonna's index is a single page (no per-country follow needed in the simplest case), so the structure is simpler than TM's. **Confirm against the fixture.**

**Files:**
- Create: `soccerdonna/spiders/competitions.py`
- Test: `tests/test_competitions_spider.py` (add to the file from Task 4)
- Sample: `samples/pages/index/wettbewerbeDE.html` (from Task 1A)

- [ ] **Step 1: Inspect the index sample to find selectors (manual)**

Open `samples/pages/index/wettbewerbeDE.html` (collected in Task 1A). The page is a country-grouped list. **Verified ground truth from recon (2026-06-25) — rely on these, but confirm against the sample:**
- Country flag images are **`.gif`**, not `.png`: `<img src="https://www.soccerdonna.de/bilder/flaggen/157.gif" alt="Spanien" title="Spanien">`. So `country_id` = the number in `/flaggen/{id}.gif`, and `country_name` comes from the `title`/`alt` attribute. **There is NO `flaggenrahmen` class** — select via `img[src*="/flaggen/"]`.
- **Country names are in German even on the `/en/` page** ("Spanien", "Argentinien", "Belgien"). Store them as-is (source truth); `country_id` is the stable key. Do not attempt translation (out of scope).
- Competition links look like `/de/primera-division-femenina/startseite/wettbewerb_ESP1.html`. They are mostly under **`/de/`** — normalize each to `/en/` before storing so downstream club/player pages return English labels and `/en/` child links (verified).
- Rows use alternating classes `hell` / `dunkel` inside `class="ac"` / `class="al"` cells — NOT `standard_tabelle` or `items`. Walk rows in document order; a flag row sets the current country for the competition rows beneath it.
- Cups appear as `pokalwettbewerb_*` (e.g. `pokalwettbewerb_CL.html`); `extract_competition_code` still recovers the code from the embedded `wettbewerb_CODE`.

Note the exact CSS selectors you'll use in Step 4.

- [ ] **Step 2: Write the failing test (anchor values + structural invariant)**

```python
# tests/test_competitions_spider.py  (append below the season tests from Task 4)
from tests.conftest import load_sample
from soccerdonna.spiders.competitions import CompetitionsSpider

PARENT = {'type': 'confederation', 'href': '/en/2010/startseite/wettbewerbeDE.html'}


def _parse_index():
    spider = CompetitionsSpider()
    resp = load_sample('index', 'wettbewerbeDE.html')
    return [i for i in spider.parse(resp, parent=PARENT) if isinstance(i, dict)]


def test_competitions_includes_spanish_first_tier():
    items = _parse_index()
    esp1 = next(i for i in items if i['competition_code'] == 'ESP1')
    assert esp1['type'] == 'competition'
    assert esp1['country_name'] == 'Spanien'   # German on the source site
    assert esp1['country_id'] == '157'
    assert esp1['href'].endswith('wettbewerb_ESP1.html')
    assert esp1['href'].startswith('/en/')     # normalized from /de/
    assert esp1['parent'] == PARENT
    assert esp1['source'] == 'soccerdonna'


def test_every_competition_has_required_fields():
    # Structural invariant across the whole index page.
    items = _parse_index()
    assert len(items) > 10
    for i in items:
        assert i['type'] == 'competition'
        assert i['competition_code']
        assert i['href']
        assert i['country_name']
```

- [ ] **Step 3: Run test to verify it fails**

Run: `poetry run pytest tests/test_competitions_spider.py -v`
Expected: FAIL (spider/parse not implemented).

- [ ] **Step 4: Implement `soccerdonna/spiders/competitions.py`**

Use this skeleton; fill the selectors confirmed in Step 2. The `country_id` regex and the inflection-based tier normalization mirror TM.

```python
import re
from inflection import parameterize, underscore
from soccerdonna.spiders.common_comp_club import BaseSpider
from soccerdonna.utils import extract_competition_code


class CompetitionsSpider(BaseSpider):
    name = 'competitions'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.seen = set()

    def parse(self, response, parent):
        current_country_id = None
        current_country_name = None
        current_tier = None

        # Iterate index rows in document order so each country flag sets the
        # context for the competition rows beneath it. ADJUST the row selector to
        # the sample; flag images are .gif at /flaggen/{id}.gif (NOT .png, NOT
        # flaggenrahmen). Competition hrefs are normalized /de/ -> /en/.
        for row in response.css('tr'):
            flag_src = row.css('img[src*="/flaggen/"]::attr(src)').get()
            flag_title = row.css('img[src*="/flaggen/"]::attr(title)').get()
            if flag_src and flag_title:
                m = re.search(r'/flaggen/([0-9]+)\.(?:gif|png)', flag_src, re.IGNORECASE)
                current_country_id = m.group(1) if m else None
                current_country_name = flag_title  # German on source

            tier_text = row.css('td b::text, td strong::text').get()
            if tier_text and not row.css('a[href*="wettbewerb_"]::attr(href)').get():
                current_tier = tier_text.strip()

            comp_href = row.css('a[href*="wettbewerb_"]::attr(href)').get()
            if not comp_href:
                continue
            comp_href = re.sub(r'^/de/', '/en/', comp_href)  # force English pages
            code = extract_competition_code(comp_href)
            if not code:
                continue
            key = f"{current_country_id}_{code}"
            if key in self.seen:
                continue
            self.seen.add(key)

            comp_type = underscore(parameterize(current_tier)) if current_tier else None
            yield {
                'type': 'competition',
                'parent': parent,
                'source': 'soccerdonna',
                'country_id': current_country_id,
                'country_name': current_country_name,
                'competition_code': code,
                'competition_type': comp_type,
                'href': comp_href,
            }
```

- [ ] **Step 5: Iterate selectors until green**

Run: `poetry run pytest tests/test_competitions_spider.py -v`
Adjust the CSS selectors in `parse` (and the country/tier-context logic) against the index sample until both new tests **and** the two season tests from Task 4 pass.
Expected (final): PASS.

- [ ] **Step 6: Smoke-test the chain**

Run:
```bash
poetry run scrapy crawl confederations > /tmp/conf.json
poetry run scrapy crawl competitions -a parents=/tmp/conf.json > /tmp/comps.json
grep -c '"competition_code"' /tmp/comps.json
grep ESP1 /tmp/comps.json
```
Expected: many competitions; the ESP1 line present.

- [ ] **Step 7: Commit**

```bash
git add soccerdonna/spiders/competitions.py tests/test_competitions_spider.py
git commit -m "feat: add competitions spider"
```

---

## Task 7: `clubs` spider — competition → clubs + inline squad

For each competition, find member clubs, visit each club's squad (`kader`) page, and emit a `club` item with club metadata and an inline `players` array. Field names mirror TM's club schema (`name`, `code`, `total_market_value`, `squad_size`, `average_age`, `coach_name`, `players[...]`).

**Reference:** TM's `tfmkt/spiders/clubs.py`.

**Files:**
- Create: `soccerdonna/spiders/clubs.py`
- Test: `tests/test_clubs_spider.py`
- Samples: `samples/pages/competition/ESP1.html`, `samples/pages/club/*.html` (from Task 1A)

- [ ] **Step 1: Inspect the samples (manual)**

In `samples/pages/competition/ESP1.html`: find the club links (`verein_*.html`). In `samples/pages/club/verein_1132.html`: find the squad table rows and, per player, the columns: shirt number, name + `spieler_*.html` link, position, nationality (flag title), age/DOB, market value. Cross-check column positions against another club sample (they should be consistent). Note selectors.

- [ ] **Step 2: Write the failing test (anchors + structural invariant across all 5 club samples)**

```python
# tests/test_clubs_spider.py
from tests.conftest import load_sample, iter_samples
from soccerdonna.spiders.clubs import ClubsSpider


def test_competition_page_yields_club_requests():
    spider = ClubsSpider()
    parent = {'type': 'competition', 'competition_code': 'ESP1',
              'href': '/en/primera-division-femenina/startseite/wettbewerb_ESP1.html'}
    resp = load_sample('competition', 'ESP1.html')
    follows = list(spider.parse(resp, parent=parent))
    hrefs = [r.url for r in follows]
    assert any('verein_1132' in h for h in hrefs)  # FC Barcelona


def test_barcelona_squad_has_known_players():
    spider = ClubsSpider()
    parent = {'type': 'competition', 'competition_code': 'ESP1'}
    resp = load_sample('club', 'verein_1132.html')
    club = list(spider.parse_details(resp, parent=parent))[0]
    assert club['type'] == 'club'
    assert 'verein_1132' in club['href']
    assert club['source'] == 'soccerdonna'
    assert isinstance(club['players'], list) and len(club['players']) > 5
    ids = {p['player_id'] for p in club['players']}
    assert '4824' in ids   # Alexia Putellas
    assert '22010' in ids  # Ewa Pajor
    putellas = next(p for p in club['players'] if p['player_id'] == '4824')
    assert putellas['href'].endswith('spieler_4824.html')
    assert putellas['name']


def test_every_club_sample_parses_with_players():
    # Structural invariant: each of the 5 squad samples yields one club with players.
    spider = ClubsSpider()
    parent = {'type': 'competition', 'competition_code': 'ESP1'}
    for filename, resp in iter_samples('club'):
        club = list(spider.parse_details(resp, parent=parent))[0]
        assert club['type'] == 'club', filename
        assert isinstance(club['players'], list) and len(club['players']) > 0, filename
        for p in club['players']:
            assert p['player_id'], filename
            assert p['href'].endswith('.html'), filename
```

- [ ] **Step 3: Run test to verify it fails**

Run: `poetry run pytest tests/test_clubs_spider.py -v`
Expected: FAIL (spider not implemented).

- [ ] **Step 4: Implement `soccerdonna/spiders/clubs.py`**

```python
from soccerdonna.spiders.common_comp_club import BaseSpider
from soccerdonna.utils import extract_entity_id, parse_market_value


class ClubsSpider(BaseSpider):
    name = 'clubs'

    def parse(self, response, parent):
        """Competition page -> follow each club's squad (kader) page."""
        # ADJUST selector to fixture: club links look like verein_*.html.
        club_hrefs = set(response.css('a[href*="verein_"]::attr(href)').getall())
        for href in club_hrefs:
            if 'verein_' not in href:
                continue
            # Route to the squad (kader) page rather than the overview.
            kader_href = href.replace('/startseite/', '/kader/')
            yield response.follow(
                self.base_url + kader_href if kader_href.startswith('/') else kader_href,
                self.parse_details,
                cb_kwargs={'parent': parent},
            )

    def parse_details(self, response, parent):
        """Squad page -> one club item with inline players[]."""
        players = []
        # ADJUST selector to fixture: each squad row.
        for row in response.css('table.standard_tabelle tr'):
            player_link = row.css('a[href*="spieler_"]::attr(href)').get()
            if not player_link:
                continue
            players.append({
                'player_id': extract_entity_id(player_link),
                'href': player_link,
                'name': self.safe_strip(row.css('a[href*="spieler_"]::text').get()),
                'number': self.safe_strip(row.css('td.rn_nummer::text').get()),
                'position': self.safe_strip(row.css('td:nth-of-type(4)::text').get()),
                'nationality': row.css('img.flaggenrahmen::attr(title)').get(),
                'market_value': self.safe_strip(row.css('td.rechts::text').get()),
            })

        yield {
            'type': 'club',
            'parent': parent,
            'source': 'soccerdonna',
            'href': self._club_href(response.url),
            'name': self.safe_strip(response.css('h1::text').get()),
            'players': players,
        }

    @staticmethod
    def _club_href(url):
        # Normalize the squad URL back to a /startseite/ club href for parent linkage.
        path = url.replace('https://www.soccerdonna.de', '')
        return path.replace('/kader/', '/startseite/')
```

- [ ] **Step 5: Iterate selectors until green**

Run: `poetry run pytest tests/test_clubs_spider.py -v`
Adjust selectors against the samples until all three tests pass. Pay attention to the position/number/market-value columns — confirm their exact `td` classes, and that they hold across all 5 club samples (the structural test will catch a club whose table differs).
Expected (final): PASS.

- [ ] **Step 6: Commit**

```bash
git add soccerdonna/spiders/clubs.py tests/test_clubs_spider.py
git commit -m "feat: add clubs spider with inline squad"
```

---

## Task 8: `players` spider — club squads → player profiles

For each player href (from club items), visit the profile page and emit a detailed `player` item: `name`, `last_name`, `date_of_birth`, `place_of_birth`, `citizenship`, `height`, `foot`, `position`, `current_club`, `current_market_value`, and `national_career`. Field names mirror TM's player schema; see `PLAYER_SCHEMA.md` in the reference repo.

**Files:**
- Create: `soccerdonna/spiders/players.py`
- Test: `tests/test_players_spider.py`
- Samples: `samples/pages/player/*.html` (from Task 1A; anchor `spieler_38461.html`)

- [ ] **Step 1: Inspect the samples (manual)**

soccerdonna profile data is a label/value list. In `samples/pages/player/spieler_38461.html` find the rows for "Date of birth", "Place of birth", "Nationality", "Height", "Foot", "Position", "Name in native country", and the market value + current club. Find the "National team career" table. Note selectors (often `td` siblings of a label cell). Glance at the other 4 player samples to confirm the label text is identical across profiles.

- [ ] **Step 2: Write the failing test (anchor values + structural invariant)**

```python
# tests/test_players_spider.py
from tests.conftest import load_sample, iter_samples
from soccerdonna.spiders.players import PlayersSpider

PARENT = {'type': 'club', 'href': '/en/fc-barcelona/startseite/verein_1132.html'}


def test_gemma_font_profile_fields():
    spider = PlayersSpider()
    resp = load_sample('player', 'spieler_38461.html')
    player = list(spider.parse(resp, parent=PARENT))[0]

    assert player['type'] == 'player'
    assert player['source'] == 'soccerdonna'
    assert player['href'].endswith('spieler_38461.html')
    assert player['date_of_birth'] == '1999-10-23'   # parsed to ISO
    assert player['position'] == 'Goalkeeper'
    assert player['citizenship'] == 'Spain'
    assert player['foot'] == 'right'
    assert player['height'] == '1,65'
    assert player['current_market_value'] == 50000


def test_every_player_sample_has_core_fields():
    # Structural invariant across all 5 player samples.
    spider = PlayersSpider()
    for filename, resp in iter_samples('player'):
        player = list(spider.parse(resp, parent=PARENT))[0]
        assert player['type'] == 'player', filename
        assert player['player_id'], filename
        assert player['name'], filename
        # DOB may be None for an odd profile, but the key must exist.
        assert 'date_of_birth' in player, filename
        assert 'national_career' in player, filename
```

- [ ] **Step 3: Run test to verify it fails**

Run: `poetry run pytest tests/test_players_spider.py -v`
Expected: FAIL (spider not implemented).

- [ ] **Step 4: Implement `soccerdonna/spiders/players.py`**

```python
from soccerdonna.spiders.common import BaseSpider
from soccerdonna.utils import extract_entity_id, parse_market_value, parse_date_de


class PlayersSpider(BaseSpider):
    name = 'players'

    def parse(self, response, parent):
        """Player profile page -> one detailed player item."""
        def field(label):
            # ADJUST to fixture: find the value cell paired with a label cell.
            return self.safe_strip(
                response.xpath(
                    f'//td[normalize-space(text())="{label}"]/following-sibling::td[1]//text()'
                ).get()
            )

        dob_raw = field('Date of birth:')
        yield {
            'type': 'player',
            'parent': parent,
            'source': 'soccerdonna',
            'href': response.url.replace('https://www.soccerdonna.de', ''),
            'player_id': extract_entity_id(response.url),
            'name': self.safe_strip(response.css('h1::text').get()),
            'name_in_home_country': field('Name in native country:'),
            'date_of_birth': parse_date_de(dob_raw),
            'place_of_birth': field('Place of birth:'),
            'citizenship': field('Nationality:'),
            'height': field('Height:'),
            'foot': field('Foot:'),
            'position': field('Position:'),
            'current_market_value': parse_market_value(field('Market value:')),
            'national_career': [],  # filled in Step 6
        }
```

- [ ] **Step 5: Iterate selectors until green**

Run: `poetry run pytest tests/test_players_spider.py -v`
The label strings (`'Date of birth:'` etc.) and the xpath pairing are the most likely things to adjust — confirm exact label text (including trailing colon/whitespace) in the sample, and that the same labels resolve on all 5 player samples (the structural test enforces this).
Expected (final): PASS.

- [ ] **Step 6: Add national-team career (flagged unknown)**

Inspect the "National team career" table in `samples/pages/player/spieler_38461.html` (and check at least one other player sample that has international caps). Replace the `national_career: []` placeholder with real parsing, mirroring TM's structure as closely as the available data allows (national team name + id via `extract_entity_id`, totals, per-competition rows). If the data is sparse, emit what exists and default missing numerics to 0. Add a test asserting Gemma Font's `national_career` contains an entry for "Spain U23" (observed live). Keep `test_every_player_sample_has_core_fields` green.

- [ ] **Step 7: Commit**

```bash
git add soccerdonna/spiders/players.py tests/test_players_spider.py
git commit -m "feat: add players spider with profile + national career"
```

---

## Task 9: `appearances` spider — players → per-match rows

For each player, visit the performance-data page (`leistungsdaten/spieler_{id}.html`) and emit one `appearance` item per match row (competition_code, matchday, date, venue, opponent, result, position, goals, assists, cards, minutes). Field names mirror TM's appearance schema.

**Files:**
- Create: `soccerdonna/spiders/appearances.py`
- Test: `tests/test_appearances_spider.py`
- Samples: `samples/pages/appearance/*.html` (from Task 1A; anchor `spieler_38461.html`)

- [ ] **Step 1: Inspect the samples (manual)**

Open `samples/pages/appearance/spieler_38461.html`. Find the per-match stats table. Identify columns: competition, matchday, date, home/away (venue), opponent (club link), result, position, goals, assists, cards, minutes. Note which columns exist (women's lower tiers may omit some), and check across the other appearance samples since column sets can vary by competition. If a page shows only the current season, note whether an "all seasons / full stats" link exists and record its URL pattern in a comment (relevant to Task 1A refresh).

- [ ] **Step 2: Write the failing test (structural invariant across samples)**

```python
# tests/test_appearances_spider.py
from tests.conftest import load_sample, iter_samples
from soccerdonna.spiders.appearances import AppearancesSpider

PARENT = {'type': 'player', 'href': '/en/gemma-font/profil/spieler_38461.html'}


def test_gemma_font_appearances_have_core_fields():
    spider = AppearancesSpider()
    resp = load_sample('appearance', 'spieler_38461.html')
    apps = [a for a in spider.parse(resp, parent=PARENT) if isinstance(a, dict)]
    assert len(apps) > 0
    for a in apps:
        assert a['type'] == 'appearance'
        assert a['source'] == 'soccerdonna'
        assert a['parent'] == PARENT
        assert 'minutes_played' in a
        assert 'date' in a


def test_every_appearance_sample_parses():
    # Structural invariant: each appearance sample yields rows with the core keys.
    spider = AppearancesSpider()
    for filename, resp in iter_samples('appearance'):
        apps = [a for a in spider.parse(resp, parent=PARENT) if isinstance(a, dict)]
        # A player may have zero matches; if rows exist they must be well-formed.
        for a in apps:
            assert a['type'] == 'appearance', filename
            assert 'minutes_played' in a, filename
            assert 'date' in a, filename
```

- [ ] **Step 3: Run test to verify it fails**

Run: `poetry run pytest tests/test_appearances_spider.py -v`
Expected: FAIL (spider not implemented).

- [ ] **Step 4: Implement `soccerdonna/spiders/appearances.py`**

```python
from soccerdonna.spiders.common import BaseSpider
from soccerdonna.utils import extract_entity_id, parse_date_de


def _int(value):
    if value is None:
        return None
    digits = ''.join(c for c in value if c.isdigit())
    return int(digits) if digits else None


class AppearancesSpider(BaseSpider):
    name = 'appearances'

    def seasonize_entrypoin_href(self, item):
        # Route player profile hrefs to their performance-data page.
        href = item['href'].replace('/profil/', '/leistungsdaten/')
        return f"{self.base_url}{href}"

    def parse(self, response, parent):
        # ADJUST selector to fixture: per-match stats rows.
        for row in response.css('table.standard_tabelle tr'):
            cells = row.css('td')
            if len(cells) < 5:
                continue
            opponent_href = row.css('a[href*="verein_"]::attr(href)').get()
            date_raw = self.safe_strip(row.css('td.no-border-rechts::text, td.zentriert::text').get())
            if not opponent_href and not date_raw:
                continue
            yield {
                'type': 'appearance',
                'parent': parent,
                'source': 'soccerdonna',
                'href': response.url.replace('https://www.soccerdonna.de', ''),
                'player_id': extract_entity_id(response.url),
                'date': parse_date_de(date_raw),
                'opponent': ({'type': 'club', 'href': opponent_href}
                             if opponent_href else None),
                'goals': _int(self.safe_strip(row.css('td.goaltd::text').get())),
                'minutes_played': _int(self.safe_strip(row.css('td:last-of-type::text').get())),
            }
```

- [ ] **Step 5: Iterate selectors until green**

Run: `poetry run pytest tests/test_appearances_spider.py -v`
Map each column position to the right field by inspecting the sample; women's stat tables may have fewer columns than TM, so only emit fields that exist. Verify against all 5 appearance samples (the structural test enforces this).
Expected (final): PASS.

- [ ] **Step 6: Commit**

```bash
git add soccerdonna/spiders/appearances.py tests/test_appearances_spider.py
git commit -m "feat: add appearances spider"
```

---

## Task 10: Bypass spiders — `clubs_by_url`, `players_from_file`

Thin wrappers that let you scrape clubs/players from a hand-supplied URL list instead of the full hierarchy. They reuse the parse logic of the hierarchy spiders.

**Files:**
- Create: `soccerdonna/spiders/clubs_by_url.py`, `soccerdonna/spiders/players_from_file.py`
- Test: `tests/test_bypass_spiders.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_bypass_spiders.py
from soccerdonna.spiders.clubs_by_url import ClubsByUrlSpider
from soccerdonna.spiders.players_from_file import PlayersFromFileSpider


def test_clubs_by_url_builds_requests_from_parents():
    spider = ClubsByUrlSpider()
    spider.entrypoints = [
        {'type': 'club', 'href': '/en/fc-barcelona/startseite/verein_1132.html'}
    ]
    reqs = spider.start_requests()
    assert any('verein_1132' in r.url for r in reqs)


def test_players_from_file_builds_requests_from_parents():
    spider = PlayersFromFileSpider()
    spider.entrypoints = [
        {'type': 'player', 'href': '/en/gemma-font/profil/spieler_38461.html'}
    ]
    reqs = spider.start_requests()
    assert any('spieler_38461' in r.url for r in reqs)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest tests/test_bypass_spiders.py -v`
Expected: FAIL (spiders not defined).

- [ ] **Step 3: Implement `soccerdonna/spiders/clubs_by_url.py`**

```python
from soccerdonna.spiders.clubs import ClubsSpider


class ClubsByUrlSpider(ClubsSpider):
    """Scrape clubs directly from a parents file of club URLs.

    Parents must be club items whose href points at the squad (kader) page, or
    a club overview href (routed to kader by ClubsSpider.parse_details upstream).
    Each entry is fetched and parsed by parse_details.
    """
    name = 'clubs_by_url'

    def start_requests(self):
        from scrapy import Request
        for item in self.entrypoints:
            href = item['href']
            # ensure we land on the kader page
            kader = href.replace('/startseite/', '/kader/')
            yield Request(self.base_url + kader, callback=self.parse_details,
                          cb_kwargs={'parent': item})
```

- [ ] **Step 4: Implement `soccerdonna/spiders/players_from_file.py`**

```python
from scrapy import Request
from soccerdonna.spiders.players import PlayersSpider


class PlayersFromFileSpider(PlayersSpider):
    """Scrape players directly from a parents file of player URLs."""
    name = 'players_from_file'

    def start_requests(self):
        for item in self.entrypoints:
            yield Request(self.base_url + item['href'], callback=self.parse,
                          cb_kwargs={'parent': item})
```

- [ ] **Step 5: Run test to verify it passes**

Run: `poetry run pytest tests/test_bypass_spiders.py -v`
Expected: PASS (2 passed).

- [ ] **Step 6: Commit**

```bash
git add soccerdonna/spiders/clubs_by_url.py soccerdonna/spiders/players_from_file.py tests/test_bypass_spiders.py
git commit -m "feat: add clubs_by_url and players_from_file bypass spiders"
```

---

## Task 11: End-to-end chain smoke test + samples

Verify the whole backbone runs against the live site and capture sample outputs
into `samples/output/` (distinct from the `samples/pages/` input HTML).

**Files:**
- Create: `samples/output/confederations.json`, `samples/output/competitions.json`, `samples/output/clubs.json`, `samples/output/players.json`, `samples/output/appearances.json`

- [ ] **Step 1: Run the full chain on a narrow slice (Spain only)**

```bash
mkdir -p samples/output
poetry run scrapy crawl confederations > samples/output/confederations.json
poetry run scrapy crawl competitions -a parents=samples/output/confederations.json > /tmp/all_comps.json
grep ESP1 /tmp/all_comps.json > samples/output/competitions.json
poetry run scrapy crawl clubs -a parents=samples/output/competitions.json > samples/output/clubs.json
head -n 1 samples/output/clubs.json | poetry run scrapy crawl players > samples/output/players.json
head -n 1 samples/output/players.json | poetry run scrapy crawl appearances > samples/output/appearances.json
```
Expected: each file is non-empty and valid JSON-Lines.

- [ ] **Step 2: Validate JSON-Lines**

Run:
```bash
for f in samples/output/*.json; do echo "== $f =="; python -c "import json,sys; [json.loads(l) for l in open('$f')]; print('ok')"; done
```
Expected: every file prints `ok`.

- [ ] **Step 3: Commit**

```bash
git add samples/output/
git commit -m "test: add end-to-end sample outputs for spain slice"
```

---

## Task 12: Documentation

Port TM's four docs, rewritten for soccerdonna. Keep them accurate to what Plan 1 actually built (note games spiders are Plan 2).

**Files:**
- Create: `README.md`, `DOCUMENTATION.md`, `SCHEMA.md`, `API_REFERENCE.md`
- Modify: `CLAUDE.md` (fill in the "TBD" build/run/test section)

- [ ] **Step 1: Write `README.md`**

Include: project purpose (women's football data from soccerdonna), install (`poetry install`), the crawl diagram `confederations → competitions → clubs → players → appearances`, and copy-pasteable run examples (the Task 11 chain). State that output mirrors the transfermarkt-scraper schema with an added `source: "soccerdonna"` marker.

- [ ] **Step 2: Write `DOCUMENTATION.md`**

Architecture + data flow: BaseSpider parent-loading, season handling, the synthetic-confederation root and why it exists, JSON-Lines piping, politeness settings.

- [ ] **Step 3: Write `SCHEMA.md`**

One section per entity (confederation, competition, club + inline player, player, appearance) with every field, its type, and an example — built from the actual `samples/output/` JSON-Lines. Note divergences from TM (e.g. `current_market_value` integer euros; ISO dates).

- [ ] **Step 4: Write `API_REFERENCE.md`**

Per-spider input/output contract and the `-a parents=` / `-a season=` arguments, with one example invocation each.

- [ ] **Step 5: Update `CLAUDE.md`**

Replace the "No code yet / TBD" status with the real build/run/test commands: `poetry install`, `poetry run scrapy crawl <spider> -a parents=<file>`, `poetry run pytest`. Note the entry point is the `confederations` spider.

- [ ] **Step 6: Commit**

```bash
git add README.md DOCUMENTATION.md SCHEMA.md API_REFERENCE.md CLAUDE.md
git commit -m "docs: add scraper documentation and schema reference"
```

---

## Task 13: Full test-suite green + wrap-up

- [ ] **Step 1: Run the whole suite**

Run: `poetry run pytest -v`
Expected: all tests pass.

- [ ] **Step 2: Confirm no spiders error on `scrapy list`**

Run: `poetry run scrapy list`
Expected: prints `appearances`, `clubs`, `clubs_by_url`, `competitions`, `confederations`, `players`, `players_from_file`.

- [ ] **Step 3: Final commit / tag**

```bash
git add -A
git commit -m "chore: plan 1 backbone complete" --allow-empty
```

---

## Plan 2 preview (separate document, written after Plan 1)

The games branch, mirroring TM's `games_urls`, `games`, `games_by_url`, `game_lineups`:
- `games_urls`: competition fixtures page (`spielplan/wettbewerb_{CODE}.html`) → game URLs + metadata (date, teams, result) without visiting each game.
- `games`: match report page (`spielbericht_{id}.html`) → lineups, events, goals, cards.
- `game_lineups`: starting XI / subs / formation.
- **Hardest unknown:** how soccerdonna encodes event minutes (TM decodes a CSS sprite via `background_position_in_px_to_minute`). Resolve by inspecting a real `spielbericht_*.html` before writing the events parser.

Plan 2 will be written as `docs/superpowers/plans/2026-06-25-soccerdonna-scraper-games.md` once Plan 1 is implemented and the squad-side selectors are proven (they de-risk the shared scaffolding).

---

## Self-review notes

- **Spec coverage:** competitions/clubs/players/appearances + bypass spiders + politeness + sample-driven tests + docs + synthetic root with marker are all covered (spec §5–§10). Games path (spec §6.2) is deferred to Plan 2 by design — flagged explicitly, not dropped.
- **Sample collection:** Task 1A downloads the first 5 real pages of every type (index, competition, club, player, appearance) into `samples/pages/<type>/` via `scripts/collect_samples.sh`, with ESP1 / FC Barcelona / Gemma Font anchored in. Every parser task tests against these — an anchor test for exact values plus a structural-invariant test that iterates all 5 samples of the type, so selector fragility shows up across real variation, not a single lucky page.
- **`samples/` layout:** `samples/pages/` = committed input HTML (Task 1A); `samples/output/` = generated JSON-Lines (Task 11). Kept distinct on purpose.
- **Unknowns (spec §7):** season grammar (Task 4 Step 1), national-team career (Task 8 Step 6) addressed with explicit verify-then-implement steps against real samples. Game-event timeline belongs to Plan 2.
- **Type consistency:** `extract_entity_id` returns a string everywhere; `player_id` is a string in clubs/players/appearances; `current_market_value` is int euros; dates are ISO strings via `parse_date_de`; `national_career` key always present (placeholder `[]` then filled). `source: "soccerdonna"` is on every top-level item.
