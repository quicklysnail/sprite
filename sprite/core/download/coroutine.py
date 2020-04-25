# -*- coding: utf-8 -*-
# @Time    : 2020-04-25 00:37
# @Author  : li
# @File    : coroutine.py

import ssl
import asyncio
from asyncio.streams import StreamWriter, StreamReader
from urllib import parse
from typing import Union, Any
from sprite.settings import Settings
from sprite.core.download.base import BaseDownloader
from sprite.utils.http.request import Request
from sprite.utils.http.response import Response
from sprite.core.download.socket.sockethub import SocketHub
from sprite.core.download.socket import Socket, BaseSocket
from sprite.core.download.codec import ID_JSON
from sprite.core.download.proto.httpproto import HttpProto
from sprite.core.download.socket.message import Message
from sprite.const import HTTP_METHOD_GET, HTTP_METHOD_POST, HTTP_PROTO_TYPE_HTTPS, HTTP_PROTO_TYPE_HTTP

SECURE_CONTEXT = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
SECURE_CONTEXT.check_hostname = True

INSECURE_CONTEXT = ssl.SSLContext()
INSECURE_CONTEXT.check_hostname = False

HTTP_PORT = 80
HTTPS_PORT = 443


class CoroutineDownloader(BaseDownloader):
    def __init__(self, settings: 'Settings'):
        self._sem = None
        self._delay = 0
        self._timeout = 0
        self._keep_alive = None
        self._socket_hub = SocketHub()
        self._init(settings)

    def _init(self, settings: 'Settings'):
        self._sem = asyncio.Semaphore(settings.getint("MAX_DOWNLOAD_NUM"))
        self._delay = settings.getfloat("DELAY")
        self._timeout = settings.getfloat("TIMEOUT")
        self._keep_alive = settings.getbool("KEEP_ALIVE")

    async def download(self, request: 'Request') -> 'Response':
        # 强制每一个请求的下载间隔一小会
        if self._delay > 0:
            await asyncio.sleep(self._delay)
        # 加锁的目的是为了限制同一时间的并发数量
        async with self._sem:
            socket = await self._generate_socket(request)
            try:
                task = self._request(socket, request)
                if self._timeout:
                    response = await asyncio.wait_for(task, self._timeout)
                else:
                    response = await task
                return response
            except (ConnectionError, TimeoutError) as error:
                raise error

    async def _request(self, socket: 'BaseSocket', request: 'Request') -> 'Response':
        request_message = self._request_to_message(request)
        await socket.write_message(request_message)
        response_message = Message(http_method=request_message.http_method,
                                   service_method=request_message.service_method)
        await socket.read_message(response_message)
        response = self._message_to_response(response_message)
        response.request = request
        return response

    async def _generate_socket(self, request: 'Request') -> 'BaseSocket':
        # 处理应用层协议
        parse_result = parse.urlparse(request.url)
        remote_port = 80 if parse_result.scheme.lower() == HTTP_PROTO_TYPE_HTTP else 443
        if parse_result.scheme.lower() not in [HTTP_PROTO_TYPE_HTTPS, HTTP_PROTO_TYPE_HTTP]:
            raise Exception("only support http or https protocol")
        # 处理代理
        remote_addr = self.get_request_proxy(request)
        if remote_addr:
            remote_ip, remote_port = remote_addr
        else:
            remote_ip = parse_result.netloc.split(":")[0]
        # 处理keep_alive
        if self._keep_alive:
            exist_socket = self._socket_hub.get(f'{remote_ip}:{remote_port}', None)
            if exist_socket:
                return exist_socket
        reader, writer = await self.create_connection(parse_result.scheme.lower(), remote_ip, remote_port)
        new_socket = Socket(request.url, reader, writer, HttpProto(reader, writer))
        if self._keep_alive:
            self._socket_hub[f'{remote_ip}:{remote_port}'] = new_socket
        return new_socket

    @staticmethod
    def _request_to_message(request: 'Request') -> 'Message':
        if request.method.upper() == HTTP_METHOD_GET:
            message = Message(
                http_method=HTTP_METHOD_GET,
                service_method=request.url
            )
        elif request.method.upper() == HTTP_METHOD_POST:
            message = Message(
                http_method=HTTP_METHOD_POST,
                service_method=request.url,
                body=request.formdata
            )
            message.set_body_codec(ID_JSON)
        else:
            raise Exception("only support GET or POST method")
        meta = message.meta
        # 填充header
        meta.update(request.headers)
        # 填充cookie
        if len(request.cookies) != 0:
            cookies_str = []
            for key, value in request.cookies.items():
                cookies_str.append(value)
            cookies_str = "; ".join(cookies_str)
            meta.update({"Cookie": cookies_str})
        return message

    @staticmethod
    def _message_to_response(message: 'Message') -> 'Response':
        # 提取header和cookie
        meta = message.meta
        headers = {}
        cookies = {}
        for key, value in meta.items():
            if key.lower() == "cookie":
                for cookie_key, cookie_value in value.replace(" ", "").split(";"):
                    cookies[cookie_key] = cookie_value
            else:
                headers[key] = value
        response = Response(
            message.service_method, status=message.status,
            headers=headers, cookies=cookies,
            body=message.body
        )
        return response

    @staticmethod
    def get_request_proxy(request: 'Request') -> Union[tuple, None]:
        proxy = request.meta.get("proxy", None)
        if proxy:
            parse_result = parse.urlparse(proxy)
            proxy = parse_result.netloc.split(":")
            remote_ip = proxy[0]
            remote_port = int(proxy[1])
            return remote_ip, remote_port

    @staticmethod
    async def create_connection(proto_type: 'str', host: 'str', port: 'int', ssl: 'Any' = None) -> ['StreamWriter',
                                                                                                    'StreamReader']:
        connection_arg = {
            'host': host,
            'port': port
        }
        if proto_type == HTTP_PROTO_TYPE_HTTPS:
            if ssl is False:
                connection_arg['ssl'] = INSECURE_CONTEXT
            elif ssl is None:
                connection_arg['ssl'] = SECURE_CONTEXT
            else:
                connection_arg['ssl'] = ssl
        reader, writer = await asyncio.open_connection(**connection_arg)
        return reader, writer
