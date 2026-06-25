# soccerdonna-scraper — Output Schema

Every spider emits **JSON-Lines** (one JSON object per line). Each top-level item
has a `type` discriminator and a `source: "soccerdonna"` marker, and embeds a
trimmed copy of its `parent` (the grandparent is stripped). Examples below are
**real rows** pulled from `samples/output/` (Spain slice, current season,
generated 2026-06-25).

The schema mirrors **transfermarkt-scraper**. Notable **divergences from TM**:

* `current_market_value` is an **integer in euros** (e.g. `50000`), not a string.
* All dates are **ISO `YYYY-MM-DD`** strings (parsed from soccerdonna's
  `DD.MM.YYYY`).
* **Country names are German** even on `/en/` pages (`"Spanien"`, not `"Spain"`);
  `country_id` is the stable key.
* International / cup competitions have `country_name = null` and
  `country_id = null`.
* **Event minutes are plain integers** (e.g. `26`), parsed from the report's
  plain-text minute column — soccerdonna does **not** use Transfermarkt's
  CSS-sprite minute encoding.
* **Lineups are a separate `game_lineup` entity** (from the `aufstellung` page),
  not nested inside the `game` item as Transfermarkt does. The `game` item from
  the match report carries the **formation**; the `game_lineup` item carries the
  starting XI / substitutes (its `formation` is always `null`).
* Club and national-team **names render in German** even on `/en/` pages.

---

## `confederation`

A single synthetic root (soccerdonna has no confederations). It exists only to
preserve the Transfermarkt pipe shape.

| Field    | Type   | Description                                            |
|----------|--------|-------------------------------------------------------|
| `type`   | string | Always `"confederation"`.                             |
| `href`   | string | Path to the competitions index page.                  |
| `name`   | string | Always `"soccerdonna"` (it is synthetic).             |
| `source` | string | Always `"soccerdonna"`.                               |

```json
{"type": "confederation", "href": "/en/2010/startseite/wettbewerbeDE.html", "name": "soccerdonna", "source": "soccerdonna"}
```

---

## `competition`

One per competition on the country-grouped index page.

| Field              | Type           | Description                                                        |
|--------------------|----------------|-------------------------------------------------------------------|
| `type`             | string         | Always `"competition"`.                                           |
| `parent`           | object         | The `confederation` item that produced it.                        |
| `source`           | string         | Always `"soccerdonna"`.                                            |
| `country_id`       | string \| null | Numeric flag id from `/flaggen/{id}.gif`. `null` for international.|
| `country_name`     | string \| null | Country name **in German** (`"Spanien"`). `null` for international.|
| `competition_code` | string         | soccerdonna competition code, e.g. `"ESP1"`, `"CL"`.              |
| `competition_type` | string \| null | Tier label, slugged via inflection, e.g. `"1_liga"`.             |
| `href`             | string         | Competition page path (normalized to `/en/`).                     |

```json
{"type": "competition", "parent": {"type": "confederation", "href": "/en/2010/startseite/wettbewerbeDE.html", "name": "soccerdonna", "source": "soccerdonna"}, "source": "soccerdonna", "country_id": "157", "country_name": "Spanien", "competition_code": "ESP1", "competition_type": "1_liga", "href": "/en/primera-division-femenina/startseite/wettbewerb_ESP1.html"}
```

---

## `club` (with inline `players[]`)

One per club. The squad is embedded as a `players[]` array of lightweight player
references (the authoritative, detailed player record comes from the `players`
spider).

| Field      | Type   | Description                                       |
|------------|--------|---------------------------------------------------|
| `type`     | string | Always `"club"`.                                  |
| `parent`   | object | The `competition` item.                           |
| `source`   | string | Always `"soccerdonna"`.                           |
| `href`     | string | Club overview (`startseite`) path.                |
| `name`     | string | Club name, e.g. `"FC Barcelona"`.                 |
| `players`  | array  | Inline squad members (see below).                 |

### Inline `players[]` element

| Field          | Type           | Description                                            |
|----------------|----------------|--------------------------------------------------------|
| `player_id`    | string         | Numeric id from `spieler_{id}.html`.                   |
| `href`         | string         | Player profile path.                                   |
| `name`         | string         | Display name.                                          |
| `number`       | string \| null | Shirt number.                                          |
| `position`     | string \| null | Position label.                                        |
| `nationality`  | string \| null | Nationality (flag title).                              |
| `market_value` | string \| null | Squad-page value — **usually `null`** (see note 2 in `DOCUMENTATION.md`). Use the player profile's `current_market_value`. |

