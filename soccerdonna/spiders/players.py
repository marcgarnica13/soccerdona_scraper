import re

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
        yield {
            'type': 'player',
            'parent': parent,
            'source': 'soccerdonna',
            'href': response.url.replace('https://www.soccerdonna.de', ''),
            'player_id': extract_entity_id(response.url),
            'name': self._name(response),
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
