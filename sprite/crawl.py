# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019-08-17 22:47'

import signal
import threading
import traceback
import os
import time
from threading import Thread
from typing import Callable
from sprite.utils.utils import SingletonMetaClass, Result, transformation_state_to_str, ClassLoader
from sprite.utils.rpc import ThreadSpriteRPCServer
from sprite.utils.log import get_logger, set_logger
from sprite.utils.coroutinePool import coroutine_pool, PyCoroutinePool
from sprite.settings import Settings
from sprite.exceptions import UniqueCrawlerNameException
from sprite.middlewaremanager import MiddlewareManager
from sprite.spider import Spider
from sprite.core.engine import Engine
from sprite.const import *

logger = get_logger()


class Crawler:
    def __init__(self, spider: Spider, middlewareManager: MiddlewareManager = None, settings: Settings = None,
                 coroutine_pool: 'PyCoroutinePool' = None):
        self._settings = settings
        self._coroutine_pool = coroutine_pool
        self._spider = spider
        self._middlewareManager = middlewareManager
        self._engine = None  # spider 和 middlewareManager属于配置对象，可以不需要重置后使用

    def _init(self):
        assert isinstance(self._spider, Spider), "spider must Spider subclass"
        assert isinstance(self._settings, Settings), "settings must Settings instance"
        assert isinstance(self._middlewareManager,
                          MiddlewareManager), "middlewareManager must MiddlewareManager instance"
        assert self._coroutine_pool is not None, "coroutine_pool is not init"
        assert isinstance(self._coroutine_pool, PyCoroutinePool), "coroutine_pool must PyCoroutinePool instance"
        self._settings.freeze()
        set_logger(self._settings)
        self._engine = Engine.from_settings(
            settings=self._settings, spider=self._spider,
            middlewareManager=self._middlewareManager,
            coroutine_pool=self._coroutine_pool)

    def run(self) -> bool:
        if self._engine:
            return False
        # 重新创建新的engine实例
        self._init()
        self._engine.start()
        logger.info(f'启动[{self.get_crawler_name()}]')
        return True

    def close(self) -> bool:
        if not self._engine:
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
        return self._spider.name

    def get_crawler_state(self):
        return transformation_state_to_str(self._engine.state)

    def set_coroutine_pool(self, coroutine_pool: 'PyCoroutinePool'):
        self._coroutine_pool = coroutine_pool

    def set_settings(self, settings: Settings):
        if self._settings is None:
            self._settings = settings


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
        assert isinstance(crawler, Crawler), "must is Crawler instance"
        if crawler.get_crawler_name() in cls.__unique_name_crawler:
            raise UniqueCrawlerNameException("存在重名的crawler")
        cls.__unique_name_crawler.add(crawler.get_crawler_name())
        cls.__crawlers__[crawler.get_crawler_name()] = crawler

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
        super(CrawlerLoader, self).__init__()

    def __init(self):
        self.__class_loader__ = ClassLoader(CrawlerManager, self.__root_dir)

    def run(self) -> None:
        self.__init()
        while True:
            try:
                self.load_crawler()
            except Exception:
                logger.error(f'load crawler find one error: \n{traceback.format_exc()}')
            if self.__env == ENV_PRODUCT:
                break
            time.sleep(THREAD_SLEEP_TIME)

    def load_crawler(self):
        self.__class_loader__.load_from_file(self.__crawler_manage_path)
        current_crawlers = {}
        for _, crawler_manager_class_object in self.__class_loader__.class_object.items():
            current_crawlers.update(crawler_manager_class_object.get_all_crawler())
        self.__crawler_runner.update_crawler(current_crawlers)
        self.__class_loader__.clear()


class CrawlerRunner(metaclass=SingletonMetaClass):
    __crawlers__ = {}
    __unique_name_crawler = set()
    __coroutine_pool__ = coroutine_pool  # 使用默认配置实例化的协程池对象

    def __init__(self, settings: 'Settings' = None, crawler_manage_path: str = "crawlerdefine"):
        self._settings = settings or Settings()
        self._env = "dev"
        self._crawler_manage_path = crawler_manage_path
        self._running_event = threading.Event()
        self._crawler_manager_lock = threading.Lock()
        self._rpc_server = None
        self._crawler_loader = None

    def _init(self):
        assert isinstance(self._settings, Settings), "settings must Settings instance"
        self._settings.freeze()
        self._env = self._settings.get('ENV')
        set_logger(self._settings)
        self._rpc_server = ThreadSpriteRPCServer(
            (self._settings.get("SERVER_IP"), self._settings.getint("SERVER_PORT"),))
        self._crawler_loader = CrawlerLoader(self._crawler_manage_path, self, self._env)
        self.reset_coroutine_pool()
        self._register_rpc()

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
        crawler.set_coroutine_pool(self.__coroutine_pool__)
        crawler.set_settings(self._settings)
        self.__crawlers__[name] = crawler
        self.__unique_name_crawler.add(name)
        logger.debug(f'update {name} crawler')

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
                result = Result("failed", data="has crawler not must stop")
            else:
                self._running_event.set()
                self._rpc_server.shutdown()  # 关闭rpc服务
                self.stop_coroutine_pool()
                self._running_event.clear()
                result = Result("ok", data=to_close_crawler_name)
        else:
            result = Result("failed", data="crawler_runner is not running")
        return result.serialize()

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
            self._init()
            self.start_coroutine_pool()
            self._crawler_loader.run()
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
                    result = Result("ok", data=crawler_name)
                else:
                    result = Result("failed", data="crawler is not running")
            else:
                result = Result("failed", data="not fund this crawler")
            return result.serialize()

    def _close_all_crawler(self) -> str:
        to_close_crawler = []
        with self._crawler_manager_lock:
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
        with self._crawler_manager_lock:
            return Result("ok", data=list(self.__crawlers__.keys())).serialize()

    def _get_crawler_state(self, crawler_name: str) -> str:
        crawler = self.__crawlers__.get(crawler_name, None)
        if crawler:
            result = Result("ok", data=crawler.get_crawler_state())
        else:
            result = Result("failed", data="not fund this crawler")
        return result.serialize()

    def _get_running_crawler_name(self) -> str:
        running_crawler = []
        for crawler in self.__crawlers__.values():
            if crawler.is_running():
                running_crawler.append(crawler.get_crawler_name())
        return Result("ok", data=running_crawler).serialize()

    def _get_coroutine_pool_state(self) -> str:
        return Result("ok", data=transformation_state_to_str(self.__coroutine_pool__.state)).serialize()

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

    def get_stopped_crawler_name(self) -> list:
        stopped_crawler = []
        for crawler in self.__crawlers__.values():
            if crawler.is_stopped():
                stopped_crawler.append(crawler.get_crawler_name())
        return stopped_crawler

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
    def get_all_crawler(cls):
        return list(cls.__unique_name_crawler)
