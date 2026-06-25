from soccerdonna.spiders.common_comp_club import BaseSpider

# The competitions index. The leading path segment ("2010") is the site's
# index identifier, NOT a season — verify against the live site if coverage
# looks wrong. See spec section 7 (unknowns).
INDEX_HREF = '/en/2010/startseite/wettbewerbeDE.html'


class ConfederationsSpider(BaseSpider):
    name = 'confederations'

    def scrape_parents(self):
        return [{'type': 'root', 'href': ''}]

    def parse(self, response, **kwargs):
        yield {
            'type': 'confederation',
            'href': INDEX_HREF,
            'name': 'soccerdonna',
            'source': 'soccerdonna',
        }
