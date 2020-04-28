# -*- coding: utf-8 -*-
# @Time    : 2020-04-27 22:56
# @Author  : li
# @File    : test_crawler.py


from examples.test_spider_one.spiders.test_first_spiders import GaodeSpider
from sprite import Settings, Crawler, CrawlerManager
from examples.test_spider_one.middlewares import test_middleware

# 实例化spider
spider = GaodeSpider()
# 实例化一个自定义的settings对象
settings = Settings(values={
            "MAX_DOWNLOAD_NUM": 1,
            "WORKER_NUM": 1,
            "DELAY": 20,
            "LOG_FILE_PATH": "test_spider_one.log",
            "JOB_DIR": "/Users/liyong/projects/open_source/sprite/examples/test_spider_one",
            "LONG_SAVE": True,
        })
# 构造一个crawler对象
crawler = Crawler(spider=spider, middleware_manager=test_middleware, settings=settings)
