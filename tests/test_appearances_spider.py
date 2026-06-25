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
