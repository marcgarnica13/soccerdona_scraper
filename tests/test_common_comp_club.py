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


def test_seasonize_is_idempotent():
    # Re-seasonizing an already-seasoned href must not stack suffixes.
    spider = _SeasonSpider(season='2024')
    item = {'type': 'competition',
            'href': '/en/primera-division-femenina/startseite/wettbewerb_ESP1_2025.html'}
    url = spider.seasonize_entrypoin_href(item)
    assert url.endswith('wettbewerb_ESP1_2024.html')
