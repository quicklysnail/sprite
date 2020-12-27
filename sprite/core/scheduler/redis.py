# -*- coding: utf-8 -*-
# @Time    : 2020-04-20 23:15
# @Author  : li
# @File    : redis.py


import pickle
import redis
from sprite.core.scheduler.base import BaseScheduler
from sprite.settings import Settings
from sprite.const import SCHEDULER_STOPPED, SCHEDULER_RUNNING
from sprite import Request
from sprite.exceptions import NotUniqueRequestException, RequestQueueNotExistException, RequestQueueEmptyException




class RedisScheduler(BaseScheduler):
    def __init__(self, settings: 'Settings'):
        self._settings = settings
        self._store = None
        self._df = None
        self._init()
        super(RedisScheduler, self).__init__()

    def _init(self):
        pool = redis.ConnectionPool(host=self._settings.get("REDIS_HOST"), port=self._settings.get("REDIS_PORT"),
                                    max_connections=self._settings.get("REDIS_MAX_CONNECTIONS"))
        self._store = redis.Redis(connection_pool =pool)

    def start(self):
        assert self._state == SCHEDULER_STOPPED, "scheduler is not stopped"
        self._init()
        self._state = SCHEDULER_RUNNING

    def stop(self):
        assert self._state == SCHEDULER_RUNNING, "scheduler not running"
        self._state = SCHEDULER_STOPPED

    def enqueue_request(self, crawler_name: 'str', request: 'Request'):
        assert self._state == SCHEDULER_RUNNING, "scheduler not running"
        request_bytes = pickle.dumps(request)
        self._store.rpush(crawler_name, request_bytes)

    def next_request(self, crawler_name: 'str') -> 'Request':
        request_bytes = self._store.lpop(crawler_name)
        if request_bytes is None:
            raise RequestQueueEmptyException("request queue is empty")
        request = pickle.loads(request_bytes)
        return request

    def has_pending_requests(self, crawler_name: 'str') -> 'bool':
        pass

    def __len__(self) -> int:
        pass
