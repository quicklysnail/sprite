# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019-08-17 22:47'

import signal
import threading
import traceback
from typing import Callable
from sprite.utils.utils import SingletonMetaClass, Result, transformation_state_to_str
from sprite.utils.rpc import ThreadSpriteRPCServer
from sprite.utils.log import get_logger, set_logger
from sprite.utils.coroutinePool import coroutine_pool
from sprite.settings import Settings
from sprite.exceptions import UniqueCrawlerNameException
from sprite.middlewaremanager import MiddlewareManager
from sprite.spider import Spider
from sprite.core.engine import Engine

logger = get_logger()


class Crawler:
    __coroutine_pool__ = None

    def __init__(self, spider: Spider, middlewareManager: MiddlewareManager = None, settings: Settings = None,
                 coroutine_pool: 'PyCoroutinePool' = None):
        self.spider = spider
        self._settings = settings or Settings()
        self._settings.freeze()
        self._coroutine_pool = self.__coroutine_pool__ or coroutine_pool
        self._engine = Engine.from_settings(
            settings=self._settings, spider=self.spider, middlewareManager=middlewareManager,
            coroutine_pool=self._coroutine_pool)

    def _init(self):
        set_logger(self._settings)

    def run(self) -> bool:
        assert self._coroutine_pool is not None, "coroutine_pool is not init"
        if not self.is_stopped():
            return False
        self._engine.start()
        logger.info(f'启动[{self.get_crawler_name()}]')
        return True

    def close(self) -> bool:
        if not self.is_to_close():
            return False
        self._engine.close()
        logger.info(f'关闭crawler')
        return True

    def is_running(self) -> bool:
        return self._engine.is_running()

    def is_stopped(self):
        return self._engine.is_stopped()

    def is_to_close(self):
        return self._engine.is_to_close()

    def get_crawler_name(self) -> str:
        return self.spider.name

    def get_crawler_state(self):
        return transformation_state_to_str(self._engine.state)

    def set_coroutine_pool(self, coroutine_pool: 'PyCoroutinePool'):
        self._coroutine_pool = coroutine_pool

    def set_settings(self, settings: Settings):
        self._settings = settings


