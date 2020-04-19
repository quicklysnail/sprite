# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019-07-21 00:43'

import asyncio
# from queue import Queue
import uuid
from typing import Union
from urllib.parse import urlencode
from typing import List
from asyncio import AbstractEventLoop, TimeoutError
from .limits import RequestRate
from .pool import ConnectionPool
from .url import URL
from .request import Request
from .response import Response
from sprite.utils.http.cookies import CookiesJar
from sprite.exceptions import TooManyRedirects, MissingSchema
from .url import parse_url
from sprite.utils.decoders import MultipartEncoder
from sprite.utils.http.cookies import SessionCookiesJar
import json as json_module
from .retries import RetryStrategy

URL_ENCODING = 'utf-8'
BODY_ENCODING = 'utf-8'


class ClientDefaults:
    TIMEOUT = 30
    HEADERS = {
        'User-Agent': 'Vibora',
        'Accept': '*/*',
        'Connection': 'keep-alive',
        'Accept-Encoding': 'gzip, deflate'
    }
    RETRY_STRATEGY = RetryStrategy()


class HTTPEngine:
    __slots__ = ('loop', 'session', 'pools', 'limits')

    def __init__(self, session: 'Session', loop: AbstractEventLoop, limits: List[RequestRate] = None):
        self.loop = loop
        self.session = session  # 对外的调用端入口实例
        self.pools = {}  # 多个connection_pool链接管理，每一个connection_pool对应一个地址和端口下的多个链接
        self.limits = limits or []

    def get_pool(self, protocol: str, host: str, port: int, proxy: str = None) -> ConnectionPool:
        key = (protocol, host, port)
        try:
            # 尝试从字典中获取指定域名的链接池
            return self.pools[key]
        except KeyError:
            self.pools[key] = ConnectionPool(loop=self.loop, host=host, port=port, protocol=protocol,
                                             keep_alive=self.session.keep_alive, proxy=proxy)
        return self.pools[key]

    async def handle_redirect(self, request: Request, response: Response, stream: bool, follow_redirects: bool,
                              max_redirects: int, decode: bool, validate_ssl, headers: dict,
                              response_cookies: CookiesJar) -> Response:
        if max_redirects == 0:
            # 禁止跳转
            raise TooManyRedirects
        try:
            location = response.headers["location"]
        except KeyError:
            raise Exception('HTTP redirect response missing location header.')
        if not location.startswith('http'):
            if not location.startswith('/'):
                location = '/' + location
            location = request.url.netloc + location
        # 解析跳转的url,返回URL实例
        redirect_url = parse_url(location.encode())
        headers['Host'] = redirect_url.host
        # 再次对跳转的URL发起请求
        return await self.request(
            url=redirect_url, method='GET', stream=stream, follow_redirects=follow_redirects,
            max_redirects=(max_redirects - 1), decode=decode, validate_ssl=validate_ssl, headers=headers,
            origin=response, cookies=response_cookies
        )

    async def throttle(self, url: str):
        # 对 需要打卡的URL进行记录
        for limit in self.limits:
            if not limit.pattern or limit.pattern.fullmatch(url):
                # 目前的limit记录的URL没有匹配模式，或者传入的URL通过了匹配模式
                await limit.notify()

    async def request(self, url: URL, method: str, stream: bool, follow_redirects: bool,
                      max_redirects: int, decode: bool, validate_ssl, headers: dict,
                      origin: Response = None, data=None, cookies: CookiesJar = None, proxy: str = None) -> Response:
        """
        先建立链接，再发起请求，分为两个阶段
        """

        # 发起链接，对指定的URL，limit限制的是发起链接的频率而不是
        if self.limits:
            await self.throttle(url.raw)
        # 1.发起一个链接池链接
        # 设置请求的域名
        headers["Host"] = url.host
        pool = self.get_pool(url.schema, url.host, url.port, proxy=proxy)
        connection = await pool.get_connection(validate_ssl)
        # 从连接引擎对象上存储的cookies容器来拉取已经请求过对应的域名，保留下来的cookies

        # 2. 实例话一个request对象，来封装这一次请求
        if cookies is None:
            cookies = self.session.cookies.get(domain=url.host)
        if proxy is None:
            request = Request(method, url, headers, data,
                              cookies=cookies, origin=origin)
        else:
            request = Request(method, url, headers, data,
                              cookies=cookies, origin=origin, isProxyReq=True)
        # 编码请求信息，并发起请求
        await request.encode(connection)

        # 3.实例话一个response对象来管理接受响应
        response = Response(request.url, connection,
                            request=request, decode=decode)
        # 4.接受headers
        await response.receive_headers()
        # 5.接受完毕headers之后，再把headers里面可能的cookie合并存储到客户端全局的cookies容器中
        response_cookies = await response.cookies
        self.session.cookies.merge(response_cookies, domain=request.url.host)
        # 6.通过读取的headers里面的信息，和客户端的配置项来决定是否跳转
        if follow_redirects:
            if response.is_redirect():
                await response.read_content()
                return await self.handle_redirect(request, response, stream, follow_redirects,
                                                  max_redirects, decode, validate_ssl, headers, response_cookies)
        if not stream:
            # 7.如果不是流式数据，直接读取指定长度的数据即可
            await response.read_content()
        # 返回响应对象实例
        return response

    def close(self):
        # 关闭所有的链接池
        for pool in self.pools.values():
            pool.close()


