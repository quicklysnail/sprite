# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019-08-24 19:09'

from sprite.middlewaremanager import MiddlewareManager

test_middleware = MiddlewareManager()


# 增加下载中间件，在下载request之前执行
@test_middleware.add_download_middleware(isBefore=True)
async def test_downloader_middleware(request, spider=None):
    spider.logger.info("这是下载中间件  before")
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
async def test_downloader_middleware(spider=None):
    spider.logger.info("这是spider中间件 before")


# 增加spider中间件，在启动spider之后执行
@test_middleware.add_spider_middleware(isBefore=False)
async def test_downloader_middleware(spider=None):
    spider.logger.info("这是spdier中间件 after")
