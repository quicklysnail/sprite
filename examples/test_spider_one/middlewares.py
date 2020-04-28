# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019-08-24 19:09'

from sprite.middleware.middlewaremanager import MiddlewareManager

test_middleware = MiddlewareManager()


# 增加下载中间件，在下载request之前执行
@test_middleware.add_download_middleware(isBefore=True)
async def test_downloader_middleware(request, spider=None):
    spider.logger.info("这是下载中间件  before")
    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Connection': 'keep-alive',
        'User-Agent': "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36",
        'X-Requested-With': 'XMLHttpRequest',
    }
    request.headers = headers
    spider.logger.info(f'捕获request   {request.url}')


# 增加下载中间件，在下载request之后执行
@test_middleware.add_download_middleware(isBefore=False)
async def test_downloader_middleware(response=None, spider=None):
    spider.logger.info("这是下载中间件 after")
    spider.logger.info(f'捕获response   {response.status}')


# 增加处理item中间件，获取item之后执行
@test_middleware.add_pipeline_middleware()
async def test_downloader_middleware(item=None, spider=None):
    spider.logger.info("这是管道中间件")
    spider.logger.info(f'捕获item   {item}')


# 增加spider中间件，在启动spider之前执行
@test_middleware.add_spider_middleware(isBefore=True)
def test_downloader_middleware(spider=None):
    spider.logger.info("这是spider中间件 before")


# 增加spider中间件，在启动spider之后执行
@test_middleware.add_spider_middleware(isBefore=False)
def test_downloader_middleware(spider=None):
    spider.logger.info("这是spdier中间件 after")
