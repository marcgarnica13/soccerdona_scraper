from scrapy import Request

from soccerdonna.spiders.games import GamesSpider


class GamesByUrlSpider(GamesSpider):
    """Parse specific match reports from a parents file of game items.

    Bypasses matchday discovery: each entrypoint game item's href is routed to
    its ``index/spielbericht_{id}.html`` report and parsed via ``parse_game``
    (inherited from ``GamesSpider``).
    """

    name = 'games_by_url'

    # Keep each entrypoint game's parent (the competition) through loading so it
    # survives to the emitted game record (see start_requests / parse_game).
    keep_parent = True

    def start_requests(self):
        for item in self.entrypoints:
            href = item['href']
            # Route to the index/ report page if a different sub-page (e.g. the
            # aufstellung lineup page) was supplied.
            href = href.replace('/aufstellung/', '/index/')
            # The competition is the entrypoint game's parent (games_to_scrape
            # items come from games_urls, whose parent is the competition). Pass
            # the competition through so parse_game records parent=competition
            # and competition_code survives to games.json (matches GamesSpider).
            parent = item.get('parent') or item
            yield Request(self.base_url + href, callback=self.parse_game,
                          cb_kwargs={'parent': parent})
