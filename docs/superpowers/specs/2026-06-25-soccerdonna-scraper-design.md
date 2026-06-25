# soccerdonna_scraper — Design Spec

**Date:** 2026-06-25
**Status:** Approved (design); pending implementation plan
**Author:** brainstorming session

## 1. Summary

A Scrapy-based scraper for [soccerdonna.de](https://www.soccerdonna.de/en/) — a
Transfermarkt-family site covering **women's football**. It replicates the
[`transfermarkt-scraper`](../../../../transfermarkt-scraper) architecture and
**mirrors its output schema exactly**, so soccerdonna data can flow through the
same downstream pipeline as the existing Transfermarkt data (e.g. a
`gemini.transfermarkt`-style warehouse), distinguished only by a `source` marker.

soccerdonna shares Transfermarkt's German URL DNA (`wettbewerb_`, `verein_`,
`spieler_`, `spielbericht_`, `leistungsdaten`, `kader`, `spielplan`), so the
port is close to 1:1. The main structural difference: soccerdonna has **no
confederations layer** — it starts from a single country-grouped competitions
index.

## 2. Goals & Non-Goals

**Goals**
- Full parity with the transfermarkt-scraper entity chain (competitions →
  clubs → players → appearances, plus games / game lineups).
- Output schema field-for-field identical to transfermarkt-scraper, enabling
  downstream pipeline reuse.
- Crawl **everything** on the competitions index by default (all countries, all
  competitions, plus international competitions).
- Current/latest season by default, with a `-a season=YYYY` override for
  historical backfill.

**Non-Goals**
- No new/fresh schema design — we constrain ourselves to TM's schema.
- No multi-season-in-one-run orchestration (run once per season externally).
- No database / storage layer — JSON-Lines to stdout, like TM.

## 3. Confirmed decisions (from brainstorming)

| Decision | Choice |
|---|---|
| Entity scope | **Full parity** with transfermarkt-scraper |
| Output schema | **Mirror TM exactly** (+ a `source` marker field) |
| Competition coverage | **Everything on the index** (filtering supported for free via parents files) |
| Seasons | **Current by default, `-a season=YYYY` override** |
| Build approach | **Port & adapt TM code**, then fix selectors/URLs/root for soccerdonna |

## 4. URL map (confirmed against the live site)

| Entity | soccerdonna pattern |
|---|---|
| Competitions index (root) | `/en/{year}/startseite/wettbewerbeDE.html` |
| Competition | `/en/{name}/startseite/wettbewerb_{CODE}.html` |
| League table | `/en/{name}/tabelle/wettbewerb_{CODE}.html` |
| Fixtures | `/en/{name}/spielplan/wettbewerb_{CODE}.html` |
| Club overview | `/en/{name}/startseite/verein_{ID}.html` |
| Squad (kader) | `/en/{name}/kader/verein_{ID}.html` |
| Player profile | `/en/{name}/profil/spieler_{ID}.html` |
| Player performance data | `/en/{name}/leistungsdaten/spieler_{ID}.html` |
| Match report | `/en/{t1}-{t2}/index/spielbericht_{ID}.html` |

Competition code format: country code + tier/letter, e.g. `ESP1`, `ESP2`,
`ENG1`, `BL1`, `NWSL`, `CL`. Cups use a letter suffix (e.g. `ESPP`).

## 5. Architecture

A standalone Scrapy project that ports transfermarkt-scraper's structure and
adapts it.

- **Stack (mirrors TM):** Python 3 + Scrapy ~2.11, Poetry, JSON-Lines to stdout,
  HTTP cache enabled, `robots.txt` obeyed. Spiders pipe to each other via
  `-a parents=<file>` or stdin, with `parent` linkage nested in each item.
- **Package layout:**
  ```
  soccerdonna_scraper/
    scrapy.cfg
    pyproject.toml
    soccerdonna/
      settings.py
      utils.py
      spiders/
        common.py            # BaseSpider (stdin/file/gzip parents)
        common_comp_club.py  # BaseSpider w/ season + URL building
        confederations.py
        competitions.py
        clubs.py
        clubs_by_url.py
        players.py
        players_from_file.py
        appearances.py
        games.py
        games_urls.py
        games_by_url.py
        game_lineups.py
    samples/                 # one JSON-lines sample per entity
    tests/                   # fixture-based parser tests
      fixtures/              # saved soccerdonna HTML pages
    README.md  DOCUMENTATION.md  SCHEMA.md  API_REFERENCE.md
  ```
- **Copied near-verbatim:** `common.py` parent-loading machinery and the
  JSON-lines / `parent`-linkage convention.
- **Rewritten for soccerdonna:** `utils.py` ID extraction and
  `common_comp_club.py` URL/season building (different URL grammar).

## 6. Spiders & crawl flow

### 6.1 Root resolution — the confederation gap

