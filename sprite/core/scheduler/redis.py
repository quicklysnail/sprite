# -*- coding: utf-8 -*-
# @Time    : 2020-04-20 23:15
# @Author  : li
# @File    : redis.py

from sprite.core.scheduler.base import BaseScheduler
from sprite.settings import settings


class RedisScheduler(BaseScheduler):
    def __init__(self):
        self._store = None
        self._df = None
        super(RedisScheduler, self).__init__()

    def _init(self):
        pass

    def start(self):
        pass

    def stop(self):
        pass

    def enqueue_request(self, crawler_name: 'str', request: 'Request'):
        pass

    def next_request(self, crawler_name: 'str') -> 'Request':
        pass

    def has_pending_requests(self, crawler_name: 'str') -> 'bool':
        pass

    def __len__(self) -> int:
        pass
