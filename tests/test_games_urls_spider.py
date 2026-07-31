# tests/test_games_urls_spider.py
import pytest
import scrapy
from scrapy.http import HtmlResponse

from tests.conftest import load_sample, iter_samples
from soccerdonna.spiders.games_urls import GamesUrlsSpider, matchday_key, matchday_options

PARENT = {'type': 'competition', 'competition_code': 'ESP1',
          'href': '/en/primera-division-femenina/startseite/wettbewerb_ESP1.html'}

BASE = 'https://www.soccerdonna.de'


def _md_url(n):
    return (f'{BASE}/en/primera-division-femenina/spieltagsuebersicht/'
            f'wettbewerb_ESP1_2025_{n}.html')


def resp(html, url):
    """A matchday-overview HtmlResponse with a real matchday-overview URL."""
    return HtmlResponse(url=url, body=html.encode('utf-8'), encoding='utf-8')


# An empty matchday-overview page: no fixture (no ``p.drunter`` with a
# ``spielbericht_`` link), but the site still renders an onclick "next matchday"
# nav button — this is exactly what triggered the unbounded walk.
MATCHDAY_EMPTY_HTML = """
<html><body>
  <div id="nav">
    <button onclick="location.href='/en/primera-division-femenina/spieltagsuebersicht/wettbewerb_ESP1_2025_34.html'">next</button>
  </div>
  <p>no fixtures this matchday</p>
</body></html>
"""


def _matchday_sample():
    # the anchor matchday-30 sample (filename starts with ESP1_ and ends _30.html)
    for name, resp in iter_samples('matchday'):
        if name.endswith('_30.html'):
            return resp
    raise AssertionError('matchday _30 anchor sample missing')


def test_parse_matchday_yields_eight_games():
    spider = GamesUrlsSpider()
    games = [g for g in spider.parse_matchday(_matchday_sample(), parent=PARENT)
             if isinstance(g, dict)]
    assert len(games) == 8
    for g in games:
        assert g['type'] == 'game'
        assert g['game_id']                      # numeric id string
        assert g['href'].endswith('.html') and 'spielbericht_' in g['href']
        assert g['home_club']['href'] and g['away_club']['href']
        assert g['source'] == 'soccerdonna'
        assert g['parent'] == PARENT


def test_anchor_game_present_in_matchday():
    spider = GamesUrlsSpider()
    games = [g for g in spider.parse_matchday(_matchday_sample(), parent=PARENT)
             if isinstance(g, dict)]
    g153373 = next(g for g in games if g['game_id'] == '153373')
    # away side is Atlético de Madrid (verein_1129)
    clubs = {g153373['home_club']['href'], g153373['away_club']['href']}
    assert any('verein_1129' in c for c in clubs)
    assert g153373.get('result') is None or __import__('re').match(r'^\d+:\d+$', g153373['result'])


def test_every_matchday_sample_parses():
    spider = GamesUrlsSpider()
    for name, response in iter_samples('matchday'):
        games = [g for g in spider.parse_matchday(response, parent=PARENT) if isinstance(g, dict)]
        assert len(games) >= 1, name
        for g in games:
            assert g['type'] == 'game' and g['game_id'], name


# --- bounded-walk regression tests -----------------------------------------

def test_real_matchday_yields_games_and_follows():
    """A matchday with fixtures yields its games AND keeps walking the nav."""
    spider = GamesUrlsSpider()
    out = list(spider.parse_matchday(_matchday_sample(), parent=PARENT))
    games = [o for o in out if isinstance(o, dict)]
    requests = [o for o in out if isinstance(o, scrapy.Request)]
    assert len(games) == 8
    assert requests, 'real matchday should follow its neighbour pages'


def test_empty_within_tolerance_still_follows():
    """An empty matchday inside the tolerance still expands (crosses a gap)."""
    spider = GamesUrlsSpider()
    out = list(spider.parse_matchday(
        resp(MATCHDAY_EMPTY_HTML, _md_url(33)), parent=PARENT, empty_streak=0))
    assert not any(isinstance(o, dict) for o in out)          # no games
    assert any(isinstance(o, scrapy.Request) for o in out)    # but still follows


def test_empty_at_tolerance_stops():
    """At the empty-streak limit the branch terminates — the core bug fix."""
    spider = GamesUrlsSpider()
    out = list(spider.parse_matchday(
        resp(MATCHDAY_EMPTY_HTML, _md_url(34)), parent=PARENT,
        empty_streak=GamesUrlsSpider.MAX_EMPTY_STREAK - 1))
    assert not any(isinstance(o, dict) for o in out)          # no games
    assert not any(isinstance(o, scrapy.Request) for o in out)  # and no follow


