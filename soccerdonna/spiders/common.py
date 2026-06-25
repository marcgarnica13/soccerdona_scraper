from io import BufferedReader
import scrapy
from scrapy import Request
import os, sys
import json
import gzip
import typing

default_base_url = 'https://www.soccerdonna.de'


def read_lines(file_name: str, reading_fn: typing.Callable[[str], BufferedReader]) -> typing.List[dict]:
    with reading_fn(file_name) as f:
        lines = f.readlines()
        parents = [json.loads(line) for line in lines]
    return parents


class BaseSpider(scrapy.Spider):
    def __init__(self, base_url=None, parents=None):
        if base_url is not None:
            self.base_url = base_url
        else:
            self.base_url = default_base_url

        # Determine whether the parents file is gzip compressed.
        if parents is not None:
            extension = parents.split(".")[-1]
            self.gzip_compressed = (extension == "gz") if extension else False
        else:
            self.gzip_compressed = False

        # Load parent objects either from a file, zipped file, or stdin.
        if parents is not None:
            if self.gzip_compressed:
                parents = read_lines(parents, gzip.open)
            else:
                parents = read_lines(parents, open)
        elif not sys.stdin.isatty() and self._stdin_is_readable():
            parents = [json.loads(line) for line in sys.stdin]
        else:
            parents = self.scrape_parents()

        # Second-level parents are redundant.
        for parent in parents:
            if parent.get('parent') is not None:
                del parent['parent']

        self.entrypoints = parents

    @staticmethod
    def _stdin_is_readable():
        # Under test runners (e.g. pytest) stdin is replaced by a guard object
        # that is not a tty but raises on read. Treat such stdin as "no parents
        # piped in" so direct spider instantiation falls through to
        # scrape_parents() instead of erroring.
        try:
            return sys.stdin.readable()
        except (ValueError, OSError):
            return False

    def scrape_parents(self):
        if not os.environ.get('SCRAPY_CHECK'):
            raise Exception("Backfilling is not yet supported, please provide a 'parents' file")
        else:
            return []

    def start_requests(self):
        applicable_items = []
        for item in self.entrypoints:
            item['seasoned_href'] = self.seasonize_entrypoin_href(item)
            applicable_items.append(item)

        return [
            Request(item['seasoned_href'], cb_kwargs={'parent': item})
            for item in applicable_items
        ]

    def seasonize_entrypoin_href(self, item):
        # Overridden in common_comp_club.BaseSpider; default is a plain join.
        return f"{self.base_url}{item['href']}"

    def safe_strip(self, word):
        return word.strip() if word else word
