# -*- coding: utf-8 -*-
# @Time    : 2020-04-25 00:37
# @Author  : li
# @File    : coroutine.py

import asyncio
from urllib import parse
from sprite.settings import Settings
from sprite.core.download.base import BaseDownloader
from sprite.utils.http.request import Request
from sprite.utils.http.response import Response
from sprite.core.download.socket.sockethub import SocketHub
from sprite.core.download.socket import Socket, BaseSocket
from sprite.core.download.codec import ID_JSON
from sprite.core.download.proto.httpproto import HttpProto
from sprite.core.download.socket.message import Message
from sprite.const import HTTP_METHOD_GET, HTTP_METHOD_POST

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
            socket = self._generate_socket(request)
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

    def _generate_socket(self, request: 'Request') -> 'BaseSocket':
        parse_result = parse.urlparse(request.url)
        if parse_result.scheme.lower() != "http":
            raise Exception("only support http protocol")

        if self._keep_alive:
            exist_socket = self._socket_hub.get(f'{parse_result.netloc}:{HTTP_PORT}', None)
            if exist_socket:
                return exist_socket
        reader, writer = asyncio.open_connection(host=parse_result.netloc, port=HTTP_PORT)
        new_socket = Socket(request.url, reader, writer, HttpProto(reader, writer))
        if self._keep_alive:
            self._socket_hub[f'{parse_result.netloc}:{HTTP_PORT}'] = new_socket
        return new_socket

    def _request_to_message(self, request: 'Request') -> 'Message':
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
        cookies_str = []
        for key, value in request.cookies.items():
            cookies_str.append(value)
        cookies_str = "; ".join(cookies_str)
        meta.update({"Cookie": cookies_str})
        return message

    def _message_to_response(self, message: 'Message') -> 'Response':
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
