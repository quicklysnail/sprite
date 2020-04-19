# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019/8/16 19:27'


class NotSupported(Exception): pass


class HTTPClientError(Exception): pass


class StreamAlreadyConsumed(HTTPClientError): pass


class TypeNotSupport(Exception): pass


class TooManyRedirects(HTTPClientError): pass


class MissingSchema(HTTPClientError): pass


class NotStartRequest(Exception): pass


class DownloadException(Exception): pass


class SchedulerEmptyException(Exception): pass


class UniqueCrawlerNameException(Exception): pass
