# -*- coding: utf-8 -*-
BOT_NAME = 'soccerdonna'

SPIDER_MODULES = ['soccerdonna.spiders']
NEWSPIDER_MODULE = 'soccerdonna.spiders'

# Obey robots.txt rules
ROBOTSTXT_OBEY = True

# Identify ourselves honestly
USER_AGENT = 'soccerdonna-scraper (+https://github.com/gemini-sports; women-football research)'

FEED_FORMAT = 'jsonlines'
FEED_URI = 'stdout:'

# soccerdonna is a small site — crawl gently.
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1.0
AUTOTHROTTLE_MAX_DELAY = 10.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
DOWNLOAD_DELAY = 1.0
CONCURRENT_REQUESTS_PER_DOMAIN = 2

EXTENSIONS = {
    'scrapy.extensions.closespider.CloseSpider': 500
}
DOWNLOADER_MIDDLEWARES = {
    'scrapy.downloadermiddlewares.httpcache.HttpCacheMiddleware': 500
}

CLOSESPIDER_PAGECOUNT = 0
LOG_LEVEL = 'ERROR'

# HTTP cache (development aid)
HTTPCACHE_ENABLED = True
HTTPCACHE_DIR = 'httpcache'

REQUEST_FINGERPRINTER_IMPLEMENTATION = '2.7'
