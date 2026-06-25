# soccerdonna-scraper — API Reference

Per-spider input/output contract and arguments. Run everything from the repo root
via `poetry run scrapy crawl <spider> [args]`. Output is JSON-Lines on stdout;
redirect it to a file.

## Common arguments

| Argument         | Applies to                                            | Meaning                                                                                   |
|------------------|-------------------------------------------------------|-------------------------------------------------------------------------------------------|
| `-a parents=<f>` | all spiders                                           | Read parent items from file `<f>` (JSON-Lines; `.gz` auto-detected). If omitted, parents are read from **stdin**, or fall back to the spider's synthetic anchor. |
| `-a season=YYYY` | `competitions`, `clubs`, `players`, `appearances`     | Season *start* year. Appends a `_{YYYY}` filename suffix. Omit for the current season (supported default). **Ignored** by `clubs_by_url` and `players_from_file`. |
| `-a base_url=<u>`| all spiders                                           | Override the base URL (default `https://www.soccerdonna.de`).                             |

Parents may be piped instead of passed as a file:
`scrapy crawl A | scrapy crawl B`.

---

## `confederations` — entry point

The pipeline entry point. Takes **no real input** (emits a synthetic root).

* **Input:** none (uses a synthetic `{type: root}` parent internally).
* **Output:** exactly one `confederation` item pointing at the competitions index.

```bash
poetry run scrapy crawl confederations > confederations.json
```

---

## `competitions`

* **Input:** `confederation` items (the index href).
* **Output:** one `competition` item per competition on the index (per-country
  leagues + international cups).

```bash
poetry run scrapy crawl competitions -a parents=confederations.json > competitions.json
```

Historical season:

```bash
poetry run scrapy crawl competitions -a parents=confederations.json -a season=2024 > competitions_2024.json
```

---

## `clubs`

* **Input:** `competition` items.
* **Output:** one `club` item per member club, each with an inline `players[]`
  array. The spider follows each club's squad (`kader`) page.
* **Note:** reliable for **league** competitions (cup/international pages may lack
  a standings table — see `DOCUMENTATION.md`, Known limitations).

```bash
poetry run scrapy crawl clubs -a parents=competitions.json > clubs.json
```

---

## `players`

* **Input:** accepts **two shapes** (drop-in like transfermarkt-scraper):
  * a `club` item with an inline `players[]` array — the spider **auto-expands**
    it into one profile request per player, setting each emitted player's
    `parent` to the club; **or**
  * a bare **player item** — a `{type, href}` whose `href` is a player
    **profile** path (`/…/profil/spieler_{id}.html`).
* **Output:** one detailed `player` item per player.

> The `clubs | players` pipe works drop-in — feed `club` items straight in and
> the inline squad is expanded automatically:
>
> ```bash
> head -n 1 clubs.json | poetry run scrapy crawl players > players.json
> ```
>
> Bare player items (e.g. from `players_from_file` or a flattened list) are
> still accepted and fetched directly.

---

## `appearances`

* **Input:** **player items** (profile hrefs). The spider routes each
  `/profil/` href to its `/leistungsdaten/` performance-data page.
* **Output:** one `appearance` item per match row.

```bash
head -n 1 players.json | poetry run scrapy crawl appearances > appearances.json
```

With a season:

```bash
poetry run scrapy crawl appearances -a parents=players.json -a season=2024 > appearances_2024.json
```

---

## Games branch

A second branch off `competition` items: fixtures, full match reports, and
lineups. `games` extends `games_urls`; `games_by_url` extends `games`. See
`DOCUMENTATION.md` ("The games branch") for the matchday-walk discovery.

### `games_urls`

* **Input:** `competition` items.
* **Output:** one **lightweight** `game` item per fixture (`game_id`, `href`,
  `date`, `home_club`/`away_club` hrefs, `result`) — **no events** — discovered
  by walking the matchday-overview pages. The fast path.
* **Note:** visits every matchday, so a full season takes a few minutes with
  AutoThrottle. League competitions only (cup/lower tiers may lack overviews →
  zero rows).

```bash
grep ESP1 competitions.json | poetry run scrapy crawl games_urls > games_urls.json
```

### `games`

* **Input:** `competition` items (same discovery as `games_urls`).
* **Output:** one **full** `game` item per fixture — adds per-club `formation`
  and the `events[]` array (goals / substitutions / cards) by following each
  fixture to its match report.

```bash
grep ESP1 competitions.json | poetry run scrapy crawl games > games.json
```

### `game_lineups`

* **Input:** `game` items. Each `href` is routed to its `aufstellung/` lineup
  page.
* **Output:** one `game_lineup` item per game (each team's starting XI +
  substitutes; `formation` is always `null` — it lives on the `game` item).

```bash
printf '%s\n' '{"type":"game","href":"/en/x/index/spielbericht_153373.html"}' \
  | poetry run scrapy crawl game_lineups > game_lineups.json
```

---

## Bypass spiders

These let you start mid-hierarchy from a hand-supplied URL list. All override
`start_requests` and therefore **ignore `-a season`** (they fetch the exact hrefs
given).

### `clubs_by_url`

* **Input:** `club` items. Each `href` (a `startseite` or `kader` path) is routed
  to the squad (`kader`) page.
* **Output:** `club` items with inline `players[]` (same as `clubs`).
* **Reuses:** `ClubsSpider.parse_details`.

```bash
poetry run scrapy crawl clubs_by_url -a parents=my_clubs.json > clubs.json
```

### `players_from_file`

* **Input:** `player` items (profile hrefs).
* **Output:** detailed `player` items (same as `players`).
* **Reuses:** `PlayersSpider.parse`.

```bash
poetry run scrapy crawl players_from_file -a parents=players_to_update.json > players.json
```

### `games_by_url`

* **Input:** `game` items (any `…/spielbericht_{id}.html` href; an
  `/aufstellung/` href is rerouted to `/index/`). The report loads by id
  regardless of slug.
* **Output:** **full** `game` items with events (same as `games`).
* **Reuses:** `GamesSpider.parse_game`.

```bash
printf '%s\n' '{"type":"game","href":"/en/x/index/spielbericht_153373.html"}' \
  | poetry run scrapy crawl games_by_url > games.json
```

---

## Item shapes

See `SCHEMA.md` for the full field list and a real example of each item type
(`confederation`, `competition`, `club` + inline player, `player`, `appearance`,
`game` + `events[]`, `game_lineup`).
