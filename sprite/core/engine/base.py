# -*- coding: utf-8 -*-
# @Time    : 2020-04-20 23:39
# @Author  : li
# @File    : base.py

from threading import Lock
from asyncio import Event
from abc import abstractmethod
from sprite.const import ENGINE_STATE_STOPPED
from sprite.core.scheduler.base import BaseScheduler, BaseSlot
from sprite.core.download.base import BaseDownloader
from sprite.settings import Settings
from sprite.middleware.middlewaremanager import MiddlewareManager
from sprite.spider import Spider
from sprite.utils.request import BaseCrawlerCounter


class BaseEngine:

    def __init__(self, id: 'int', spider: 'Spider', downloader: 'BaseDownloader', scheduler: 'BaseScheduler',
                 middleware_manager: 'MiddlewareManager', slot: 'BaseSlot', settings: 'Settings',
                 crawler_counter: 'BaseCrawlerCounter'):
        self._crawler_name = spider.name
        self._id = id

        self._settings = settings

        self._state = ENGINE_STATE_STOPPED
        self._state_signal = Event()

        # 引擎组件
        self._spider = spider
        self._middleware_manager = middleware_manager
        self._downloader = downloader
        self._crawler_counter = crawler_counter

        self._slot = slot
        self._scheduler = scheduler

    @abstractmethod
    async def run(self):
        """
        运行引擎
        """

    @abstractmethod
    def stop(self):
        """
        停止引擎
        """

    @abstractmethod
    def pause(self):
        """
        暂停引擎
        :return:
        """

    @abstractmethod
    def reduction(self):
        """
        恢复运行引擎
        :return:
        """
