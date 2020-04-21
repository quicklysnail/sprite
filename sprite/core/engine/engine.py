# # -*- coding:utf-8 -*-
# __author__ = 'liyong'
# __date__ = '2019/8/16 19:45'
#
# import time
# import traceback
# import asyncio
# from asyncio import Event
# from threading import Lock
# from typing import Callable, Coroutine
# from types import AsyncGeneratorType
# from sprite.core.scheduler.memory import Slot, MemoryScheduler
# from sprite.core.download import Downloader
# from sprite.utils.coroutinepool import PyCoroutinePool
# from sprite.middleware.middlewaremanager import MiddlewareManager
# from sprite.settings import Settings
# from sprite.spider import Spider
# from sprite.utils.http.request import Request
# from sprite.utils.http.response import Response
# from sprite.utils.log import get_logger
# from sprite.item import Item
# from sprite.utils.request import Counter
# from sprite.utils.asyncHandler import detailCallable
# from sprite.exceptions import SchedulerEmptyException
# from sprite.const import *
#
# logger = get_logger()
#
#
# class Engine:
#     def __init__(self, scheduler: MemoryScheduler, downloader: Downloader, middlewareManager: MiddlewareManager,
#                  spider: Spider, settings: Settings, coroutine_pool: PyCoroutinePool = None):
#
#         self._slot = Slot()
#         self._scheduler = scheduler
#         self._downloader = downloader
#         self._coroutine_pool = coroutine_pool
#         self._middlewareManager = middlewareManager
#         self._spider = spider
#         self._settings = settings
#
#         self._state_lock = Lock()
#         self._state = ENGINE_STATE_STOPPED
#         self._state_signal = Event()
#         self._request_added = Event()
#
#         self._unfinished_workers = 0
#
#         self._start_time = time.time()
#         self._downloaded_request_count = 0
#         self._success_request_count = 0
#         self._failed_request_count = 0
#
#         self._item_counter = Counter(unit=settings.getint("ITEM_COUNTER_UNIT"))
#         self._response_counter = Counter(
#             unit=settings.getint("RESPONSE_COUNTER_UNIT"))
#
#     @property
#     def state(self):
#         with self._state_lock:
#             return self._state
#
#     def is_running(self):
#         with self._state_lock:
#             return (self._state == ENGINE_STATE_RUNNING)
#
#     def is_stopping(self):
#         with self._state_lock:
#             return (self._state == ENGINE_STATE_STOPPING)
#
#     def is_stopped(self):
#         with self._state_lock:
#             return (self._state == ENGINE_STATE_STOPPED)
#
#     def is_to_close(self):
#         if self.is_running() and self._request_added.is_set():
#             return True
#         return False
#
#     def start(self) -> bool:
#         with self._state_lock:
#             if self._state != ENGINE_STATE_STOPPED:
#                 return False
#         self._coroutine_pool.go(self._init())
#         logger.info(f'启动engine')
#         return True
#
#     async def _init(self):
#         with self._state_lock:
#             self._state = ENGINE_STATE_RUNNING
#             self._state_signal.clear()
#             self._request_added.clear()
#         # 启动调度器
#         self._scheduler.start()
#         # 注入start_requests
#         self._coroutine_pool.go(self._get_start_requests())
#
#         # 查询调度器中是否填充了request，如果没有直接退出程序
#         await self._request_added.wait()
#         if not self._scheduler.has_pending_requests():
#             logger.error(
#                 "scheduler 为空，没有构造start request或者填充start request失败, 关闭程序")
#             self.close()
#             return
#         # 设定工作协程的数量
#         self._unfinished_workers = self._settings.getint("WORKER_NUM")
#
#         # 检测工作协程是否都退出
#         self._coroutine_pool.go(self._status_check())
#         # 启动所有的工作协程
#         for _ in range(self._unfinished_workers):
#             self._coroutine_pool.go(self._doSomething())
#
#     async def _get_start_requests(self):
#         # 执行爬虫中间件
#         await self._middlewareManager.process_spider_start(self._spider)
#         if not self._scheduler.has_pending_requests():
#             # 检测非断点续爬
#             try:
#                 if self._spider.start_requests is not None:
#                     for url in self._spider.start_requests:
#                         request = Request(url=url, headers=self._settings.getdict(
#                             "HEADERS"), callback=self._spider.parse)
#                         self._scheduler.enqueue_request(request)
#                 else:
#                     # async for request in self._spider.start_request():
#                     #     self._scheduler.enqueue_request(request)
#                     await detailCallable(self._spider.start_request, self._scheduler.enqueue_request)
#             except Exception as e:
#                 logger.info(
#                     f'填充start request 过程中发生错误: \n{traceback.format_exc()}')
#         with self._state_lock:
#             self._request_added.set()
#
#     # 不断检测所有的工作协程是否都结束，如果都结束的化，则启动关闭引擎的流程
#     async def _status_check(self):
#         while True:
#             if self._unfinished_workers <= 0 and self._settings.getbool('ENGINE_MOST_STOP'):
#                 self.close()
#                 break
#             await asyncio.sleep(COROUTINE_SLEEP_TIME)
#
#     async def _doSomething(self):
#         while True:
#             # 1.首先判断spider非close
#             with self._state_lock:
#                 state = self._state
#             if state == ENGINE_STATE_RUNNING:
#                 # 2.再尝试从调度器里面提取request
#                 try:
#                     # 获取到request之后，开始处理请求,先将request放入正在处理队列记录一下
#                     self._slot.addRequest(self._scheduler.next_request())
#                 except SchedulerEmptyException:
#                     if self._slot.has_pending_request():
#                         await asyncio.sleep(COROUTINE_SLEEP_TIME)
#                         continue
#                     else:
#                         self._unfinished_workers -= 1
#                         break
#                 # 再取出
#                 request = self._slot.getRequest()
#                 try:
#                     await self._doCrawl(request)
#                 except Exception:
#                     logger.error(f'find one error: \n{traceback.format_exc()}')
#                 # 处理完一个request，打一个标记
#                 self._slot.toDone()
#                 self._downloaded_request_count += 1
#             else:
#                 self._unfinished_workers -= 1
#                 break
#
#     # 获取到request之后，开始处理请求
#     async def _doCrawl(self, request: Request):
#         response = None
#         # 1.首先调用下载中间件
#         result = await self._middlewareManager.process_request(request, spider=self._spider)
#         if result:
#             if isinstance(result, Request):
#                 request = result
#             elif isinstance(result, Response):
#                 response = result
#         if response is None:
#             # 2.调用下载器下载request
#             logger.debug(f'downloading request: {request.url} {request.query}')
#             response = await self._downloader.request(request=request)
#             if response.error:
#                 logger.debug(
#                     f'downloaded request failure: {request.url} {request.query}')
#             else:
#                 logger.debug(
#                     f'downloaded request: {request.url}[{response.status}]'
#                 )
#                 unit_speed, unit_count = self._response_counter.dot()
#                 if unit_speed or unit_count:
#                     logger.info(
#                         f'目前获取response的速度：{unit_speed}/s   每{self._item_counter.unit}s获取{unit_count}个response')
#                 self._success_request_count += 1
#         # 3.调用下载中间件处理response
#         result = await self._middlewareManager.process_response(response, self._spider)
#         if result:
#             if isinstance(result, Request):
#                 # 丢入调度器中
#                 request = result
#                 self._scheduler.enqueue_request(request)
#                 return
#             elif isinstance(result, Response):
#                 response = result
#         # 4.调用request的回调函数，对response进行处理
#         await self._handle_request_callback(request.callback, response)
#
#     async def _handle_request_callback(self, callback: Callable, response: Response):
#         # 传入resposne，调用回调函数进行处理
#         # 调用回调函数
#         callback_results = callback(response)
#         if isinstance(callback_results, AsyncGeneratorType):
#             # print(f'回调函数是 AsyncGeneratorType')
#             await self._process_async_callback(callback_results=callback_results)
#         elif isinstance(callback_results, Coroutine):
#             # print(f'回调函数是 一个Coroutine')
#             await self._handle_coroutine_callback(callback_results)
#
#     # 处理回调（以协程的方式）
#     async def _process_async_callback(self, callback_results: AsyncGeneratorType):
#         async for callback_result in callback_results:  # AsyncGeneratorType对象 协程生成器对象
#             # yield 的返回结果类型
#             if isinstance(callback_result, AsyncGeneratorType):
#                 # 继续递归
#                 await self._process_async_callback(callback_result)
#             elif isinstance(callback_result, (Request, Item)):
#                 # yield 的返回值是Request or Item类型
#                 if callback_result:
#                     if isinstance(callback_result, Request):
#                         await self._handle_request_result(callback_result)
#                     elif isinstance(callback_result, Item):
#                         await self._handle_item_result(callback_result)
#             elif isinstance(callback_result, Coroutine):
#                 await self._handle_coroutine_callback(callback_result)
#
#     async def _handle_coroutine_callback(self, aws_callback: Coroutine):
#         result = await aws_callback
#         if result:
#             if isinstance(result, Request):
#                 await self._handle_request_result(result)
#             elif isinstance(result, Item):
#                 await self._handle_item_result(result)
#
#     async def _handle_request_result(self, request: 'Request'):
#         self._scheduler.enqueue_request(request)
#
#     async def _handle_item_result(self, item: 'Item'):
#         logger.debug(
#             f'crawled one Item: {item}'
#         )
#         # 5. 调用管道处理item
#         unit_speed, unit_count = self._item_counter.dot()
#         if unit_count or unit_speed:
#             logger.info(
#                 f'目前获取item的速度：{unit_speed}/s   每{self._item_counter.unit}s获取{unit_count}个item')
#         await self._middlewareManager.pipeline_process_item(item=item, spider=self._spider)
#
#     def get_download_staticate(self) -> [int, int, int]:
#         return self._failed_request_count, self._success_request_count, self._downloaded_request_count
#
#     # 对外的接口，用于关闭引擎
#     def close(self) -> bool:
#         with self._state_lock:
#             if self._state != ENGINE_STATE_RUNNING or not self._request_added.is_set():
#                 return False
#             # 1. 首先关发出关闭信号，
#             self._state = ENGINE_STATE_STOPPING
#         # 2.在协程中执行关闭流程
#         self._coroutine_pool.go(self._close())
#         return True
#
#     async def _close(self):
#         # 关闭引擎的步骤
#         # 1.首先关闭调度器
#         self._scheduler.close()
#         # 2.等待正在执行的reques执行结束
#         await self._slot.join()
#         logger.info("正在处理的request处理完毕！")
#         logger.info(f'一共耗时：{time.time() - self._start_time}s')
#         logger.info(
#             f'下载情况统计： 一共发送请求：{self._downloaded_request_count}    成功请求数量：{self._success_request_count}    失败请求数量：{self._downloaded_request_count - self._success_request_count}')
#         # 3.关闭所有的tcp连接
#         self._downloader.close()
#         # 4.执行爬虫中间件
#         await self._middlewareManager.process_spider_close(self._spider)
#         # 5.然后关闭协程池
#         with self._state_lock:
#             self._state_signal.set()
#             self._state = ENGINE_STATE_STOPPED
#
#     @classmethod
#     def from_settings(cls, settings: Settings, spider: Spider, middlewareManager: MiddlewareManager,
#                       coroutine_pool: PyCoroutinePool = None):
#         if middlewareManager is None:
#             middlewareManager = MiddlewareManager()
#         if coroutine_pool is None:
#             coroutine_pool = PyCoroutinePool.from_setting(settings)
#         obj = cls(
#             scheduler=MemoryScheduler.from_settings(settings, spider),
#             downloader=Downloader.from_settings(settings, coroutine_pool),
#             coroutine_pool=coroutine_pool,
#             spider=spider,
#             settings=settings,
#             middlewareManager=middlewareManager,
#         )
#         return obj
