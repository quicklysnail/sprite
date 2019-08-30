# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019-07-20 22:05'

import asyncio
from asyncio import AbstractEventLoop

from collections import deque
from .connection import Connection, SECURE_CONTEXT, INSECURE_CONTEXT
from .proxy import ProxyHandler


class ConnectionPool:
    __slots__ = ('loop', 'host', 'port', 'protocol', 'max_connections', 'connections', 'available_connections',
                 'keep_alive', 'wait_connection_available', 'proxy')

    def __init__(self, loop: AbstractEventLoop, host: str, port: int, protocol: str, keep_alive: bool = True,
                 proxy: str = None):
        self.loop = loop
        self.host = host  # ip
        self.port = port  # 端口
        self.protocol = protocol  # 应用层协议 http/https
        self.available_connections = deque()  # 存储可用的闲置连接
        self.connections = set()  # 存储已经连接的链接
        self.keep_alive = keep_alive
        self.proxy = proxy
        # 代理模式下的链接不保存
        if self.proxy is not None:
            self.keep_alive = False

    async def create_connection(self, ssl=None) -> Connection:
        # 利用协程创建一个socket链接的参数
        args = {
            'host': self.host,
            'port': self.port,
            'loop': self.loop,
        }
        if self.proxy:
            self.proxy = ProxyHandler.prepend_scheme_if_needed(self.proxy, "http")
            proxy_protocol, proxy_host, proxy_port = ProxyHandler.parse_proxy(self.proxy)
            args = {
                'host': proxy_host,
                'port': proxy_port,
                'loop': self.loop,
            }
        # 配置https的ssl
        if self.proxy is None and self.protocol == 'https':
            if ssl is False:
                args['ssl'] = INSECURE_CONTEXT
            elif ssl is None:
                args['ssl'] = SECURE_CONTEXT
            else:
                args['ssl'] = ssl
        # 在协程里面创建一个socket连接
        #  (host=None, port=None, *, loop=None, limit=None, ssl=None, family=0, proto=0, flags=0, sock=None, local_addr=None, server_hostname=None, ssl_handshake_timeout=None)
        reader, writer = await asyncio.open_connection(**args)
        # 实例化一个connection
        connection = Connection(self.loop, reader, writer, self)
        self.connections.add(connection)
        return connection

    async def get_connection(self, ssl):
        try:
            # 从可用链接队列尾部里面取出一个链接
            connection = self.available_connections.pop()
            if not await connection.is_dropped():
                # 从可用链接中获取到一个connection，且能正常读取
                return connection
            else:
                # 可用链接读取超时
                await self.release_connection(connection)
                # 创建新的链接
                return await self.create_connection(ssl)
        except IndexError:
            # 可用链接队列为空，无法pop
            return await self.create_connection(ssl)

    async def release_connection(self, connection: Connection, keep_alive: bool = True):
        if keep_alive and self.keep_alive:
            # 单个链接是长链接，且域名链接是长链接，则把链接放在可用链接队列的头部
            self.available_connections.appendleft(connection)
        else:
            # 只要有一个设置的不是长链接
            # 关闭链接
            connection.close()  # 关闭链接需要等待
            self.connections.discard(connection)

    def close(self):
        # 关闭域名下的所有链接
        for connection in self.connections:
            connection.close()
