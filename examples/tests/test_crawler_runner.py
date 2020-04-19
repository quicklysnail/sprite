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
    # addr = "localhost:8088"
    # result = client_call(addr, "get_all_crawler_name")
    # print(result)
    # result = client_call(addr, "stop_server")
    # print(result)
    # result = client_call(addr, "stop_server")
    # print(result)
    # module_name = "examples.tests.test_crawler_config.py"
    # module_object = import_module(module_name)
    # print(module_object)
    # print(CrawlerRunner.get_all_crawler())
    test_spider = CustomSpider()
    assert isinstance(test_spider, CrawlerRunner), "not subclass"
