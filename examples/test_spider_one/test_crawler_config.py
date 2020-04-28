# -*- coding: utf-8 -*-
# @Time    : 2020-04-19 13:30
# @Author  : li
# @File    : test_crawler_config.py

from examples.test_spider_one.spiders.test_first_spiders import GaodeSpider
from sprite import Settings, Crawler, CrawlerManager
from examples.test_spider_one.middlewares import test_middleware


class TestCrawler(CrawlerManager):
    @CrawlerManager.add_crawler()
    def get_bilibili_crawler(self):
        # 实例化spider
        spider = GaodeSpider()
        # 实例化一个自定义的settings对象
        settings = Settings(values={
            "MAX_DOWNLOAD_NUM": 5,
            "WORKER_NUM": 5,
            "DELAY": 0,
            "LOG_FILE_PATH": "/Users/liyong/projects/open_source/sprite/examples/test_spider_one.log",
            "LONG_SAVE": True,
        })
        # 构造一个crawler对象
        crawler = Crawler(spider=spider, middleware_manager=test_middleware, settings=settings)
        return crawler

    # @CrawlerManager.add_crawler()
    # def set_test_one_crawler(self):
    #     # 实例化spider
    #     spider = GaodeSpider()
    #     # 实例化一个自定义的settings对象
    #     settings = Settings(values={
    #         "MAX_DOWNLOAD_NUM": 5,
    #         "WORKER_NUM": 5,
    #         "DELAY": 0,
    #         "LOG_FILE_PATH": "/Users/liyong/projects/open_source/sprite/examples/test_spider_one.log",
    #         "LONG_SAVE": True,
    #     })
    #     # 构造一个crawler对象
    #     crawler = Crawler(spider=spider, middleware_manager=test_middleware, settings=settings)
    #     return crawler
