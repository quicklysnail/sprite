# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019/8/16 19:50'

from typing import Callable
from sprite.http.headers import Headers


class Request:
    __slots__ = (
        '_encoding', '_query', 'method', '_formdata', 'priority', 'callback', 'cookies', 'headers', 'dont_filter',
        '_meta',
        '_url'
    )

    def __init__(self, url, callback: Callable = None, method='GET', headers=None, query=None, formdata=None,
                 cookies=None, meta=None, encoding='utf-8', priority=0,
                 dont_filter=False):
        self._encoding = encoding
        self._query = query
        self.method = str(method).upper()
        self._set_url(url)
        self._formdata = formdata
        assert isinstance(priority, int), "Request priority not an integer: %r" % priority
        self.priority = priority

        if callback is not None and not callable(callback):
            raise TypeError('callback must be a callable, got %s' % type(callback).__name__)

        self.callback = callback
        assert callback is not None, 'Request[%s]的回调函数[callback]不能为None!' % self._url
        self.cookies = cookies or {}
        self.headers = Headers(headers or {}, encoding=encoding)

        self.dont_filter = dont_filter

        self._meta = dict(meta) if meta else None

    @property
    def query(self):
        if self._query is None:
            return {}
        return self._query

    @property
    def formdata(self):
        if self._formdata is None:
            self._formdata = {}
        return self._formdata

    @property
    def meta(self):
        if self._meta is None:
            self._meta = {}
        return self._meta

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, url: str):
        self._set_url(url)

    def _set_url(self, url):
        self._url = url

        if ':' not in self._url:
            raise ValueError('Missing scheme in request url: %s' % self._url)

    @property
    def encoding(self):
        return self._encoding

    def toUniqueStr(self):
        if self.method == "GET":
            return f'{self.url}'
        return f'{self.url},{self.formdata}'

    def __str__(self):
        return "<method:%s url:%s formdata:%s headers:%s cookies:%s>" % (
            self.method, self._url, self.formdata, self.headers.to_string(), self.cookies)

    __repr__ = __str__

    def copy(self):
        return self.replace()

    def replace(self, *args, **kwargs):
        """
        传入相关属性，生成一个新的request，不传入的属性，默认使用自身的属性
        """
        for x in ['url', 'method', 'headers', 'cookies', 'meta',
                  'encoding', 'priority', 'dont_filter', 'callback']:
            kwargs.setdefault(x, getattr(self, x))
        cls = kwargs.pop('cls', self.__class__)
        return cls(*args, **kwargs)

