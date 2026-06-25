# tests/test_games_urls_spider.py
from tests.conftest import load_sample, iter_samples
from soccerdonna.spiders.games_urls import GamesUrlsSpider

PARENT = {'type': 'competition', 'competition_code': 'ESP1',
          'href': '/en/primera-division-femenina/startseite/wettbewerb_ESP1.html'}


def _matchday_sample():
    # the anchor matchday-30 sample (filename starts with ESP1_ and ends _30.html)
    for name, resp in iter_samples('matchday'):
        if name.endswith('_30.html'):
            return resp
    raise AssertionError('matchday _30 anchor sample missing')


def test_parse_matchday_yields_eight_games():
    spider = GamesUrlsSpider()
    games = [g for g in spider.parse_matchday(_matchday_sample(), parent=PARENT)
             if isinstance(g, dict)]
    assert len(games) == 8
    for g in games:
        assert g['type'] == 'game'
        assert g['game_id']                      # numeric id string
        assert g['href'].endswith('.html') and 'spielbericht_' in g['href']
        assert g['home_club']['href'] and g['away_club']['href']
        assert g['source'] == 'soccerdonna'
        assert g['parent'] == PARENT


def test_anchor_game_present_in_matchday():
    spider = GamesUrlsSpider()
    games = [g for g in spider.parse_matchday(_matchday_sample(), parent=PARENT)
             if isinstance(g, dict)]
    g153373 = next(g for g in games if g['game_id'] == '153373')
    # away side is Atlético de Madrid (verein_1129)
    clubs = {g153373['home_club']['href'], g153373['away_club']['href']}
    assert any('verein_1129' in c for c in clubs)
    assert g153373.get('result') is None or __import__('re').match(r'^\d+:\d+$', g153373['result'])


def test_every_matchday_sample_parses():
    spider = GamesUrlsSpider()
    for name, resp in iter_samples('matchday'):
        games = [g for g in spider.parse_matchday(resp, parent=PARENT) if isinstance(g, dict)]
        assert len(games) >= 1, name
        for g in games:
            assert g['type'] == 'game' and g['game_id'], name
