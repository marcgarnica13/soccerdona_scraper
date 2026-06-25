import re

from soccerdonna.spiders.games_urls import GamesUrlsSpider, _to_en
from soccerdonna.utils import extract_entity_id, parse_date_de

# Plain-text minute, e.g. "26.  min." (Goals/Subs) or "48.  min.," (Cards).
MINUTE_RE = re.compile(r'(\d{1,3})\s*\.\s*min', re.IGNORECASE)
# ISO date embedded in the header date link, e.g. datum_2026-05-31.html
ISO_DATE_RE = re.compile(r'(\d{4}-\d{2}-\d{2})')
DE_DATE_RE = re.compile(r'(\d{2}\.\d{2}\.\d{4})')


class GamesSpider(GamesUrlsSpider):
    """Competition -> matchday overviews -> follow each game to its full report.

    Reuses ``games_urls`` matchday discovery (the real ``<p class="drunter">``
    fixture links + the regex matchday-nav walk) but, instead of yielding
    lightweight metadata, follows each match-report link to ``parse_game`` which
    parses the full report into one ``game`` item carrying an ``events`` list.
    """

    name = 'games'

    def parse_matchday(self, response, parent):
        """Override: follow each discovered game to the full report.

        Discovery is delegated to the base spider's ``_game_links`` so this
        walks the exact same fixtures ``games_urls`` does; the matchday-nav graph
        walk is likewise reused via ``_follow_matchdays``.
        """
        m = re.search(r'spieltagsuebersicht/wettbewerb_[A-Za-z0-9]+_\d+_(\d+)\.html',
                      response.url)
        if m:
            self.seen_matchdays.add(m.group(1))

        for _fixture, game_href in self._game_links(response):
            yield response.follow(game_href, self.parse_game,
                                  cb_kwargs={'parent': parent})

        yield from self._follow_matchdays(response, parent)

    def parse_game(self, response, parent):
        """Full match report -> one game item with events."""
        home, away = self._home_away(response)

        # Result: the big score in the report header banner.
        result_raw = self.safe_strip(
            response.css('div#centerbig p.ac::text').re_first(r'^\s*\d+:\d+\s*$'))
        result = result_raw if result_raw and re.match(r'^\d+:\d+$', result_raw) else None

        # Date: the header carries a "datum_YYYY-MM-DD.html" link (ISO) and a
        # "DD.MM.YYYY" label. Prefer ISO; fall back to the German label.
        date = self._date(response)

        events = []
        events += self._parse_event_section(response, 'Goals', 'goal', home, away)
        events += self._parse_event_section(response, 'Substitutions', 'substitution', home, away)
        events += self._parse_event_section(response, 'Cards', 'card', home, away)

        yield {
            'type': 'game',
            'parent': parent,
            'source': 'soccerdonna',
            'game_id': extract_entity_id(response.url),
            'href': response.url.replace(self.base_url, ''),
            'date': date,
            'home_club': {'href': home},
            'away_club': {'href': away},
            'result': result,
            'events': events,
        }

    def _home_away(self, response):
        """Reliably resolve home/away club hrefs from the report header.

        The header banner marks the teams with ``<img name="wappen_h">`` (home)
        and ``<img name="wappen_g">`` (guest/away); each is wrapped in an
        ``<a href*="verein_">``. This is unambiguous even though ~48 verein links
        exist elsewhere on the page (line-ups, minifotos, stadium, etc.).
        """
        home = self._club_for_wappen(response, 'wappen_h')
        away = self._club_for_wappen(response, 'wappen_g')
        return home, away

    def _club_for_wappen(self, response, name):
        href = response.xpath(
            f'//a[.//img[@name="{name}"]]/@href').get()
        return _to_en(href) if href else None

    def _date(self, response):
        iso = response.css('a[href*="datum_"]::attr(href)').re_first(
            r'datum_(\d{4}-\d{2}-\d{2})\.html')
        if iso:
            return iso
        de = DE_DATE_RE.search(response.text)
        return parse_date_de(de.group(1)) if de else None

    def _parse_event_section(self, response, heading, event_type, home, away):
        """Extract events under the ``<h2>`` whose text == ``heading``.

        The section is laid out as two side-by-side tables: a left
        ``<div class="fl">`` (home club) and a right ``<div class="fr">`` (away
        club). Event rows carry the player link + plain-text minute; the club is
        inferred from which side the row sits on.
        """
        events = []
        for side, club in (('fl', home), ('fr', away)):
            table = response.xpath(
                f'//h2[contains(normalize-space(.), "{heading}")]'
                f'/following-sibling::div[contains(@class, "{side}")][1]'
                f'//table')
            for row in table.css('tr'):
                player_href = row.css('a[href*="spieler_"]::attr(href)').get()
                if not player_href:
                    continue  # skip header rows / "none" placeholder rows
                text = self.safe_strip(' '.join(row.css('::text').getall()))
                mm = MINUTE_RE.search(text or '')
                minute = int(mm.group(1)) if mm else None
                events.append({
                    'type': event_type,
                    'minute': minute,
                    'player': {'href': _to_en(player_href)},
                    'club': {'href': club} if club else None,
                })
        return events
