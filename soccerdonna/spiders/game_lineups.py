import re

from scrapy import Request

from soccerdonna.spiders.common import BaseSpider
from soccerdonna.utils import extract_entity_id


def _to_en(href):
    """Normalize a /de/ href to /en/ so pages load in English."""
    return re.sub(r'^/de/', '/en/', href) if href else href


class GameLineupsSpider(BaseSpider):
    """Game -> its separate aufstellung (lineup) page -> one game_lineup item.

    The aufstellung page lays out three ``<h2 class="tabellen_ueberschrift al">``
    sections: "Starting team", "Substitutes" and "Coaches". The first two each
    contain a left ``<div class="fl">`` (home club) and a right
    ``<div class="fr">`` (away club) block, each holding one table of players
    (``spieler_{id}`` links). Home/away are pinned by the header banner's
    ``<img name="wappen_h">`` (home) / ``wappen_g`` (away) club crests, matching
    the match-report convention. The Coaches section uses ``trainer_`` links, so
    it never collides with the player selectors.

    No per-team formation string is shown on this page, so ``formation`` is None.
    """

    name = 'game_lineups'

    def start_requests(self):
        for item in self.entrypoints:
            href = item['href'].replace('/index/', '/aufstellung/')
            if '/aufstellung/' not in href:
                # Route any other report sub-page to the aufstellung page.
                href = re.sub(r'/[a-z]+/spielbericht_',
                              '/aufstellung/spielbericht_', href)
            yield Request(self.base_url + href, callback=self.parse_lineups,
                          cb_kwargs={'parent': item})

    def scrape_parents(self):
        # Allow direct instantiation (tests / `scrapy check`) without a parents
        # pipe. The real entrypoint is a game item.
        try:
            return super().scrape_parents()
        except Exception:
            return [{
                'type': 'game',
                'href': '/en/x/index/spielbericht_153373.html',
            }]

    def parse_lineups(self, response, parent):
        home_href = self._club_for_wappen(response, 'wappen_h')
        away_href = self._club_for_wappen(response, 'wappen_g')

        home = {
            'href': home_href,
            'formation': None,
            'starting_lineup': self._players(response, 'Starting team', 'fl'),
            'substitutes': self._players(response, 'Substitutes', 'fl'),
        }
        away = {
            'href': away_href,
            'formation': None,
            'starting_lineup': self._players(response, 'Starting team', 'fr'),
            'substitutes': self._players(response, 'Substitutes', 'fr'),
        }

        yield {
            'type': 'game_lineup',
            'parent': parent,
            'source': 'soccerdonna',
            'game_id': extract_entity_id(response.url),
            'href': response.url.replace(self.base_url, ''),
            'home_club': home,
            'away_club': away,
        }

    def _club_for_wappen(self, response, name):
        href = response.xpath(f'//a[.//img[@name="{name}"]]/@href').get()
        return _to_en(href) if href else None

    def _players(self, response, heading, side):
        """Player rows under the ``<h2>heading</h2>`` section's ``div.{side}``.

        ``side`` is 'fl' (home/left) or 'fr' (away/right). Each player row is a
        ``<tr>`` with the shirt number in the first ``td.ac`` and the player in a
        ``spieler_`` anchor; non-player rows (the average-age footer, header
        rows) carry no such anchor and are skipped.
        """
        players = []
        rows = response.xpath(
            f'//h2[contains(normalize-space(.), "{heading}")]'
            f'/following-sibling::div[contains(concat(" ", normalize-space(@class), " "),'
            f' " {side} ")][1]//table//tr')
        for row in rows:
            href = row.css('a[href*="spieler_"]::attr(href)').get()
            if not href:
                continue
            players.append({
                'player_id': extract_entity_id(href),
                'href': _to_en(href),
                'name': self.safe_strip(
                    row.css('a[href*="spieler_"]::text').get()),
                'number': self.safe_strip(row.css('td.ac::text').get()),
            })
        return players
