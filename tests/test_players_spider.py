from tests.conftest import load_sample, iter_samples
from soccerdonna.spiders.players import PlayersSpider

PARENT = {'type': 'club', 'href': '/en/fc-barcelona/startseite/verein_1132.html'}


def test_start_requests_expands_inline_club_players():
    # A club item carries an inline squad; the players spider must fan out one
    # profile request per inline player (TM-style clubs | players pipe).
    spider = PlayersSpider()
    club = {
        'type': 'club',
        'href': '/en/fc-barcelona/startseite/verein_1132.html',
        'players': [
            {'href': '/en/gemma-font/profil/spieler_38461.html'},
            {'href': '/en/alexia-putellas/profil/spieler_4824.html'},
        ],
    }
    spider.entrypoints = [club]
    reqs = list(spider.start_requests())
    assert len(reqs) == 2
    urls = [r.url for r in reqs]
    assert any('spieler_38461' in u for u in urls)
    assert any('spieler_4824' in u for u in urls)
    # Each emitted player's parent is the club (matches TM).
    assert all(r.cb_kwargs['parent'] == club for r in reqs)


def test_start_requests_handles_direct_player_item():
    # A bare player entrypoint (players_from_file / flattened list) still yields
    # a single request to its own href.
    spider = PlayersSpider()
    player = {'type': 'player', 'href': '/en/gemma-font/profil/spieler_38461.html'}
    spider.entrypoints = [player]
    reqs = list(spider.start_requests())
    assert len(reqs) == 1
    assert 'spieler_38461' in reqs[0].url


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
    assert player['last_name'] == 'Font'
    assert isinstance(player['current_club'], dict)
    assert 'verein_1132' in player['current_club']['href']


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
        assert 'current_club' in player, filename
        assert 'last_name' in player, filename


def test_gemma_font_national_career():
    # The team name is rendered in German even on the /en/ page (observed live
    # 2026-06-25): "Spanien U23" (Spain U23), 4 caps.
    spider = PlayersSpider()
    resp = load_sample('player', 'spieler_38461.html')
    player = list(spider.parse(resp, parent=PARENT))[0]

    career = player['national_career']
    assert career, 'expected at least one national-team entry'
    spain_u23 = next(e for e in career if 'Spanien U23' in (e['name'] or ''))
    assert spain_u23['national_team_id'] == '8954'
    assert spain_u23['href'].endswith('nationalmannschaft_8954.html')
    assert spain_u23['matches'] == 4
    assert spain_u23['goals'] == 0
