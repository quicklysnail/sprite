# -*- coding: utf-8 -*-
# @Time    : 2020-04-22 20:39
# @Author  : li
# @File    : __init__.py.py

import hashlib
import zlib
from abc import abstractmethod
from typing import Iterator, List, Callable
from sprite.const import MD5LENGTH


class BaseXferFilter:
    @classmethod
    @abstractmethod
    def id(cls) -> 'int':
        """
        获取传输过滤器编号
        :return:
        """

    @classmethod
    @abstractmethod
    def name(cls) -> 'str':
        """
        获取传输过滤器名称
        :return:
        """

    @classmethod
    @abstractmethod
    def on_pack(cls, data: 'bytes') -> 'bytes':
        """
        对二进制数据进行打包
        :param data:
        :return:
        """

    @classmethod
    @abstractmethod
    def on_unpack(cls, data: 'bytes') -> 'bytes':
        """
        对二进制数据进行拆包
        :param data:
        :return:
        """


class XferFilterMap:
    __id_map__ = {}
    __name__map__ = {}

    @classmethod
    def get(cls, id: 'int') -> BaseXferFilter:
        return cls.__id_map__.get(id)

    @classmethod
    def get_by_name(cls, name: 'str') -> BaseXferFilter:
        return cls.__name__map__.get(name)

    @classmethod
    def register(cls, ):
        def decorate_xfer_filter(xfer_filter_cls):
            assert issubclass(xfer_filter_cls, BaseXferFilter), "must BaseCodec subclass"
            # 先去重
            if xfer_filter_cls.id() in cls.__id_map__:
                raise Exception(f'multi-register transfer filter id: {xfer_filter_cls.id()}')
            if xfer_filter_cls.name() in cls.__id_map__:
                raise Exception(f'multi-register transfer filter name: {xfer_filter_cls.name()}')
            cls.__id_map__[xfer_filter_cls.id()] = xfer_filter_cls
            cls.__name__map__[xfer_filter_cls.name()] = xfer_filter_cls

        return decorate_xfer_filter


def get_md5(data: 'bytes') -> 'bytes':
    hash = hashlib.new("md5")
    hash.update(data)
    return hash.hexdigest().encode('utf-8')


@XferFilterMap.register()
class Md5Hash(BaseXferFilter):
    __filter_name__ = "md5"
    __id__ = 1

    @classmethod
    def name(cls) -> 'str':
        return cls.__filter_name__

    @classmethod
    def id(cls) -> 'int':
        return cls.__id__

    @classmethod
    def on_pack(cls, data: 'bytes') -> 'bytes':
        if not None or len(data) == 0:
            return bytes()
        content = get_md5(data)
        data = data + content
        return data

    @classmethod
    def on_unpack(cls, data: 'bytes') -> 'bytes':
        data_length = len(data)
        if len(data) < MD5LENGTH:
            raise Exception("please check data, unpack failed")
        src_data = data[:(data_length - MD5LENGTH)]
        content = get_md5(src_data)
        if content != data[(data_length - MD5LENGTH):]:
            raise Exception("please check data, unpack failed")
        return src_data


class GzipDecoder(object):

    def __init__(self):
        self._obj = zlib.decompressobj(16 + zlib.MAX_WBITS)

    def __getattr__(self, name):
        return getattr(self._obj, name)

    def decompress(self, data):
        if not data:
            return data
        return self._obj.decompress(data)


# gzip
@XferFilterMap.register()
class Gzip(BaseXferFilter):
    __filter_name__ = "gzip"
    __id__ = 2
    __obj__ = zlib.decompressobj(16 + zlib.MAX_WBITS)

    @classmethod
    def name(cls) -> 'str':
        return cls.__filter_name__

    @classmethod
    def id(cls) -> 'int':
        return cls.__id__

    @classmethod
    def on_pack(cls, data: 'bytes') -> 'bytes':
        if not data:
            return data
        return cls.__obj__.compress(data)

    @classmethod
    def on_unpack(cls, data: 'bytes') -> 'bytes':
        if not data:
            return data
        return cls.__obj__.decompress(data)


class XferPipe:
    def __init__(self):
        self._filters = []

    @property
    def filters(self) -> 'List':
        return self._filters

    def reset(self):
        self._filters.clear()

    def append(self, filter_id: 'Iterator'):
        for id in filter_id:
            self._filters.append(XferFilterMap.get(id))
        self.check()

    def append_from(self, xfer_pipe: 'XferPipe'):
        self._filters.extend(xfer_pipe.filters)

    def __len__(self) -> 'int':
        return len(self._filters)

    def ids(self) -> 'List':
        xfer_filter_ids = []
        for filter in self._filters:
            xfer_filter_ids.append(filter.id)
        return xfer_filter_ids

    def names(self) -> 'List':
        xfer_filter_names = []
        for filter in self._filters:
            xfer_filter_names.append(filter.name)
        return xfer_filter_names

    def range(self, callback_func: 'Callable'):
        for idx, filter in enumerate(self._filters):
            if not callback_func(idx, filter):
                break

    def on_pack(self, data: 'bytes') -> 'bytes':
        for filter in self._filters:
            data = filter.on_pack(data)
        return data

    def on_unpack(self, data: 'bytes') -> 'bytes':
        for filter in self._filters:
            data = filter.on_unpack(data)
        return data

    def check(self):
        pass


if __name__ == "__main__":
    test_bytes = bytes(b'sadad')
    print(get_md5(test_bytes))
