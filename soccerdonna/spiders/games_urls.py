import re

from soccerdonna.spiders.common_comp_club import BaseSpider
from soccerdonna.utils import extract_entity_id, parse_date_de


def _to_en(href):
    """Normalize a /de/ href to /en/ so the report loads in English."""
    return re.sub(r'^/de/', '/en/', href) if href else href


# Matchday-overview URL form, e.g.
# /en/<slug>/spieltagsuebersicht/wettbewerb_ESP1_2025_30.html
MATCHDAY_HREF_RE = re.compile(
    r'/[a-z]{2}/[^"\']*spieltagsuebersicht/wettbewerb_[A-Za-z0-9]+_\d+_\d+\.html')
MATCHDAY_NUM_RE = re.compile(
    r'spieltagsuebersicht/wettbewerb_[A-Za-z0-9]+_\d+_(\d+)\.html')


class GamesUrlsSpider(BaseSpider):
    """Competition -> matchday-overview pages -> one lightweight game item per fixture.

    The fast path: discover every game's URL plus lightweight metadata (date,
    teams, result) without opening each match report. ``parse`` finds the
    current matchday overview linked from the competition startseite and walks
    the matchday navigation graph; ``parse_matchday`` yields one game item per
    fixture and follows not-yet-seen matchday pages.
    """

    name = 'games_urls'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.seen_matchdays = set()

    def scrape_parents(self):
        # Allow direct instantiation (tests / `scrapy check`) without a parents
        # pipe. The real entrypoint is a competition startseite item.
        try:
            return super().scrape_parents()
        except Exception:
            return [{
                'type': 'competition',
                'competition_code': 'ESP1',
                'href': '/en/primera-division-femenina/startseite/wettbewerb_ESP1.html',
            }]

    def parse(self, response, parent):
        """Competition page -> follow the current matchday-overview page."""
        md_href = response.css(
            'a[href*="spieltagsuebersicht/wettbewerb_"]::attr(href)').get()
        if not md_href:
            return
        md_href = _to_en(md_href)
        yield response.follow(md_href, self.parse_matchday,
                              cb_kwargs={'parent': parent})

    def _matchday_links(self, response):
        """All matchday-overview hrefs reachable from this page.

        On the matchday-overview page the prev/next navigation is rendered as
        JS button ``onclick="location.href='...'"`` rather than as ``<a href>``,
        and the matchday ``<select>`` carries only bare option values. So scan
        the raw response text for the matchday-overview URL form (covers both
        anchors and onclick handlers).
        """
        return MATCHDAY_HREF_RE.findall(response.text)

    def parse_matchday(self, response, parent):
        """Matchday-overview page -> one game item per fixture + walk the nav."""
        # Mark this matchday seen (dedupe the nav-graph walk).
        m = MATCHDAY_NUM_RE.search(response.url)
        if m:
            self.seen_matchdays.add(m.group(1))

        # Each fixture is a `table.tabelle_grafik`; the match-report link lives
        # in the sibling `<p class="drunter">` that immediately follows it.
        for p in response.css('p.drunter'):
            game_href = p.css('a[href*="spielbericht_"]::attr(href)').get()
            if not game_href:
                continue
            fixture = p.xpath('preceding-sibling::table[1]')
            game = self.extract_game(fixture, game_href, parent)
            if game:
                yield game

        # Follow other matchday-overview links not yet visited (reaches all).
        for href in self._matchday_links(response):
            href = _to_en(href)
            mm = MATCHDAY_NUM_RE.search(href)
            if mm and mm.group(1) not in self.seen_matchdays:
                self.seen_matchdays.add(mm.group(1))  # pre-mark, avoid dup reqs
                yield response.follow(href, self.parse_matchday,
                                      cb_kwargs={'parent': parent})

    def extract_game(self, fixture, game_href, parent):
        game_href = _to_en(game_href)
        club_hrefs = [_to_en(h)
                      for h in fixture.css('a[href*="verein_"]::attr(href)').getall()]
        # Home is the first club link (left), away the second (right) — confirmed
        # against the matchday sample (the fixture header reads "Home - Away").
        home = club_hrefs[0] if len(club_hrefs) >= 1 else None
        away = club_hrefs[1] if len(club_hrefs) >= 2 else None

        # Result is the centred bold score cell between the two club names.
        result_raw = self.safe_strip(fixture.css('td.ac.fb::text').get())
        result = result_raw if result_raw and re.match(r'^\d+:\d+$', result_raw) else None

        # Date (when shown) lives in a "Kick-off: HH:MM - DD.MM.YYYY" cell.
        ko = fixture.xpath('.//td[contains(text(), "Kick-off")]/text()').get()
        date_raw = None
        if ko:
            dm = re.search(r'(\d{2}\.\d{2}\.\d{4})', ko)
            if dm:
                date_raw = dm.group(1)

        return {
            'type': 'game',
            'parent': parent,
            'source': 'soccerdonna',
            'game_id': extract_entity_id(game_href),
            'href': game_href,
            'date': parse_date_de(date_raw) if date_raw else None,
            'home_club': {'href': home},
            'away_club': {'href': away},
            'result': result,
        }