```json
{"type": "club", "parent": {"type": "competition", "country_id": "157", "country_name": "Spanien", "competition_code": "ESP1", "competition_type": "1_liga", "href": "/en/primera-division-femenina/startseite/wettbewerb_ESP1.html"}, "source": "soccerdonna", "href": "/en/fc-barcelona/startseite/verein_1132.html", "name": "FC Barcelona", "players": [{"player_id": "38461", "href": "/en/gemma-font/profil/spieler_38461.html", "name": "Gemma Font", "number": "1", "position": "Goalkeeper", "nationality": "Spain", "market_value": null}]}
```

---

## `player`

The detailed profile record. Input to this spider is a **player item** (a profile
href), so its embedded `parent` is the player reference it was fed.

| Field                  | Type           | Description                                                       |
|------------------------|----------------|------------------------------------------------------------------|
| `type`                 | string         | Always `"player"`.                                               |
| `parent`               | object         | The player item it was fed.                                      |
| `source`               | string         | Always `"soccerdonna"`.                                          |
| `href`                 | string         | Player profile path.                                            |
| `player_id`            | string         | Numeric id from `spieler_{id}.html`.                           |
| `name`                 | string         | Display name (leading shirt number stripped).                  |
| `last_name`            | string \| null | Last whitespace-delimited token of `name`.                     |
| `current_club`         | object \| null | `{ "href": <club startseite href> }`.                          |
| `name_in_home_country` | string \| null | Native-country name.                                            |
| `date_of_birth`        | string \| null | ISO `YYYY-MM-DD`.                                               |
| `place_of_birth`       | string \| null | Birthplace.                                                    |
| `citizenship`          | string \| null | Nationality.                                                   |
| `height`               | string \| null | Height as shown, e.g. `"1,65"` (comma decimal, source format). |
| `foot`                 | string \| null | `"right"`, `"left"`, `"both"`, …                              |
| `position`             | string \| null | Playing position.                                              |
| `current_market_value` | int \| null    | **Integer euros** (e.g. `50000`); `null` if absent.            |
| `national_career`      | array          | National-team entries (see below); `[]` if none.              |

### `national_career[]` element

| Field              | Type           | Description                                                  |
|--------------------|----------------|-------------------------------------------------------------|
| `national_team_id` | string         | Id from `nationalmannschaft_{id}.html`.                     |
| `href`             | string         | National-team page path.                                    |
| `name`             | string         | Team name **in German** (e.g. `"Spanien U23"`).             |
| `season`           | string \| null | Season label, or `null`.                                    |
| `matches`          | int            | Caps (defaults to `0`).                                     |
| `goals`            | int            | Goals (defaults to `0`).                                    |

```json
{"type": "player", "parent": {"type": "player", "href": "/en/gemma-font/profil/spieler_38461.html"}, "source": "soccerdonna", "href": "/en/gemma-font/profil/spieler_38461.html", "player_id": "38461", "name": "Gemma Font", "last_name": "Font", "current_club": {"href": "/en/fc-barcelona/startseite/verein_1132.html"}, "name_in_home_country": "Gemma Font Oliveras", "date_of_birth": "1999-10-23", "place_of_birth": "Tagamanent", "citizenship": "Spain", "height": "1,65", "foot": "right", "position": "Goalkeeper", "current_market_value": 50000, "national_career": [{"national_team_id": "8954", "href": "/en/spanien-u23/startseite/nationalmannschaft_8954.html", "name": "Spanien U23", "season": null, "matches": 4, "goals": 0}]}
```

---

## `appearance`

One per match row on a player's performance-data (`leistungsdaten`) page. Input
is a **player item**; the spider routes `/profil/` → `/leistungsdaten/`.

| Field              | Type           | Description                                                            |
|--------------------|----------------|------------------------------------------------------------------------|
| `type`             | string         | Always `"appearance"`.                                                 |
| `parent`           | object         | The player item it was fed.                                            |
| `source`           | string         | Always `"soccerdonna"`.                                                |
| `href`             | string         | Performance-data page path.                                            |
| `player_id`        | string         | Numeric id from `spieler_{id}.html`.                                 |
| `date`             | string         | Match date, ISO `YYYY-MM-DD`.                                          |
| `competition_code` | string \| null | Competition the match belongs to, e.g. `"ESP1"`.                     |
| `opponent`         | object \| null | The other club: `{ "type": "club", "href": …, "club_id": … }`.      |
| `home`             | object \| null | Home club ref (same shape as `opponent`).                            |
| `away`             | object \| null | Away club ref.                                                        |
| `result`           | string \| null | Final score, e.g. `"8:0"`.                                            |
| `match_id`         | string \| null | Id from `spielbericht_{id}.html` (for downstream joins).            |
| `goals`            | int \| null    | Goals scored. `null` for an unused-substitute ("On the bench") row.   |
| `minutes_played`   | int \| null    | Minutes. `null` when the player did not play (bench / no minutes).    |

