from scrapy import Request

from soccerdonna.spiders.games import GamesSpider


class GamesByUrlSpider(GamesSpider):
    """Parse specific match reports from a parents file of game items.

    Bypasses matchday discovery: each entrypoint game item's href is routed to
    its ``index/spielbericht_{id}.html`` report and parsed via ``parse_game``
    (inherited from ``GamesSpider``).
    """

    name = 'games_by_url'

    def start_requests(self):
        for item in self.entrypoints:
            href = item['href']
            # Route to the index/ report page if a different sub-page (e.g. the
            # aufstellung lineup page) was supplied.
            href = href.replace('/aufstellung/', '/index/')
            yield Request(self.base_url + href, callback=self.parse_game,
                          cb_kwargs={'parent': item})
