import re

from tests.conftest import load_sample, iter_samples
from soccerdonna.spiders.appearances import AppearancesSpider

PARENT = {'type': 'player', 'href': '/en/gemma-font/profil/spieler_38461.html'}


def test_gemma_font_appearances_have_core_fields():
    # Granularity (verified 2026-06-25): the default leistungsdaten page shows
    # PER-MATCH detail tables, so each row is one match the player was part of
    # (including unused-substitute "On the bench" rows, where minutes is None).
    spider = AppearancesSpider()
    resp = load_sample('appearance', 'spieler_38461.html')
    apps = [a for a in spider.parse(resp, parent=PARENT) if isinstance(a, dict)]
    assert len(apps) > 0
    for a in apps:
        assert a['type'] == 'appearance'
        assert a['source'] == 'soccerdonna'
        assert a['parent'] == PARENT
        assert 'minutes_played' in a
        assert 'date' in a


def test_gemma_font_appearance_row_is_well_formed():
    # Spot-check the structural shape of a per-match row: every emitted row has
    # a date and an opponent club ref, and at least one row records minutes.
    spider = AppearancesSpider()
    resp = load_sample('appearance', 'spieler_38461.html')
    apps = [a for a in spider.parse(resp, parent=PARENT) if isinstance(a, dict)]
    for a in apps:
        assert a['date'] is not None
        assert a['opponent'] is not None
        assert a['opponent']['type'] == 'club'
        assert a['opponent']['href'].startswith('/en/')
    assert any(a['minutes_played'] for a in apps)


def test_appearances_capture_draw_results():
    # Regression: the result cell must be matched by STRUCTURE (an N:N
    # scoreline), not by colour class. Wins/losses carry a colour class
    # (td.green / td.red); DRAWS render as a plain `td class="ac s10"` with no
    # colour, so a colour-only selector silently dropped them. The Gemma Font
    # sample has draws (0:0, 1:1), so at least one captured result must be a draw.
    spider = AppearancesSpider()
    resp = load_sample('appearance', 'spieler_38461.html')
    apps = [a for a in spider.parse(resp, parent=PARENT) if isinstance(a, dict)]
    results = [a['result'] for a in apps if a['result']]
    # Every captured result is a digit:digit scoreline.
    assert all(re.match(r'^\d+:\d+$', r) for r in results)
    # At least one DRAW (home == away score) is now captured.
    assert any(r.split(':')[0] == r.split(':')[1] for r in results)


def test_every_appearance_sample_parses():
    # Structural invariant: each appearance sample yields rows with the core
    # keys. A player may have zero per-match rows (e.g. a career-aggregate
    # leistungsdaten view with no detail tables); if rows exist they must be
    # well-formed.
    spider = AppearancesSpider()
    for filename, resp in iter_samples('appearance'):
        apps = [a for a in spider.parse(resp, parent=PARENT) if isinstance(a, dict)]
        for a in apps:
            assert a['type'] == 'appearance', filename
            assert a['source'] == 'soccerdonna', filename
            assert 'minutes_played' in a, filename
            assert 'date' in a, filename
