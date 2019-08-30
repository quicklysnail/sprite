# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019-08-24 19:09'

from sprite.middlewaremanager import MiddlewareManager

test_middleware = MiddlewareManager()

@test_middleware.add_download_middleware(isBefore=True)
async def test_downloader_middleware(request=None, response=None, spider=None, item=None):
    spider.logger.info("这是下载中间件test_download_middleware")
    spider.logger.info(f'捕获request   {request.url}')





