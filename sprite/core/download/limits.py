# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019-07-21 00:47'


import re
import time
import asyncio


class RequestRate:
    __slots__ = ('_count', '_period', '_actual_usage', '_next_flush', 'pattern', 'optimistic')

    def __init__(self, count:int, period:int, pattern=None, optimistic:bool=False):
        """

        :param count: How many requests per period are allowed.
                              If the request rate is 10 requests per minute than count=10 with period=60.
        :param period: How many seconds between each cycle.
                               If the request rate is 10 requests per minute than the period is 60.
        :param pattern: A pattern to match against URLs and skip the rate for those that don't match the pattern.
        :param optimistic: Request rate is complicated because you never know how __exactly__ the server is measuring
        the throughput... By default frame is optimistic and assumes that the server will honor the rate/period
        accurately.
        """
        if isinstance(pattern, str):
            # 如果pattern是正则字符串
            self.pattern =re.compile(pattern)
        else:
            self.pattern = pattern
        self.optimistic = optimistic
        self._count=count
        self._period = period
        self._actual_usage = 0
        self._next_flush = None

    async def notify(self):
        # 请求认证通过了，可以接着执行下一步的代码
        now = time.time()
        if self._next_flush is None:
            # 下一次刷新时间戳没有确定，则是开始计时状态
            self._next_flush = now+self._period
        elif now >self._next_flush:
            # 目前时间已经到达下一次时间戳
            self._next_flush = now +self._period
            # 晴空 已经通过的请求数量
            self._actual_usage = 0
        elif now<self._next_flush and self._actual_usage>=self._count:
            # 还未到下一次重置已经通过请求数量，但是已经通过的请求数量已经到达阈值
            if self.optimistic:
                wait_time = (self._next_flush-now) or 0
            else:
                wait_time = self._period
            # 目前协程进行休眠指定的时间，以防止请求速度放行过快
            await asyncio.sleep(wait_time)
            # 到达下一次循环时间戳，则重置通过的请求的数量统计
            self._actual_usage = 0
        # 在一个周期内，允许已经通过的请求数量+1
        self._actual_usage +=1

