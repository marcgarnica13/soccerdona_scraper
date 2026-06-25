from tests.conftest import load_sample, iter_samples
from soccerdonna.spiders.players import PlayersSpider

PARENT = {'type': 'club', 'href': '/en/fc-barcelona/startseite/verein_1132.html'}


def test_gemma_font_profile_fields():
    spider = PlayersSpider()
    resp = load_sample('player', 'spieler_38461.html')
    player = list(spider.parse(resp, parent=PARENT))[0]

    assert player['type'] == 'player'
    assert player['source'] == 'soccerdonna'
    assert player['href'].endswith('spieler_38461.html')
    assert player['date_of_birth'] == '1999-10-23'   # parsed to ISO
    assert player['position'] == 'Goalkeeper'
    assert player['citizenship'] == 'Spain'
    assert player['foot'] == 'right'
    assert player['height'] == '1,65'
    assert player['current_market_value'] == 50000


def test_every_player_sample_has_core_fields():
    # Structural invariant across all 5 player samples.
    spider = PlayersSpider()
    for filename, resp in iter_samples('player'):
        player = list(spider.parse(resp, parent=PARENT))[0]
        assert player['type'] == 'player', filename
        assert player['player_id'], filename
        assert player['name'], filename
        # DOB may be None for an odd profile, but the key must exist.
        assert 'date_of_birth' in player, filename
        assert 'national_career' in player, filename
