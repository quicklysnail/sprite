# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019/8/16 19:45'

import time
import traceback
import asyncio
import threading
from typing import Callable, Coroutine
from types import AsyncGeneratorType
from sprite.core.scheduler import Slot, Scheduler
from sprite.core.download import Downloader
from sprite.utils.coroutinePool import PyCoroutinePool
from sprite.middlewaremanager import MiddlewareManager
from sprite.settings import Settings
from sprite.spider import Spider
from sprite.http.request import Request
from sprite.http.response import Response
from sprite.utils.log import get_logger
from sprite.item import Item
from sprite.utils.request import Counter
from sprite.utils.asyncHandler import detailCallable

logger = get_logger()


class Engine:
    def __init__(self, scheduler: Scheduler, downloader: Downloader, coroutine_pool: PyCoroutinePool,
                 middlewareManager: MiddlewareManager,
                 spider: Spider, settings: Settings):
        self._slot = Slot()
        self._scheduler = scheduler
        self._downloader = downloader
        self._coroutine_pool = coroutine_pool
        self._middlewareManager = middlewareManager
        self._spider = spider
        self._settings = settings

        self._running = threading.Event()
        self._init = threading.Event()
        self._unfinished_workers = 0

        self._start_time = time.time()
        self._downloaded_request_count = 0
        self._success_request_count = 0
        self._failed_request_count = 0

        self._item_counter = Counter(unit=settings.getint("ITEM_COUNTER_UNIT"))
        self._response_counter = Counter(
            unit=settings.getint("RESPONSE_COUNTER_UNIT"))

    def isClose(self) -> bool:
        if self._running.is_set():
            return True
        return False

    def start(self):
        logger.info(f'启动engine')
        # 启动协程池
        self._coroutine_pool.start()
        # 注入start_requests
        self._coroutine_pool.go(self._get_start_requests())

        # 查询调度器中是否填充了request，如果没有直接退出程序
        self._init.wait()
        if not self._scheduler.has_pending_requests():
            logger.error(
                "scheduler 为空，没有构造start request或者填充start request失败, 关闭程序")
            self.close()
            return

        # 执行爬虫中间件
        self._coroutine_pool.go(
            self._middlewareManager.process_spider_start(self._spider))
        # 设定工作协程的数量
        self._unfinished_workers = self._settings.getint("WORKER_NUM")

        # 检测工作协程是否都退出
        self._coroutine_pool.go(self._status_check())
        # 启动所有的工作协程
        for _ in range(self._unfinished_workers):
            self._coroutine_pool.go(self._doSomething())

    async def _get_start_requests(self):
        try:
            if self._spider.start_requests is not None:
                for url in self._spider.start_requests:
                    request = Request(url=url, headers=self._settings.getdict(
                        "HEADERS"), callback=self._spider.parse)
                    self._scheduler.enqueue_request(request)
            else:
                # async for request in self._spider.start_request():
                #     self._scheduler.enqueue_request(request)
                await detailCallable(self._spider.start_request, self._scheduler.enqueue_request)
        except Exception as e:
            logger.info(f'填充start request 过程中发生错误: \n{traceback.format_exc()}')
        self._init.set()

    # 不断检测所有的工作协程是否都结束，如果都结束的化，则启动关闭引擎的流程
    async def _status_check(self):
        while True:
            if self._unfinished_workers <= 0:
                self.close()
                break
            await asyncio.sleep(0.001)

    async def _doSomething(self):
        while True:
            # 1.首先判断spider非close
            if not self._running.is_set():
                # 2.再尝试从调度器里面提取request
                request = self._scheduler.next_request()
                if request:
                    # 获取到request之后，开始处理请求
                    await self._slot.addRequest(request)
                    # 先将request放入正在处理队列记录一下，再取出
                    request = self._slot.getRequest()
                    try:
                        await self._doCrawl(request)
                    except Exception as e:
                        logger.error(
                            f'find one error: \n{traceback.format_exc()}')
                    # 处理完一个request，打一个标记
                    self._slot.toDone()
                else:
                    if self._slot.has_pending_request():
                        await asyncio.sleep(0.001)
                        continue
                    else:
                        self._unfinished_workers -= 1
                        break
            else:
                self._unfinished_workers -= 1
                break

    # 获取到request之后，开始处理请求
    async def _doCrawl(self, request: Request):
        response = None
        # 1.首先调用下载中间件
        result = await self._middlewareManager.process_request(request, spider=self._spider)
        if result:
            if isinstance(result, Request):
                request = result
            elif isinstance(result, Response):
                response = result
        if response is None:
            # 2.调用下载器下载request
            logger.debug(f'downloading request: {request.url} {request.query}')
            self._downloaded_request_count += 1
            response = await self._downloader.request(request=request)
            if response.error:
                self._failed_request_count += 1
                logger.error(
                    f'downloaded request failure: {request.url} {request.query}  [failure message: {response.error}]')
            else:

                logger.debug(
                    f'downloaded request: {request.url}[{response.status}]'
                )
                unit_speed, unit_count = self._response_counter.dot()
                if unit_speed or unit_count:
                    logger.info(
                        f'目前获取response的速度：{unit_speed}/s   每{self._item_counter.unit}s获取{unit_count}个response')
                self._success_request_count += 1
        # 3.调用下载中间件处理response
        result = await self._middlewareManager.process_response(response, self._spider)
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
            return await self._process_async_callback(callback_results=callback_results)
        elif isinstance(callback_results, Coroutine):
            # print(f'回调函数是 一个Coroutine')
            result = await self._handle_coroutine_callback(callback_results)
            if result:
                if isinstance(result, Request):
                    self._scheduler.enqueue_request(result)
                elif isinstance(result, Item):
                    # 5. 调用管道处理item
                    await self._middlewareManager.pipeline_process_item(item=result, spider=self._spider)

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
                        self._scheduler.enqueue_request(callback_result)
                    elif isinstance(callback_result, Item):
                        logger.debug(
                            f'crawled one Item: {callback_result}'
                        )
                        # 5. 调用管道处理item
                        unit_speed, unit_count = self._item_counter.dot()
                        if unit_count or unit_speed:
                            logger.info(
                                f'目前获取item的速度：{unit_speed}/s   每{self._item_counter.unit}s获取{unit_count}个item')
                        await self._middlewareManager.pipeline_process_item(item=callback_result, spider=self._spider)
            elif isinstance(callback_result, Coroutine):
                await self._handle_coroutine_callback(callback_result)

    async def _handle_coroutine_callback(self, aws_callback: Coroutine):
        result = await aws_callback
        if result:
            if isinstance(result, Request):
                self._scheduler.enqueue_request(result)
            elif isinstance(result, Item):
                # 5. 调用管道处理item
                await self._middlewareManager.pipeline_process_item(item=result, spider=self._spider)

    def get_download_staticate(self) -> [int, int, int]:
        return self._failed_request_count, self._success_request_count, self._downloaded_request_count

    # 对外的接口，用于关闭引擎
    def close(self):
        if self._running.is_set():
            return
        # 1. 首先关闭发出关闭信号，
        self._running.set()
        # 2.在协程中执行关闭流程
        self._coroutine_pool.go(self._close())

    async def _close(self):
        logger.info(f'开始关闭spider')
        # 关闭引擎的步骤
        # 1.首先关闭调度器
        self._scheduler.close()
        # 2.等待正在执行的reques执行结束
        await self._slot.join()
        logger.info("正在处理的request处理完毕！")
        logger.info(f'一共耗时：{time.time() - self._start_time}s')
        logger.info(
            f'下载情况统计： 一共发送请求：{self._downloaded_request_count}    成功请求数量：{self._success_request_count}    失败请求数量：{self._failed_request_count}')
        # 3.关闭所有的tcp连接
        self._downloader.close()
        # 4.然后关闭协程池
        await self._middlewareManager.process_spider_close(self._spider)

        # 5.执行爬虫中间件
        self._coroutine_pool.stop()

    @classmethod
    def from_settings(cls, settings: Settings, spider: Spider, middlewareManager: MiddlewareManager):
        if middlewareManager is None:
            middlewareManager = MiddlewareManager()
        coroutine_pool = PyCoroutinePool.from_setting(settings)
        obj = cls(
            scheduler=Scheduler.from_settings(settings),
            downloader=Downloader.from_settings(settings, coroutine_pool),
            coroutine_pool=coroutine_pool,
            spider=spider,
            settings=settings,
            middlewareManager=middlewareManager,
        )
        return obj
