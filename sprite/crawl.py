# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019-08-17 22:47'

import signal
import threading
import traceback
import os
import time
import inspect
from threading import Thread
from typing import Callable
from sprite.utils.utils import SingletonMetaClass, Result, transformation_state_to_str, ClassLoader
from sprite.utils.rpc import ThreadSpriteRPCServer
from sprite.utils.log import get_logger, set_logger
from sprite.utils.coroutinepool import coroutine_pool, PyCoroutinePool
from sprite.settings import Settings
from sprite.exceptions import UniqueCrawlerNameException
from sprite.middleware.middlewaremanager import MiddlewareManager
from sprite.spider import Spider
from sprite.utils.http.request import Request
from sprite.core.scheduler.memory import MemoryScheduler, MemorySlot
from sprite.core.engine.coroutine import CoroutineEngine
from sprite.core.scheduler.base import BaseScheduler, BaseSlot
from sprite.core.download.base import BaseDownloader
from sprite.core.download.coroutine import CoroutineDownloader
from sprite.utils.request import MemoryCrawlerCounter
from sprite.const import *

logger = get_logger()


class Crawler:
    def __init__(self, spider: 'Spider', middleware_manager: 'MiddlewareManager' = None,
                 settings: 'Settings' = None, singleton: 'bool' = True):
        self._spider = spider
        self._settings = settings
        self._coroutine_pool = coroutine_pool
        self._middleware_manager = middleware_manager

        self._engines = []
        self._engines_task = []

        self._crawler_counter = None

        self._coroutine_pool = None
        self._slot = None
        self._scheduler = None
        self._downloader = None

        self._singleton = singleton

    def _init_component(self):
        """
        组装crawler实例的所有所需组件
        :return:
        """
        self._check_component()
        self._crawler_counter = MemoryCrawlerCounter(
            item_counter_unit=self._settings.getint("ITEM_COUNTER_UNIT"),
            response_counter_unit=self._settings.getint("RESPONSE_COUNTER_UNIT")
        )
        self._engines = [
            CoroutineEngine(
                self._spider, self._downloader, self._scheduler, self._middleware_manager, self._slot,
                self._settings, self._crawler_counter
            )
            for _ in range(self._settings.getint("ITEM_COUNTER_UNIT"))
        ]

    def _init_start_request(self):
        if self._spider.start_requests:
            for url in self._spider.start_requests:
                self._scheduler.enqueue_request(self._spider.name, Request(url=url, callback=self._spider.parse))
        else:
            assert not inspect.iscoroutinefunction(self._spider.start_request), "start_request must is normal method"
            for request in self._spider.start_request():
                assert isinstance(request, Request), "call start_request method receive no Request instance"
                self._scheduler.enqueue_request(self._spider.name, request)

    def get_crawler_name(self) -> str:
        return self._spider.name

    def get_crawler_state(self) -> 'str':
        pass

    def is_running(self) -> 'bool':
        result = True
        for engine in self._engines:
            if engine.state == ENGINE_STATE_RUNNING:
                result = False
                break
        return result

    def is_paused(self) -> bool:
        result = True
        for engine in self._engines:
            if engine.state == ENGINE_STATE_PAUSE:
                result = False
                break
        return result

    def is_stopped(self):
        result = True
        for engine in self._engines:
            if engine.state != ENGINE_STATE_STOPPED:
                result = False
                break
        return result

    def run(self):
        if len(self._engines_task) != 0:
            return
        self._init_component()
        self._init_start_request()
        try:
            self._engines_task = [
                self._coroutine_pool.go(engine.run(), engine.stop)
                for engine in self._engines
            ]
        except:
            logger.error(f'run engine find error: \n{traceback.format_exc()}')

    def stop(self):
        try:
            for engine_task, engine in zip(self._engines_task, self._engines):
                if engine.state not in [ENGINE_STATE_RUNNING, ENGINE_STATE_PAUSE]:
                    continue
                if engine_task.cancelled():
                    continue
                engine_task.cancel()
        except:
            logger.error(f'stop engine find error: \n{traceback.format_exc()}')
        try:
            if self._singleton:
                self._coroutine_pool.stop()
                self._scheduler.stop()
        except:
            logger.error(f'stop public component find error: \n{traceback.format_exc()}')

    def pause(self):
        try:
            for engine in self._engines:
                engine.pause()
        except:
            logger.error(f'pause engine find error: \n{traceback.format_exc()}')

    def reduction(self):
        try:
            for engine in self._engines:
                engine.reduction()
        except:
            logger.error(f'reduction engine find error: \n{traceback.format_exc()}')

    def replenish_component(self, settings: 'Settings', coroutine_pool: 'PyCoroutinePool', slot: 'BaseSlot',
                            scheduler: 'BaseScheduler', downloader: 'BaseDownloader'):
        """
        # 用全局组件补充crawler的关键组件
        :param coroutine_pool:
        :param slot:
        :param settings:
        :param scheduler:
        :return:
        """
        # settings
        if not settings:
            self._settings = settings
        # scheduler
        if not self._scheduler:
            self._scheduler = scheduler
        # slot
        if not self._settings:
            self._settings = slot
        # coroutine_pool
        if not self._coroutine_pool:
            self._coroutine_pool = coroutine_pool
        # downloader
        if not self._downloader:
            self._downloader = downloader
        self._singleton = False

    def _check_component(self):
        """
        检查crawler组件是否装配完成，没有完成自动生成默认组件
        :return:
        """
        # settings
        if not self._settings:
            self._settings = Settings()
            set_logger(self._settings)
        # middleware
        if not self._middleware_manager:
            self._middleware_manager = MiddlewareManager()
        # slot
        if not self._slot:
            self._slot = MemorySlot()
        # scheduler
        if not self._scheduler:
            self._scheduler = MemoryScheduler()
            self._scheduler.start()
        # coroutine_pool
        if not self._coroutine_pool:
            self._coroutine_pool = PyCoroutinePool(
                max_coroutine_amount=self._settings.getint("MAX_COROUTINE_AMOUNT"),
                max_coroutineIdle_time=self._settings.getint("MAX_COROUTINE_IDLE_TIME"),
                most_stop=self._settings.getbool("MOST_STOP")
            )
            self._coroutine_pool.start()
        # downloader
        if not self._downloader:
            self._downloader = CoroutineDownloader(self._settings)


