# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019-08-25 22:09'

from urllib import parse


class URL:

    def __init__(self, schema: bytes, host: bytes, port, path: bytes,
                 query: bytes, fragment: bytes, userinfo: bytes):
        self.schema = schema.decode('utf-8')
        self.host = host.decode('utf-8')
        self.port = port or 443 if self.schema == "https" else 80
        self.path = path.decode('utf-8')
        self.query = query.decode('utf-8')
        self.fragment = fragment.decode('utf-8')
        self.userinfo = userinfo.decode('utf-8')
        self.netloc = self._setNetloc()

    def __repr__(self):
        return ('<URL schema: {!r}, host: {!r}, port: {!r}, path: {!r}, '
                'query: {!r}, fragment: {!r}, userinfo: {!r}>'
                .format(self.schema, self.host, self.port, self.path, self.query, self.fragment, self.userinfo))

    @property
    def raw(self):
        _raw = self.netloc
        if self.path:
            _raw += '/' + self.path
            if self.query:
                _raw += '?' + self.query
        return _raw

    def _setNetloc(self):
        if self.query:
            return self.path + "?" + self.query
        return self.path


def parse_url(url: bytes) -> URL:
    parse_result = parse.urlparse(url)
    return URL(schema=parse_result.scheme,
               host=parse_result.netloc.split(b':')[0],
               port=parse_result.port,
               path=parse_result.path,
               query=parse_result.query,
               fragment=parse_result.fragment,
               userinfo=b'')