def test_followed_request_carries_incremented_streak():
    """On the FALLBACK path, empty pages increment the counter and real pages reset it.

    The streak only governs the no-picker fallback now, so both halves use
    picker-less pages; a page with a ``spieltag`` picker enumerates instead and
    its requests carry no ``empty_streak`` at all (see
    ``test_enumerated_requests_do_not_carry_streak``).
    """
    spider = GamesUrlsSpider()

    empty_reqs = [o for o in spider.parse_matchday(
        resp(MATCHDAY_EMPTY_HTML, _md_url(33)), parent=PARENT, empty_streak=0)
        if isinstance(o, scrapy.Request)]
    assert empty_reqs
    assert all(r.cb_kwargs['empty_streak'] == 1 for r in empty_reqs)

    real_no_picker = _nav_html(_md_url_for('ESP1', 2025, 29, slug='primera-division-femenina'),
                               fixture=True)
    real_reqs = [o for o in spider.parse_matchday(
        resp(real_no_picker, _md_url(30)), parent=PARENT)
        if isinstance(o, scrapy.Request)]
    assert real_reqs
    assert all(r.cb_kwargs['empty_streak'] == 0 for r in real_reqs)


# --- per-competition scope regression tests --------------------------------
#
# The bug these pin: the visited-set used to be keyed on the bare matchday
# NUMBER, spider-wide. One spider instance serves every competition in a run
# (crawl_games_urls issues a single runner.crawl for the whole parents file) and
# Scrapy parses them concurrently, so competition B's matchday 12 was shadowed
# by competition A's matchday 12 and B's walk died after one page. Prod:
# 81 games / 15 comps at N=125, versus 240 games / full season at N=1.

def _md_url_for(code, season, matchday, slug='x'):
    return (f'{BASE}/en/{slug}/spieltagsuebersicht/'
            f'wettbewerb_{code}_{season}_{matchday}.html')


def _nav_html(*hrefs, fixture=True):
    """A matchday page linking ``hrefs`` via onclick nav, with/without a fixture.

    The fixture shape mirrors the real site: the match-report link lives in a
    ``p.drunter`` immediately following the fixture ``table.tabelle_grafik``.
    """
    buttons = ''.join(
        f'<button onclick="location.href=\'{h}\'">go</button>' for h in hrefs)
    fixture_html = ''
    if fixture:
        fixture_html = (
            '<table class="tabelle_grafik">'
            '<tr><td><a href="/en/a/startseite/verein_1.html">H</a></td>'
            '<td class="ac fb">1:0</td>'
            '<td><a href="/en/b/startseite/verein_2.html">A</a></td></tr>'
            '<tr><td>Kick-off: 18:00 - 01.03.2026</td></tr>'
            '</table>'
            '<p class="drunter">'
            '<a href="/en/x/index/spielbericht_999.html">report</a></p>')
    return f'<html><body><div id="nav">{buttons}</div>{fixture_html}</body></html>'


def test_same_matchday_number_across_competitions_not_shadowed():
    """Two competitions sharing a matchday NUMBER must both keep walking.

    Minimal regression for the shared-visited-set bug: under the old bare-number
    key, ESP1 matchday 12 claimed "12" globally and NWSL's own matchday 12 then
    found every neighbour already seen, emitting zero follows.
    """
    spider = GamesUrlsSpider()

    esp_out = list(spider.parse_matchday(
        resp(_nav_html(_md_url_for('ESP1', 2025, 11),
                       _md_url_for('ESP1', 2025, 13)),
             _md_url_for('ESP1', 2025, 12)),
        parent={'competition_code': 'ESP1'}))
    nwsl_out = list(spider.parse_matchday(
        resp(_nav_html(_md_url_for('NWSL', 2026, 11),
                       _md_url_for('NWSL', 2026, 13)),
             _md_url_for('NWSL', 2026, 12)),
        parent={'competition_code': 'NWSL'}))

    assert [o for o in esp_out if isinstance(o, scrapy.Request)]
    assert [o for o in nwsl_out if isinstance(o, scrapy.Request)], (
        'NWSL matchday 12 was shadowed by ESP1 matchday 12')