class CrawlerManager:
    __crawlers__ = {}
    __unique_name_crawler = set()

    def __int__(self, *args, **kwargs):
        pass

    @classmethod
    @property
    def crawlers(cls):
        return cls.__crawlers__

    @classmethod
    @property
    def unique_name_crawler(cls):
        return cls.__unique_name_crawler

    @classmethod
    def add_crawler(cls, *args, **kwargs):
        if len(args) > 0:
            get_crawler_func = args[0]
            cls.without_params_get_crawler_func(get_crawler_func)
        return cls.has_params_get_crawler_func(**kwargs)

    @classmethod
    def without_params_get_crawler_func(cls, func: Callable):
        try:
            crawler = func()
            cls._add_crawler(crawler)
        except:
            logger.error(f'add crawler failed: \n{traceback.format_exc()}')

    @classmethod
    def has_params_get_crawler_func(cls, **kwargs):
        def _wrap_get_crawler(func: Callable):
            try:
                crawler = func()
                cls._add_crawler(crawler)
            except:
                logger.error(f'add crawler failed: \n{traceback.format_exc()}')

        return _wrap_get_crawler

    @classmethod
    def _add_crawler(cls, crawler: 'Crawler'):
        crawler_name = crawler.get_crawler_name()
        assert isinstance(crawler, Crawler), f'{crawler_name} is not Crawler instance'
        if crawler_name in cls.__unique_name_crawler:
            raise UniqueCrawlerNameException("存在重名的crawler")
        cls.__unique_name_crawler.add(crawler_name)
        cls.__crawlers__[crawler_name] = crawler

    @classmethod
    def get_all_crawler_name(cls):
        return cls.__unique_name_crawler

    @classmethod
    def get_all_crawler(cls):
        return cls.__crawlers__


class CrawlerLoader(Thread):
    def __init__(self, crawler_manage_path: str, crawler_runner: 'CrawlerRunner', env="dev"):
        self.__crawler_manage_path = crawler_manage_path
        self.__crawler_runner = crawler_runner
        self.__env = env
        self.__root_dir = os.getcwd()
        self.__class_loader__ = None
        self.__init()
        super(CrawlerLoader, self).__init__()

    def __init(self):
        self.__class_loader__ = ClassLoader(CrawlerManager, self.__root_dir)

    def run(self) -> None:
        while True:
            self.load_crawler()
            if self.__env == ENV_PRODUCT:
                break
            time.sleep(THREAD_SLEEP_TIME)

    def load_crawler(self):
        try:
            self.__class_loader__.load_from_file(self.__crawler_manage_path)
            current_crawlers = {}
            for crawler_manager_class_object in self.__class_loader__.class_object.values():
                current_crawlers.update(crawler_manager_class_object.get_all_crawler())
            self.__crawler_runner.update_crawler(current_crawlers)
            self.__class_loader__.clear()
        except Exception:
            logger.error(f'load crawler find one error: \n{traceback.format_exc()}')


