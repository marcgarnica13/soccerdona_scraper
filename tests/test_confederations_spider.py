# tests/test_confederations_spider.py
from soccerdonna.spiders.confederations import ConfederationsSpider, INDEX_HREF


def test_scrape_parents_returns_root():
    spider = ConfederationsSpider()
    parents = spider.scrape_parents()
    assert parents == [{'type': 'root', 'href': ''}]


def test_parse_yields_single_synthetic_confederation():
    spider = ConfederationsSpider()
    results = list(spider.parse(response=None))
    assert len(results) == 1
    conf = results[0]
    assert conf['type'] == 'confederation'
    assert conf['href'] == INDEX_HREF
    assert conf['source'] == 'soccerdonna'
    assert conf['name'] == 'soccerdonna'
