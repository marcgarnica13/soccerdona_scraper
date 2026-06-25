from tests.conftest import load_sample, iter_samples
from soccerdonna.spiders.game_lineups import GameLineupsSpider

PARENT = {'type': 'game', 'href': '/en/x/index/spielbericht_153373.html'}


def test_parse_lineups_core():
    spider = GameLineupsSpider()
    resp = load_sample('lineup', 'spielbericht_153373.html')
    item = list(spider.parse_lineups(resp, parent=PARENT))[0]
    assert item['type'] == 'game_lineup'
    assert item['game_id'] == '153373'
    assert item['source'] == 'soccerdonna'
    for side in ('home_club', 'away_club'):
        club = item[side]
        assert 'href' in club
        assert isinstance(club['starting_lineup'], list)
        assert isinstance(club['substitutes'], list)
        # a full XI is 11 starters (allow some slack for data gaps)
        assert len(club['starting_lineup']) >= 7
        for p in club['starting_lineup']:
            assert p['href'].endswith('.html') and 'spieler_' in p['href']
            assert p['player_id']


def test_every_lineup_sample_parses():
    spider = GameLineupsSpider()
    for name, resp in iter_samples('lineup'):
        rows = list(spider.parse_lineups(resp, parent=PARENT))
        assert len(rows) == 1, name
        item = rows[0]
        assert item['type'] == 'game_lineup' and item['game_id'], name
        assert 'home_club' in item and 'away_club' in item, name
