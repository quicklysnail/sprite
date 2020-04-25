# -*- coding: utf-8 -*-
# @Time    : 2020-04-22 22:33
# @Author  : li
# @File    : __init__.py.py

from abc import abstractmethod
from sprite.core.download.socket import Message


class BaseProto:
    @abstractmethod
    async def pack(self, message: 'Message'):
        """
        发送消息
        :param message:
        :return:
        """

    @abstractmethod
    async def un_pack(self, message: 'Message'):
        """
        接受消息
        :param message:
        :return:
        """
