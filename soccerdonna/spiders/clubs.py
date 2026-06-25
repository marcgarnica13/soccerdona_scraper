from soccerdonna.spiders.common_comp_club import BaseSpider
from soccerdonna.utils import extract_entity_id, parse_market_value


class ClubsSpider(BaseSpider):
    name = 'clubs'

    def scrape_parents(self):
        # Synthetic fallback so the spider can run (and be instantiated in tests)
        # without an explicit parents pipe. Points at a known competition page,
        # the same shape the `competitions` spider emits.
        return [{
            'type': 'competition',
            'competition_code': 'ESP1',
            'href': '/en/primera-division-femenina/startseite/wettbewerb_ESP1.html',
        }]

    def parse(self, response, parent):
        """Competition page -> follow each club's squad (kader) page."""
        # Scope club links to the standings table only. A page-wide
        # a[href*="verein_"] also grabs transfers/rumours sidebars (free-agent
        # `vereinslos`, foreign-league teams, reserve sides), polluting the
        # crawl. The first table that contains verein_ links is the standings
        # table, holding exactly the league members.
        # NOTE: cup / international competition pages may not have a standings
        # table in this exact form; those are tracked separately and may need
        # revisiting here.
        members_tables = response.xpath('//table[.//a[contains(@href,"verein_")]]')
        scope = members_tables[0] if members_tables else None
        club_hrefs = (
            set(scope.css('a[href*="verein_"]::attr(href)').getall()) if scope else set()
        )
        for href in club_hrefs:
            if 'verein_' not in href:
                continue
            # Route to the squad (kader) page rather than the overview.
            kader_href = href.replace('/startseite/', '/kader/')
            yield response.follow(
                self.base_url + kader_href if kader_href.startswith('/') else kader_href,
                self.parse_details,
                cb_kwargs={'parent': parent},
            )

    def parse_details(self, response, parent):
        """Squad page -> one club item with inline players[].

        The squad table is `table#spieler`. Each player is an outer row
        (class hell/dunkel) whose direct `td` columns are, in order:
          0: shirt number
          1: nested table with the player photo, name+spieler link, and position
          2: foot
          3: age
          4: height
          5: nationality flag (img title)
          6: at club since (year)
          7: contract until (year)
        There is no market value column on the squad page, so `market_value`
        is always None here (kept for schema parity with the player schema).
        """
        players = []
        for row in response.css('table#spieler tr'):
            # Only outer player rows directly contain the spieler link plus the
            # full set of columns; nested name/position tables are skipped.
            cells = row.xpath('./td')
            if len(cells) < 6:
                continue
            player_link = row.css('a[href*="spieler_"]::attr(href)').get()
            if not player_link:
                continue

            name_cell = cells[1]
            # The position sits in the last inner <tr> of the nested name table.
            inner_rows = name_cell.css('table tr')
            position = None
            if inner_rows:
                position = self.safe_strip(
                    inner_rows[-1].xpath('normalize-space(string())').get()
                )

            players.append({
                'player_id': extract_entity_id(player_link),
                'href': player_link,
                'name': self.safe_strip(row.css('a[href*="spieler_"]::text').get()),
                'number': self.safe_strip(cells[0].xpath('normalize-space(string())').get()),
                'position': position,
                'nationality': cells[5].css('img[src*="/flaggen/"]::attr(title)').get(),
                'market_value': parse_market_value(
                    self.safe_strip(row.css('td.rechts::text').get())
                ),
            })

        yield {
            'type': 'club',
            'parent': parent,
            'source': 'soccerdonna',
            'href': self._club_href(response.url),
            # Club name only: the header h1 nests country + federation links;
            # the club name is the first <a id="vereinsinfo"> within it.
            'name': self.safe_strip(response.css('h1 a#vereinsinfo::text').get()),
            'players': players,
        }

    def _club_href(self, url):
        # Normalize the squad URL back to a /startseite/ club href for parent
        # linkage. Strip the configured base_url (not a hardcoded host) so a
        # custom `-a base_url=` run doesn't leak the full URL into emitted hrefs.
        return url.replace(self.base_url, '').replace('/kader/', '/startseite/')
