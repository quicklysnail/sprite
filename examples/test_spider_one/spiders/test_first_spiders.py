# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019-08-24 19:27'

import sprite
from sprite import Spider, Response, Settings, Crawler
from examples.test_spider_one.middlewares import test_middleware
from examples.test_spider_one.items import TestItem


class GaodeSpider(Spider):
    name = "test_spider"

    def start_request(self):
        headers = {
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Connection': 'keep-alive',
            'User-Agent': "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36",
            'X-Requested-With': 'XMLHttpRequest',
        }
        start_requests = ["https://apmconfig.douyucdn.cn/big/apm/front/config/report?client_sys=web",
                          "https://www.douyu.com/japi/search/api/getHotList"]
        for url in start_requests:
            yield sprite.Request(url=url, headers=headers, callback=self.parse, dont_filter=True)

    async def parse(self, response: Response):
        self.logger.info("执行parse")
        self.logger.info(f'response body {response.body}')

        headers = {
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Connection': 'keep-alive',
            'User-Agent': "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36",
            'X-Requested-With': 'XMLHttpRequest',
        }
        start_requests = ["https://www.jianshu.com/p/2afbe455b526"]
        for url in start_requests:
            self.logger.info("抛出一个请求！！！")
            yield sprite.Request(url=url, headers=headers, callback=self.test_parse, dont_filter=True)

    async def test_parse(self, response: Response):
        self.logger.info("test_parse")
        item = TestItem()
        item["body"] = response.body
        yield item


if __name__ == '__main__':
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
    # 启动crawler
    crawler.run()