class CrawlerRunner(metaclass=SingletonMetaClass):
    __crawlers__ = {}
    __unique_name_crawler = set()

    def __init__(self, settings: 'Settings' = None, crawler_manage_path: str = "crawlerdefine",
                 coroutine_pool: 'PyCoroutinePool' = None, slot: 'BaseSlot' = None,
                 scheduler: 'BaseScheduler' = None, downloader: 'BaseDownloader' = None):
        self._settings = settings or Settings()
        self._env = "dev"
        self._crawler_manage_path = crawler_manage_path
        self._running_event = threading.Event()
        self._crawler_manager_lock = threading.Lock()
        self._rpc_server = None
        self._crawler_loader = None
        self._coroutine_pool = coroutine_pool
        self._slot = slot
        self._scheduler = scheduler
        self._downloader = downloader

    def _init(self):
        assert isinstance(self._settings, Settings), "settings must Settings instance"
        self._settings.freeze()
        set_logger(self._settings)
        self._rpc_server = ThreadSpriteRPCServer(
            (self._settings.get("SERVER_IP"), self._settings.getint("SERVER_PORT"),))
        self._crawler_loader = CrawlerLoader(self._crawler_manage_path, self, self._env)
        self._register_rpc()
        self._env = self._settings.get('ENV')

        # slot
        if not self._slot:
            self._slot = MemorySlot()
        # scheduler
        if not self._scheduler:
            self._scheduler = MemoryScheduler()
            self._scheduler.start()
        # coroutine_pool
        if not self._coroutine_pool:
            self._coroutine_pool = PyCoroutinePool(
                max_coroutine_amount=self._settings.getint("MAX_COROUTINE_AMOUNT"),
                max_coroutineIdle_time=self._settings.getint("MAX_COROUTINE_IDLE_TIME"),
                most_stop=self._settings.getbool("MOST_STOP")
            )
            self._coroutine_pool.start()
        # downloader
        if not self._downloader:
            self._downloader = CoroutineDownloader(self._settings)

    def _register_rpc(self):
        self._rpc_server.register_function(self._run_crawler, "run_crawler")
        self._rpc_server.register_function(self._run_all_crawler, "run_all_crawler")
        self._rpc_server.register_function(self._close_crawl, "close_crawl")
        self._rpc_server.register_function(self._close_all_crawler, "close_all_crawler")
        self._rpc_server.register_function(self._get_all_crawler_name, "get_all_crawler_name")
        self._rpc_server.register_function(self._get_running_crawler_name, "get_running_crawler_name")
        self._rpc_server.register_function(self._get_crawler_state, "get_crawler_state")
        self._rpc_server.register_function(self._get_coroutine_pool_state, "get_coroutine_pool_state")
        self._rpc_server.register_function(self._stop_server, "stop_server")
        self._rpc_server.register_function(self._reload_crawler, "reload_crawler")

    def _stop_server(self) -> str:
        if not self._running_event.is_set():
            to_close_crawler_name = self.close_all_crawler()
            logger.info(f'to close crawler: {",".join(to_close_crawler_name)}')
            stopped_crawler_name = self.get_stopped_crawler_name()
            if len(self.__unique_name_crawler) - len(stopped_crawler_name) != len(to_close_crawler_name):
                result = Result("failed", data="has crawler not to be stop")
            else:
                self._running_event.set()
                self._rpc_server.shutdown()  # 关闭rpc服务
                self._scheduler.stop()
                self._coroutine_pool.stop()

                self._running_event.clear()
                result = Result("ok", data=to_close_crawler_name)
        else:
            result = Result("failed", data="crawler_runner is not running")
        return result.serialize()

    def _close(self, signal_num: int, frame):
        with self._crawler_manager_lock:
            if not self._running_event.is_set():
                to_close_crawler_name = self.close_all_crawler()
                logger.info(f'to close crawler: {",".join(to_close_crawler_name)}')
                stopped_crawler_name = self.get_stopped_crawler_name()
                if len(self.__unique_name_crawler) - len(stopped_crawler_name) == len(to_close_crawler_name):
                    self._running_event.set()
                    self._rpc_server.shutdown()  # 关闭rpc服务
                    self._scheduler.stop()
                    self._coroutine_pool.stop()

                    self._running_event.clear()

    def start(self):
        if not self._running_event.is_set():
            self._init()
            # self._crawler_loader.run()
            self._crawler_loader.load_crawler()
            logger.info("server start")
            signal.signal(signal.SIGTERM, self._close)  # SIGTERM 关闭程序信号
            signal.signal(signal.SIGINT, self._close)  # 接收ctrl+c 信号
            self._running_event.wait()  # 主线程阻塞等待

    def _run_crawler(self, crawl_name) -> str:
        with self._crawler_manager_lock:
            crawler = self.__crawlers__.get(crawl_name, None)
            if crawler:
                if crawler.is_stopped():
                    crawler.run()
                    result = Result("ok", data=crawl_name)
                else:
                    result = Result("failed", data="crawler is running")
            else:
                result = Result("failed", data="not fund this crawler")
        return result.serialize()

    def _run_all_crawler(self) -> str:
        with self._crawler_manager_lock:
            to_run_crawler = []
            with self._crawler_manager_lock:
                for crawler in self.__crawlers__.values():
                    if crawler.is_stopped():
                        to_run_crawler.append(crawler.get_crawler_name())
                        crawler.run()
            return Result("ok", data=to_run_crawler).serialize()

    def _close_crawl(self, crawler_name) -> str:
        with self._crawler_manager_lock:
            crawler = self.__crawlers__.get(crawler_name, None)
            if crawler:
                if crawler.is_running() or crawler.is_paused():
                    crawler.close()
                    result = Result("ok", data=crawler_name)
                else:
                    result = Result("failed", data="crawler is not running")
            else:
                result = Result("failed", data="not fund this crawler")
            return result.serialize()

    def _close_all_crawler(self) -> str:
        with self._crawler_manager_lock:
            to_close_crawler = []
            with self._crawler_manager_lock:
                for crawler in self.__crawlers__.values():
                    if crawler.is_running() or crawler.is_paused():
                        to_close_crawler.append(crawler.get_crawler_name())
                        crawler.stop()
                return Result("ok", data=to_close_crawler).serialize()

    def close_all_crawler(self) -> list:
        to_close_crawler = []
        for crawler in self.__crawlers__.values():
            if crawler.is_running() or crawler.is_paused():
                to_close_crawler.append(crawler.get_crawler_name())
                crawler.stop()
        return to_close_crawler

    def _get_all_crawler_name(self) -> str:
        with self._crawler_manager_lock:
            return Result("ok", data=list(self.__crawlers__.keys())).serialize()

    def _get_crawler_state(self, crawler_name: str) -> str:
        with self._crawler_manager_lock:
            crawler = self.__crawlers__.get(crawler_name, None)
            if crawler:
                result = Result("ok", data=crawler.get_crawler_state())
            else:
                result = Result("failed", data="not fund this crawler")
            return result.serialize()

    def _get_running_crawler_name(self) -> str:
        with self._crawler_manager_lock:
            running_crawler = []
            for crawler in self.__crawlers__.values():
                if crawler.is_running():
                    running_crawler.append(crawler.get_crawler_name())
            return Result("ok", data=running_crawler).serialize()

    def _get_coroutine_pool_state(self) -> str:
        with self._crawler_manager_lock:
            return Result("ok", data=transformation_state_to_str(self._coroutine_pool.state)).serialize()

    def _reload_crawler(self) -> str:
        if self._env == ENV_DEV:
            result = Result("failed", data="dev env is auto reload crawler")
        else:
            try:
                self._crawler_loader.load_crawler()
                result = Result("ok", data="reload success")
            except Exception:
                result = Result('failed', data=f'at reload fund one error: \n{traceback.format_exc()}')
        return result.serialize()

    def update_crawler(self, crawlers: dict):
        with self._crawler_manager_lock:
            for name, crawler in crawlers.items():
                if name in self.__unique_name_crawler:
                    """
                    更新名称相同的crawler
                    如果原先的crawler处于stopped状态，则可以更新，否则日志提醒，无法更新，需手动暂停原先的crawler
                    """
                    if self.__crawlers__[name].is_stopped():
                        self.__update_crawler(name, crawler)
                    else:
                        logger.error(
                            'exist the same name of crawler and old crawler is not stopped, not update this crawler')
                else:
                    self.__update_crawler(name, crawler)

    def __update_crawler(self, name: str, crawler: 'Crawler'):
        crawler.replenish_component(self._settings, self._coroutine_pool, self._slot,
                                    self._scheduler, self._downloader)
        self.__crawlers__[name] = crawler
        self.__unique_name_crawler.add(name)
        if self._env == ENV_PRODUCT:
            logger.debug(f'update {name} crawler')

    def get_stopped_crawler_name(self) -> list:
        stopped_crawler = []
        for crawler in self.__crawlers__.values():
            if crawler.is_stopped():
                stopped_crawler.append(crawler.get_crawler_name())
        return stopped_crawler

    @classmethod
    def get_all_crawler(cls):
        return list(cls.__unique_name_crawler)