def _drive(spider, seeds, page_for):
    """Breadth-first drive the spider to fixpoint over a fake site.

    ``seeds`` are (url, parent) pairs; ``page_for(url)`` returns the page HTML.
    Returns the list of URLs requested (in order), i.e. the request count.
    """
    queue = [(url, parent, 0) for url, parent in seeds]
    visited = []
    while queue:
        url, parent, streak = queue.pop(0)
        visited.append(url)
        for out in spider.parse_matchday(
                resp(page_for(url), url), parent=parent, empty_streak=streak):
            if isinstance(out, scrapy.Request):
                queue.append((out.url, out.cb_kwargs['parent'],
                              out.cb_kwargs.get('empty_streak', 0)))
    return visited


def _fake_site(matchdays):
    """Page factory: matchdays 1..M have a fixture, anything beyond is empty.

    Every page links its prev/next neighbour, so beyond matchday M the site
    keeps offering "next matchday" forever — only MAX_EMPTY_STREAK stops it.
    """
    def page_for(url):
        code, season, matchday = matchday_key(url)
        neighbours = [_md_url_for(code, season, n)
                      for n in (int(matchday) - 1, int(matchday) + 1) if n >= 1]
        return _nav_html(*neighbours, fixture=1 <= int(matchday) <= matchdays)
    return page_for


def test_two_competitions_walk_independently():
    """N=2 competitions each visit all their own matchdays; lanes don't mix."""
    matchdays = 8
    spider = GamesUrlsSpider()
    seeds = [(_md_url_for('ESP1', 2025, 1), {'competition_code': 'ESP1'}),
             (_md_url_for('NWSL', 2026, 1), {'competition_code': 'NWSL'})]
    visited = _drive(spider, seeds, _fake_site(matchdays))

    esp = {matchday_key(u)[2] for u in visited if matchday_key(u)[0] == 'ESP1'}
    nwsl = {matchday_key(u)[2] for u in visited if matchday_key(u)[0] == 'NWSL'}
    # Every real matchday of each competition is reached, independently.
    assert {str(n) for n in range(1, matchdays + 1)} <= esp
    assert {str(n) for n in range(1, matchdays + 1)} <= nwsl
    # And the visited set partitions cleanly by competition code.
    assert {matchday_key(u)[0] for u in visited} == {'ESP1', 'NWSL'}


def test_walk_stays_in_own_competition_lane():
    """A foreign competition's matchday href on the page is never followed.

    Guards against trading the scoping bug for an unboundedness bug: the key is
    now the full tuple, so a foreign href looks "unseen" and would be followed
    if the lane guard were missing — misattributing its games to this parent and
    opening an unbounded crawl of the site.
    """
    spider = GamesUrlsSpider()
    out = list(spider.parse_matchday(
        resp(_nav_html(_md_url_for('ESP1', 2025, 29),
                       _md_url_for('BL1', 2025, 9)),
             _md_url_for('ESP1', 2025, 30)),
        parent={'competition_code': 'ESP1'}))
    urls = [o.url for o in out if isinstance(o, scrapy.Request)]
    assert urls, 'should still follow its own neighbour'
    assert not any('BL1' in u for u in urls)


def test_walk_stays_in_own_season_lane():
    """A previous-season matchday href is never followed on a current-season run."""
    spider = GamesUrlsSpider()
    out = list(spider.parse_matchday(
        resp(_nav_html(_md_url_for('ESP1', 2025, 29),
                       _md_url_for('ESP1', 2024, 30)),
             _md_url_for('ESP1', 2025, 30)),
        parent={'competition_code': 'ESP1'}))
    urls = [o.url for o in out if isinstance(o, scrapy.Request)]
    assert urls
    assert not any('_2024_' in u for u in urls)


def test_matchday_cap_bounds_a_pathological_competition():
    """A site that never runs out of fixtures is still bounded by the cap.

    MAX_EMPTY_STREAK can never fire here (every page has a fixture), so the
    per-scope cap is the only thing standing between this and an infinite walk —
    the failure mode that burned a 224-min prod backfill.
    """
    spider = GamesUrlsSpider()

    def endless(url):
        code, season, matchday = matchday_key(url)
        return _nav_html(_md_url_for(code, season, int(matchday) + 1),
                         fixture=True)

    visited = _drive(spider, [(_md_url_for('ESP1', 2025, 1),
                               {'competition_code': 'ESP1'})], endless)
    assert len(visited) <= GamesUrlsSpider.MAX_MATCHDAYS_PER_SCOPE + 1





