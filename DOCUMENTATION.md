# soccerdonna-scraper — Architecture & Data Flow

This document explains how the scraper is built and how data moves through it.
For field-level detail see `SCHEMA.md`; for per-spider arguments see
`API_REFERENCE.md`.

## Design goal

Produce JSON-Lines whose schema mirrors the **transfermarkt-scraper** so the two
sources are interchangeable downstream. The scaffolding (the parent-loading
`BaseSpider`, the JSON-Lines `parent`-linkage convention, the synthetic root) is
ported from Transfermarkt near-verbatim; only the URL/ID grammar and the CSS/XPath
selectors are adapted to soccerdonna. Every top-level item carries
`"source": "soccerdonna"`.

## The pipe model

Scrapy is configured to read parent items and write child items as JSON-Lines on
stdout (`FEED_FORMAT='jsonlines'`, `FEED_URI='stdout:'`). Each spider:

1. Loads **parent** items (the previous stage's output).
2. Builds one request per parent (its `href`, optionally seasonized).
3. Parses each response and emits **child** items, each embedding a trimmed copy
   of its `parent`.

Because input and output are both JSON-Lines, spiders compose by piping or via
`-a parents=<file>`:

```
confederations → competitions → clubs → players → appearances
```

### Parent loading (`spiders/common.py` — `BaseSpider`)

`BaseSpider.__init__` resolves parents from, in priority order:

1. **A file** — `-a parents=path.json`. If the filename ends in `.gz` it is read
   with `gzip.open`, otherwise with `open`. (gzip detection is purely by
   extension.)
2. **stdin** — when something is piped in and stdin is non-interactive and
   readable. Each line is parsed as one JSON object.
3. **The spider's `scrape_parents()`** — a synthetic fallback so a spider can run
   standalone (e.g. `scrapy crawl confederations` with no pipe). Most hierarchy
   spiders define a single anchor parent here (ESP1 / FC Barcelona / Gemma Font)
   for convenience and tests.

To keep items compact, **second-level parents are stripped**: when a loaded
parent itself has a nested `parent`, that nested key is deleted before use. So a
child embeds its parent, but not its grandparent.

`start_requests` then issues one `Request` per parent, attaching the parent via
`cb_kwargs={'parent': item}` so the parse callback can embed it in the child.

### Season handling (`spiders/common_comp_club.py`)

`competitions`, `clubs`, `players` and `appearances` extend a season-aware
`BaseSpider` that overrides `seasonize_entrypoin_href`:

* **No `-a season`** (the default, current season): the href is passed through
  **unchanged** — a plain `base_url + href` join. This is the supported,
  well-tested path.
* **`-a season=YYYY`**: the season *start* year is appended as a **filename
  suffix** before `.html`:
  `wettbewerb_ESP1.html` → `wettbewerb_ESP1_2025.html`. Applying the same season
  twice is a no-op (idempotent).

> **Why a filename suffix and not `/saison_id/{year}`?** Recon against live pages
> (2026-06-25) showed soccerdonna encodes the season as a trailing `_{year}`
> token in the filename, **not** as a `/saison_id/` path segment as
> Transfermarkt does. This `_{year}` grammar is **verified for competitions**
> (`wettbewerb_ESP1_2025.html`) and is **best-effort for clubs/players** — treat
> historical-season crawls of those entities as unverified.

> **Entity-id safety.** soccerdonna entity ids and season years are *both* bare
> digit runs in the `_<n>.html` suffix (`verein_1132.html`,
> `wettbewerb_ESP1_2025.html`). A naïve "strip a 4-digit suffix" would destroy
> 4-digit ids (`verein_1132.html → verein.html`). So the seasonizer **never**
> strips a generic digit suffix: with no season it touches nothing, and with a
> season it only *adds* (or keeps) the exact `_{season}` token.

The `appearances` spider additionally routes the player profile href to its
performance-data page: `/profil/` → `/leistungsdaten/` (after applying the season
rule). The **bypass** spiders (`clubs_by_url`, `players_from_file`) override
`start_requests` and therefore **ignore `-a season`** entirely.

## The synthetic confederation root — and why it exists

soccerdonna has **no confederation layer** (no UEFA/CONMEBOL grouping); it has a
single competitions index. Transfermarkt's pipeline, however, starts at
`confederations`. To keep the **pipe shape identical** to Transfermarkt — so the
same orchestration scripts work for both sources — the `confederations` spider
emits **one synthetic confederation item** whose `href` points at soccerdonna's
competitions index page (`/en/2010/startseite/wettbewerbeDE.html`) and whose
`name`/`source` are both `"soccerdonna"`. It is honest about being synthetic (the
marker) while preserving the contract that "the entry point is the
`confederations` spider, fed by nothing."

## Entity hierarchy

| Stage            | Input (parent)        | Page fetched                         | Output item       |
|------------------|-----------------------|--------------------------------------|-------------------|
| `confederations` | *(none / synthetic)*  | *(none — emits a constant)*          | `confederation`   |
| `competitions`   | `confederation`       | competitions index (`wettbewerbeDE`) | `competition` (× many) |
| `clubs`          | `competition`         | each club squad (`kader`)            | `club` + inline `players[]` |
| `players`        | `player`              | player profile (`profil`)            | `player`          |
| `appearances`    | `player`              | performance data (`leistungsdaten`)  | `appearance` (× per match) |

Note the `clubs` spider's `country_name` (and inline player `nationality`) come
straight from the source: country names are rendered in **German even on the
`/en/` pages** (e.g. `"Spanien"`). `country_id` is the stable key. Competition
links on the index are mostly under `/de/` and are normalized to `/en/` so that
all downstream club/player pages and their child links come back in English.

## Politeness

soccerdonna is a small community site, so the crawler is deliberately gentle
(`soccerdonna/settings.py`):

* `ROBOTSTXT_OBEY = True`
* An honest, identifying `USER_AGENT`.
* **AutoThrottle on** — `AUTOTHROTTLE_ENABLED = True`, start delay 1.0s, max delay
  10.0s, target concurrency 1.0.
* `DOWNLOAD_DELAY = 1.0`, `CONCURRENT_REQUESTS_PER_DOMAIN = 2`.
* `CloseSpider` extension capped at 500 items; `HTTPCACHE_ENABLED = True`
  (development aid — responses are cached under `httpcache/`).

Because of these delays, a full chain run takes a minute or two even on a narrow
slice. That is expected.

## Known limitations

1. **Cup / international competitions may lack a standings table.** The `clubs`
   spider extracts club links from the first standings-style table on the
   competition page. League competitions have one; some cup/international
   competition pages do not, so `clubs` is reliable for **league** competitions
   and may return no clubs for others.
2. **Squad pages carry no market value.** The inline `players[].market_value`
   from the `clubs` spider is typically empty/`null`; the authoritative
   `current_market_value` (integer euros) comes from the **player profile**
   (`players` spider).
3. **Bypass spiders ignore `-a season`.** `clubs_by_url` and `players_from_file`
   fetch the exact hrefs they are given and do not seasonize.
4. **Historical-season URL grammar is verified only for competitions.** The
   `_{year}` filename suffix is confirmed for `wettbewerb_*`; for clubs/players
   it is best-effort. The current-season default is the supported path.
5. **Plan 2 (games / fixtures / lineups) is not implemented.** The match-report
   branch (`games_urls`, `games`, `game_lineups`) is a separate, future plan.
