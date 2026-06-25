# tests/test_common_comp_club.py
#
# Season-building tests for common_comp_club.BaseSpider.
#
# NOTE: The plan (Task 4 Step 3) originally placed these tests against
# `soccerdonna.spiders.competitions.CompetitionsSpider`, which does not exist
# until Task 6. To keep the suite green during the foundation phase, they run
# here against a minimal throwaway subclass of common_comp_club.BaseSpider.
#
# The plan's working hypothesis was a `/saison_id/{year}` path segment. Recon
# against live samples (2026-06-25) proved soccerdonna actually encodes the
# season as a filename suffix (`wettbewerb_ESP1_2025.html`), NOT a path segment.
# The "with season" assertion below is adjusted to that VERIFIED grammar.
#
# Entity-id safety: season years and entity ids are both bare digit runs, so
# seasonize must NOT strip a generic 4-digit suffix or it destroys ids like
# `verein_1132`. The current-season default (season=None) does a plain join;
# the regression tests below lock this in.
from soccerdonna.spiders.common_comp_club import BaseSpider


class _SeasonSpider(BaseSpider):
    name = 'season_test_only'

    def scrape_parents(self):
        return []


def test_seasonize_without_season_is_plain_join():
    spider = _SeasonSpider()
    item = {'type': 'competition',
            'href': '/en/primera-division-femenina/startseite/wettbewerb_ESP1.html'}
    url = spider.seasonize_entrypoin_href(item)
    assert url == ('https://www.soccerdonna.de'
                   '/en/primera-division-femenina/startseite/wettbewerb_ESP1.html')


def test_seasonize_with_season_inserts_segment():
    spider = _SeasonSpider(season='2024')
    item = {'type': 'competition',
            'href': '/en/primera-division-femenina/startseite/wettbewerb_ESP1.html'}
    url = spider.seasonize_entrypoin_href(item)
    # Verified grammar: season is a filename suffix, e.g. wettbewerb_ESP1_2024.html
    assert '_2024' in url
    assert 'wettbewerb_ESP1_2024.html' in url
    assert url.endswith('.html')


def test_seasonize_is_idempotent_for_same_season():
    # Applying the same season twice must not stack suffixes.
    spider = _SeasonSpider(season='2024')
    item = {'type': 'competition',
            'href': '/en/primera-division-femenina/startseite/wettbewerb_ESP1.html'}
    once = spider.seasonize_entrypoin_href(item)
    twice = spider.seasonize_entrypoin_href({'href': once.replace('https://www.soccerdonna.de', '')})
    assert once == twice
    assert once.endswith('wettbewerb_ESP1_2024.html')


# --- Regression: a 4-DIGIT ENTITY ID must never be confused for a season. ---
# `verein_1132` is FC Barcelona's club id; a broad `_\d{4}.html` strip would
# destroy it (verein_1132.html -> verein.html). These guard against that.

CLUB_HREF = '/en/fc-barcelona/kader/verein_1132.html'


def test_four_digit_entity_id_unchanged_without_season():
    spider = _SeasonSpider()  # season=None (current-season default)
    url = spider.seasonize_entrypoin_href({'type': 'club', 'href': CLUB_HREF})
    assert url == f'https://www.soccerdonna.de{CLUB_HREF}'  # ID intact, untouched


def test_four_digit_entity_id_gets_season_suffix_not_replaced():
    spider = _SeasonSpider(season='2024')
    url = spider.seasonize_entrypoin_href({'type': 'club', 'href': CLUB_HREF})
    # The 1132 id is preserved; the season is appended after it.
    assert url.endswith('verein_1132_2024.html')


def test_four_digit_entity_id_seasonize_is_idempotent():
    spider = _SeasonSpider(season='2024')
    item = {'type': 'club', 'href': CLUB_HREF}
    once = spider.seasonize_entrypoin_href(item)
    twice = spider.seasonize_entrypoin_href({'href': once.replace('https://www.soccerdonna.de', '')})
    assert once == twice
    assert once.endswith('verein_1132_2024.html')