@pytest.mark.parametrize('competitions', [1, 2, 5])
def test_request_count_proportional_to_competitions_times_matchdays(competitions):
    """Total requests scale as O(competitions x matchdays) — the boundedness proof.

    PROJECT_RULES requires an external spider be proven bounded before it is
    wired into a DAG. The fake site has M real matchdays per competition and
    then empty pages forever, so a correct walk costs M pages plus at most
    MAX_EMPTY_STREAK overshoot on each of the two branches.
    """
    matchdays = 10
    codes = [f'C{i}' for i in range(competitions)]
    spider = GamesUrlsSpider()
    seeds = [(_md_url_for(code, 2025, 1), {'competition_code': code})
             for code in codes]
    visited = _drive(spider, seeds, _fake_site(matchdays))

    lower = competitions * matchdays
    upper = competitions * (matchdays + 2 * GamesUrlsSpider.MAX_EMPTY_STREAK)
    assert lower <= len(visited) <= upper
    # Per-competition cost is constant, i.e. strictly proportional to N.
    assert len(visited) % competitions == 0


# --- real-upstream-artifact test -------------------------------------------

def test_real_samples_two_competitions_do_not_shadow():
    """Two REAL competitions at overlapping matchday numbers stay independent.

    PROJECT_RULES requires at least one test driven by a verbatim upstream
    artifact rather than hand-built mocks, because a mock encodes the consumer's
    own assumptions. Every sample here is a live soccerdonna page captured on
    2026-07-30: NWSL and IRL1 were both mid-season at matchdays 11-14, which is
    exactly the overlap that collapsed the walk in production.

    Sequence: walk NWSL's real matchdays 12/13/14 (which under the old bare-number
    key claimed "12", "13", "14" globally, plus pre-marked neighbours "11"/"15"),
    then hand the spider IRL1's real matchday 12. Its neighbours are IRL1 11 and
    13 - both already claimed by NWSL - so the old key emitted zero follows and
    IRL1's season ended after one page. Live confirmation on the same 5-competition
    seed: old spider 79 games over 4 competitions (one league taking 65 of them),
    patched spider 406 games over 5, each with a full-season window.
    """
    spider = GamesUrlsSpider()

    nwsl_parent = {'type': 'competition', 'competition_code': 'NWSL'}
    for matchday in (12, 13, 14):
        out = list(spider.parse_matchday(
            load_sample('matchday', f'NWSL_2025_{matchday}.html'),
            parent=nwsl_parent))
        games = [o for o in out if isinstance(o, dict)]
        assert games, f'real NWSL matchday {matchday} sample yielded no games'
        assert all(g['parent'] is nwsl_parent for g in games)

    irl_parent = {'type': 'competition', 'competition_code': 'IRL1'}
    out = list(spider.parse_matchday(
        load_sample('matchday', 'IRL1_2025_12.html'), parent=irl_parent))

    games = [o for o in out if isinstance(o, dict)]
    follows = [o for o in out if isinstance(o, scrapy.Request)]
    assert games, 'real IRL1 sample yielded no games'
    assert all(g['parent'] is irl_parent for g in games)
    assert follows, (
        'IRL1 matchday 12 was shadowed by NWSL matchdays 12-14 - the walk died '
        'after one page, which is the production bug')
    # Every follow stays in IRL1's own lane.
    assert all(matchday_key(r.url)[0] == 'IRL1' for r in follows)


# --- matchday-picker enumeration ------------------------------------------
#
# The neighbour walk had to guess where a season ended, and MAX_EMPTY_STREAK made
# that guess by stopping after two consecutive empty matchdays — which a
# mid-season break is indistinguishable from. Production 2026-07-30: DV1S got 8
# games over 8 days while sibling divisions DV1M/DV1N, same calendar and same
# matchday numbering, got 84 and 87 across three months. Every real matchday page
# carries a `spieltag` picker listing the whole season (verified: ESP1 1..30,
# NWSL 1..26, IRL1 1..22, contiguous), so enumeration removes the guess.

def _picker_html(numbers, *, fixture=True, nav_hrefs=()):
    """A matchday page carrying a real-shaped ``spieltag`` picker."""
    opts = ''.join(f'<option value="{n}">{n}. Match day</option>' for n in numbers)
    select = f'<select name="spieltag">{opts}</select>'
    return _nav_html(*nav_hrefs, fixture=fixture).replace('</body>', select + '</body>')


