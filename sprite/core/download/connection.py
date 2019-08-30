# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019-07-20 23:39'


import ssl
from asyncio import StreamReader,StreamWriter,AbstractEventLoop, wait_for, TimeoutError
from typing import Coroutine

SECURE_CONTEXT = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
SECURE_CONTEXT.check_hostname = True

INSECURE_CONTEXT = ssl.SSLContext()
INSECURE_CONTEXT.check_hostname = False


class Connection:
    __slots__ = ('loop','reader','writer', 'pool')
    def __init__(self, loop:AbstractEventLoop, reader:StreamReader,writer:StreamWriter,pool):
        self.loop = loop
        self.reader = reader
        self.writer = writer
        self.pool = pool # 一个域名的连接池

    # 发送数据，生成一个
    def sendall(self, data:bytes)->Coroutine:
        # print(f'send data : {data.decode("utf-8")}')
        self.writer.write(data)
        # 返回一个写数据协程，等待知道写到缓冲区中
        return self.writer.drain()

    # 读取固定长度的数据，从可读对象中
    def read_exactly(self, length:int)->Coroutine:
        return self.reader.readexactly(length)

    # 从可读对象中读取到指定的字节为止
    def read_until(self, delimiter:bytes)->Coroutine:
        return self.reader.readuntil(delimiter)

    def close(self):
        self.writer.close()

    async def is_dropped(self):
        try:
            # 验证连接是否空闲
            await wait_for(self.reader.readexactly(0), 0.001)
            return True
        except TimeoutError:
            # 捕获到超时异常
            return False

    def release(self, keep_alive:bool=False):
        # 把连接实例传入进去，关闭连接
        self.pool.release_connection(self, keep_alive)
