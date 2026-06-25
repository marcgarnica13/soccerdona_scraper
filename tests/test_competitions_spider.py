from tests.conftest import load_sample
from soccerdonna.spiders.competitions import CompetitionsSpider

PARENT = {'type': 'confederation', 'href': '/en/2010/startseite/wettbewerbeDE.html'}


def _parse_index():
    spider = CompetitionsSpider()
    resp = load_sample('index', 'wettbewerbeDE.html')
    return [i for i in spider.parse(resp, parent=PARENT) if isinstance(i, dict)]


def test_competitions_includes_spanish_first_tier():
    items = _parse_index()
    esp1 = next(i for i in items if i['competition_code'] == 'ESP1')
    assert esp1['type'] == 'competition'
    assert esp1['country_name'] == 'Spanien'   # German on the source site
    assert esp1['country_id'] == '157'
    assert esp1['href'].endswith('wettbewerb_ESP1.html')
    assert esp1['href'].startswith('/en/')     # normalized from /de/
    assert esp1['parent'] == PARENT
    assert esp1['source'] == 'soccerdonna'


def test_international_competition_not_attributed_to_stale_country():
    # The UEFA Women's Champions League (CL) lives in the international section,
    # which has no country flag. It must NOT inherit the previous country
    # (observed bug: it was tagged as Wales). Country should be None and the
    # tier heuristic must not produce a bare numeric competition_type.
    items = _parse_index()
    cl = next(i for i in items if i['competition_code'] == 'CL')
    assert cl['country_name'] in (None, 'international')
    assert cl['country_id'] in (None, 'international')
    assert cl['competition_type'] is None or not cl['competition_type'].isdigit()


def test_every_competition_has_required_fields():
    # Structural invariant across the whole index page.
    items = _parse_index()
    assert len(items) > 10
    for i in items:
        assert i['type'] == 'competition'
        assert i['competition_code']
        assert i['href']
        # country_name may legitimately be None for international competitions.
        assert 'country_name' in i
