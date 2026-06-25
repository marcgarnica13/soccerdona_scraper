# soccerdonna-scraper

A [Scrapy](https://scrapy.org/) project that collects **women's football data**
from [soccerdonna.de](https://www.soccerdonna.de) and emits it as JSON-Lines.

The output schema **mirrors the
[transfermarkt-scraper](https://github.com/dcaribou/transfermarkt-scraper)
schema** as closely as the source data allows, so downstream consumers can reuse
the same pipelines. Every top-level item additionally carries a
`"source": "soccerdonna"` marker so soccerdonna rows are never confused with
Transfermarkt rows.

> **Scope:** This is **Plan 1 — the player backbone**
> (`confederations → competitions → clubs → players → appearances`). The games
> branch (fixtures, match reports, lineups) is Plan 2 and is **not yet
> implemented**.

## Install

```bash
poetry install
```

This creates a virtual environment and installs Scrapy, inflection,
python-dateutil and the dev dependency pytest.

## Crawl model

Each spider reads **parent** items (JSON-Lines) on stdin or from a file
(`-a parents=<file>`) and emits **child** items to stdout, so spiders pipe into
each other:

```
confederations  →  competitions  →  clubs  →  players  →  appearances
 (synthetic root)    (index page)    (squad)   (profile)   (per-match)
```

* `confederations` — synthetic root (soccerdonna has no confederations); emits a
  single item pointing at the competitions index.
* `competitions` — parses the country-grouped index into one item per
  competition (Spain, Germany, … plus international cups).
* `clubs` — for each competition, follows every member club's squad (`kader`)
  page and emits a `club` item with an inline `players[]` array.
* `players` — for each player, fetches the profile page and emits a detailed
  `player` item (DOB, nationality, height, foot, market value, national career …).
* `appearances` — for each player, fetches the performance-data
  (`leistungsdaten`) page and emits one `appearance` item per match.

Two **bypass** spiders let you start in the middle from a hand-supplied URL list:
`clubs_by_url` and `players_from_file`.

## Run examples

The full Plan-1 chain on a narrow Spain slice (this is exactly how
`samples/output/` was generated):

```bash
mkdir -p samples/output

# 1. Synthetic root
poetry run scrapy crawl confederations > samples/output/confederations.json

# 2. All competitions, then keep just the Spanish first tier (ESP1)
poetry run scrapy crawl competitions -a parents=samples/output/confederations.json > /tmp/all_comps.json
grep ESP1 /tmp/all_comps.json > samples/output/competitions.json

# 3. Clubs (each with an inline players[] array)
poetry run scrapy crawl clubs -a parents=samples/output/competitions.json > samples/output/clubs.json

# 4. Players — pipe club items straight in; the inline players[] is auto-expanded
head -n 1 samples/output/clubs.json | poetry run scrapy crawl players > samples/output/players.json

# 5. Appearances — input is player items (profile hrefs)
head -n 1 samples/output/players.json | poetry run scrapy crawl appearances > samples/output/appearances.json
```

> **Note on the players/appearances input.** The `clubs | players` pipe works
> drop-in, exactly like transfermarkt-scraper. The `clubs` spider nests its
> squad inside each club's `players[]` array, and the `players` spider
> **auto-expands** that array into one profile request per player (the emitted
> player's `parent` is the club). You can also feed bare **player items** (each
> with a player-profile `href`) directly — e.g. from `players_from_file` or a
> flattened list. The `appearances` spider consumes player items.
> See `API_REFERENCE.md` for the per-spider input contract.

### Bypass spiders

```bash
# Scrape specific clubs from a URL list (skips competition discovery)
poetry run scrapy crawl clubs_by_url -a parents=my_clubs.json > clubs.json

# Re-scrape specific players from a URL list (skips the whole hierarchy)
poetry run scrapy crawl players_from_file -a parents=players_to_update.json > players.json
```

### Historical seasons

Pass `-a season=YYYY` (the season *start* year) to `competitions`, `clubs`,
`players` or `appearances`. When omitted, the **current season** (the supported,
well-tested default) is used. See `DOCUMENTATION.md` for the season URL grammar
and its caveats.

## Validate the output

Every file is newline-delimited JSON. To check it:

```bash
for f in samples/output/*.json; do
  echo "== $f =="
  python3 -c "import json; [json.loads(l) for l in open('$f') if l.strip()]; print('ok')"
done
```

## Documentation

| File               | Contents                                                        |
|--------------------|-----------------------------------------------------------------|
| `DOCUMENTATION.md` | Architecture, data flow, season handling, politeness, limits.   |
| `SCHEMA.md`        | Every entity's fields, types and real examples.                 |
| `API_REFERENCE.md` | Per-spider input/output contract and arguments.                 |

## Tests

```bash
poetry run pytest
```

Tests run **offline** against committed HTML samples in `samples/pages/` (the raw
input the parsers read — distinct from `samples/output/`, the generated
JSON-Lines).
