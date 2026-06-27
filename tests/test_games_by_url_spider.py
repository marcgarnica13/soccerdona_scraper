from tests.conftest import load_sample
from soccerdonna.spiders.games_by_url import GamesByUrlSpider


def test_builds_report_requests_from_parents():
    spider = GamesByUrlSpider()
    spider.entrypoints = [
        {'type': 'game', 'href': '/en/x/index/spielbericht_153373.html'}
    ]
    reqs = list(spider.start_requests())
    assert any('spielbericht_153373' in r.url for r in reqs)
    # callback must be the full-report parser
    assert all(r.callback == spider.parse_game for r in reqs)


def test_passes_competition_as_parent():
    """The entrypoint's competition (item['parent']) must be threaded through as
    the request parent, so parse_game records parent=competition and
    competition_code survives to games.json."""
    spider = GamesByUrlSpider()
    competition = {'type': 'competition', 'competition_code': 'ESP1',
                   'href': '/en/x/startseite/wettbewerb_ESP1.html'}
    spider.entrypoints = [
        {'type': 'game', 'href': '/en/x/index/spielbericht_153373.html',
         'parent': competition}
    ]
    req = list(spider.start_requests())[0]
    assert req.cb_kwargs['parent'] == competition
    assert req.cb_kwargs['parent']['competition_code'] == 'ESP1'


def test_falls_back_to_item_when_no_parent():
    """Entrypoints without a parent key keep the prior behaviour (parent=item),
    without crashing."""
    spider = GamesByUrlSpider()
    item = {'type': 'game', 'href': '/en/x/index/spielbericht_153373.html'}
    spider.entrypoints = [item]
    req = list(spider.start_requests())[0]
    assert req.cb_kwargs['parent'] == item


def test_parse_game_records_competition_code():
    """End-to-end contract parse_games depends on: the emitted game record
    carries parent.competition_code."""
    spider = GamesByUrlSpider()
    competition = {'type': 'competition', 'competition_code': 'ESP1'}
    resp = load_sample('game', 'spielbericht_153373.html')
    record = list(spider.parse_game(resp, parent=competition))[0]
    assert record['parent']['competition_code'] == 'ESP1'
