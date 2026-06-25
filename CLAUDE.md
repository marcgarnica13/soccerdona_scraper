# soccerdona_scraper

Scrapy project that collects women's football data from
[soccerdonna.de](https://www.soccerdonna.de) and emits JSON-Lines whose schema
mirrors transfermarkt-scraper (with an added `source: "soccerdonna"` marker).

## Status
**Both branches implemented — 11 spiders, all tests green.**
- **Plan 1 (player backbone):**
  `confederations → competitions → clubs → players → appearances`, plus the
  `clubs_by_url` / `players_from_file` bypass spiders.
- **Plan 2 (games branch):** `games_urls → games → game_lineups`, plus the
  `games_by_url` bypass spider.

The 11 spiders: `appearances`, `clubs`, `clubs_by_url`, `competitions`,
`confederations`, `game_lineups`, `games`, `games_by_url`, `games_urls`,
`players`, `players_from_file`.

## Build / run / test
- **Install:** `poetry install`
- **Entry point:** the `confederations` spider (the synthetic pipeline root).
- **Run a spider:** `poetry run scrapy crawl <spider> -a parents=<file>`
  (parents may also be piped on stdin). Optional `-a season=YYYY` for a
  historical season on `competitions`/`clubs`/`players`/`appearances`.
- **List spiders:** `poetry run scrapy list`
- **Tests:** `poetry run pytest` (offline, against committed HTML in
  `samples/pages/`).

See `README.md`, `DOCUMENTATION.md`, `SCHEMA.md`, and `API_REFERENCE.md` for full
detail.

## Conventions
- Language: Python 3 (^3.9)
- Dependency manager: Poetry
- Test runner: pytest
- Output: JSON-Lines to stdout; each spider reads parent items and emits child
  items, so spiders pipe into each other.
