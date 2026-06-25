import re

from scrapy import Request

from soccerdonna.spiders.common_comp_club import BaseSpider
from soccerdonna.utils import extract_entity_id, parse_market_value, parse_date_de


def _int(value):
    """Parse a soccerdonna integer cell ('4', '-', '') into an int, default 0."""
    if not value:
        return 0
    digits = re.sub(r'[^0-9]', '', value)
    return int(digits) if digits else 0


class PlayersSpider(BaseSpider):
    name = 'players'

    def scrape_parents(self):
        # Synthetic fallback so the spider can run (and be instantiated in tests)
        # without an explicit parents pipe. Points at a known player profile,
        # the same shape the `clubs` spider emits for inline players[].
        return [{
            'type': 'player',
            'href': '/en/gemma-font/profil/spieler_38461.html',
        }]

    def start_requests(self):
        """Build profile requests, expanding inline club squads (TM-style).

        Mirrors transfermarkt-scraper's `clubs | players` pipe: a `clubs` item
        carries an inline `players[]` squad, so we fan out one profile request
        per inline player and set the emitted player's `parent` to the club
        (matching TM, where `player.parent == club`). Any other entrypoint
        (a bare player item, as produced by `players_from_file` or a flattened
        list) is fetched directly by its own href. Purely additive: direct
        player piping is unchanged.
        """
        for item in self.entrypoints:
            players = item.get('players')
            if item.get('type') == 'club' and isinstance(players, list):
                for player in players:
                    href = player.get('href')
                    if not href:
                        continue
                    url = self.seasonize_entrypoin_href(
                        {'type': 'player', 'href': href}
                    )
                    yield Request(url, cb_kwargs={'parent': item})
            else:
                url = self.seasonize_entrypoin_href(item)
                yield Request(url, cb_kwargs={'parent': item})

    def parse(self, response, parent):
        """Player profile page -> one detailed player item."""
        def field(label):
            # soccerdonna profile data is a label/value list; the value lives in
            # the td immediately following the label td.
            return self.safe_strip(
                response.xpath(
                    f'//td[normalize-space(text())="{label}"]'
                    f'/following-sibling::td[1]'
                ).xpath('normalize-space(string())').get()
            )

        dob_raw = field('Date of birth:')
        name = self._name(response)
        yield {
            'type': 'player',
            'parent': parent,
            'source': 'soccerdonna',
            'href': response.url.replace(self.base_url, ''),
            'player_id': extract_entity_id(response.url),
            'name': name,
            'last_name': self._last_name(name),
            'current_club': self._current_club(response),
            'name_in_home_country': field('Name in native country:'),
            'date_of_birth': parse_date_de(dob_raw),
            'place_of_birth': field('Place of birth:'),
            'citizenship': field('Nationality:'),
            'height': field('Height:'),
            'foot': field('Foot:'),
            'position': field('Position:'),
            'current_market_value': parse_market_value(field('Market value:')),
            'national_career': self._national_career(response),
        }

    def _name(self, response):
        # The h1 carries a leading shirt number, e.g. "1 Gemma Font". Strip a
        # leading digit run so we keep just the player's name.
        raw = self.safe_strip(
            response.css('h1').xpath('normalize-space(string())').get()
        )
        if not raw:
            return raw
        return re.sub(r'^\d+\s+', '', raw).strip()

    def _last_name(self, name):
        # The last whitespace-delimited token of the display name (TM uses the
        # same simple definition). "Gemma Font" -> "Font".
        if not name:
            return None
        tokens = name.split()
        return tokens[-1] if tokens else None

    def _current_club(self, response):
        """The player's current club as {'href': <club href>} (or None).

        The current club is the first `verein_{id}` link inside the player-info
        header table (class="tabelle_spieler"), the row directly under the h1.
        We scope to that table so we never pick up unrelated verein links (e.g.
        former clubs, sidebar/career links) elsewhere on the page, and we exclude
        national-team (`nationalmannschaft_`) links by construction.
        """
        href = response.css(
            'table.tabelle_spieler a[href*="verein_"]::attr(href)'
        ).get()
        return {'href': href} if href else None

    def _national_career(self, response):
        """Parse the "National team career" table into a list of entries.

        Structure (verified across all 5 player samples, 2026-06-25):
          header row: SN | National team | Matches | Goals
          data rows : season | <a nationalmannschaft_{id}>Team Name</a> | M | G

        The team name is rendered in German even on /en/ pages (e.g.
        "Spanien U23"). Missing numerics default to 0. Note a separate
        player-info table can also carry a nationalmannschaft link ("Current
        national player: ..."); we only read the career table, identified by its
        header row, so that link is ignored.
        """
        career = []
        for table in response.xpath('//table'):
            header = [
                c.xpath('normalize-space(string())').get()
                for c in table.xpath('.//tr[1]/td | .//tr[1]/th')
            ]
            if header[:4] != ['SN', 'National team', 'Matches', 'Goals']:
                continue
            for row in table.xpath('.//tr[position() > 1]'):
                href = row.css(
                    'a[href*="nationalmannschaft_"]::attr(href)'
                ).get()
                if not href:
                    continue
                cells = row.xpath('./td')
                team_name = self.safe_strip(
                    row.css('a[href*="nationalmannschaft_"]')
                    .xpath('normalize-space(string())').get()
                )
                season = (
                    self.safe_strip(cells[0].xpath('normalize-space(string())').get())
                    if cells else None
                )
                career.append({
                    'national_team_id': extract_entity_id(href),
                    'href': href,
                    'name': team_name,
                    'season': season if season and season != '-' else None,
                    'matches': _int(
                        cells[2].xpath('normalize-space(string())').get()
                    ) if len(cells) > 2 else 0,
                    'goals': _int(
                        cells[3].xpath('normalize-space(string())').get()
                    ) if len(cells) > 3 else 0,
                })
        return career
