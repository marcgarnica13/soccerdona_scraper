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

* **Input:** **player items** — each a `{type, href}` whose `href` is a player
  **profile** path (`/…/profil/spieler_{id}.html`).
* **Output:** one detailed `player` item per input.

> The `clubs` spider nests players inside each club's `players[]`. To go
> clubs → players, **flatten** that array into one player item per line first:
>
> ```bash
> cat clubs.json \
>   | python3 -c 'import json,sys
> for line in sys.stdin:
>     c=json.loads(line)
>     for p in c["players"]:
>         print(json.dumps({"type":"player","href":p["href"]}))' \
>   | poetry run scrapy crawl players > players.json
> ```
>
> Feeding a raw `club` item to `players` would fetch the *club* page and
> mis-parse it.

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

## Bypass spiders

These let you start mid-hierarchy from a hand-supplied URL list. Both override
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

---

## Item shapes

See `SCHEMA.md` for the full field list and a real example of each item type
(`confederation`, `competition`, `club` + inline player, `player`, `appearance`).
