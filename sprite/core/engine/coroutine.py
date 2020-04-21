# -*- coding: utf-8 -*-
# @Time    : 2020-04-21 15:29
# @Author  : li
# @File    : coroutine.py

import traceback
import asyncio
from typing import Callable, Coroutine
from types import AsyncGeneratorType, GeneratorType
from sprite.core.engine.base import BaseEngine
from sprite.const import ENGINE_STATE_STOPPED, ENGINE_STATE_RUNNING, ENGINE_STATE_PAUSE, COROUTINE_SLEEP_TIME
from sprite.core.scheduler.base import BaseScheduler, BaseSlot
from sprite.core.download.base import BaseDownloader
from sprite.utils.request import BaseCrawlerCounter, MemoryCrawlerCounter
from sprite.middleware.middlewaremanager import MiddlewareManager
from sprite.utils.http.request import Request
from sprite.utils.http.response import Response
from sprite.spider import Spider
from sprite.settings import Settings
from sprite.utils.log import get_logger
from sprite.exceptions import RequestQueueEmptyException
from sprite.item import Item

logger = get_logger()


class CoroutineEngine(BaseEngine):

    def __init__(self, spider: 'Spider', downloader: 'BaseDownloader', scheduler: 'BaseScheduler',
                 middleware_manager: 'MiddlewareManager', slot: 'BaseSlot', settings: 'Settings',
                 crawler_counter: 'BaseCrawlerCounter'):
        super(CoroutineEngine, self).__init__(spider, downloader, scheduler, middleware_manager, slot,
                                              settings, crawler_counter)

    async def run(self):
        """
        运行引擎
        """
        with self._state_lock:
            assert self._state ==ENGINE_STATE_STOPPED, "engine must in stopped state"
            self._state = ENGINE_STATE_RUNNING
        await self._do_work()

    def stop(self):
        """
        停止引擎
        """
        with self._state_lock:
            assert self._state == ENGINE_STATE_RUNNING, "engine must in running state"
            self._state = ENGINE_STATE_STOPPED

    def pause(self):
        """
        暂停引擎
        :return:
        """
        with self._state_lock:
            assert self._state == ENGINE_STATE_RUNNING, "engine must in running state"
            self._state_signal.clear()
            self._state = ENGINE_STATE_PAUSE

    def reduction(self):
        """
        恢复运行引擎
        :return:
        """
        with self._state_lock:
            assert self._state == ENGINE_STATE_PAUSE, "engine must in pause state"
            self._state_signal.set()
            self._state = ENGINE_STATE_RUNNING

    async def _do_work(self):
        """
        不断的从调度器里面request
        从respond里面获取到request同样上传到调度器
        :return:
        """
        while self._state == ENGINE_STATE_RUNNING:
            try:
                request = self._scheduler.next_request(self._crawler_name)
                self._slot.addRequest(self._crawler_name)
                await self._do_crawl(request)
                self._slot.getRequest(self._crawler_name)
            except RequestQueueEmptyException:
                # 调度器中request队列为空
                if self._slot.has_request(self._crawler_name):
                    # 有正在处理的request
                    await asyncio.sleep(COROUTINE_SLEEP_TIME)
                    continue
                else:
                    # 已经没有正在处理的request了
                    break
            except Exception:
                logger.error(f'find one error: \n{traceback.format_exc()}')

    # 获取到request之后，开始处理请求
    async def _do_crawl(self, request: Request):
        response = None
        # 1.首先调用下载中间件
        result = await self._middleware_manager.process_request(request, spider=self._spider)
        if result:
            if isinstance(result, Request):
                request = result
            elif isinstance(result, Response):
                response = result
        if response is None:
            # 2.调用下载器下载request
            logger.debug(f'downloading request: {request.url} {request.query}')
            response = await self.download_request(request)
            if response.error:
                self._crawler_counter.recorded_failed_request()
                logger.debug(
                    f'downloaded request failure: {request.url} {request.query}')
            else:
                self._crawler_counter.response_dot()
                self._crawler_counter.recorded_success_request()
                logger.debug(
                    f'downloaded request: {request.url}[{response.status}]'
                )
        # 3.调用下载中间件处理response
        result = await self._middleware_manager.process_response(response, self._spider)
        if result:
            if isinstance(result, Request):
                # 丢入调度器中
                request = result
                self._scheduler.enqueue_request(request)
                return
            elif isinstance(result, Response):
                response = result
        # 4.调用request的回调函数，对response进行处理
        await self._handle_request_callback(request.callback, response)

    async def _handle_request_callback(self, callback: Callable, response: Response):
        # 传入resposne，调用回调函数进行处理
        # 调用回调函数
        callback_results = callback(response)
        if isinstance(callback_results, AsyncGeneratorType):
            # print(f'回调函数是 AsyncGeneratorType')
            await self._process_async_callback(callback_results=callback_results)
        elif isinstance(callback_results, Coroutine):
            # print(f'回调函数是 一个Coroutine')
            await self._handle_coroutine_callback(callback_results)

    # 处理回调（以协程的方式）
    async def _process_async_callback(self, callback_results: AsyncGeneratorType):
        async for callback_result in callback_results:  # AsyncGeneratorType对象 协程生成器对象
            # yield 的返回结果类型
            if isinstance(callback_result, AsyncGeneratorType):
                # 继续递归
                await self._process_async_callback(callback_result)
            elif isinstance(callback_result, (Request, Item)):
                # yield 的返回值是Request or Item类型
                if callback_result:
                    if isinstance(callback_result, Request):
                        await self._handle_request_result(callback_result)
                    elif isinstance(callback_result, Item):
                        await self._handle_item_result(callback_result)
            elif isinstance(callback_result, Coroutine):
                await self._handle_coroutine_callback(callback_result)

    async def _handle_coroutine_callback(self, aws_callback: Coroutine):
        result = await aws_callback
        if result:
            if isinstance(result, Request):
                await self._handle_request_result(result)
            elif isinstance(result, Item):
                await self._handle_item_result(result)

    async def _handle_request_result(self, request: 'Request'):
        self._scheduler.enqueue_request(request)

    async def _handle_item_result(self, item: 'Item'):
        logger.debug(
            f'crawled one Item: {item}'
        )
        # 5. 调用管道处理item
        self._crawler_counter.item_dot()
        await self._middleware_manager.pipeline_process_item(item=item, spider=self._spider)

    async def recognition_state_signal(self):
        """
        识别暂停信号
        :return:
        """
        await self._state_signal.wait()

    async def download_request(self, request: 'Request') -> 'Response':
        """
        调用下载器进行下载
        :param request:
        :return:
        """
        await self.recognition_state_signal()
        response = await self._downloader.download(request)
        await self.recognition_state_signal()
        return response
