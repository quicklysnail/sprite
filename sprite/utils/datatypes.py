# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019/8/16 19:50'

from collections import Mapping


class CaselessDict(dict):
    __slots__ = ()

    def __init__(self, seq=None):
        super(CaselessDict, self).__init__()
        if seq:
            self.update(seq)

    def __getitem__(self, key):
        return dict.__getitem__(self, self.normkey(key))

    def __setitem__(self, key, value):
        dict.__setitem__(self, self.normkey(key), self.normvalue(value))

    def __delitem__(self, key):
        dict.__delitem__(self, self.normkey(key))

    def __contains__(self, key):
        return dict.__contains__(self, self.normkey(key))

    has_key = __contains__

    def __copy__(self):
        return self.__class__(self)

    copy = __copy__

    def normkey(self, key):
        """Method to normalize dictionary key access"""
        try:
            return key.lower()
        except TypeError:
            tmp_str = ""
            for c in key:
                try:
                    tmp_str += c.lower()
                except TypeError:
                    tmp_str += c
        return tmp_str

    def normvalue(self, value):
        """Method to normalize values prior to be setted"""
        return value

    def get(self, key, def_val=None):
        return dict.get(self, self.normkey(key), self.normvalue(def_val))

    def setdefault(self, key, def_val=None):
        return dict.setdefault(self, self.normkey(key), self.normvalue(def_val))

    def update(self, seq):
        seq = seq.items() if isinstance(seq, Mapping) else seq
        iseq = ((self.normkey(k), self.normvalue(v)) for k, v in seq)
        super(CaselessDict, self).update(iseq)

    @classmethod
    def fromkeys(cls, keys, value=None):
        return cls((k, value) for k in keys)

    def pop(self, key, *args):
        return dict.pop(self, self.normkey(key), *args)


# class URL:
#
#     def __init__(self, schema: bytes, host: bytes, port, path: bytes,
#                  query: bytes, fragment: bytes, userinfo: bytes):
#         self.schema = schema.decode('utf-8')
#         self.host = host.decode('utf-8')
#         self.port = port if port else 80
#         self.path = path.decode('utf-8')
#         self.query = query.decode('utf-8')
#         self.fragment = fragment.decode('utf-8')
#         self.userinfo = userinfo.decode('utf-8')
#         self.netloc = self.schema + '://' + self.host + self.port
#
#     def __repr__(self):
#         return ('<URL schema: {!r}, host: {!r}, port: {!r}, path: {!r}, '
#                 'query: {!r}, fragment: {!r}, userinfo: {!r}>'
#                 .format(self.schema, self.host, self.port, self.path, self.query, self.fragment, self.userinfo))


if __name__ == '__main__':
    test_dict = {
        "S52LYYYYYY": "liyong"
    }

    testCaselessDict = CaselessDict(test_dict)
    print(testCaselessDict)
