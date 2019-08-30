# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019-08-25 22:09'

from urllib import parse


class URL:

    def __init__(self, schema: bytes, host: bytes, port, path: bytes,
                 query: bytes, fragment: bytes, userinfo: bytes):
        self.schema = schema.decode('utf-8')
        self.host = host.decode('utf-8')
        self.port = port if port else 443
        self.path = path.decode('utf-8')
        self.query = query.decode('utf-8')
        self.fragment = fragment.decode('utf-8')
        self.userinfo = userinfo.decode('utf-8')
        self.netloc = self.schema + '://' + self.host + ":" + str(self.port)

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


def parse_url(url: bytes) -> URL:
    """
    ParseResultBytes(scheme=b'https', netloc=b'www.baidu.com', path=b'/page/name/age', params=b'', query=b'id=1001&token=01254514', fragment=b'')
    b'/page/name/age'
    None
    """
    parse_result = parse.urlparse(url)
    return URL(schema=parse_result.scheme,
               host=parse_result.netloc.split(b':')[0],
               port=parse_result.port or b'',
               path=parse_result.path,
               query=parse_result.query,
               fragment=parse_result.fragment,
               userinfo=b'')