```json
{"type": "appearance", "parent": {"type": "player", "href": "/en/gemma-font/profil/spieler_38461.html"}, "source": "soccerdonna", "href": "/en/gemma-font/leistungsdaten/spieler_38461.html", "player_id": "38461", "date": "2025-08-30", "competition_code": "ESP1", "opponent": {"type": "club", "href": "/en/alhama-cf/historische-kader/verein_7543_2025.html", "club_id": "7543"}, "home": {"type": "club", "href": "/en/fc-barcelona/historische-kader/verein_1132_2025.html", "club_id": "1132"}, "away": {"type": "club", "href": "/en/alhama-cf/historische-kader/verein_7543_2025.html", "club_id": "7543"}, "result": "8:0", "match_id": "152154", "goals": null, "minutes_played": null}
```

> In the Gemma Font sample, 48 appearance rows were emitted (the full squad
> match list), 15 of them with non-null `minutes_played` — she is a goalkeeper,
> so many rows are bench appearances with `null` minutes. That is by design:
> `null` distinguishes "in the squad but did not play" from "played 0 minutes".

---

## `game`

One per fixture. Two spiders emit it:

* `games_urls` emits a **lightweight metadata** `game` (no events, no
  formations) discovered from the matchday overview — the fast path.
* `games` / `games_by_url` emit a **full** `game` from the match report, adding
  per-club `formation` and the `events[]` array.

The example below is a real **full** `game` (from `games_by_url`).

| Field        | Type           | Description                                                                 |
|--------------|----------------|-----------------------------------------------------------------------------|
| `type`       | string         | Always `"game"`.                                                            |
| `parent`     | object         | The `competition` item (`games`/`games_urls`) or the fed `game` item (`games_by_url`). |
| `source`     | string         | Always `"soccerdonna"`.                                                     |
| `game_id`    | string         | Numeric id from `spielbericht_{id}.html`.                                  |
| `href`       | string         | Match-report path (`index/spielbericht_{id}.html`).                        |
| `date`       | string \| null | Kickoff date, ISO `YYYY-MM-DD`, or `null`.                                 |
| `home_club`  | object         | `{ "href": <club startseite href>, "formation": <str \| null> }`.          |
| `away_club`  | object         | Same shape as `home_club`.                                                  |
| `result`     | string \| null | Final score, e.g. `"2:0"`, or `null`.                                      |
| `events`     | array          | Goals, substitutions, and cards (see below). `[]` from `games_urls`.       |

> On the **lightweight** metadata `game` from `games_urls`, `home_club`/`away_club`
> are just `{ "href": … }` (no `formation`) and there is **no `events` key**.

### `events[]` — goal / card

| Field    | Type        | Description                                            |
|----------|-------------|--------------------------------------------------------|
| `type`   | string      | `"goal"` or `"card"`.                                  |
| `minute` | int \| null | Match minute (plain integer), or `null` if unparsable. |
| `club`   | object \| null | `{ "href": <club href> }` — the scoring/booked team. |
| `player` | object \| null | `{ "href": <player profile href> }`.                |

### `events[]` — substitution

| Field        | Type        | Description                                                     |
|--------------|-------------|-----------------------------------------------------------------|
| `type`       | string      | `"substitution"`.                                              |
| `minute`     | int \| null | Match minute.                                                  |
| `club`       | object \| null | `{ "href": <club href> }`.                                  |
| `player_out` | object      | `{ "href": … }` — the player coming off.                       |
| `player_in`  | object      | `{ "href": … }` — the player coming on.                        |
| `player`     | object      | Alias of `player_out` (kept for consistency with goal/card).  |

