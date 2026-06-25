from soccerdonna.spiders.common import BaseSpider as _BaseSpider, read_lines, default_base_url
import re


class BaseSpider(_BaseSpider):
    r"""BaseSpider that knows how to seasonize soccerdonna entrypoint URLs.

    `season` is an optional spider argument (`-a season=2024`). When unset, the
    site's default/current season is used and the href is passed through
    UNCHANGED.

    VERIFIED season grammar (recon against live samples, 2026-06-25): soccerdonna
    does NOT use a `/saison_id/{year}` path segment. Instead it appends the season
    start year as a filename suffix before `.html`, e.g.
    `wettbewerb_ESP1.html` -> `wettbewerb_ESP1_2025.html`. (The live site
    sometimes also carries a second token, e.g. `_2025_26`/`_2025_30`, that is
    competition-specific.) The seasoned form is VERIFIED for competitions
    (`wettbewerb_ESP1_2025.html`) but NOT yet for clubs/players — Tasks 6/7 must
    re-confirm against live club/player pages. The supported, well-tested default
    is the current season (`season=None`), which does a plain join.

    CRITICAL — entity-id safety: soccerdonna entity ids and season years are both
    bare digit runs in the `_<n>.html` suffix (e.g. `verein_1132.html` has a
    4-digit ID, `wettbewerb_ESP1_2025.html` has a 4-digit season). A broad
    `_\d{4}\.html` strip cannot tell them apart and would destroy 4-digit ids
    (`verein_1132.html` -> `verein.html`). So we NEVER strip a generic 4-digit
    suffix. When season is None we touch nothing; when a season is set we only
    add/keep an exact `_<season>` suffix (idempotent for the same season).
    """

    def __init__(self, season=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.season = season

    def seasonize_entrypoin_href(self, item):
        href = item['href']

        # Default (current season): plain join, no rewriting — guarantees entity
        # ids (e.g. verein_1132) are never touched.
        if not self.season:
            return f"{self.base_url}{href}"

        # Season set: insert `_{season}` before `.html`, but only if that exact
        # season suffix isn't already present (so applying twice is a no-op).
        # We do NOT strip any other digit suffix, to keep entity ids intact.
        if re.search(rf'_{re.escape(str(self.season))}\.html$', href):
            return f"{self.base_url}{href}"

        seasoned = re.sub(r'\.html$', f'_{self.season}.html', href)
        return f"{self.base_url}{seasoned}"
