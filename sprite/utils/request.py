# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019-08-17 22:00'

import time
from typing import Dict, Callable
from abc import abstractmethod
from collections import deque
from sprite.utils.http.request import Request
from sprite.exceptions import TypeNotSupport
from sprite.utils.utils import SingletonMetaClass


def request_to_dict(request: Request) -> Dict:
    if not isinstance(request, Request):
        raise TypeNotSupport("不能转换类型非Request的实例为字典！")
    d = {
        'url': request.url,
        'callback': request.callback.__name__,
        'method': request.method,
        'headers': dict(request.headers),
        'cookies': request.cookies,
        'meta': request.meta,
        '_encoding': request._encoding,
        'priority': request.priority,
        'dont_filter': request.dont_filter,
    }

    return d


def request_from_dict(spider: "Spider", d: Dict) -> Request:
    if not isinstance(d, Dict):
        raise TypeNotSupport("不能转换类型非字典对象为Request实例")
    return Request(
        url=d["url"],
        callback=_get_method(spider, d["callback"]),
        method=d['method'],
        headers=d['headers'],
        cookies=d['cookies'],
        meta=d['meta'],
        encoding=d['_encoding'],
        priority=d['priority'],
        dont_filter=d['dont_filter'])


def _get_method(obj, method_name: str) -> Callable:
    try:
        return getattr(obj, method_name)
    except AttributeError:
        raise ValueError(f'method {method_name} not found in {obj}')


class Counter:
    def __init__(self, unit: int = 60):
        self._first_time: float = time.time()
        self._first_count = 0
        self._travel_record = deque()
        self._count = 0
        self._unit = unit

    def dot(self) -> [int, int]:
        speed = None
        unit_count = None

        now = time.time()
        passed = now - self._first_time
        self._count += 1
        if passed < self._unit:
            self._travel_record.append((now, self._count))
        else:
            speed, unit_count = self._getUintSpedd(), self._getUintCount()
            # 更新单位时间点的数据
            self._first_time, self._first_count = now - \
                                                  (now - self._unit), self._count
            # 清空上个单位时间段的记录
            self._travel_record.clear()
            # 记录这个时间段的第一笔数据
            self._travel_record.append((now, self._count))
        return speed, unit_count

    def _getUintSpedd(self) -> float:
        try:
            _, last_count = self._travel_record[-1]
            return (last_count - self._first_count) / self._unit
        except IndexError:
            return 0

    def _getUintCount(self) -> int:
        try:
            _, last_count = self._travel_record[-1]
            return last_count - self._first_count
        except IndexError:
            return 0

    @property
    def unit(self) -> int:
        return self._unit


class BaseCrawlerCounter(metaclass=SingletonMetaClass):

    @abstractmethod
    def run(self):
        """
        运行crawl计数器
        :return:
        """

    @abstractmethod
    def recorded_success_request(self):
        """
        记录一个处理成功的request
        :return:
        """

    @abstractmethod
    def recorded_failed_request(self):
        """
        记录失败的request
        :return:
        """

    @abstractmethod
    def item_dot(self) -> [int, int]:
        """
        统计单位时间item获取的情况
        :return:
        """

    @abstractmethod
    def response_dot(self) -> [int, int]:
        """
        统计单位时间response获取的情况
        :return:
        """

    @abstractmethod
    def get_download_statistics(self) -> [int, int, int]:
        """
        获取整个运行期间统计结果
        :return:
        """


class MemoryCrawlerCounter(BaseCrawlerCounter):

    def __init__(self, item_counter_unit: 'int', response_counter_unit: 'int'):
        self._start_time = None
        self._downloaded_request_count = 0
        self._success_request_count = 0
        self._failed_request_count = 0

        self._item_counter = Counter(unit=item_counter_unit)
        self._response_counter = Counter(unit=response_counter_unit)

    def run(self):
        self._start_time = time.time()

    def recorded_success_request(self):
        self._success_request_count += 1
        self._downloaded_request_count += 1

    def recorded_failed_request(self):
        self._failed_request_count += 1
        self._downloaded_request_count += 1

    def item_dot(self) -> [int, int]:
        return self._item_counter.dot()

    def response_dot(self) -> [int, int]:
        return self._response_counter.dot()

    def get_download_statistics(self) -> [int, int, int]:
        return self._failed_request_count, self._success_request_count, self._downloaded_request_count
