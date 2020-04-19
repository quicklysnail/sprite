# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019/8/16 19:46'

from typing import Callable, List, Awaitable
from sprite.utils.http.request import Request
from sprite.utils.http.response import Response
from sprite.item import Item
from sprite.spider import Spider

from sprite.exceptions import TypeNotSupport

DOWNLOAD_MIDDLEWARE, PIPELINE_MIDDLEWARE, SPIDER_MIDDLEWARE = range(3)

BEFORE = "before"
AFTER = "after"


class MiddlewareManager:
    def __init__(self):
        self._middleware = {

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

    def _type_check(self, func: Callable):
        if not isinstance(func, Awaitable):
            raise TypeNotSupport("中间件类型必须是协程！")

    def _getMiddleWareByposition(self, middleware_name: str, position: str = None) -> List:
        if position:
            target_middleware = self._middleware.get(middleware_name, {})
            return target_middleware.get(position, [])
        return self._middleware.get(middleware_name, [])

    def add_download_middleware(self, isBefore: bool = True):
        def wrappFunc(func: Callable):
            def register_middleware(func: Callable):
                # self._type_check(func)
                if isBefore:
                    self._middleware[DOWNLOAD_MIDDLEWARE][BEFORE].append(func)
                else:
                    self._middleware[DOWNLOAD_MIDDLEWARE][AFTER].append(func)

            register_middleware(func)

        return wrappFunc

    def add_pipeline_middleware(self):
        def wrappFunc(func: Callable):
            def register_middleware(func):
                # self._type_check(func)
                self._middleware[PIPELINE_MIDDLEWARE].append(func)

            register_middleware(func)

        return wrappFunc

    def add_spider_middleware(self, isBefore: bool = True):
        def wrappFunc(func: Callable):
            def register_middleware(func: Callable):
                # self._type_check(func)
                if isBefore:
                    self._middleware[SPIDER_MIDDLEWARE][BEFORE].append(func)
                else:
                    self._middleware[SPIDER_MIDDLEWARE][AFTER].append(func)

            register_middleware(func)

        return wrappFunc

    async def process_request(self, request: Request, spider: Spider):
        result = None
        for method in self._getMiddleWareByposition(middleware_name=DOWNLOAD_MIDDLEWARE, position=BEFORE):
            result = await method(request=request, spider=spider)
            assert result is None or isinstance(
                result, (Request,
                         Response)), f'this middleware {self.func_name(method)} must return None or Resquest or Response, but got {type(result)}'
            # 有返回值表示 下面的中间件不再执行
            if result:
                return result
        return result

    async def process_response(self, response: Response, spider: Spider):
        result = None
        for method in self._getMiddleWareByposition(middleware_name=DOWNLOAD_MIDDLEWARE, position=AFTER):
            result = await method(response=response, spider=spider)
            assert result is None or isinstance(
                result, (Request,
                         Response)), f'this middleware {self.func_name(method)} must return None or Resquest or Response, but got {type(result)}'
            # 有返回值表示 下面的中间件不再执行
            if result:
                return result
        return result

    async def pipeline_process_item(self, item: Item, spider: Spider):
        for method in self._getMiddleWareByposition(middleware_name=PIPELINE_MIDDLEWARE):
            result = await method(spider=spider, item=item)
            assert result is None or isinstance(
                result,
                Item), f'this middleware {self.func_name(method)} must return None or Item, but got {type(result)}'
            if result is None:
                return

    async def process_spider_start(self, spider: Spider):
        for method in self._getMiddleWareByposition(middleware_name=SPIDER_MIDDLEWARE, position=BEFORE):
            await method(spider=spider)

    async def process_spider_close(self, spider: Spider):
        for method in self._getMiddleWareByposition(middleware_name=SPIDER_MIDDLEWARE, position=AFTER):
            await method(spider=spider)

    @staticmethod
    def func_name(func):
        return f'{func.__name__}'


middleware_manager = MiddlewareManager()
