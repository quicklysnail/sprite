# -*- coding: utf-8 -*-
# @Time    : 2020-04-21 13:52
# @Author  : li
# @File    : base.py

from abc import abstractmethod
from sprite.utils.utils import SingletonMetaClass
from sprite.utils.http.request import Request
from sprite.utils.http.response import Response


class BaseDownloader(metaclass=SingletonMetaClass):
    @abstractmethod
    def download(self, request: 'Request') -> 'Response':
        """
        发起一个request请求
        :param request:
        :return:
        """
