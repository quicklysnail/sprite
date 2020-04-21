# -*- coding: utf-8 -*-
# @Time    : 2020-04-20 21:30
# @Author  : li
# @File    : base.py

from abc import abstractmethod
from sprite.utils.utils import SingletonMetaClass
from sprite import Request
from sprite.const import *


class BaseScheduler(metaclass=SingletonMetaClass):

    def __init__(self):
        # 一直都在单线程中运行，没有线程切换和协程切换的问题
        self._state = SCHEDULER_STOPPED

    @abstractmethod
    def start(self):
        """
        启动调度器
        :return:
        """

    @abstractmethod
    def stop(self):
        """
        停止调度器
        :return:
        """

    @abstractmethod
    def enqueue_request(self, crawler_name: 'str', request: 'Request'):
        """
        提取指定队列里面的request
        :param crawler_name:
        :param request:
        :return:
        """

    @abstractmethod
    def next_request(self, crawler_name: 'str') -> 'Request':
        """
        像指定队列上传request
        :param crawler_name:
        :return:
        """

    @abstractmethod
    def has_pending_requests(self, crawler_name: 'str') -> 'bool':
        """
        判断指定的队列是否还有request
        :param crawler_name:
        :return:
        """

    @abstractmethod
    def __len__(self) -> 'int':
        """
        返回调度器中所有队列现存的缓存request总数
        :return: int
        """


"""
正在处理的request数量统计
"""


class BaseSlot(metaclass=SingletonMetaClass):

    @abstractmethod
    def addRequest(self, crawler_name: 'str'):
        """
        新增一个正在处理的request
        :param request:
        :return:
        """

    @abstractmethod
    def getRequest(self, crawler_name: 'str'):
        """
        完成一个request，正在处理的request数量减一
        :return:
        """

    @abstractmethod
    def has_request(self, crawler_name: 'str') -> 'bool':
        """
        是否还存在正在处理的request
        :return:
        """

    @abstractmethod
    def __len__(self) -> 'int':
        """
        目前所有crawler正在处理的request的数量
        :return:
        """
    @abstractmethod
    def join(self):
        """
        如果存在正在处理的request则阻塞等待
        :return:
        """
