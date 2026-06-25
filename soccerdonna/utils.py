from __future__ import annotations

import re
from datetime import datetime


def extract_entity_id(href: str) -> str | None:
    """Extract the numeric id from a soccerdonna href.

    soccerdonna encodes ids as a `_<digits>.html` suffix, e.g.
    `verein_1132.html`, `spieler_38461.html`, `spielbericht_153373.html`.
    Returns the digits as a string, or None if there is no id (e.g. the
    competitions index page).
    """
    if not href:
        return None
    match = re.search(r'_(\d+)\.html', href)
    return match.group(1) if match else None


def extract_competition_code(href: str) -> str | None:
    """Extract the competition code from a soccerdonna competition href.

    e.g. `/en/primera-division-femenina/startseite/wettbewerb_ESP1.html` -> `ESP1`.
    """
    if not href:
        return None
    match = re.search(r'wettbewerb_([A-Za-z0-9]+)\.html', href)
    return match.group(1) if match else None


def parse_market_value(value: str) -> int | None:
    """Parse a soccerdonna market value string like '€50,000' into an int (euros).

    Returns None for blank/placeholder values ('', '-', '?', None).
    """
    if not value:
        return None
    digits = re.sub(r'[^0-9]', '', value)
    return int(digits) if digits else None


def parse_date_de(value: str) -> str | None:
    """Convert a soccerdonna DD.MM.YYYY date into ISO YYYY-MM-DD.

    Returns None for blank input.
    """
    if not value:
        return None
    value = value.strip()
    try:
        return datetime.strptime(value, "%d.%m.%Y").strftime("%Y-%m-%d")
    except ValueError:
        return None
