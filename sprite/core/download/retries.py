# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019-07-21 17:38'


class RetryStrategy:
    __slots__ = ('network_failures', 'responses')

    def __init__(self, network_failures: dict = None, responses: dict = None):
        self.network_failures = network_failures or {'GET': 1}

        self.responses = responses or {}

    def clone(self) -> 'RetryStrategy':
        return RetryStrategy(network_failures=self.network_failures.copy(), responses=self.responses.copy())
