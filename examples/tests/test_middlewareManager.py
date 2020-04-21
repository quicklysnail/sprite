# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019/8/19 16:41'


from sprite.middleware.middlewaremanager import MiddlewareManager

middlewareManager = MiddlewareManager()



@middlewareManager.add_download_middleware(isBefore=True)
async def test_middleware(request=None, response=None, spider=None, item=None):
    print("test")
    print("test_middleware")


