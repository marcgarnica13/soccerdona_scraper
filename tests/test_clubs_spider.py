# tests/test_clubs_spider.py
from tests.conftest import load_sample, iter_samples
from soccerdonna.spiders.clubs import ClubsSpider


def test_competition_page_yields_club_requests():
    spider = ClubsSpider()
    parent = {'type': 'competition', 'competition_code': 'ESP1',
              'href': '/en/primera-division-femenina/startseite/wettbewerb_ESP1.html'}
    resp = load_sample('competition', 'ESP1.html')
    follows = list(spider.parse(resp, parent=parent))
    hrefs = [r.url for r in follows]
    assert any('verein_1132' in h for h in hrefs)  # FC Barcelona
    # Scoped to the standings table: ~16 league members, not the page-wide
    # set (which leaks free-agent/foreign/reserve teams).
    assert 12 <= len(follows) <= 20


def test_barcelona_squad_has_known_players():
    spider = ClubsSpider()
    parent = {'type': 'competition', 'competition_code': 'ESP1'}
    resp = load_sample('club', 'verein_1132.html')
    club = list(spider.parse_details(resp, parent=parent))[0]
    assert club['type'] == 'club'
    assert 'verein_1132' in club['href']
    assert club['source'] == 'soccerdonna'
    assert club['name'] == 'FC Barcelona'
    assert isinstance(club['players'], list) and len(club['players']) > 5
    ids = {p['player_id'] for p in club['players']}
    assert '4824' in ids   # Alexia Putellas
    assert '22010' in ids  # Ewa Pajor
    putellas = next(p for p in club['players'] if p['player_id'] == '4824')
    assert putellas['href'].endswith('spieler_4824.html')
    assert putellas['name']


def test_every_club_sample_parses_with_players():
    # Structural invariant: each of the 5 squad samples yields one club with players.
    spider = ClubsSpider()
    parent = {'type': 'competition', 'competition_code': 'ESP1'}
    for filename, resp in iter_samples('club'):
        club = list(spider.parse_details(resp, parent=parent))[0]
        assert club['type'] == 'club', filename
        # Club name is clean: just the club, no newline, no country/federation marker.
        name = club['name']
        assert name and '\n' not in name, filename
        assert 'Federaci' not in name, filename
        assert 'Verband' not in name, filename
        assert 'Federation' not in name, filename
        assert isinstance(club['players'], list) and len(club['players']) > 0, filename
        for p in club['players']:
            assert p['player_id'], filename
            assert p['href'].endswith('.html'), filename
