# -*- coding: utf-8 -*-
# @Time    : 2020-04-22 22:37
# @Author  : li
# @File    : __init__.py.py


import json
from abc import abstractmethod
from typing import Any

NONE_CODEC_ID = 0

NAME_JSON = "json"
ID_JSON = 1

NAME_HTML = "html"
ID_HTML = 2


class BaseCodec:
    @classmethod
    @abstractmethod
    def id(cls) -> 'int':
        """
        返回序列化器的编号
        :return:
        """

    @classmethod
    @abstractmethod
    def name(cls) -> 'str':
        """
        返回序列化器的名称
        :return:
        """

    @classmethod
    @abstractmethod
    def marshal(cls, v: 'Any') -> 'bytearray':
        """
        序列化
        :return:
        """

    @classmethod
    @abstractmethod
    def un_marshal(cls, data: 'bytearray') -> 'Any':
        """
        反序列化
        :param data:
        :param v:
        :return:
        """


# 自动注册序列化器
class CodecMap:
    __id_map__ = {}
    __name__map__ = {}

    @classmethod
    def register(cls):
        def decorate_codec(codec_cls):
            assert issubclass(codec_cls, BaseCodec), "must BaseCodec subclass"
            if codec_cls.id() == NONE_CODEC_ID:
                raise Exception(f'codec id can not be {codec_cls.id()}')
            if codec_cls.id() in cls.__id_map__:
                raise Exception(f'"multi-register codec id: {codec_cls.id()}')
            if codec_cls.name() in cls.__name__map__:
                raise Exception(f'"multi-register codec name: {codec_cls.name()}')
            cls.__id_map__[codec_cls.id()] = codec_cls
            cls.__name__map__[codec_cls.name()] = codec_cls

        return decorate_codec

    @classmethod
    def get(cls, id: 'int') -> 'BaseCodec':
        return cls.__id_map__.get(id)

    @classmethod
    def get_by_name(cls, name: 'str') -> 'BaseCodec':
        return cls.__name__map__.get(name)

    @classmethod
    def marshal(cls, id: 'int', v: 'Any') -> 'bytearray':
        codec = cls.get(id)
        return codec.marshal(v)

    @classmethod
    def un_marshal(cls, id: 'int', data: 'bytearray') -> 'Any':
        codec = cls.get(id)
        return codec.un_marshal(data)

    @classmethod
    def marshal_by_name(cls, name: 'str', v: 'Any') -> 'bytearray':
        codec = cls.get_by_name(name)
        return codec.marshal(v)

    @classmethod
    def un_marshal_by_name(cls, name: 'str', data: 'bytearray') -> 'Any':
        codec = cls.get_by_name(name)
        return codec.un_marshal(data)


@CodecMap.register()
class JsonCodec(BaseCodec):
    __id__ = 1
    __codec_name__ = "json"

    @classmethod
    def id(cls) -> 'int':
        """
        返回序列化器的编号
        :return:
        """
        return cls.__id__

    @classmethod
    def name(cls) -> 'str':
        """
        返回序列化器的名称
        :return:
        """
        return cls.__codec_name__

    @classmethod
    def marshal(cls, v: 'Any') -> 'bytearray':
        """
        序列化
        :return:
        """
        return bytearray(json.dumps(v).encode("utf-8"))

    @classmethod
    def un_marshal(cls, data: 'bytearray') -> 'Any':
        """
        反序列化
        :param data:
        :param v:
        :return:
        """
        return json.loads(data.decode("utf-8"), encoding="utf-8")


@CodecMap.register()
class HtmlCodec(BaseCodec):
    __id__ = 2
    __codec_name__ = "html"

    @classmethod
    def id(cls) -> 'int':
        """
        返回序列化器的编号
        :return:
        """
        return cls.__id__

    @classmethod
    def name(cls) -> 'str':
        """
        返回序列化器的名称
        :return:
        """
        return cls.__codec_name__

    @classmethod
    def marshal(cls, v: 'Any') -> 'bytearray':
        """
        序列化
        :return:
        """
        raise Exception("无法序列化成html")

    @classmethod
    def un_marshal(cls, data: 'bytearray') -> 'Any':
        """
        反序列化
        :param data:
        :param v:
        :return:
        """
        return data.decode("utf-8")


if __name__ == "__main__":
    test_dict = {"name": "liyong"}
    marshal_bytes = CodecMap.marshal_by_name("json", test_dict)
    print(marshal_bytes)
    un_marshal_object = CodecMap.un_marshal_by_name("json", marshal_bytes)
    print(un_marshal_object)
