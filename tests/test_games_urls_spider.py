# tests/test_games_urls_spider.py
import scrapy
from scrapy.http import HtmlResponse

from tests.conftest import load_sample, iter_samples
from soccerdonna.spiders.games_urls import GamesUrlsSpider

PARENT = {'type': 'competition', 'competition_code': 'ESP1',
          'href': '/en/primera-division-femenina/startseite/wettbewerb_ESP1.html'}

BASE = 'https://www.soccerdonna.de'


def _md_url(n):
    return (f'{BASE}/en/primera-division-femenina/spieltagsuebersicht/'
            f'wettbewerb_ESP1_2025_{n}.html')


def resp(html, url):
    """A matchday-overview HtmlResponse with a real matchday-overview URL."""
    return HtmlResponse(url=url, body=html.encode('utf-8'), encoding='utf-8')


# An empty matchday-overview page: no fixture (no ``p.drunter`` with a
# ``spielbericht_`` link), but the site still renders an onclick "next matchday"
# nav button — this is exactly what triggered the unbounded walk.
MATCHDAY_EMPTY_HTML = """
<html><body>
  <div id="nav">
    <button onclick="location.href='/en/primera-division-femenina/spieltagsuebersicht/wettbewerb_ESP1_2025_34.html'">next</button>
  </div>
  <p>no fixtures this matchday</p>
</body></html>
"""


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
    for name, response in iter_samples('matchday'):
        games = [g for g in spider.parse_matchday(response, parent=PARENT) if isinstance(g, dict)]
        assert len(games) >= 1, name
        for g in games:
            assert g['type'] == 'game' and g['game_id'], name


# --- bounded-walk regression tests -----------------------------------------

def test_real_matchday_yields_games_and_follows():
    """A matchday with fixtures yields its games AND keeps walking the nav."""
    spider = GamesUrlsSpider()
    out = list(spider.parse_matchday(_matchday_sample(), parent=PARENT))
    games = [o for o in out if isinstance(o, dict)]
    requests = [o for o in out if isinstance(o, scrapy.Request)]
    assert len(games) == 8
    assert requests, 'real matchday should follow its neighbour pages'


def test_empty_within_tolerance_still_follows():
    """An empty matchday inside the tolerance still expands (crosses a gap)."""
    spider = GamesUrlsSpider()
    out = list(spider.parse_matchday(
        resp(MATCHDAY_EMPTY_HTML, _md_url(33)), parent=PARENT, empty_streak=0))
    assert not any(isinstance(o, dict) for o in out)          # no games
    assert any(isinstance(o, scrapy.Request) for o in out)    # but still follows


def test_empty_at_tolerance_stops():
    """At the empty-streak limit the branch terminates — the core bug fix."""
    spider = GamesUrlsSpider()
    out = list(spider.parse_matchday(
        resp(MATCHDAY_EMPTY_HTML, _md_url(34)), parent=PARENT,
        empty_streak=GamesUrlsSpider.MAX_EMPTY_STREAK - 1))
    assert not any(isinstance(o, dict) for o in out)          # no games
    assert not any(isinstance(o, scrapy.Request) for o in out)  # and no follow


def test_followed_request_carries_incremented_streak():
    """Empty pages increment the per-branch counter; real pages reset it."""
    spider = GamesUrlsSpider()

    empty_reqs = [o for o in spider.parse_matchday(
        resp(MATCHDAY_EMPTY_HTML, _md_url(33)), parent=PARENT, empty_streak=0)
        if isinstance(o, scrapy.Request)]
    assert empty_reqs
    assert all(r.cb_kwargs['empty_streak'] == 1 for r in empty_reqs)

    real_reqs = [o for o in spider.parse_matchday(_matchday_sample(), parent=PARENT)
                 if isinstance(o, scrapy.Request)]
    assert real_reqs
    assert all(r.cb_kwargs['empty_streak'] == 0 for r in real_reqs)
