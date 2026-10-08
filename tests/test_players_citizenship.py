import re

import pytest
from scrapy.http import HtmlResponse

from soccerdonna.spiders.players import PlayersSpider
from soccerdonna.spiders.players_from_file import PlayersFromFileSpider
from tests.conftest import _url_for, load_sample

PARENT = {'type': 'club', 'href': '/en/fc-barcelona/startseite/verein_1132.html'}

SPIDERS = [PlayersSpider, PlayersFromFileSpider]

# The Nationality cell: one <img title="Country"> per citizenship, in page order.
NATIONALITY_CELL = re.compile(
    r'(<td>Nationality:</td>\s*<td>)(.*?)(</td>)', re.DOTALL)


def _parse(spider_cls, response):
    return list(spider_cls().parse(response, parent=PARENT))[0]


def _mutated(filename, transform):
    """Load a player sample and rewrite its Nationality cell content."""
    original = load_sample('player', filename)
    html = original.text
    mutated, count = NATIONALITY_CELL.subn(
        lambda m: m.group(1) + transform(m.group(2)) + m.group(3), html)
    assert count == 1, 'Nationality cell not found in sample'
    return HtmlResponse(url=original.url, body=mutated.encode('utf-8'),
                        encoding='utf-8')


@pytest.mark.parametrize('spider_cls', SPIDERS)
@pytest.mark.parametrize('filename, expected', [
    ('spieler_78529.html', ['Spain', 'Guine']),
    ('spieler_9110.html', ['Poland', 'Germany']),
    ('spieler_50532.html', ['Turkey', 'Germany']),
    ('spieler_38461.html', ['Spain']),
])
def test_citizenship_is_a_list_in_page_order(spider_cls, filename, expected):
    player = _parse(spider_cls, load_sample('player', filename))
    assert player['citizenship'] == expected


@pytest.mark.parametrize('spider_cls', SPIDERS)
def test_country_name_with_a_comma_stays_one_element(spider_cls):
    response = _mutated(
        'spieler_38461.html',
        lambda cell: '<img src="x.gif" title="Korea, South" /> Korea, South')
    assert _parse(spider_cls, response)['citizenship'] == ['Korea, South']


@pytest.mark.parametrize('spider_cls', SPIDERS)
def test_blank_flag_titles_are_dropped(spider_cls):
    response = _mutated(
        'spieler_78529.html',
        lambda cell: re.sub(r'title="Spain"', 'title=" "', cell))
    assert _parse(spider_cls, response)['citizenship'] == ['Guine']


@pytest.mark.parametrize('spider_cls', SPIDERS)
def test_all_blank_flag_titles_give_none(spider_cls):
    response = _mutated(
        'spieler_78529.html',
        lambda cell: re.sub(r'title="[^"]*"', 'title=" "', cell))
    assert _parse(spider_cls, response)['citizenship'] is None


@pytest.mark.parametrize('spider_cls', SPIDERS)
def test_cell_without_flags_gives_none_never_empty_list(spider_cls):
    response = _mutated('spieler_78529.html', lambda cell: ' Spain Guine ')
    assert _parse(spider_cls, response)['citizenship'] is None


@pytest.mark.parametrize('spider_cls', SPIDERS)
def test_missing_nationality_row_gives_none(spider_cls):
    original = load_sample('player', 'spieler_38461.html')
    html, count = re.subn(
        r'<tr>\s*<td>Nationality:</td>.*?</tr>', '', original.text,
        flags=re.DOTALL)
    assert count == 1
    response = HtmlResponse(url=original.url, body=html.encode('utf-8'),
                            encoding='utf-8')
    assert _parse(spider_cls, response)['citizenship'] is None


def test_sample_urls_resolve_for_new_fixtures():
    # Guards the conftest URL reconstruction the fixtures above rely on.
    assert _url_for('player', 'spieler_78529.html').endswith(
        '/profil/spieler_78529.html')
