import os
import glob
import pytest
from scrapy.http import HtmlResponse

SAMPLES = os.path.join(os.path.dirname(__file__), '..', 'samples', 'pages')
BASE = 'https://www.soccerdonna.de'


def _url_for(category, filename):
    """Best-effort reconstruct a plausible page URL from the sample filename."""
    stem = filename.replace('.html', '')
    if category == 'index':
        return f'{BASE}/en/2010/startseite/wettbewerbeDE.html'
    if category == 'competition':
        return f'{BASE}/en/x/startseite/wettbewerb_{stem}.html'
    if category == 'club':
        return f'{BASE}/en/x/kader/{stem}.html'
    if category == 'player':
        return f'{BASE}/en/x/profil/{stem}.html'
    if category == 'appearance':
        return f'{BASE}/en/x/leistungsdaten/{stem}.html'
    return f'{BASE}/en/{stem}.html'


def load_sample(category, filename):
    """Load one named sample as a Scrapy HtmlResponse."""
    path = os.path.join(SAMPLES, category, filename)
    with open(path, 'rb') as f:
        body = f.read()
    return HtmlResponse(url=_url_for(category, filename), body=body, encoding='utf-8')


def iter_samples(category):
    """Yield (filename, HtmlResponse) for every sample of a category."""
    for path in sorted(glob.glob(os.path.join(SAMPLES, category, '*.html'))):
        filename = os.path.basename(path)
        yield filename, load_sample(category, filename)


# Expose helpers as fixtures too, for convenience.
@pytest.fixture
def samples():
    return iter_samples
