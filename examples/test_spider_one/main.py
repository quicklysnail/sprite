# -*- coding: utf-8 -*-
# @Time    : 2020-04-18 00:04
# @Author  : li
# @File    : main.py

from examples.test_spider_one.spiders.test_first_spiders import GaodeSpider
from sprite import Settings, Crawler, CrawlerRunner
from examples.test_spider_one.middlewares import test_middleware


# @CrawlerRunner.add_crawler()
# def set_test_one_crawler():
#     # 实例化spider
#     spider = GaodeSpider()
#     # 实例化一个自定义的settings对象
#     settings = Settings(values={
#         "MAX_DOWNLOAD_NUM": 1,
#         "WORKER_NUM": 1,
#         "DELAY": 20,
#         "LOG_FILE_PATH": "test_spider_one.log",
#         "JOB_DIR": "/Users/liyong/projects/open_source/sprite/examples/test_spider_one",
#         "LONG_SAVE": True,
#     })
#     # 构造一个crawler对象
#     crawler = Crawler(
#         spider=spider, middlewareManager=test_middleware, settings=settings)
#     return crawler


if __name__ == "__main__":
    settings = Settings(values={
        "MAX_DOWNLOAD_NUM": 1,
        "WORKER_NUM": 1,
        "DELAY": 20,
        "LOG_FILE_PATH": "test_spider_one.log",
        "JOB_DIR": "/Users/liyong/projects/open_source/sprite/examples/test_spider_one",
        "LONG_SAVE": True,
    })
    crawler_runner = CrawlerRunner(settings=settings)
    crawler_runner.start()
