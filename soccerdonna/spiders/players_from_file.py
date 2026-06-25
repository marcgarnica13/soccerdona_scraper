from scrapy import Request

from soccerdonna.spiders.players import PlayersSpider


class PlayersFromFileSpider(PlayersSpider):
    """Scrape players directly from a parents file of player URLs."""
    name = 'players_from_file'

    def start_requests(self):
        for item in self.entrypoints:
            yield Request(self.base_url + item['href'], callback=self.parse,
                          cb_kwargs={'parent': item})
