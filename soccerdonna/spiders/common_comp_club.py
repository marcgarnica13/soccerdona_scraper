from soccerdonna.spiders.common import BaseSpider as _BaseSpider, read_lines, default_base_url
import re


class BaseSpider(_BaseSpider):
    """BaseSpider that knows how to seasonize soccerdonna entrypoint URLs.

    `season` is an optional spider argument (`-a season=2024`). When unset, the
    site's default/current season is used (no season segment added).

    VERIFIED season grammar (recon against live samples, 2026-06-25): soccerdonna
    does NOT use a `/saison_id/{year}` path segment. Instead it appends the season
    start year as a filename suffix before `.html`, e.g.
    `wettbewerb_ESP1.html` -> `wettbewerb_ESP1_2025.html` and
    `verein_1132.html` -> `verein_1132_2025.html`. (The live site sometimes also
    carries a second token, e.g. `_2025_26`/`_2025_30`, that is competition-
    specific; for entrypoint seasonization we insert just the start year, which
    the site resolves.) We strip any pre-existing `_{4-digit-year}(_NN)?` suffix
    first so re-runs are idempotent.
    """

    def __init__(self, season=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.season = season

    def seasonize_entrypoin_href(self, item):
        # Strip any existing season suffix first, so re-runs are idempotent.
        base_href = re.sub(r'_(\d{4})(_\d+)?\.html$', '.html', item['href'])

        if self.season:
            # Insert `_{season}` as a filename suffix before the `.html` suffix.
            seasoned = re.sub(r'\.html$', f'_{self.season}.html', base_href)
            return f"{self.base_url}{seasoned}"

        return f"{self.base_url}{base_href}"
