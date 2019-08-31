# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019/8/19 16:41'


from sprite.middlewaremanager import MiddlewareManager
from sprite.middlewaremanager import DOWNLOAD_MIDDLEWARE, BEFORE, AFTER


middlewareManager = MiddlewareManager()



@middlewareManager.add_download_middleware(isBefore=True)
async def test_middleware(request=None, response=None, spider=None, item=None):
    print("test")
    print("test_middleware")


