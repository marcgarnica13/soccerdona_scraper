# soccerdonna_scraper — Plan 2: Games Branch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the games branch to the existing soccerdonna scraper — `games_urls` (fast game-URL + metadata extraction), `games` (full match reports with events), `games_by_url` (bypass), and `game_lineups` (starting XI / subs / formation) — mirroring transfermarkt-scraper's schema.

**Architecture:** Reuse the existing scaffolding (`BaseSpider`, `utils`, `settings`, `tests/conftest.py`, sample infrastructure). Game discovery walks per-matchday overview pages; full reports parse the `<h2>`-sectioned report (Formation/Goals/Substitutions/Cards); lineups parse the separate `aufstellung` page. The four spiders share parse logic via inheritance to stay DRY.

**Tech Stack:** Python 3 (^3.9), Scrapy ^2.11, Poetry, pytest. Output = JSON-Lines to stdout.

**Spec:** `docs/superpowers/specs/2026-06-25-soccerdonna-scraper-design.md` (§6.2 games path).
**Plan 1 (backbone, already implemented):** `docs/superpowers/plans/2026-06-25-soccerdonna-scraper-backbone.md` — 7 spiders, 33 tests, all green.
**Reference repo:** `/home/marc/Development/gemini/transfermarkt-scraper` (read `tfmkt/spiders/{games,games_urls,games_by_url,game_lineups}.py` for the schema TM emits).

---

## What already exists (reuse, don't re-create)

- `soccerdonna/spiders/common.py` — `BaseSpider` (loads parents from stdin/file/gzip; `start_requests` builds one request per entrypoint via `seasonize_entrypoin_href`; `safe_strip`; a stdin guard so empty pipes fall back to `scrape_parents()`).
- `soccerdonna/spiders/common_comp_club.py` — `BaseSpider` subclass with season-suffix URL handling (`-a season=YYYY`; current season = plain join, ID-safe).
- `soccerdonna/utils.py` — `extract_entity_id(href)` (parses `_(\d+)\.html`; works on `spielbericht_153373.html` → `'153373'`), `extract_competition_code`, `parse_market_value`, `parse_date_de` (DD.MM.YYYY → ISO).
- `tests/conftest.py` — `load_sample(category, filename)` → Scrapy `HtmlResponse`; `iter_samples(category)` → `(filename, response)` for every sample of a category.
- `scripts/collect_samples.sh` — collects Plan-1 page samples. **Do not edit it**; Plan 2 adds a sibling script.
- `samples/pages/<category>/` — committed input HTML; `samples/output/` — generated JSON-Lines.
- `soccerdonna/settings.py` — autothrottle + politeness already on.

Run everything via `poetry run`. The repo is on `main` (greenfield, user-consented direct-to-main). Each task = its own commit.

---

## VERIFIED GROUND TRUTH (confirmed live 2026-06-25 — trust, confirm against samples)

