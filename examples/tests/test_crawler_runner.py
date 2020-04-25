# -*- coding: utf-8 -*-
# @Time    : 2020-04-18 00:41
# @Author  : li
# @File    : test_crawler_runner.py

from sprite.utils.rpc import client_call
from sprite.utils.utils import import_module
from sprite.crawl import CrawlerRunner

from sprite import Spider


class CustomSpider(Spider):
    def __init__(self):
        super(CustomSpider, self).__init__()
        pass


if __name__ == "__main__":
    crawler_runner = CrawlerRunner()