class Session:
    __slots__ = ('_loop', '_downloader', '_engine', '_headers', 'follow_redirects', 'max_redirects',
                 'stream', 'decode', 'ssl', 'prefix', 'keep_alive', 'retries_policy',
                 'timeout', 'cookies', 'limits')

    def __init__(self, loop: AbstractEventLoop, downloader: 'Downloader' = None, headers: dict = None,
                 follow_redirects: bool = False, max_redirects: int = 30,
                 stream: bool = False, decode: bin = True, ssl=None, keep_alive: bool = True,
                 prefix: str = '', timeout: Union[int, float] = ClientDefaults.TIMEOUT,
                 retries: RetryStrategy = None, limits: List[RequestRate] = None):
        self._downloader = downloader
        self._loop = loop
        # 全局的connection链接管理
        self._engine = HTTPEngine(self, self._loop, limits=limits)
        # 全局的headers
        self._headers = ClientDefaults.HEADERS
        if headers:
            self._headers.update(headers)
        self.follow_redirects = follow_redirects
        self.max_redirects = max_redirects
        self.stream = stream
        self.decode = decode
        self.ssl = ssl
        self.prefix = prefix.encode(URL_ENCODING) or b''  # 设定URL饿前缀域名
        self.keep_alive = keep_alive
        self.retries_policy = retries or ClientDefaults.RETRY_STRATEGY
        self.timeout = timeout
        # 全局的session管理
        self.cookies = SessionCookiesJar()  # 会话管理对象的cookie默认是无法设置，初始状态为空
        self.limits = limits

    @staticmethod
    def build_url(prefix: bytes, url: bytes, query: dict):
        if not url:
            raise ValueError('Url parameter must not be empty.')
        if prefix and prefix.endswith(b'/'):
            if url.startswith(b'/'):
                url = url[1:]
            url = prefix + url
        elif prefix:
            if url.startswith(b'/'):
                url = prefix + url
            else:
                url = prefix + b'/' + url

        if not url.startswith(b'http'):
            raise MissingSchema(f'Missing schema in {url.decode(URL_ENCODING)}. '
                                f'Perhaps you meant http://{url.decode(URL_ENCODING)} ?.')
        if query:
            url = url + b'?' + urlencode(query).encode(URL_ENCODING)

        return url

    async def request(self, url: str = '/', stream: bool = None, follow_redirects: bool = None,
                      max_redirects: int = 30, decode: bool = None, ssl=None, timeout: int = None,
                      retries: Union[RetryStrategy, int] = None, cookies: dict = None,
                      headers: dict = None, method: str = 'GET', query: dict = None,
                      json: dict = None, ignore_prefix: bool = False, body=None,
                      form: dict = None, proxy: str = None) -> Response:

        # Asserting the user is not using conflicting params.
        if sum([body is not None, json is not None, form is not None]) > 1:
            raise ValueError(
                'You cannot set body, json or form together. You must pick one and only one.')

        # Handling default parameters.
        stream = stream if stream is not None else self.stream
        follow_redirects = follow_redirects if follow_redirects is not None else self.follow_redirects
        max_redirects = max_redirects if max_redirects is not None else self.max_redirects
        decode = decode if decode else self.decode
        timeout = timeout if timeout else self.timeout
        ssl = ssl if ssl is not None else self.ssl
        # 配置重试策略
        # retries = retries.clone() if retries is not None else RetryStrategy()

        request_headers = self._headers.copy()
        if cookies is not None:
            cookies = CookiesJar(cookies)
        if headers:
            # 用自定义的headers更新默认的headers
            request_headers.update(headers)

        # Constructing the URL.
        # 利用传入的URL和客户端保存的URL前缀来拼接出完整的URL，是一个字节数组
        url = self.build_url(prefix=self.prefix if not ignore_prefix else b'', url=url.encode(URL_ENCODING),
                             query=query)
        # 解析字节数组成字符串URL
        parsed_url = parse_url(url)

        if json is not None:
            body = json_module.dumps(json).encode('utf-8')
            request_headers['Content-Type'] = 'application/json'

        if form is not None:
            boundary = str(uuid.uuid4()).replace('-', '').encode()
            body = MultipartEncoder(delimiter=boundary, params=form)
            request_headers['Content-Type'] = f'multipart/form-data; boundary={boundary.decode()}'

        while True:
            try:
                task = self._engine.request(
                    url=parsed_url, data=body, method=method, stream=stream,
                    follow_redirects=follow_redirects, max_redirects=max_redirects, decode=decode,
                    validate_ssl=ssl, headers=request_headers, cookies=cookies, proxy=proxy)
                if timeout:
                    response = await asyncio.wait_for(task, timeout)
                else:
                    response = await task
                return response
            except (ConnectionError, TimeoutError) as error:
                raise error

            # 这里触发多次尝试的机制，失败则抛出error
            # try:
            #     task = self._engine.request(
            #         url=parsed_url, data=body, method=method, stream=stream,
            #         follow_redirects=follow_redirects, max_redirects=max_redirects, decode=decode,
            #         validate_ssl=ssl, headers=request_headers, cookies=cookies)
            #     if timeout:
            #         response = await asyncio.wait_for(task, timeout)
            #     else:
            #         response = await task
            #     if retries.responses.get(response.status_code, 0) > 0:
            #         retries.responses[response.status_code] -= 1
            #         continue
            #     return response
            # except (ConnectionError, TimeoutError) as error:
            #     if retries.network_failures.get(method, 0) > 0:
            #         retries.network_failures[method] -= 1
            #         continue
            #     raise error

    # session的入口方法， 这个方法在超时或者连接失败或者多次尝试失败的情况下，会抛出异常的error（ConnectionError, TimeoutError）
    async def get(self, url: str = '', stream: bool = None, follow_redirects: bool = None, max_redirects: int = 30,
                  decode: bool = None, ssl=None, timeout: int = None,
                  retries: RetryStrategy = None, headers: dict = None, cookies: dict = None,
                  query: dict = None, ignore_prefix: bool = False, proxy: str = None) -> Response:

        response = await self.request(url=url, stream=stream, follow_redirects=follow_redirects,
                                      max_redirects=max_redirects, decode=decode, ssl=ssl, cookies=cookies,
                                      retries=retries, headers=headers, timeout=timeout, method='GET', query=query,
                                      ignore_prefix=ignore_prefix, proxy=proxy)
        return response

    # session的入口方法， 这个方法在超时或者连接失败或者多次尝试失败的情况下，会抛出异常的error（ConnectionError, TimeoutError）
    async def post(self, url: str = '', stream: bool = None, follow_redirects: bool = None, max_redirects: int = 30,
                   decode: bool = None, ssl=None, timeout=ClientDefaults.TIMEOUT, cookies: dict = None,
                   retries: Union[RetryStrategy, int] = None, headers: dict = None, query: dict = None,
                   body=None, form=None, json=None, ignore_prefix: bool = False, proxy: str = None) -> Response:
        response = await self.request(url=url, stream=stream, follow_redirects=follow_redirects,
                                      max_redirects=max_redirects, decode=decode, ssl=ssl, cookies=cookies,
                                      retries=retries, headers=headers, timeout=timeout, method='POST', query=query,
                                      ignore_prefix=ignore_prefix, body=body, form=form, json=json, proxy=proxy)
        return response

    def close(self):
        """

        :return:
        """
        self._engine.close()

    async def __aenter__(self):
        """

        :return:
        """
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """

        :param exc_type:
        :param exc_val:
        :param exc_tb:
        :return:
        """
        self.close()
        await asyncio.sleep(0)
        if exc_val:
            raise exc_val
