# -*- coding: utf-8 -*-
# @Time    : 2020-04-23 00:10
# @Author  : li
# @File    : __init__.py.py


from abc import abstractmethod
from typing import List
from asyncio.streams import StreamWriter, StreamReader
from asyncio import Lock
from sprite.core.download.socket.message import Message
from sprite.core.download.proto import BaseProto
from sprite.utils.ip import get_ip
from sprite.const import SOCKET_STATE_NORMAL, SOCKET_STATE_ACTIVATE_CLOSE


class BaseSocket:
    @abstractmethod
    def local_addr(self) -> 'str':
        """
        返回loacl的ip地址
        :return:
        """

    @abstractmethod
    def remote_addr(self) -> 'str':
        """
        返回remote的ip地址
        :return:
        """

    @abstractmethod
    def set_deadline(self, t: 'float'):
        """
        :param t:
        :return:
        """

    @abstractmethod
    def set_read_deadline(self, t: 'float'):
        """

        :param t:
        :return:
        """

    @abstractmethod
    def set_write_deadline(self, t: 'float'):
        """

        :param t:
        :return:
        """

    @abstractmethod
    def write_message(self, message: 'Message'):
        """

        :param message:
        :return:
        """

    @abstractmethod
    def read_message(self, message: 'Message'):
        """

        :param message:
        :return:
        """

    @abstractmethod
    def read(self, n: 'int') -> 'bytearray':
        """

        :param b:
        :return:
        """

    @abstractmethod
    def write(self, b: 'bytearray') -> 'int':
        """

        :param b:
        :return:
        """

    @abstractmethod
    def close(self):
        """

        :return:
        """

    @abstractmethod
    def swap(self, new_swap: 'List[dict]'):
        """

        :param new_swap:
        :return:
        """

    @abstractmethod
    def swap_len(self) -> 'int':
        """

        :return:
        """

    @abstractmethod
    def id(self) -> 'str':
        """

        :return:
        """

    @abstractmethod
    def set_id(self, id: 'str'):
        """

        :param id:
        :return:
        """

    @abstractmethod
    def raw(self) -> ['StreamReader', 'StreamWriter']:
        """
        Ω
        :return:
        """


class Socket(BaseSocket):
    def __init__(self, remote_addr:'str',reader: 'StreamReader', writer: 'StreamWriter',
                 protocol: 'BaseProto'):
        self._reader = reader
        self._writer = writer
        self._protocol = protocol
        self._remote_addr =remote_addr

        self._id = ""
        self._swap = None

        self._state = SOCKET_STATE_NORMAL
        self._state_lock = Lock

    def raw(self) -> ['StreamReader', 'StreamWriter']:
        return self._reader, self._writer

    async def read(self, n: 'int') -> 'bytearray':
        return bytearray(await self._reader.read(n))

    async def write_message(self, message: 'Message'):
        await self._protocol.pack(message)

    async def read_message(self, message: 'Message'):
        await self._protocol.un_pack(message)

    async def close(self):
        async with self._state_lock:
            if self._state == SOCKET_STATE_ACTIVATE_CLOSE:
                return

            self._state = SOCKET_STATE_ACTIVATE_CLOSE
            self._writer.close()

    def swap(self, new_swap: 'List[dict]'):
        if len(new_swap) > 0:
            self._swap = new_swap[0]
        elif self._swap is None:
            self._swap = {}
        return self._swap

    def swap_len(self) -> 'int':
        return len(self._swap)

    def id(self) -> 'str':
        if len(self._id) ==0:
            self._id = self._remote_addr
        return self._id

    def set_id(self, id: 'str'):
        self._id = id
