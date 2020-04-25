# -*- coding: utf-8 -*-
# @Time    : 2020-04-20 22:19
# @Author  : li
# @File    : memory.py

from asyncio import Event
from collections import defaultdict
from sprite.core.scheduler.base import BaseScheduler
from sprite.utils.queues import PriorityQueue, Queue
from sprite.utils.pybloomfilter import ScalableBloomFilter
from sprite.settings import Settings
from sprite import Request
from sprite.const import SCHEDULER_STOPPED, SCHEDULER_RUNNING
from sprite.exceptions import NotUniqueRequestException, RequestQueueNotExistException, RequestQueueEmptyException


class MemoryScheduler(BaseScheduler):

    def __init__(self, settings: 'Settings'):
        self._settings = settings
        self._store = None
        self._df = None
        super(MemoryScheduler, self).__init__()

    def _init(self):
        self._store = defaultdict(PriorityQueue)
        initial_capacity = self._settings.get("INITIAL_CAPACITY")
        error_rate = self._settings.getfloat("ERROR_RATE")
        self._df = ScalableBloomFilter(initial_capacity, error_rate)

    def start(self):
        assert self._state != SCHEDULER_STOPPED, "scheduler not stopped"
        self._init()
        self._state = SCHEDULER_RUNNING

    def stop(self):
        assert self._state != SCHEDULER_STOPPED, "scheduler not running"
        self._state = SCHEDULER_STOPPED

    def enqueue_request(self, crawler_name: 'str', request: 'Request'):
        assert self._state != SCHEDULER_STOPPED, "scheduler not running"
        unique_request = request.toUniqueStr()
        if unique_request in self._df:
            raise NotUniqueRequestException("request is repeat")
        self._df.add(unique_request)
        self._store[crawler_name].push(request, request.priority)

    def next_request(self, crawler_name: 'str') -> 'Request':
        assert self._state != SCHEDULER_STOPPED, "scheduler not running"
        request_queue = self._store.get(crawler_name, None)
        if request_queue is None:
            raise RequestQueueNotExistException("request queue is no exist")
        try:
            request, _ = request_queue.pop()
        except IndexError:
            # 队列为空
            raise RequestQueueEmptyException("request queue is empty")
        return request

    def has_pending_requests(self, crawler_name: 'str') -> 'bool':
        request_list = self._store.get(crawler_name, None)
        if request_list is None:
            raise RequestQueueNotExistException("request queue is no exist")
        if len(request_list) == 0:
            return False
        return True

    def __len__(self) -> int:
        length = 0
        for _, request_queue in self._store.items():
            length = length + len(request_queue)
        return length


class MemorySlot:
    def __init__(self):
        self._state_signal = defaultdict(Event)
        self.__processing_request = defaultdict(int)

    def addRequest(self, crawler_name: 'str'):
        """
        新增一个正在处理的request
        :param request:
        :return:
        """
        self.__processing_request[crawler_name] += 1

    def getRequest(self, crawler_name: 'str'):
        """
        完成一个request，正在处理的request数量减一
        :return:
        """
        if self.__processing_request[crawler_name] <= 0:
            raise Exception("not more many request to consume")
        self.__processing_request[crawler_name] -= 1
        if self.__processing_request[crawler_name] <= 0:
            self._state_signal[crawler_name].set()

    def has_request(self, crawler_name: 'str') -> 'bool':
        """
        是否还存在正在处理的request
        :return:
        """
        return True if self.__processing_request[crawler_name] > 0 else False

    def __len__(self) -> 'int':
        """
        目前所有crawler正在处理的request的数量
        :return:
        """
        num = 0
        for request_num in self.__processing_request.values():
            num = num + request_num
        return num

    async def join(self, crawler_name: 'str'):
        """
        如果存在正在处理的request则阻塞等待
        :return:
        """
        await self._state_signal[crawler_name].wait()