- **Game discovery:** the competition `startseite` page links the *current* matchday-overview page: `/en/{slug}/spieltagsuebersicht/wettbewerb_{CODE}_{SEASON}_{MATCHDAY}.html` (e.g. `wettbewerb_ESP1_2025_30.html`). Each matchday-overview page lists that round's games (ESP1: 8 games) and carries navigation to other matchdays (prev/next, e.g. matchday 29 and 31 link out from 30). Walking the nav reaches every matchday.
- **Game link form:** `/en/{home-slug}_{away-slug}/index/spielbericht_{ID}.html`. The report loads by **ID regardless of slug** — `/en/x/index/spielbericht_153373.html` returns 200. Extract the id with `extract_entity_id`.
- **Match report (`index/spielbericht_{ID}.html`)** is sectioned by `<h2 class="tabellen_ueberschrift al">` headers, in English on `/en/`: **"Formation"**, **"Goals"**, **"Substitutions"**, **"Cards"**. There is **NO CSS-sprite minute encoding** (none of TM's `background-position`/`sb-sprite-uhr`) — minutes are plain text in the event rows. The report has ~32 `spieler_` links (16/team) and the two clubs' `verein_` links (anchor `spielbericht_153373`: away = Atlético de Madrid `verein_1129`).
- **Lineups** live on a SEPARATE page: `/en/{slug}/aufstellung/spielbericht_{ID}.html` (linked from the report). The `index/` report shows formation + events; the `aufstellung/` page shows full starting XI + substitutes per team.
- **Anchor game:** `spielbericht_153373` (Real Sociedad vs Atlético de Madrid, ESP1 matchday 30). Anchor matchday page: `spieltagsuebersicht/wettbewerb_ESP1_2025_30.html` (8 games).

### Honest unknowns to resolve by inspecting samples (not blockers)
1. **Exact minute format** in event rows (plain text — e.g. `45'`, `45.`, or a bare number in a cell). Resolve per the `game/` sample.
2. **Matchday enumeration mechanism** — whether the overview page has a full matchday `<select>` dropdown or only prev/next arrows. Either works (walk the nav graph); confirm from the `matchday/` sample.
3. **stadium / attendance** may be sparse or absent for women's matches → emit `None`, keep the key.
4. **Lineup page layout** (separate starting-XI vs substitutes tables; whether formation is shown there too).
5. Some lower-tier / cup competitions may have no match reports at all — spiders must degrade to zero rows, not crash.

---

## File Structure

```
soccerdonna_scraper/
  scripts/
    collect_game_samples.sh        # NEW: collects matchday/game/lineup samples
  soccerdonna/spiders/
    games_urls.py                  # NEW: competition -> matchday pages -> game metadata (fast)
    games.py                       # NEW: GamesSpider(GamesUrlsSpider) -> full match report
    games_by_url.py                # NEW: GamesByUrlSpider(GamesSpider) -> report by URL (bypass)
    game_lineups.py                # NEW: aufstellung page -> starting XI / subs / formation
  tests/
    conftest.py                    # MODIFY: nothing required (helpers already generic)
    test_games_urls_spider.py      # NEW
    test_games_spider.py           # NEW
    test_games_by_url_spider.py    # NEW
    test_game_lineups_spider.py    # NEW
  samples/pages/
    matchday/                      # NEW: 5 matchday-overview pages
    game/                          # NEW: 5 match-report pages
    lineup/                        # NEW: 5 aufstellung pages
  samples/output/                  # MODIFY: add games.json, game_lineups.json
  README.md DOCUMENTATION.md SCHEMA.md API_REFERENCE.md CLAUDE.md  # MODIFY: document games
```

Each spider has one responsibility; shared logic lives in the base spiders via inheritance (`games` extends `games_urls`; `games_by_url` extends `games`).

---

## Task 1: Collect game-branch samples

Collect 5 real pages of each new type (matchday-overview, match-report, lineup) into `samples/pages/{matchday,game,lineup}/`, with anchors guaranteed. These committed samples back the offline tests.

**Files:**
- Create: `scripts/collect_game_samples.sh`
- Create (script output): `samples/pages/{matchday,game,lineup}/*.html`

- [ ] **Step 1: Write `scripts/collect_game_samples.sh`**

```bash
#!/usr/bin/env bash
# Collect game-branch samples (matchday overviews, match reports, lineup pages)
# into samples/pages/{matchday,game,lineup}/, plus guaranteed anchors. Idempotent.
set -euo pipefail

BASE='https://www.soccerdonna.de'
UA='soccerdonna-scraper (+research; women-football)'
OUT='samples/pages'
START='/en/primera-division-femenina/startseite/wettbewerb_ESP1.html'   # ESP1 competition

mkdir -p "$OUT"/{matchday,game,lineup}
get() { curl -fsS -A "$UA" "$BASE$1" -o "$2"; echo "saved $2"; }

# 1) Find the current matchday-overview link on the competition startseite, e.g.
#    /en/.../spieltagsuebersicht/wettbewerb_ESP1_2025_30.html
curl -fsS -A "$UA" "$BASE$START" -o /tmp/_scd_start.html
CUR=$(grep -oE '/en/[^"]*spieltagsuebersicht/wettbewerb_[A-Z0-9]+_[0-9]+_[0-9]+\.html' /tmp/_scd_start.html | head -1)
echo "current matchday overview: $CUR"
CODE=$(echo "$CUR" | grep -oE 'wettbewerb_[A-Z0-9]+' | sed 's/wettbewerb_//')
SEASON=$(echo "$CUR" | grep -oE '_[0-9]+_[0-9]+\.html' | grep -oE '[0-9]+' | head -1)
MD=$(echo "$CUR" | grep -oE '_[0-9]+\.html' | grep -oE '[0-9]+')
SLUG=$(echo "$CUR" | sed -E 's#^/en/([^/]+)/.*#\1#')
echo "code=$CODE season=$SEASON current_matchday=$MD slug=$SLUG"

# 2) Collect 5 matchday-overview pages: current + the 4 prior matchdays.
for i in 0 1 2 3 4; do
  n=$((MD - i)); [ "$n" -lt 1 ] && continue
  href="/en/${SLUG}/spieltagsuebersicht/wettbewerb_${CODE}_${SEASON}_${n}.html"
  get "$href" "$OUT/matchday/${CODE}_${SEASON}_${n}.html"
done

# 3) Collect 5 match reports from the current matchday overview (+ anchor 153373).
mapfile -t GAME_IDS < <(
  { echo "153373";
    grep -oE 'spielbericht_[0-9]+\.html' "$OUT/matchday/${CODE}_${SEASON}_${MD}.html" \
      | grep -oE '[0-9]+'; } | awk '!seen[$0]++' | head -n 5)
for id in "${GAME_IDS[@]}"; do
  # Slug doesn't matter — the report loads by id.
  get "/en/x/index/spielbericht_${id}.html"        "$OUT/game/spielbericht_${id}.html"
  # 4) Matching lineup (aufstellung) page for the same game.
  get "/en/x/aufstellung/spielbericht_${id}.html"  "$OUT/lineup/spielbericht_${id}.html"
done

echo "Done. Sample counts:"
for d in matchday game lineup; do echo "  $d: $(ls -1 "$OUT/$d" | wc -l)"; done
```

- [ ] **Step 2: Run it**

Run:
```bash
chmod +x scripts/collect_game_samples.sh
./scripts/collect_game_samples.sh
```
Expected: prints `saved ...` and final counts `matchday: 5`, `game: 5`, `lineup: 5`. If matchday collects fewer than 5 (early in a season), that's acceptable — note it; the anchor `_2025_30` matchday + `spielbericht_153373` game/lineup MUST exist:
```bash
ls samples/pages/matchday/ESP1_*_30.html samples/pages/game/spielbericht_153373.html samples/pages/lineup/spielbericht_153373.html
```
Expected: all three exist. (If the live current matchday has moved past 30, the anchor matchday filename will differ — in that case also explicitly fetch `wettbewerb_ESP1_2025_30.html` so the anchor tests below remain valid, and note it.)

- [ ] **Step 3: Confirm the samples are real (not error pages)**

Run:
```bash
grep -c 'spielbericht_' samples/pages/matchday/*_30.html        # expect ~8 per matchday page
grep -ci 'Goals\|Substitutions\|Cards' samples/pages/game/spielbericht_153373.html  # expect >0
```
Expected: matchday page references ~8 games; the report contains the section headers.

- [ ] **Step 4: Commit**

```bash
git add scripts/collect_game_samples.sh samples/pages/matchday samples/pages/game samples/pages/lineup
git commit -m "test: collect game-branch samples (matchday/game/lineup)"
```

---

## Task 2: `games_urls` spider — competition → matchday overviews → game metadata

The fast path: discover every game's URL + lightweight metadata (date, teams, result) without opening each match report. `parse` (competition page) finds the current matchday-overview and walks the matchday nav; `parse_matchday` yields one game item per fixture.

**Files:**
- Create: `soccerdonna/spiders/games_urls.py`
- Test: `tests/test_games_urls_spider.py`
- Samples: `samples/pages/matchday/*.html` (anchor `ESP1_2025_30.html`-form), `samples/pages/competition/ESP1.html` (Plan-1 sample, reused)

- [ ] **Step 1: Inspect samples (manual)**

In a `samples/pages/matchday/*_30.html` file: find the per-game rows. Each game row should give: the `spielbericht_{id}.html` link, the two club links (`verein_{id}.html`) + names, the date, and the result/score. Also find the matchday-navigation links (`spieltagsuebersicht/wettbewerb_..._{n}.html`) — a dropdown or prev/next. In `samples/pages/competition/ESP1.html`: find the link to the current matchday overview (`spieltagsuebersicht/...`). Note selectors.

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_games_urls_spider.py
from tests.conftest import load_sample, iter_samples
from soccerdonna.spiders.games_urls import GamesUrlsSpider

PARENT = {'type': 'competition', 'competition_code': 'ESP1',
          'href': '/en/primera-division-femenina/startseite/wettbewerb_ESP1.html'}


def _matchday_sample():
    # the anchor matchday-30 sample (filename starts with ESP1_ and ends _30.html)
    for name, resp in iter_samples('matchday'):
        if name.endswith('_30.html'):
            return resp
    raise AssertionError('matchday _30 anchor sample missing')


def test_parse_matchday_yields_eight_games():
    spider = GamesUrlsSpider()
    games = [g for g in spider.parse_matchday(_matchday_sample(), parent=PARENT)
             if isinstance(g, dict)]
    assert len(games) == 8
    for g in games:
        assert g['type'] == 'game'
        assert g['game_id']                      # numeric id string
        assert g['href'].endswith('.html') and 'spielbericht_' in g['href']
        assert g['home_club']['href'] and g['away_club']['href']
        assert g['source'] == 'soccerdonna'
        assert g['parent'] == PARENT


def test_anchor_game_present_in_matchday():
    spider = GamesUrlsSpider()
    games = [g for g in spider.parse_matchday(_matchday_sample(), parent=PARENT)
             if isinstance(g, dict)]
    g153373 = next(g for g in games if g['game_id'] == '153373')
    # away side is Atlético de Madrid (verein_1129)
    clubs = {g153373['home_club']['href'], g153373['away_club']['href']}
    assert any('verein_1129' in c for c in clubs)
    assert g153373.get('result') is None or __import__('re').match(r'^\d+:\d+$', g153373['result'])


def test_every_matchday_sample_parses():
    spider = GamesUrlsSpider()
    for name, resp in iter_samples('matchday'):
        games = [g for g in spider.parse_matchday(resp, parent=PARENT) if isinstance(g, dict)]
        assert len(games) >= 1, name
        for g in games:
            assert g['type'] == 'game' and g['game_id'], name
```

- [ ] **Step 3: Run to verify failure**

Run: `poetry run pytest tests/test_games_urls_spider.py -v`
Expected: FAIL (spider not implemented).

- [ ] **Step 4: Implement `soccerdonna/spiders/games_urls.py`**

Adapt selectors to the sample. This skeleton: `parse` (competition page) follows the current matchday link; `parse_matchday` yields games AND follows any not-yet-seen matchday-overview links (walking the nav graph reaches all matchdays); `extract_game` builds one metadata item from a fixture row.

```python
import re
from soccerdonna.spiders.common_comp_club import BaseSpider
from soccerdonna.utils import extract_entity_id, parse_date_de


class GamesUrlsSpider(BaseSpider):
    name = 'games_urls'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.seen_matchdays = set()

    def parse(self, response, parent):
        """Competition page -> follow the current matchday-overview page."""
        # ADJUST selector: the startseite links the current spieltagsuebersicht page.
        md_href = response.css('a[href*="spieltagsuebersicht/wettbewerb_"]::attr(href)').get()
        if not md_href:
            return
        md_href = re.sub(r'^/de/', '/en/', md_href)
        yield response.follow(self.base_url + md_href, self.parse_matchday,
                              cb_kwargs={'parent': parent})

    def parse_matchday(self, response, parent):
        """Matchday-overview page -> one game item per fixture + walk to other matchdays."""
        # Mark this matchday seen (dedupe the nav-graph walk).
        m = re.search(r'spieltagsuebersicht/wettbewerb_[A-Z0-9]+_\d+_(\d+)\.html', response.url)
        if m:
            self.seen_matchdays.add(m.group(1))

        # ADJUST selector: iterate fixture rows that contain a spielbericht link.
        for row in response.css('tr'):
            game_href = row.css('a[href*="spielbericht_"]::attr(href)').get()
            if not game_href:
                continue
            game = self.extract_game(row, game_href, parent)
            if game:
                yield game

        # Follow other matchday-overview links not yet visited (reaches all matchdays).
        for href in response.css('a[href*="spieltagsuebersicht/wettbewerb_"]::attr(href)').getall():
            href = re.sub(r'^/de/', '/en/', href)
            mm = re.search(r'_\d+_(\d+)\.html', href)
            if mm and mm.group(1) not in self.seen_matchdays:
                self.seen_matchdays.add(mm.group(1))  # pre-mark to avoid duplicate requests
                yield response.follow(self.base_url + href, self.parse_matchday,
                                      cb_kwargs={'parent': parent})

    def extract_game(self, row, game_href, parent):
        game_href = re.sub(r'^/de/', '/en/', game_href)
        club_hrefs = [re.sub(r'^/de/', '/en/', h)
                      for h in row.css('a[href*="verein_"]::attr(href)').getall()]
        # ADJUST: home is the first club link, away the second (confirm against sample).
        home = club_hrefs[0] if len(club_hrefs) >= 1 else None
        away = club_hrefs[1] if len(club_hrefs) >= 2 else None
        date_raw = self.safe_strip(row.css('td.zentriert::text, td.datum::text').get())
        result_raw = self.safe_strip(row.css('a[href*="spielbericht_"]::text').get())
        result = result_raw if result_raw and re.match(r'^\d+:\d+$', result_raw) else None
        return {
            'type': 'game',
            'parent': parent,
            'source': 'soccerdonna',
            'game_id': extract_entity_id(game_href),
            'href': game_href,
            'date': parse_date_de(date_raw) if date_raw else None,
            'home_club': {'href': home},
            'away_club': {'href': away},
            'result': result,
        }
```

- [ ] **Step 5: Iterate selectors until green**

Run: `poetry run pytest tests/test_games_urls_spider.py -v`
Adjust the fixture-row, club, date, and result selectors against the matchday samples until all tests pass. Confirm exactly 8 games on the matchday-30 sample and that home/away club hrefs are populated.
Expected (final): PASS.

- [ ] **Step 6: Smoke-test the chain**

Run:
```bash
poetry run scrapy crawl confederations | poetry run scrapy crawl competitions 2>/dev/null | grep ESP1 | poetry run scrapy crawl games_urls 2>/dev/null > /tmp/g.json
grep -c '"type": "game"' /tmp/g.json
grep 153373 /tmp/g.json | head -1
```
Expected: many games across all ESP1 matchdays (a full season ≈ 8 × matchdays); the anchor game present. (This visits every matchday page, so it takes a minute with autothrottle.)

- [ ] **Step 7: Commit**

```bash
git add soccerdonna/spiders/games_urls.py tests/test_games_urls_spider.py
git commit -m "feat: add games_urls spider"
```

---

## Task 3: `games` spider — full match reports with events

`GamesSpider` extends `GamesUrlsSpider` to reuse matchday discovery, but instead of yielding lightweight metadata it follows each `spielbericht` link to `parse_game`, which parses the full report: clubs, result, date, formations, and the Goals/Substitutions/Cards events.

**Files:**
- Create: `soccerdonna/spiders/games.py`
- Test: `tests/test_games_spider.py`
- Samples: `samples/pages/game/*.html` (anchor `spielbericht_153373.html`)

- [ ] **Step 1: Inspect samples (manual)**

In `samples/pages/game/spielbericht_153373.html`: locate the `<h2 class="tabellen_ueberschrift al">` sections "Formation", "Goals", "Substitutions", "Cards". For each event row under Goals/Substitutions/Cards, find: the minute (plain text — determine the exact format), the player link (`spieler_{id}.html`), and which club it belongs to. Find the home/away club links + names, the final result/score, the date, and (if present) stadium/attendance. Note selectors. There is NO CSS sprite — do not look for `background-position`.

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_games_spider.py
import re
from tests.conftest import load_sample, iter_samples
from soccerdonna.spiders.games import GamesSpider

PARENT = {'type': 'competition', 'competition_code': 'ESP1'}


def test_parse_game_core_fields():
    spider = GamesSpider()
    resp = load_sample('game', 'spielbericht_153373.html')
    game = list(spider.parse_game(resp, parent=PARENT))[0]
    assert game['type'] == 'game'
    assert game['game_id'] == '153373'
    assert game['source'] == 'soccerdonna'
    assert game['home_club']['href'] and game['away_club']['href']
    assert re.match(r'^\d+:\d+$', game['result'])
    assert isinstance(game['events'], list)
    # the report has Goals/Substitutions/Cards -> at least one event
    assert len(game['events']) >= 1


def test_game_events_well_formed():
    spider = GamesSpider()
    resp = load_sample('game', 'spielbericht_153373.html')
    game = list(spider.parse_game(resp, parent=PARENT))[0]
    for e in game['events']:
        assert e['type'] in ('goal', 'substitution', 'card')
        assert 'minute' in e          # may be None, key must exist
        assert 'club' in e            # {'href': ...} or None
    types = {e['type'] for e in game['events']}
    assert 'goal' in types or 'card' in types or 'substitution' in types


def test_every_game_sample_parses():
    spider = GamesSpider()
    for name, resp in iter_samples('game'):
        rows = list(spider.parse_game(resp, parent=PARENT))
        assert len(rows) == 1, name
        g = rows[0]
        assert g['type'] == 'game' and g['game_id'], name
        assert isinstance(g['events'], list), name
```

- [ ] **Step 3: Run to verify failure**

Run: `poetry run pytest tests/test_games_spider.py -v`
Expected: FAIL.

- [ ] **Step 4: Implement `soccerdonna/spiders/games.py`**

Adapt selectors to the sample. `_parse_event_section` extracts events from one `<h2>` section by its heading text.

```python
import re
from soccerdonna.spiders.games_urls import GamesUrlsSpider
from soccerdonna.utils import extract_entity_id, parse_date_de


class GamesSpider(GamesUrlsSpider):
    name = 'games'

    def parse_matchday(self, response, parent):
        """Override: instead of yielding metadata, follow each game to the full report.
        Still walks the matchday nav graph (reuse the parent logic for that)."""
        for href in set(response.css('a[href*="spielbericht_"]::attr(href)').getall()):
            if 'aufstellung' in href:   # skip the lineup link if present here
                continue
            href = re.sub(r'^/de/', '/en/', href)
            yield response.follow(self.base_url + href, self.parse_game,
                                  cb_kwargs={'parent': parent})
        # walk to other matchdays (same nav logic as the base spider)
        import re as _re
        m = _re.search(r'spieltagsuebersicht/wettbewerb_[A-Z0-9]+_\d+_(\d+)\.html', response.url)
        if m:
            self.seen_matchdays.add(m.group(1))
        for href in response.css('a[href*="spieltagsuebersicht/wettbewerb_"]::attr(href)').getall():
            href = _re.sub(r'^/de/', '/en/', href)
            mm = _re.search(r'_\d+_(\d+)\.html', href)
            if mm and mm.group(1) not in self.seen_matchdays:
                self.seen_matchdays.add(mm.group(1))
                yield response.follow(self.base_url + href, self.parse_matchday,
                                      cb_kwargs={'parent': parent})

    def parse_game(self, response, parent):
        """Full match report -> one game item with events."""
        club_hrefs = [re.sub(r'^/de/', '/en/', h)
                      for h in response.css('a[href*="verein_"]::attr(href)').getall()]
        # ADJUST: the two team headers give home (first) and away (second).
        home = club_hrefs[0] if len(club_hrefs) >= 1 else None
        away = club_hrefs[1] if len(club_hrefs) >= 2 else None

        # ADJUST: result + date selectors from the report header.
        result_raw = self.safe_strip(response.css('.ergebnis::text, h1::text').re_first(r'\d+:\d+'))
        date_raw = self.safe_strip(response.css('.spieldatum::text, td.datum::text').get())

        events = []
        events += self._parse_event_section(response, 'Goals', 'goal')
        events += self._parse_event_section(response, 'Substitutions', 'substitution')
        events += self._parse_event_section(response, 'Cards', 'card')

        yield {
            'type': 'game',
            'parent': parent,
            'source': 'soccerdonna',
            'game_id': extract_entity_id(response.url),
            'href': response.url.replace(self.base_url, ''),
            'date': parse_date_de(date_raw) if date_raw else None,
            'home_club': {'href': home},
            'away_club': {'href': away},
            'result': result_raw,
            'events': events,
        }

    def _parse_event_section(self, response, heading, event_type):
        """Extract event rows under the <h2> whose text == heading."""
        events = []
        # ADJUST: locate the table that follows the matching <h2>.
        section = response.xpath(
            f'//h2[contains(normalize-space(.), "{heading}")]/following-sibling::*[1]')
        for row in section.css('tr'):
            player_href = row.css('a[href*="spieler_"]::attr(href)').get()
            club_href = row.css('a[href*="verein_"]::attr(href)').get()
            minute_text = self.safe_strip(' '.join(row.css('::text').getall()))
            minute = None
            mm = re.search(r'(\d{1,3})\D*[\'\.]', minute_text or '')
            if mm:
                minute = int(mm.group(1))
            if not player_href and not club_href:
                continue
            events.append({
                'type': event_type,
                'minute': minute,
                'player': {'href': re.sub(r'^/de/', '/en/', player_href)} if player_href else None,
                'club': {'href': re.sub(r'^/de/', '/en/', club_href)} if club_href else None,
            })
        return events
```

- [ ] **Step 5: Iterate selectors until green**

Run: `poetry run pytest tests/test_games_spider.py -v`
The minute regex and the section-locating xpath are the most likely to need adjustment — confirm the exact minute text format and the element type that follows each `<h2>` (table vs div). Verify against all 5 game samples.
Expected (final): PASS.

- [ ] **Step 6: Smoke-test**

Run:
```bash
echo '{"type":"game","href":"/en/x/index/spielbericht_153373.html"}' | poetry run scrapy crawl games_by_url 2>/dev/null | head -1
```
(That uses Task 4's spider; if not built yet, instead pipe one competition through `games` and check a game line has a non-empty `events` array.) Confirm the anchor game emits clubs, result, and events.

- [ ] **Step 7: Commit**

```bash
git add soccerdonna/spiders/games.py tests/test_games_spider.py
git commit -m "feat: add games spider with event parsing"
```

---

## Task 4: `games_by_url` spider — match report by URL (bypass)

`GamesByUrlSpider` extends `GamesSpider` to parse specific game reports from a hand-supplied parents file of game items, bypassing matchday discovery.

**Files:**
- Create: `soccerdonna/spiders/games_by_url.py`
- Test: `tests/test_games_by_url_spider.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_games_by_url_spider.py
from soccerdonna.spiders.games_by_url import GamesByUrlSpider


def test_builds_report_requests_from_parents():
    spider = GamesByUrlSpider()
    spider.entrypoints = [
        {'type': 'game', 'href': '/en/x/index/spielbericht_153373.html'}
    ]
    reqs = list(spider.start_requests())
    assert any('spielbericht_153373' in r.url for r in reqs)
    # callback must be the full-report parser
    assert all(r.callback == spider.parse_game for r in reqs)
```

- [ ] **Step 2: Run to verify failure**

Run: `poetry run pytest tests/test_games_by_url_spider.py -v`
Expected: FAIL (spider not defined).

- [ ] **Step 3: Implement `soccerdonna/spiders/games_by_url.py`**

```python
from scrapy import Request
from soccerdonna.spiders.games import GamesSpider


class GamesByUrlSpider(GamesSpider):
    """Parse specific match reports from a parents file of game items."""
    name = 'games_by_url'

    def start_requests(self):
        for item in self.entrypoints:
            href = item['href']
            # route to the index/ report page if a different sub-page was supplied
            href = href.replace('/aufstellung/', '/index/')
            yield Request(self.base_url + href, callback=self.parse_game,
                          cb_kwargs={'parent': item})
```

- [ ] **Step 4: Run to verify it passes**

Run: `poetry run pytest tests/test_games_by_url_spider.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add soccerdonna/spiders/games_by_url.py tests/test_games_by_url_spider.py
git commit -m "feat: add games_by_url bypass spider"
```

---

## Task 5: `game_lineups` spider — starting XI / subs / formation

For each game, fetch the separate `aufstellung` page and emit a `game_lineup` item with each team's formation, starting lineup, and substitutes.

**Files:**
- Create: `soccerdonna/spiders/game_lineups.py`
- Test: `tests/test_game_lineups_spider.py`
- Samples: `samples/pages/lineup/*.html` (anchor `spielbericht_153373.html`)

- [ ] **Step 1: Inspect samples (manual)**

In `samples/pages/lineup/spielbericht_153373.html`: find the per-team blocks. For each team identify: the club (`verein_{id}`), the formation string (e.g. "4-3-3"), the starting-XI table and the substitutes table, and per player the shirt number, name, and `spieler_{id}` link (plus position if shown). Note selectors and how home vs away are distinguished.

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_game_lineups_spider.py
from tests.conftest import load_sample, iter_samples
from soccerdonna.spiders.game_lineups import GameLineupsSpider

PARENT = {'type': 'game', 'href': '/en/x/index/spielbericht_153373.html'}


def test_parse_lineups_core():
    spider = GameLineupsSpider()
    resp = load_sample('lineup', 'spielbericht_153373.html')
    item = list(spider.parse_lineups(resp, parent=PARENT))[0]
    assert item['type'] == 'game_lineup'
    assert item['game_id'] == '153373'
    assert item['source'] == 'soccerdonna'
    for side in ('home_club', 'away_club'):
        club = item[side]
        assert 'href' in club
        assert isinstance(club['starting_lineup'], list)
        assert isinstance(club['substitutes'], list)
        # a full XI is 11 starters (allow some slack for data gaps)
        assert len(club['starting_lineup']) >= 7
        for p in club['starting_lineup']:
            assert p['href'].endswith('.html') and 'spieler_' in p['href']
            assert p['player_id']


def test_every_lineup_sample_parses():
    spider = GameLineupsSpider()
    for name, resp in iter_samples('lineup'):
        rows = list(spider.parse_lineups(resp, parent=PARENT))
        assert len(rows) == 1, name
        item = rows[0]
        assert item['type'] == 'game_lineup' and item['game_id'], name
        assert 'home_club' in item and 'away_club' in item, name
```

- [ ] **Step 3: Run to verify failure**

Run: `poetry run pytest tests/test_game_lineups_spider.py -v`
Expected: FAIL.

- [ ] **Step 4: Implement `soccerdonna/spiders/game_lineups.py`**

Adapt selectors to the sample. The spider routes a game href to its `/aufstellung/` page in `start_requests`, then `parse_lineups` builds the item.

```python
import re
from scrapy import Request
from soccerdonna.spiders.common import BaseSpider
from soccerdonna.utils import extract_entity_id


class GameLineupsSpider(BaseSpider):
    name = 'game_lineups'

    def start_requests(self):
        for item in self.entrypoints:
            href = item['href'].replace('/index/', '/aufstellung/')
            if '/aufstellung/' not in href:
                href = re.sub(r'/[a-z]+/spielbericht_', '/aufstellung/spielbericht_', href)
            yield Request(self.base_url + href, callback=self.parse_lineups,
                          cb_kwargs={'parent': item})

    def scrape_parents(self):
        return [{'type': 'game', 'href': '/en/x/index/spielbericht_153373.html'}]

    def parse_lineups(self, response, parent):
        # ADJUST: find the two team blocks (home first, away second).
        team_blocks = response.css('div.aufstellung-team, table.aufstellung')  # adjust to sample
        home = self._parse_team(team_blocks[0]) if len(team_blocks) >= 1 else self._empty_team()
        away = self._parse_team(team_blocks[1]) if len(team_blocks) >= 2 else self._empty_team()
        yield {
            'type': 'game_lineup',
            'parent': parent,
            'source': 'soccerdonna',
            'game_id': extract_entity_id(response.url),
            'href': response.url.replace(self.base_url, ''),
            'home_club': home,
            'away_club': away,
        }

    def _parse_team(self, block):
        club_href = block.css('a[href*="verein_"]::attr(href)').get()
        formation = self.safe_strip(block.css('::text').re_first(r'\d-\d[-\d]*'))
        starting, subs = [], []
        # ADJUST: the block has a starting-XI table and a substitutes table.
        tables = block.css('table')
        if tables:
            starting = self._players(tables[0])
            if len(tables) >= 2:
                subs = self._players(tables[1])
        return {'href': re.sub(r'^/de/', '/en/', club_href) if club_href else None,
                'formation': formation, 'starting_lineup': starting, 'substitutes': subs}

    def _players(self, table):
        players = []
        for row in table.css('tr'):
            href = row.css('a[href*="spieler_"]::attr(href)').get()
            if not href:
                continue
            players.append({
                'player_id': extract_entity_id(href),
                'href': re.sub(r'^/de/', '/en/', href),
                'name': self.safe_strip(row.css('a[href*="spieler_"]::text').get()),
                'number': self.safe_strip(row.css('td.rn::text, td:first-child::text').get()),
            })
        return players

    @staticmethod
    def _empty_team():
        return {'href': None, 'formation': None, 'starting_lineup': [], 'substitutes': []}
```

- [ ] **Step 5: Iterate selectors until green**

Run: `poetry run pytest tests/test_game_lineups_spider.py -v`
The team-block, starting-XI vs substitutes table, and formation selectors are the most likely to need adjustment. Verify each team has a plausible starting XI across all 5 lineup samples.
Expected (final): PASS.

- [ ] **Step 6: Commit**

```bash
git add soccerdonna/spiders/game_lineups.py tests/test_game_lineups_spider.py
git commit -m "feat: add game_lineups spider"
```

---

## Task 6: End-to-end + sample outputs + documentation

**Files:**
- Create: `samples/output/games.json`, `samples/output/game_lineups.json`
- Modify: `README.md`, `DOCUMENTATION.md`, `SCHEMA.md`, `API_REFERENCE.md`, `CLAUDE.md`

- [ ] **Step 1: Generate game-branch sample outputs**

Run:
```bash
# games (full reports) for ESP1 — cherry-pick a couple via games_by_url for a fast, deterministic sample
printf '%s\n%s\n' \
  '{"type":"game","href":"/en/x/index/spielbericht_153373.html"}' \
  '{"type":"game","href":"/en/x/index/spielbericht_153376.html"}' \
  | poetry run scrapy crawl games_by_url > samples/output/games.json
# lineups for the same games
printf '%s\n%s\n' \
  '{"type":"game","href":"/en/x/index/spielbericht_153373.html"}' \
  '{"type":"game","href":"/en/x/index/spielbericht_153376.html"}' \
  | poetry run scrapy crawl game_lineups > samples/output/game_lineups.json
```
Validate:
```bash
for f in samples/output/games.json samples/output/game_lineups.json; do
  python3 -c "import json; rows=[json.loads(l) for l in open('$f') if l.strip()]; print('$f', len(rows), 'ok')"
done
```
Expected: each file has 2 rows and prints `ok`. Confirm `games.json` rows have non-empty `events` and `game_lineups.json` rows have starting lineups.

- [ ] **Step 2: Update docs**

- `README.md`: extend the crawl diagram to show the games branch
  (`competitions → games_urls → games → game_lineups`, plus `games_by_url`), add run examples (the Task 6 commands and a full `competitions | games` example), and update the scope note — Plan 2 is now implemented.
- `DOCUMENTATION.md`: document game discovery (matchday-overview walk), the `index/` report vs `aufstellung/` lineup pages, and that minutes are plain text (no CSS sprite). Move games out of "not yet implemented" in Known Limitations; keep any genuine caveat (e.g. cup competitions may lack matchday overviews).
- `SCHEMA.md`: add `game` and `game_lineup` sections with every field, type, and a real example from `samples/output/`.
- `API_REFERENCE.md`: add the four spiders' input/output contracts and example invocations.
- `CLAUDE.md`: update the Status section — the games branch is built; the project now has 11 spiders.

- [ ] **Step 3: Commit**

```bash
git add samples/output/games.json samples/output/game_lineups.json README.md DOCUMENTATION.md SCHEMA.md API_REFERENCE.md CLAUDE.md
git commit -m "docs: document games branch + add game/lineup sample outputs"
```

---

## Task 7: Wrap-up

- [ ] **Step 1: Full suite green**

Run: `poetry run pytest -v`
Expected: all pass (the 33 Plan-1 tests plus the new games tests).

- [ ] **Step 2: All 11 spiders registered**

Run: `poetry run scrapy list`
Expected: `appearances, clubs, clubs_by_url, competitions, confederations, game_lineups, games, games_by_url, games_urls, players, players_from_file`.

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "chore: plan 2 games branch complete" --allow-empty
```

---

## Self-review notes

- **Spec coverage (design §6.2):** `games_urls` (Task 2), `games` (Task 3), `games_by_url` (Task 4), `game_lineups` (Task 5) all covered, plus samples (Task 1), e2e + docs (Task 6), wrap-up (Task 7). Matches the four games spiders the spec lists.
- **Reuse / DRY:** `games` extends `games_urls` (shared matchday discovery); `games_by_url` extends `games` (shared `parse_game`); all reuse existing `utils`, `BaseSpider`, `conftest`, sample infra. No duplication of the backbone scaffolding.
- **Unknowns handled with verify-then-implement steps:** minute format (Task 3 Step 1), matchday enumeration (Task 2 Step 1), stadium/attendance sparsity (emit None), lineup layout (Task 5 Step 1), competitions with no reports (zero-row degradation enforced by structural tests).
- **Type consistency:** `extract_entity_id` returns a string; `game_id`/`player_id` are strings; `events` is always a list with each event carrying `type`/`minute`/`player`/`club`; `home_club`/`away_club` are dicts with at least `href`; `source: "soccerdonna"` on every top-level item. Event `type` values are lowercase `goal`/`substitution`/`card` consistently across Task 3's test and implementation.
- **Known divergences from TM (acceptable, to document in SCHEMA.md):** TM decodes event minutes from a CSS sprite; soccerdonna uses plain-text minutes (simpler). TM's game item nests full lineups inside the game; here lineups are a separate `game_lineup` entity from the `aufstellung` page (matching TM's `game_lineups` spider split).
```