soccerdonna has no confederations. To preserve TM's exact pipe shape and
`parent`-chain structure, the `confederations` spider emits a **single synthetic
root** pointing at the competitions index, rather than TM's 4 hardcoded
confederations:

```json
{"type": "confederation", "href": "/en/2010/startseite/wettbewerbeDE.html", "name": "soccerdonna", "source": "soccerdonna"}
```

The node carries an honest `name`/`source` marker so it is self-evidently a
structural root (not a real confederation) and is trivially filterable
downstream.

The `competitions` spider parses that country-grouped index, derives
`country_id` / `country_name` per league (from the flag image + country
heading — the same approach TM uses), and emits one competition per league,
including the "international" section (with an empty / `international` country).

*Alternative considered and rejected:* drop `confederations` entirely and make
`competitions` the root. Rejected because it breaks schema parity for no real
gain.

### 6.2 Spider inventory (11, 1:1 with TM)

| Spider | Input → Output |
|---|---|
| `confederations` | root → 1 synthetic confederation (the index) |
| `competitions` | confederation → competitions (per country, incl. international) |
| `clubs` | competition → clubs + inline squad players |
| `clubs_by_url` | club URLs → clubs (bypass hierarchy) |
| `players` | clubs → detailed player profiles + national-team career |
| `players_from_file` | player URLs → players (bypass hierarchy) |
| `appearances` | players → per-match appearance rows |
| `games_urls` | competition → game URLs + metadata (fast path) |
| `games` | competition → full match reports (events, lineups) |
| `games_by_url` | game URLs → games (bypass hierarchy) |
| `game_lineups` | games → starting XI / subs / formation |

### 6.3 Filtering

Because every level reads a parents file, narrow runs ("only ESP1", "only
Spain") need no special code — just filter/grep the competitions file before
piping it onward. Default crawl covers everything on the index.

## 7. Output schema

Field names and nesting mirror transfermarkt-scraper exactly. The only addition
is a provenance marker on top-level entities:

```json
"source": "soccerdonna"
```

### soccerdonna-specific parsing deltas (field names unchanged)

- **ID extraction:** regex on the `_{digits}.html` suffix (`verein_1132`,
  `spieler_38461`, `spielbericht_153373`) and `wettbewerb_([A-Z0-9]+)` for
  competition codes — replaces TM's path-style IDs.
- **Market value:** soccerdonna shows plain euros (`€50,000`). Keep the raw
  string in `market_value` and the parsed int in `current_market_value`,
  matching TM's types.
- **Date format:** soccerdonna uses `DD.MM.YYYY` (`23.10.1999`) vs TM's
  `Mon D, YYYY`. Normalize within the same fields.
- **English labels:** we scrape the `/en/` site, so `:contains(...)` selectors
  use English headings (e.g. "Domestic leagues", "National team career").

### Unknowns to verify at implementation time (not blockers)

These are where soccerdonna may diverge from TM and need fresh selector work:

1. **Season URL grammar** — whether clubs/competitions use `/saison_id/{year}`
   and how cups seasonize (TM swaps `wettbewerb` → `pokalwettbewerb`).
2. **Game event timeline** — TM decodes minutes from a CSS sprite
   (`background-position`); soccerdonna's match report may encode events
   differently.
3. **National-team career sub-page** structure on the player profile.

Each unknown should be resolved by saving a real page to `tests/fixtures/` and
inspecting it before writing the corresponding parser.

## 8. Politeness & settings

soccerdonna is a smaller site than Transfermarkt, so crawl gently:

- Enable `AUTOTHROTTLE_ENABLED`.
- Set a modest `DOWNLOAD_DELAY`.
- Set a descriptive, identifiable `USER_AGENT`.
- Keep `HTTPCACHE_ENABLED` and `ROBOTSTXT_OBEY = True`.
- `FEED_FORMAT = jsonlines`, `FEED_URI = stdout:` (same as TM).

(This deviates from TM, which does not autothrottle.)

## 9. Testing

Fixture-based, offline, deterministic parser tests:

- Save representative soccerdonna HTML pages into `tests/fixtures/`.
- Run each spider's `parse` over the fixture and assert on extracted field
  values.
- Mirrors TM's `test_*_spider.py` approach but with no live network in tests.

## 10. Documentation

Port TM's four docs, rewritten for soccerdonna:

- `README.md` — quick start + crawl diagram.
- `DOCUMENTATION.md` — architecture & data flow.
- `SCHEMA.md` — exhaustive per-entity schemas (like TM's `PLAYER_SCHEMA.md`).
- `API_REFERENCE.md` — per-spider input/output reference.

## 11. Open risks

- The three "unknowns" in §7 are the highest-risk parser work; the game event
  timeline is the most likely to differ materially from TM.
- soccerdonna data completeness at lower tiers / smaller countries is unknown;
  parsers must degrade gracefully on missing fields (inherited from TM's
  approach).
- Selector fragility: `:contains()` English-label selectors break if the site's
  labels change; keep them centralized where practical.