def test_matchday_options_parses_real_samples():
    for name, expected in (('ESP1_2025_30.html', 30), ('NWSL_2025_13.html', 26),
                           ('IRL1_2025_12.html', 22)):
        nums = matchday_options(load_sample('matchday', name).text)
        assert nums == list(range(1, expected + 1)), name


def test_enumerates_full_season_from_real_sample():
    """The real ESP1 matchday-30 page fans out to all 29 other matchdays."""
    spider = GamesUrlsSpider()
    out = list(spider.parse_matchday(_matchday_sample(), parent=PARENT))
    reqs = [o for o in out if isinstance(o, scrapy.Request)]
    got = sorted(int(matchday_key(r.url)[2]) for r in reqs)
    assert got == [n for n in range(1, 31) if n != 30]
    assert all(matchday_key(r.url)[:2] == ('ESP1', '2025') for r in reqs)


def test_mid_season_break_does_not_truncate():
    """The DV1S regression: a break longer than MAX_EMPTY_STREAK must not end the season.

    Matchdays 5-9 have no fixtures — five consecutive empty pages, well past the
    two-page tolerance. Under the neighbour walk the branch died there and
    everything from 10 on was lost. Enumeration reaches all 20.
    """
    season = list(range(1, 21))
    spider = GamesUrlsSpider()

    def page_for(url):
        md = int(matchday_key(url)[2])
        return _picker_html(season, fixture=not (5 <= md <= 9))

    visited = _drive(spider, [(_md_url_for('DV1S', 2025, 12), {'competition_code': 'DV1S'})],
                     page_for)
    assert sorted(int(matchday_key(u)[2]) for u in visited) == season


def test_enumerated_requests_do_not_carry_streak():
    spider = GamesUrlsSpider()
    out = list(spider.parse_matchday(
        resp(_picker_html([1, 2, 3]), _md_url_for('ESP1', 2025, 2)), parent=PARENT))
    reqs = [o for o in out if isinstance(o, scrapy.Request)]
    assert reqs and all('empty_streak' not in r.cb_kwargs for r in reqs)


def test_falls_back_to_walk_when_no_picker():
    """No picker (cup page, or a site-shape change) -> the bounded walk still runs."""
    spider = GamesUrlsSpider()
    out = list(spider.parse_matchday(
        resp(_nav_html(_md_url_for('ESP1', 2025, 29)), _md_url_for('ESP1', 2025, 30)),
        parent=PARENT))
    reqs = [o for o in out if isinstance(o, scrapy.Request)]
    assert reqs and all('empty_streak' in r.cb_kwargs for r in reqs)


def test_enumeration_still_respects_the_per_scope_cap():
    spider = GamesUrlsSpider()
    huge = list(range(1, GamesUrlsSpider.MAX_MATCHDAYS_PER_SCOPE + 40))
    out = list(spider.parse_matchday(
        resp(_picker_html(huge), _md_url_for('ESP1', 2025, 1)), parent=PARENT))
    reqs = [o for o in out if isinstance(o, scrapy.Request)]
    # Non-empty matters: `<= cap` alone is satisfied by zero requests, so the
    # assertion would pass against a spider with no enumeration at all.
    assert reqs
    assert len(reqs) <= GamesUrlsSpider.MAX_MATCHDAYS_PER_SCOPE


def test_picker_page_never_falls_back_to_the_walk():
    """A page WITH a picker enumerates, even when everything is already claimed.

    The branch is on picker presence, not on whether enumeration yielded
    anything. Otherwise the second and later pages of a competition — whose
    matchdays are all claimed by then — would each drop into the neighbour walk
    and overrun the season boundary by up to MAX_EMPTY_STREAK pages.
    """
    spider = GamesUrlsSpider()
    page = _picker_html([1, 2, 3], nav_hrefs=(_md_url_for('ESP1', 2025, 99),))

    first = [o for o in spider.parse_matchday(
        resp(page, _md_url_for('ESP1', 2025, 2)), parent=PARENT)
        if isinstance(o, scrapy.Request)]
    assert sorted(int(matchday_key(r.url)[2]) for r in first) == [1, 3]

    # Same competition, another page: everything claimed, so nothing new -- and
    # crucially no fallback request to the out-of-season matchday 99.
    second = [o for o in spider.parse_matchday(
        resp(page, _md_url_for('ESP1', 2025, 1)), parent=PARENT)
        if isinstance(o, scrapy.Request)]
    assert second == []
