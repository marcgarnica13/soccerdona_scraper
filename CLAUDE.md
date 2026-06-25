# soccerdona_scraper

Scrapy project that collects women's football data from
[soccerdonna.de](https://www.soccerdonna.de) and emits JSON-Lines whose schema
mirrors transfermarkt-scraper (with an added `source: "soccerdonna"` marker).

## Status
**Plan 1 (player backbone) implemented:**
`confederations → competitions → clubs → players → appearances`, plus the
`clubs_by_url` / `players_from_file` bypass spiders. Plan 2 (games / fixtures /
lineups) is not yet built.

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
