from scrapy import Request

from soccerdonna.spiders.clubs import ClubsSpider


class ClubsByUrlSpider(ClubsSpider):
    """Scrape clubs directly from a parents file of club URLs.

    Parents must be club items whose href points at the squad (kader) page, or
    a club overview href (routed to kader here). Each entry is fetched and
    parsed by ``parse_details``.
    """
    name = 'clubs_by_url'

    def start_requests(self):
        for item in self.entrypoints:
            href = item['href']
            # ensure we land on the kader page
            kader = href.replace('/startseite/', '/kader/')
            yield Request(self.base_url + kader, callback=self.parse_details,
                          cb_kwargs={'parent': item})
