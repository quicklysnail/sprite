# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019-07-20 00:50'

import asyncio
from queue import Queue
import traceback
from typing import Union
from typing import List
from asyncio import AbstractEventLoop, TimeoutError
from .limits import RequestRate
from .pool import ConnectionPool
from sprite.http.request import Request
from sprite.http.response import Response
from .retries import RetryStrategy
from .retries import RetryStrategy
from sprite.utils.coroutinePool import PyCoroutinePool
from .session import ClientDefaults, Session
from sprite.settings import Settings
from sprite.utils.log import get_logger
from .limits import RequestRate

logger = get_logger()


class Downloader:
    __slots__ = (
        '_session', '_loop', '_coroutine_pool', '_downloaded_response', '_downloaded_request', '_crawler', '_settings',
        '_sem', '_delay', '_no_complete_task')

    def __init__(self, loop: AbstractEventLoop, max_download_num: int = 5, coroutine_pool: PyCoroutinePool = None,
                 headers: dict = None,
                 follow_redirects: bool = False, max_redirects: int = 30, delay: int = 1,
                 stream: bool = False, decode: bin = True, ssl=None, keep_alive: bool = True,
                 prefix: str = '', timeout: Union[int, float] = ClientDefaults.TIMEOUT,
                 retries: RetryStrategy = None, limits: List[RequestRate] = None):
        self._loop = loop
        self._sem = asyncio.Semaphore(max_download_num)
        self._delay = delay
        self._no_complete_task = 0

        self._session = Session(loop=self._loop, headers=headers, follow_redirects=follow_redirects,
                                max_redirects=max_redirects,
                                stream=stream, decode=decode, ssl=ssl, keep_alive=keep_alive, prefix=prefix,
                                timeout=timeout,
                                retries=retries, limits=limits)
        # 协程池
        if coroutine_pool is None:
            self._coroutine_pool = PyCoroutinePool()
            self._coroutine_pool.start()
        # 自带的缓冲队列
        self._downloaded_response = Queue()

    # 添加下载任务
    def addTask(self, request: Request):
        task = self.request(request)
        # 添加到协程池中执行
        self._coroutine_pool.go(task=task)
        self._no_complete_task += 1

    def getResponse(self) -> Union[Response, Exception]:
        # 阻塞获取response
        response = self._downloaded_response.get()
        return response

    def addResponse(self, response: Union[Response, Exception]):
        self._downloaded_response.put(response)
        self._no_complete_task -= 1

    def _get_proxy(self, request: Request):
        return request.meta.get("proxy", None)

    async def request(self, request: Request) -> Union[Response, Exception]:
        # 强制每一个请求的下载间隔一小会
        if self._delay > 0:
            await asyncio.sleep(self._delay)
        # 加锁的目的是为了限制同一时间的并发数量
        async with self._sem:
            try:
                proxy = self._get_proxy(request)
                if request.method == "GET":
                    response = await self._session.get(url=request.url, headers=request.headers,
                                                       query=request.query,
                                                       cookies=request.cookies, ignore_prefix=True, proxy=proxy)
                else:
                    response = await self._session.post(url=request.url, headers=request.headers,
                                                        query=request.query,
                                                        form=request.formdata, cookies=request.cookies,
                                                        ignore_prefix=True, proxy=proxy)
                response = Response(url=response.url, status=response.status_code, headers=response.headers.dump(),
                                    body=response.content.decode("utf-8"), request=request, )
                self.addResponse(response)
                return response
            # 请求失败
            except (ConnectionError, TimeoutError) as error:
                if isinstance(error, ConnectionError):
                    logger.info(f'find one connection of error')
                elif isinstance(error, TimeoutError):
                    logger.info(f'find one timeout of error')
                response = Response(url=request.url, status=400, headers=request.headers,
                                    request=request, error=error)
                self.addResponse(response)
                return response
            except Exception as error:
                logger.info(f'下载过程中发现一个错误！丢失request！\n{traceback.format_exc()}')
                self.addResponse(error)
                raise error

    def close(self):
        self._session.close()

    def has_pending_response(self):
        if self._downloaded_response.empty():
            return False
        else:
            return True

    def has_no_complete_task(self) -> bool:
        if self._no_complete_task > 0:
            return True
        return False

    @classmethod
    def from_settings(cls, settings: Settings, coroutine_pool: PyCoroutinePool):
        max_download_num = settings.getint("MAX_DOWNLOAD_NUM")
        headers = settings.getdict("HEADERS")
        follow_redirects = settings.getbool("FOLLOW_REDIRECTS")
        max_redirects = settings.getint("MAX_REDIRECTS")
        stream = settings.getbool("STREAM")
        decode = settings.getbool("DECODE")
        ssl = settings.get("SSL")
        keep_alive = settings.getbool("KEEP_ALIVE")
        prefix = settings.get("PREFIX")
        timeout = settings.get("TIMEOUT")
        limits = settings.get("LIMITS")
        delay = settings.getint("DELAY")

        obj = cls(loop=coroutine_pool.loop, max_download_num=max_download_num, coroutine_pool=coroutine_pool,
                  headers=headers, follow_redirects=follow_redirects, max_redirects=max_redirects, delay=delay,
                  stream=stream, decode=decode, ssl=ssl, keep_alive=keep_alive, prefix=prefix,
                  timeout=timeout, limits=limits)
        return obj
