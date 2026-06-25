import re
from inflection import parameterize, underscore
from soccerdonna.spiders.common_comp_club import BaseSpider
from soccerdonna.utils import extract_competition_code


class CompetitionsSpider(BaseSpider):
    name = 'competitions'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.seen = set()

    def scrape_parents(self):
        # Synthetic fallback so the spider can run (and be instantiated in tests)
        # without an explicit parents pipe. Points at the competitions index, the
        # same entrypoint the `confederations` spider emits.
        return [{
            'type': 'confederation',
            'href': '/en/2010/startseite/wettbewerbeDE.html',
            'name': 'soccerdonna',
            'source': 'soccerdonna',
        }]

    def parse(self, response, parent):
        current_country_id = None
        current_country_name = None

        # Iterate index rows in document order so each country flag sets the
        # context for the competition rows beneath it. Flag images are .gif at
        # /flaggen/{id}.gif (NOT .png, NOT flaggenrahmen). Competition hrefs are
        # normalized /de/ -> /en/ so downstream pages return English labels.
        for row in response.css('tr'):
            flag_src = row.css('img[src*="/flaggen/"]::attr(src)').get()
            flag_title = row.css('img[src*="/flaggen/"]::attr(title)').get()
            if flag_src and flag_title:
                m = re.search(r'/flaggen/([0-9]+)\.(?:gif|png)', flag_src, re.IGNORECASE)
                current_country_id = m.group(1) if m else None
                current_country_name = flag_title  # German on source
            elif row.css('td.al.fb'):
                # A section header cell (td.al.fb) with no flag image marks the
                # start of a flag-less block: the international competitions
                # ("Internationaler Vereinspokal") and the national-team sections
                # that follow it. Reset the country context so those competitions
                # are not mis-attributed to the previous country (e.g. Wales).
                current_country_id = None
                current_country_name = None

            comp_href = row.css('a[href*="wettbewerb_"]::attr(href)').get()
            if not comp_href:
                continue
            comp_href = re.sub(r'^/de/', '/en/', comp_href)  # force English pages
            code = extract_competition_code(comp_href)
            if not code:
                continue
            key = f"{current_country_id}_{code}"
            if key in self.seen:
                continue
            self.seen.add(key)

            # Tier text lives in a sibling cell on the same row (e.g. "1. Liga").
            # It immediately follows the competition link cell. Fall back to None.
            tier_text = None
            cells = [self.safe_strip(t) for t in row.css('td.ac::text').getall()]
            cells = [c for c in cells if c]
            if cells:
                tier_text = cells[0]
            # International rows have no tier label cell: the first td.ac is a
            # numeric stat (Teams count), which would otherwise yield a junk
            # numeric competition_type (e.g. "18"). Only accept a real label.
            if tier_text and re.fullmatch(r'[0-9.\s]+', tier_text):
                tier_text = None
            comp_type = underscore(parameterize(tier_text)) if tier_text else None

            yield {
                'type': 'competition',
                'parent': parent,
                'source': 'soccerdonna',
                'country_id': current_country_id,
                'country_name': current_country_name,
                'competition_code': code,
                'competition_type': comp_type,
                'href': comp_href,
            }
