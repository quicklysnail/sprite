# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019/8/16 19:50'

from urllib.parse import urljoin
from typing import Dict, Callable, Union
from sprite.http.headers import Headers
from sprite.exceptions import NotSupported
from sprite.http.request import Request
from sprite.http.cookies import CookiesJar


class Response:
    __slots__ = ('headers', 'status', '_body', '_url', '_cookiesJar', 'request', '_error')

    def __init__(self, url: str, status: int = 200, headers: Dict = None, body: str = "", cookies: Dict = None,
                 request: Request = None, error: Exception = None):
        self.headers = Headers(headers or {})
        self.status = int(status)
        self._body = body
        self._url = url
        self._cookiesJar = CookiesJar(cookies)
        self.request = request
        self._error = error

    @property
    def meta(self):
        try:
            return self.request.meta
        except AttributeError:
            raise AttributeError(
                "Response.meta not available, this response "
                "is not tied to any request"
            )

    @property
    def error(self) -> Union[Exception, None]:
        return self._error

    @property
    def url(self):
        return self._url

    @property
    def body(self):
        return self._body

    @property
    def cookies(self):
        return self._cookiesJar

    @property
    def callback(self):
        return self.request.callback

    def __str__(self):
        return "<%d %s>" % (self.status, self.url)

    __repr__ = __str__

    def copy(self):
        return self.replace()

    def replace(self, *args, **kwargs):
        for x in ['url', 'status', 'headers', 'body', 'request']:
            kwargs.setdefault(x, getattr(self, x))
        cls = kwargs.pop('cls', self.__class__)
        return cls(*args, **kwargs)

    def urljoin(self, url: str):
        return urljoin(self.url, url)

    def css(self, *a, **kw):
        raise NotSupported("Response content isn't text")

    def xpath(self, *a, **kw):
        raise NotSupported("Response content isn't text")

    def follow(self, url: str = None, callback: Callable = None, method: str = 'GET', headers: Dict = None,
               cookies: Dict = None, meta: Dict = None, encoding: str = 'utf-8', priority: int = 0,
               dont_filter: bool = False, ) -> Request:
        if url is None:
            url = self._url
        if headers is None:
            headers = self.headers
        if callback is None:
            callback = self.request.callback
        if cookies is None:
            cookies = self.request.cookies
        if meta is None:
            meta = self.request.meta
        return Request(url, callback,
                       method=method,
                       headers=headers,
                       cookies=cookies,
                       meta=meta,
                       encoding=encoding,
                       priority=priority,
                       dont_filter=dont_filter,
                       )
