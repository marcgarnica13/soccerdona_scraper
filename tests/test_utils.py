# tests/test_utils.py
from soccerdonna.utils import (
    extract_entity_id,
    extract_competition_code,
    parse_market_value,
    parse_date_de,
)


def test_extract_entity_id_from_player_href():
    assert extract_entity_id("/en/gemma-font/profil/spieler_38461.html") == "38461"


def test_extract_entity_id_from_club_href():
    assert extract_entity_id("/en/fc-barcelona/startseite/verein_1132.html") == "1132"


def test_extract_entity_id_returns_none_when_absent():
    assert extract_entity_id("/en/2010/startseite/wettbewerbeDE.html") is None


def test_extract_competition_code():
    href = "/en/primera-division-femenina/startseite/wettbewerb_ESP1.html"
    assert extract_competition_code(href) == "ESP1"


def test_parse_market_value_euros():
    assert parse_market_value("€50,000") == 50000


def test_parse_market_value_handles_blank():
    assert parse_market_value("-") is None
    assert parse_market_value("") is None
    assert parse_market_value(None) is None


def test_parse_date_de():
    # soccerdonna uses DD.MM.YYYY
    assert parse_date_de("23.10.1999") == "1999-10-23"


def test_parse_date_de_handles_blank():
    assert parse_date_de("") is None
    assert parse_date_de(None) is None
