# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019/8/16 19:46'


from typing import Callable, List, Coroutine, Awaitable
from sprite.http.request import Request
from sprite.http.response import Response
from sprite.item import Item
from sprite.spider import Spider

from sprite.exceptions import TypeNotSupport


DOWNLOAD_MIDDLEWARE, PIPELINE_MIDDLEWARE, SPIDER_MIDDLEWARE = range(3)

BEFORE = "before"
AFTER = "after"


class MiddlewareManager:
    def __init__(self):
        self._middlewares = {

        DOWNLOAD_MIDDLEWARE: {
            BEFORE: [],
            AFTER: [],
        },

        PIPELINE_MIDDLEWARE: [],

        SPIDER_MIDDLEWARE: {
            BEFORE: [],
            AFTER: [],
        },
    }

    def _type_check(self, func:Callable):
        if not isinstance(func, Awaitable):
            raise TypeNotSupport("中间件类型必须是协程！")

    def add_download_middleware(self, isBefore: bool = True):
        def wrappFunc(func: Callable):
            def register_middleware(func: Callable):
                # self._type_check(func)
                if isBefore:
                    self._middlewares[DOWNLOAD_MIDDLEWARE][BEFORE].append(func)
                else:
                    self._middlewares[DOWNLOAD_MIDDLEWARE][AFTER].append(func)

            register_middleware(func)

        return wrappFunc

    def add_pipeline_middleware(self):
        def wrappFunc(func: Callable):
            def register_middleware(func):
                # self._type_check(func)
                self._middlewares[PIPELINE_MIDDLEWARE].append(func)

            register_middleware(func)

        return wrappFunc

    def add_spider_middleware(self, isBefore: bool = True):
        def wrappFunc(func: Callable):
            def register_middleware(func: Callable):
                # self._type_check(func)
                if isBefore:
                    self._middlewares[SPIDER_MIDDLEWARE][BEFORE].append(func)
                else:
                    self._middlewares[SPIDER_MIDDLEWARE][AFTER].append(func)

            register_middleware(func)

        return wrappFunc

    def _getMiddleWareByPostion(self, middleware_name: str, postion: str=None) -> List:
        if postion:
            return self._middlewares[middleware_name][postion]
        return self._middlewares[middleware_name]


    async def process_request(self,request:Request, spider:Spider):
        fname = lambda f: f'{f.__name__}'
        result = None
        for method in self._getMiddleWareByPostion(middleware_name=DOWNLOAD_MIDDLEWARE,postion=BEFORE):
            result =await method(request=request, spider=spider)
            assert result is None or isinstance(result, (Request, Response)), f'this middleware {fname(method)} must return None or Resquest or Response, but got {type(result)}'
            # 有返回值表示 下面的中间件不再执行
            if result:
                return result
        return result

    async def process_response(self, response:Response , spider:Spider):
        fname = lambda f: f'{f.__name__}'
        result = None
        for method in self._getMiddleWareByPostion(middleware_name=DOWNLOAD_MIDDLEWARE, postion=AFTER):
            result =await method(response=response, spider=spider)
            assert result is None or isinstance(result, (Request, Response)), f'this middleware {fname(method)} must return None or Resquest or Response, but got {type(result)}'
            if result:
                return result
        return result


    async def pipeline_process_item(self, item:Item, spider:Spider):
        fname = lambda f:f'{f.__name__}'
        for method in self._getMiddleWareByPostion(middleware_name=PIPELINE_MIDDLEWARE):
            result =await method(spider=spider, item=item)
            assert result is None or isinstance(result, Item), f'this middleware {fname(method)} must return None or Item, but got {type(result)}'
            if result is None:
                return

    async def process_spider_start(self, spider:Spider):
        for method in self._getMiddleWareByPostion(middleware_name=SPIDER_MIDDLEWARE, postion=BEFORE):
            await method(spider=spider)


    async def process_spider_close(self, spider:Spider):
        for method in self._getMiddleWareByPostion(middleware_name=SPIDER_MIDDLEWARE, postion=AFTER):
            await method(spider=spider)


