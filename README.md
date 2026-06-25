# soccerdonna-scraper

A [Scrapy](https://scrapy.org/) project that collects **women's football data**
from [soccerdonna.de](https://www.soccerdonna.de) and emits it as JSON-Lines.

The output schema **mirrors the
[transfermarkt-scraper](https://github.com/dcaribou/transfermarkt-scraper)
schema** as closely as the source data allows, so downstream consumers can reuse
the same pipelines. Every top-level item additionally carries a
`"source": "soccerdonna"` marker so soccerdonna rows are never confused with
Transfermarkt rows.

> **Scope:** Both planned branches are implemented. **Plan 1 — the player
> backbone** (`confederations → competitions → clubs → players → appearances`)
> and **Plan 2 — the games branch** (`games_urls → games → game_lineups`, plus
> the `games_by_url` bypass). The project has **11 spiders** in total.

## Repository

```bash
git clone git@github.com:marcgarnica13/soccerdona_scraper.git
cd soccerdona_scraper
```

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
                  ┌─ players  →  appearances        (player backbone)
confederations  →  competitions  →  clubs
                  └─ games_urls  →  games  →  game_lineups   (games branch)
 (synthetic root)    (index page)
```

The two branches share the same `competition` items as input. The **player
backbone**:

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

The **games branch**:

* `games_urls` — for each competition, walks the per-matchday overview pages and
  emits one lightweight `game` item per fixture (date, teams, result) **without**
  opening each match report (the fast path).
* `games` — extends `games_urls`: instead of metadata, follows every fixture to
  its full match report (`index/spielbericht_{id}.html`) and emits a `game` item
  with formations and a `events[]` array (goals, substitutions, cards).
* `game_lineups` — for each game, fetches the separate lineup
  (`aufstellung/spielbericht_{id}.html`) page and emits a `game_lineup` item with
  each team's starting XI and substitutes.

Three **bypass** spiders let you start in the middle from a hand-supplied URL
list: `clubs_by_url`, `players_from_file`, and `games_by_url` (parse specific
match reports by URL, skipping matchday discovery).

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

### Games branch

The full games chain on the Spanish first tier (this visits every matchday, so
it takes a few minutes with AutoThrottle):

```bash
# Full match reports (with events) for every ESP1 fixture
grep ESP1 samples/output/competitions.json | poetry run scrapy crawl games > games.json
```

`samples/output/{games,game_lineups}.json` were generated deterministically via
the `games_by_url` / `game_lineups` bypass on two anchor games:

```bash
# Full match reports (clubs, formations, events) by URL
printf '%s\n%s\n' \
  '{"type":"game","href":"/en/x/index/spielbericht_153373.html"}' \
  '{"type":"game","href":"/en/x/index/spielbericht_153376.html"}' \
  | poetry run scrapy crawl games_by_url > samples/output/games.json

# Lineups (starting XI + substitutes) for the same games
printf '%s\n%s\n' \
  '{"type":"game","href":"/en/x/index/spielbericht_153373.html"}' \
  '{"type":"game","href":"/en/x/index/spielbericht_153376.html"}' \
  | poetry run scrapy crawl game_lineups > samples/output/game_lineups.json
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

## Disclaimer

This project is for research and educational purposes. It scrapes publicly
available data from soccerdonna.de; respect the site's `robots.txt` and terms of
use, and crawl politely (the spiders enable AutoThrottle by default).

## License

Released under the [MIT License](LICENSE).
