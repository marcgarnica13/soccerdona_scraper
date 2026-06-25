from soccerdonna.spiders.clubs_by_url import ClubsByUrlSpider
from soccerdonna.spiders.players_from_file import PlayersFromFileSpider


def test_clubs_by_url_builds_requests_from_parents():
    spider = ClubsByUrlSpider()
    spider.entrypoints = [
        {'type': 'club', 'href': '/en/fc-barcelona/startseite/verein_1132.html'}
    ]
    reqs = spider.start_requests()
    assert any('verein_1132' in r.url for r in reqs)


def test_players_from_file_builds_requests_from_parents():
    spider = PlayersFromFileSpider()
    spider.entrypoints = [
        {'type': 'player', 'href': '/en/gemma-font/profil/spieler_38461.html'}
    ]
    reqs = spider.start_requests()
    assert any('spieler_38461' in r.url for r in reqs)
