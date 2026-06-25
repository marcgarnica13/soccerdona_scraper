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