class CrawlerRunner(metaclass=SingletonMetaClass):
    __crawlers__ = {}
    __unique_name_crawler = set()
    __coroutine_pool__ = coroutine_pool  # 使用默认配置实例化的协程池对象

    def __init__(self, settings: 'Settings' = None):
        self._settings = settings or Settings()
        self._settings.freeze()
        self._rpc_server = ThreadSpriteRPCServer(
            (self._settings.get("SERVER_IP"), self._settings.getint("SERVER_PORT"),))
        self._running_event = threading.Event()
        self._crawler_manager_lock = threading.Lock()
        self._init()

    def _init(self):
        set_logger(self._settings)
        self.reset_coroutine_pool()
        self._register_rpc()

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

    def _stop_server(self) -> str:
        if not self._running_event.is_set():
            to_close_crawler_name = self.close_all_crawler()
            logger.info(f'to close crawler: {",".join(to_close_crawler_name)}')
            stopped_crawler_name = self.get_stopped_crawler_name()
            if len(self.__unique_name_crawler) - len(stopped_crawler_name) != len(to_close_crawler_name):
                result = Result("failed", data="has crawler not must stop").serialize()
            else:
                self._running_event.set()
                self._rpc_server.shutdown()  # 关闭rpc服务
                self.stop_coroutine_pool()
                result = Result("ok", data=to_close_crawler_name).serialize()
        else:
            result = Result("failed", data="crawler_runner is not running").serialize()
        return result

    def _close(self, signal_num: int, frame):
        if not self._running_event.is_set():
            to_close_crawler_name = self.close_all_crawler()
            logger.info(f'to close crawler: {",".join(to_close_crawler_name)}')
            stopped_crawler_name = self.get_stopped_crawler_name()
            if len(self.__unique_name_crawler) - len(stopped_crawler_name) == len(to_close_crawler_name):
                self._running_event.set()
                self._rpc_server.shutdown()  # 关闭rpc服务
                self.stop_coroutine_pool()

    def start(self):
        if not self._running_event.is_set():
            logger.info("server start")
            self.start_coroutine_pool()
            signal.signal(signal.SIGTERM, self._close)  # SIGTERM 关闭程序信号
            signal.signal(signal.SIGINT, self._close)  # 接收ctrl+c 信号
            self._running_event.wait()  # 主线程阻塞等待

    def _run_crawler(self, crawl_name) -> str:
        with self._crawler_manager_lock:
            crawler = self.__crawlers__.get(crawl_name, None)
            if crawler:
                if crawler.is_stopped():
                    crawler.run()
                    result = Result("ok", data=crawl_name).serialize()
                else:
                    result = Result("failed", data="crawler is running").serialize()
            else:
                result = Result("failed", data="not fund this crawler").serialize()
        return result

    def _run_all_crawler(self) -> str:
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
                if crawler.is_to_close():
                    crawler.close()
                    result = Result("ok", data=crawler_name).serialize()
                else:
                    result = Result("failed", data="crawler is not running").serialize()
            else:
                result = Result("failed", data="not fund this crawler").serialize()
            return result

    def _close_all_crawler(self) -> str:
        to_close_crawler = []
        for crawler in self.__crawlers__.values():
            if crawler.is_to_close():
                to_close_crawler.append(crawler.get_crawler_name())
                crawler.close()
        return Result("ok", data=to_close_crawler).serialize()

    def close_all_crawler(self) -> list:
        to_close_crawler = []
        for crawler in self.__crawlers__.values():
            if crawler.is_to_close():
                to_close_crawler.append(crawler.get_crawler_name())
                crawler.close()
        return to_close_crawler

    def _get_all_crawler_name(self) -> str:
        return Result("ok", data=list(self.__crawlers__.keys())).serialize()

    def _get_crawler_state(self, crawler_name: str):
        crawler = self.__crawlers__.get(crawler_name, None)
        if crawler:
            result = Result("ok", data=crawler.get_crawler_state()).serialize()
        else:
            result = Result("failed", data="not fund this crawler").serialize()
        return result

    def _get_running_crawler_name(self) -> str:
        running_crawler = []
        for crawler in self.__crawlers__.values():
            if crawler.is_running():
                running_crawler.append(crawler.get_crawler_name())
        return Result("ok", data=running_crawler).serialize()

    def get_stopped_crawler_name(self) -> list:
        stopped_crawler = []
        for crawler in self.__crawlers__.values():
            if crawler.is_stopped():
                stopped_crawler.append(crawler.get_crawler_name())
        return stopped_crawler

    def _get_coroutine_pool_state(self):
        return Result("ok", data=transformation_state_to_str(self.__coroutine_pool__.state)).serialize()

    def stop_coroutine_pool(self):
        self.__coroutine_pool__.stop()

    def start_coroutine_pool(self):
        self.__coroutine_pool__.start()

    def reset_coroutine_pool(self):
        self.__coroutine_pool__.reset(
            max_coroutine_amount=self._settings.getint("MAX_COROUTINE_AMOUNT"),
            max_coroutineIdle_time=self._settings.getint("MAX_COROUTINE_IDLE_TIME"),
            most_stop=self._settings.getbool("MOST_STOP")
        )

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
        assert isinstance(crawler, Crawler), "must is Crawler instance"
        if crawler.get_crawler_name() in cls.__unique_name_crawler:
            raise UniqueCrawlerNameException("存在重名的crawler")
        cls.__unique_name_crawler.add(crawler.get_crawler_name())
        cls.__crawlers__[crawler.get_crawler_name()] = crawler
        crawler.set_coroutine_pool(cls.__coroutine_pool__)
