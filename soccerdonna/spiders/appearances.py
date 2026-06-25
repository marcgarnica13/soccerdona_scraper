import re

from soccerdonna.spiders.common_comp_club import BaseSpider
from soccerdonna.utils import extract_entity_id


def _int(value):
    """Parse a soccerdonna integer cell ('90', '-', '', None) into an int or None.

    Unlike the hierarchy spiders (which default missing numerics to 0), an
    appearance row legitimately has *no* minutes value (an unused substitute,
    "On the bench"), so we return None rather than 0 to preserve that distinction.
    """
    if not value:
        return None
    digits = re.sub(r'[^0-9]', '', value)
    return int(digits) if digits else None


class AppearancesSpider(BaseSpider):
    """Per-player performance data -> one `appearance` item per match.

    GRANULARITY (verified against samples, 2026-06-25)
    --------------------------------------------------
    soccerdonna's `leistungsdaten` page mirrors Transfermarkt's PER-MATCH model.
    The default (current-season) view renders, per competition the player
    featured in, a detail table with one row PER MATCH:

        pl. | Date | Home team | Visiting team | Result | goals | own goals |
        assists | yellow | yellow-red | red | subbed-on | subbed-off | minutes |
        (match-report link)

    We emit one `appearance` per such match row. Rows where the player was an
    unused substitute render a single ``colspan="9"`` "On the bench" cell instead
    of the stat columns; we still emit those (they ARE appearances in the squad),
    with `minutes_played` (and the other per-match stats) left as None.

    The opponent is whichever of the two club cells is NOT the player's own club.
    soccerdonna marks the player's own club with the CSS class ``grey`` on its
    link (and ``opacity70`` on its crest); we pick the *other* club link as the
    opponent. (Verified: exactly one club per row carries ``grey`` across all
    samples with detail tables.)

    DIVERGENCE / EDGE CASE
    ----------------------
    Not every leistungsdaten page carries per-match detail tables. The
    career/all-seasons aggregate view (e.g. sample `spieler_35389.html`) shows
    only per-competition-season AGGREGATE rows (a "Season" + "Club / Competition"
    + "Matches" + totals layout) with NO per-match dates or match-report links.
    For such pages this spider yields ZERO rows (no per-match data to emit) rather
    than fabricating aggregate rows. The richer per-match view is the default we
    fetch (`/leistungsdaten/spieler_{id}.html`), so under normal crawling we land
    on the per-match layout; the aggregate layout only appears when an explicit
    all-seasons season selection has been POSTed. If full history per match is
    ever required, the per-match tables are anchored by ``<a name="{CODE}">``
    headers and reachable per-season via the page's season `<form>` (POST to the
    same `/leistungsdaten/` URL) — not chased here.

    Each match row links to a match report (`spielbericht_{id}.html`); that id is
    captured as `match_id` for downstream joins, but the per-match report page is
    not fetched in this task.
    """

    name = 'appearances'

    def scrape_parents(self):
        # Synthetic fallback so the spider can run (and be instantiated in tests)
        # without an explicit parents pipe. Mirrors the player item shape the
        # `players`/`clubs` spiders emit (a `/profil/` href), which this spider
        # routes to its `/leistungsdaten/` performance-data page.
        return [{
            'type': 'player',
            'href': '/en/gemma-font/profil/spieler_38461.html',
        }]

    def seasonize_entrypoin_href(self, item):
        # Apply the inherited season handling first (plain join when no season is
        # set; `_{season}` suffix otherwise — entity ids are never touched), then
        # route the player-profile URL to its performance-data page.
        url = super().seasonize_entrypoin_href(item)
        return url.replace('/profil/', '/leistungsdaten/')

    def parse(self, response, parent):
        """Performance-data page -> one `appearance` per per-match detail row."""
        href = response.url.replace(self.base_url, '')
        player_id = extract_entity_id(response.url)

        # Each per-match detail table is preceded by an `<a name="{CODE}">`
        # competition anchor (e.g. `<a name="ESP1">Primera División - 25/26</a>`).
        # Iterate tables so we can attach that competition code to every row;
        # aggregate/summary tables (no preceding match anchor, no date cells)
        # naturally yield nothing.
        for table in response.css('table.standard_tabelle'):
            competition_code = self._table_competition_code(table)
            for row in table.css('tr'):
                # A per-match row always carries a date (a `datum_...` link).
                # Header, spacer, summary and "Total" rows have none.
                date_iso = self._row_date(row)
                if not date_iso:
                    continue

                home, away = self._home_away(row)
                # Without any club link we can't be sure this is a match row.
                if home is None and away is None:
                    continue

                yield {
                    'type': 'appearance',
                    'parent': parent,
                    'source': 'soccerdonna',
                    'href': href,
                    'player_id': player_id,
                    'date': date_iso,
                    'competition_code': competition_code,
                    'opponent': self._opponent(row),
                    'home': home,
                    'away': away,
                    'result': self._result(row),
                    'match_id': self._match_id(row),
                    'goals': self._stat(row, on_bench_default=None,
                                        col=self._GOALS_COL),
                    'minutes_played': self._minutes(row),
                }

    # -- row field extractors -------------------------------------------------

    # Detail table column order (0-based) on a played row:
    #   0 pl. | 1 date | 2 home-crest | 3 home-club | 4 away-crest |
    #   5 away-club | 6 result | 7 goals | 8 own-goals | 9 assists |
    #   10 yellow | 11 yellow-red | 12 red | 13 subbed-on | 14 subbed-off |
    #   15 minutes | 16 match-report-link
    _GOALS_COL = 7

    def _row_date(self, row):
        # soccerdonna links each match date to a "what happened" page whose href
        # carries the ISO date: /.../datum_2025-08-30.html -> 2025-08-30. This is
        # more robust than parsing the DD.MM.YY cell text (2-digit year).
        link = row.css('a[href*="datum_"]::attr(href)').get()
        if not link:
            return None
        match = re.search(r'datum_(\d{4}-\d{2}-\d{2})\.html', link)
        return match.group(1) if match else None

    def _club_links(self, row):
        # Club cells point at the squad page: /en/{slug}/historische-kader/
        # verein_{id}_{year}.html. Return (href, is_own) per club link, where
        # `is_own` is True for the player's own club (marked with class `grey`).
        links = []
        for a in row.css('a[href*="verein_"]'):
            cls = a.attrib.get('class', '') or ''
            href = a.attrib.get('href')
            links.append((href, 'grey' in cls.split()))
        return links

    def _home_away(self, row):
        links = self._club_links(row)
        home = self._club_ref(links[0]) if len(links) > 0 else None
        away = self._club_ref(links[1]) if len(links) > 1 else None
        return home, away

    @staticmethod
    def _club_ref(link):
        href, _is_own = link
        # Club hrefs in detail tables are `verein_{id}_{year}.html`; the generic
        # id extractor would grab the trailing season year, so pull the verein id
        # explicitly (falling back to the generic extractor for `verein_{id}.html`).
        match = re.search(r'verein_(\d+)', href)
        club_id = match.group(1) if match else extract_entity_id(href)
        return {'type': 'club', 'href': href, 'club_id': club_id}

    def _opponent(self, row):
        # The opponent is the club that is NOT the player's own. soccerdonna
        # marks the player's own club link with class `grey`; the other club is
        # the opponent. If no marker is present (defensive), fall back to the
        # away side (the second club link), the common "X vs opponent" case.
        links = self._club_links(row)
        if not links:
            return None
        not_own = [link for link in links if not link[1]]
        if not_own:
            return self._club_ref(not_own[0])
        # All marked own (shouldn't happen) -> use the second club if present.
        return self._club_ref(links[1] if len(links) > 1 else links[0])

    def _table_competition_code(self, table):
        # The competition code is the `name` of the nearest preceding `<a name>`
        # anchor (inside the table's preceding <h2> header), e.g. "ESP1", "CL".
        name = table.xpath(
            './preceding::a[@name][1]/@name'
        ).get()
        return name or None

    # A result cell holds a digit:digit scoreline (e.g. "8:0", "0:0", "1:1").
    _RESULT_RE = re.compile(r'^\d+:\d+$')

    def _result(self, row):
        # Match the per-match result cell by STRUCTURE, not colour. Wins/losses
        # carry a colour class (``td.green`` / ``td.red``), but DRAWS render as a
        # plain ``td class="ac s10"`` with no colour class, so a colour-based
        # selector silently dropped them. The result is the (single) cell whose
        # text is an ``N:N`` scoreline; scan the row's cells and return the first
        # such match. Rows with no scoreline (e.g. genuinely result-less rows)
        # yield None.
        for cell in row.css('td'):
            text = self.safe_strip(cell.css('::text').get())
            if text and self._RESULT_RE.match(text):
                return text
        return None

    def _match_id(self, row):
        href = row.css('a[href*="spielbericht_"]::attr(href)').get()
        return extract_entity_id(href) if href else None

    def _minutes(self, row):
        # Played rows put minutes in the second-to-last cell (the last cell is the
        # match-report link). "On the bench" rows have a single colspan="9" cell
        # in place of the stat columns, so there is no minutes cell -> None.
        if row.css('td[colspan="9"]'):
            return None
        cells = row.css('td')
        if len(cells) < 2:
            return None
        return _int(self.safe_strip(cells[-2].css('::text').get()))

    def _stat(self, row, on_bench_default, col):
        if row.css('td[colspan="9"]'):
            return on_bench_default
        cells = row.css('td')
        if len(cells) <= col:
            return on_bench_default
        return _int(self.safe_strip(cells[col].css('::text').get()))