```json
{"type": "game", "parent": {"type": "game", "href": "/en/x/index/spielbericht_153373.html"}, "source": "soccerdonna", "game_id": "153373", "href": "/en/x/index/spielbericht_153373.html", "date": "2026-05-31", "home_club": {"href": "/en/real-sociedad/startseite/verein_1135.html", "formation": "4-4-2"}, "away_club": {"href": "/en/atletico-de-madrid/startseite/verein_1129.html", "formation": "3-5-2"}, "result": "2:0", "events": [{"type": "goal", "minute": 26, "club": {"href": "/en/real-sociedad/startseite/verein_1135.html"}, "player": {"href": "/en/pardo/profil/spieler_51098.html"}}, {"type": "substitution", "minute": 57, "club": {"href": "/en/real-sociedad/startseite/verein_1135.html"}, "player": {"href": "/en/uria/profil/spieler_42898.html"}, "player_out": {"href": "/en/uria/profil/spieler_42898.html"}, "player_in": {"href": "/en/cahynova/profil/spieler_11566.html"}}, {"type": "card", "minute": 48, "club": {"href": "/en/atletico-de-madrid/startseite/verein_1129.html"}, "player": {"href": "/en/menayo/profil/spieler_22162.html"}}]}
```

> The anchor game `153373` (Real Sociedad 2:0 Atlético de Madrid) emitted **14
> events** — 2 goals, 10 substitutions, 2 cards. Club and player names render in
> **German**; `href` is the stable reference.

---

## `game_lineup`

One per game, from the separate `aufstellung` lineup page. Input is a **game
item** (the `game_lineups` spider routes its `href` to the `aufstellung/`
sub-page).

| Field       | Type   | Description                                              |
|-------------|--------|----------------------------------------------------------|
| `type`      | string | Always `"game_lineup"`.                                  |
| `parent`    | object | The `game` item it was fed.                              |
| `source`    | string | Always `"soccerdonna"`.                                  |
| `game_id`   | string | Numeric id from `spielbericht_{id}.html`.               |
| `href`      | string | Lineup page path (`aufstellung/spielbericht_{id}.html`). |
| `home_club` | object | Home team lineup (see below).                            |
| `away_club` | object | Away team lineup (same shape).                           |

### `home_club` / `away_club`

| Field             | Type           | Description                                                            |
|-------------------|----------------|------------------------------------------------------------------------|
| `href`            | string \| null | Club `startseite` href.                                                |
| `formation`       | `null`         | **Always `null`** — the aufstellung page has no formation string; the formation lives on the `game` item (see header note). |
| `starting_lineup` | array          | The starting XI — typically **11** player elements.                    |
| `substitutes`     | array          | The named substitutes.                                                 |

### player element (in `starting_lineup` / `substitutes`)

| Field       | Type           | Description                              |
|-------------|----------------|------------------------------------------|
| `player_id` | string         | Numeric id from `spieler_{id}.html`.    |
| `href`      | string         | Player profile path.                     |
| `name`      | string         | Display name.                            |
| `number`    | string \| null | Shirt number.                            |

```json
{"type": "game_lineup", "parent": {"type": "game", "href": "/en/x/index/spielbericht_153373.html"}, "source": "soccerdonna", "game_id": "153373", "href": "/en/x/aufstellung/spielbericht_153373.html", "home_club": {"href": "/en/real-sociedad/startseite/verein_1135.html", "formation": null, "starting_lineup": [{"player_id": "88505", "href": "/en/julia-arrula/profil/spieler_88505.html", "name": "Julia Arrula", "number": "13"}, {"player_id": "84969", "href": "/en/aiara-agirrezabala/profil/spieler_84969.html", "name": "Aiara Agirrezabala", "number": "24"}], "substitutes": [{"player_id": "78404", "href": "/en/alazne-estensoro/profil/spieler_78404.html", "name": "Alazne Estensoro", "number": "1"}]}, "away_club": {"href": "/en/atletico-de-madrid/startseite/verein_1129.html", "formation": null, "starting_lineup": [{"player_id": "3659", "href": "/en/lola-gallardo/profil/spieler_3659.html", "name": "Lola Gallardo", "number": "1"}, {"player_id": "37897", "href": "/en/lauren-leal/profil/spieler_37897.html", "name": "Lauren Leal", "number": "4"}], "substitutes": [{"player_id": "4591", "href": "/en/patricia-larque/profil/spieler_4591.html", "name": "Patricia Larqué", "number": "13"}]}}
```

> The anchor game `153373` lineup emitted **11 starters per side** (7 home subs,
> 9 away subs). The starting and substitute lists shown above are truncated to
> two/one entries for readability.
