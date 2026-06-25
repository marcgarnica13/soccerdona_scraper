# tests/test_games_spider.py
import re
from tests.conftest import load_sample, iter_samples
from soccerdonna.spiders.games import GamesSpider

PARENT = {'type': 'competition', 'competition_code': 'ESP1'}


def test_parse_game_core_fields():
    spider = GamesSpider()
    resp = load_sample('game', 'spielbericht_153373.html')
    game = list(spider.parse_game(resp, parent=PARENT))[0]
    assert game['type'] == 'game'
    assert game['game_id'] == '153373'
    assert game['source'] == 'soccerdonna'
    assert game['home_club']['href'] and game['away_club']['href']
    assert re.match(r'^\d+:\d+$', game['result'])
    assert isinstance(game['events'], list)
    # the report has Goals/Substitutions/Cards -> at least one event
    assert len(game['events']) >= 1
    # both teams' formations are captured from the Formation section
    assert 'formation' in game['home_club'] and 'formation' in game['away_club']
    assert isinstance(game['home_club']['formation'], str) and game['home_club']['formation']
    assert isinstance(game['away_club']['formation'], str) and game['away_club']['formation']


def test_substitution_captures_both_players():
    spider = GamesSpider()
    resp = load_sample('game', 'spielbericht_153373.html')
    game = list(spider.parse_game(resp, parent=PARENT))[0]
    subs = [e for e in game['events'] if e['type'] == 'substitution']
    assert subs  # the anchor has 10 substitutions
    assert any(
        e.get('player_in') and e['player_in'].get('href')
        and e.get('player_out') and e['player_out'].get('href')
        for e in subs
    )


def test_game_events_well_formed():
    spider = GamesSpider()
    resp = load_sample('game', 'spielbericht_153373.html')
    game = list(spider.parse_game(resp, parent=PARENT))[0]
    for e in game['events']:
        assert e['type'] in ('goal', 'substitution', 'card')
        assert 'minute' in e          # may be None, key must exist
        assert 'club' in e            # {'href': ...} or None
    types = {e['type'] for e in game['events']}
    assert 'goal' in types or 'card' in types or 'substitution' in types


def test_every_game_sample_parses():
    spider = GamesSpider()
    for name, resp in iter_samples('game'):
        rows = list(spider.parse_game(resp, parent=PARENT))
        assert len(rows) == 1, name
        g = rows[0]
        assert g['type'] == 'game' and g['game_id'], name
        assert isinstance(g['events'], list), name
