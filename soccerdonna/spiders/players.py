import re

from soccerdonna.spiders.common_comp_club import BaseSpider
from soccerdonna.utils import extract_entity_id, parse_market_value, parse_date_de


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
            'national_career': [],  # filled in Step 6
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
