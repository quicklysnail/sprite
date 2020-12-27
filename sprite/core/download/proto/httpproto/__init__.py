# -*- coding: utf-8 -*-
# @Time    : 2020-04-22 22:33
# @Author  : li
# @File    : __init__.py.py

import httptools
from urllib.parse import urlparse
from asyncio.streams import StreamReader, StreamWriter
from sprite.core.download import codec
from sprite.core.download.xfer import BaseXferFilter, XferFilterMap
from sprite.core.download.proto import BaseProto
from sprite.core.download.socket import Message
from sprite.const import XFER_PIPE_GZIP, DEFAULT_CODING, TYPE_REPLY, HTTP_METHOD_POST
from sprite.utils.args import Args
from sprite.utils.log import get_logger

logger = get_logger()

BODY_CODEC_MAPPING = {
    "application/json;charset=UTF-8": codec.ID_JSON,
    "text/html;charset=utf-8": codec.ID_HTML
}

CONTENT_TYPE_MAPPING = {
    codec.ID_JSON: "application/json;charset=utf-8",
    codec.ID_HTML: "text/html;charset=utf-8"
}


def register_body_codec(content_type: 'str', codec_id: 'int'):
    BODY_CODEC_MAPPING[content_type] = codec_id
    CONTENT_TYPE_MAPPING[codec_id] = content_type


def get_body_codec(content_type: 'str', default_id: 'int'):
    return BODY_CODEC_MAPPING.get(content_type, default_id)


def get_content_type(codec_id: 'int', default_type: 'str'):
    return CONTENT_TYPE_MAPPING.get(codec_id, default_type)


class HttpProto(BaseProto):
    __space = ' '
    __colon = ':'
    __crlf = '\r\n'
    __line_feed = '\n'

    class __Header:
        content_type = 'Content-Type'
        content_length = 'Content-Length'
        content_encoding = 'Content-Encoding'
        accept_encoding = "Accept-Encoding"
        host = "Host"
        x_seq = 'X-Seq'
        x_mtype = 'X-Mtype'


    class Request_First_Line:

        def __init__(self, http_method:'str', uri: 'str',proto_version:'str'='HTTP/1.1'):
            self.http_method = http_method.upper()
            self.uri = uri
            self.proto_version = proto_version

        def pack(self)->'str':
            return  f'{self.http_method} {self.uri} {self.proto_version}'



    def __init__(self, reader: 'StreamReader', writer: 'StreamWriter',
                 name: 'str' = "http", id: 'int' = 1, print_message: 'bool' = True):
        self._reader = reader
        self._writer = writer

        self._id = id
        self._name = name

        self._print_message = print_message

    def version(self) -> ['int', 'str']:
        return self._id, self._name

    def un_pack(self, message: 'Message'):
        pass

    async def pack(self, message: 'Message'):
        # pack request
        http_request = self.__pack_request(message)
        # message.set_size(len(http_request))
        # write request
        self._writer.write(http_request)
        await self._writer.drain()
        if self._print_message:
            logger.info(f'Send HTTP Message:\n{http_request}')

    def __pack_request(self, message: 'Message')->'bytes':
        # first line
        parse_result = urlparse(message.service_method)
        uri = f'{parse_result.path}?{parse_result.query}' if len(parse_result.query) != 0 else f'{parse_result.path}'
        first_line  = self.Request_First_Line(message.msg_type, uri).pack()
        # header
        header = {}
        for key, value in message.meta.items():
            header[key] = value
        header[self.__Header.host] = parse_result.netloc
        header[self.__Header.accept_encoding] = "gzip"
        # body
        body_bytes = message.marshal_body()
        # do transfer pipe
        if len(body_bytes) != 0:
            content_encoding = []
            for filter in message.xfer_pipe.filters:
                if filter.id() != XFER_PIPE_GZIP:
                    raise Exception(f'unsupport xfer filter: {filter.name()}')
                body_bytes = filter.on_pack(body_bytes)
                content_encoding.append(filter.name())
            header[self.__Header.content_encoding] = ";".join(content_encoding)
            header[self.__Header.content_type] = get_content_type(message.body_codec, "text/plain;charset=utf-8")
            header[self.__Header.content_length] = len(body_bytes)
            body_bytes = self.__crlf.encode(DEFAULT_CODING) + body_bytes
        # pack
        http_request = first_line
        for key, value in header.items():
            http_request = http_request + f'{key}{self.__colon}{self.__space}{value}{self.__line_feed}'
        http_request = http_request.encode(DEFAULT_CODING) +  body_bytes
        return http_request


    @staticmethod
    def __pack_request_first_line(message: 'Message')->'str':
        parse_result = urlparse(message.service_method)
        uri = f'{parse_result.path}?{parse_result.query}' if len(parse_result.query) != 0 else f'{parse_result.path}'
        request_first_line = HttpProto.Request_First_Line(message.msg_type, uri)
        return request_first_line.pack()

    async def __unpack_response_first_line(self,):
        first_line = await self._reader.readline()
        content = first_line.decode(DEFAULT_CODING)
        proto_version, status_code, status_reason = content.replace('\r\n', '').split(self.__space)
        return proto_version, status_code, status_reason

    async def __unpack_response_header(self, message):
        while True:
            content = await self._reader.readline()
            content = content.decode(DEFAULT_CODING)
            content = content.replace('\r\n', '').replace(' ', '')
            if len(content) == 0:
                # blank line, to read body
                break
            # 尝试读取各种header
            header_line = content.split(self.__colon, 1)
            if len(header_line) != 2:
                raise Exception("receive error response")
            header_key = header_line[0]
            header_value = header_line[1]
            # meta
            message.meta[header_key.decode(DEFAULT_CODING)] = header_value
            if header_key == self.__content_type__:
                message.set_body_codec(get_body_codec(header_value, codec.NONE_CODEC_ID))
                continue
            if header_key == self.__content_length__:
                body_size = int(header_value)
                size += body_size
                continue
            if header_key == self.__content_encoding__:
                filter = XferFilterMap.get_by_name(header_value)
                message.xfer_pipe.filters.append(filter)
                continue
            if header_key == self.__x_seq__:
                message.set_seq(int(header_value))
                continue
            if header_key == self.__x_mtype__:
                message.set_mtype(header_value)
                continue

    def __unpack_response_body(self, content: 'str') -> 'bytes':
        pass

    async def un_pack(self, message: 'Message') -> 'Message':
        proto_version, status_code, status_reason =await self.__unpack_response_first_line()



        size = 5
        m = b''
        # read http mark
        http_mark = await self._reader.read(size)
        first_line = await self._reader.readline()
        size += len(first_line)
        first_line = http_mark + first_line
        m = m + first_line
        # request
        if self.__http_response_mark__ != http_mark:
            raise Exception("receive error response")
        message.set_mtype(TYPE_REPLY)
        # status line
        status_line = first_line.replace(b'\r\n', b'').split(self.__space__, 1)
        if len(status_line) != 2:
            raise Exception("receive error response")
        if status_line[1] == self.__ok__:
            message.set_status(200)
        elif status_line[1] == self.__biz_err__:
            raise Exception("unsupport http code")
        body_size = 0
        # time line
        time_line = await self._reader.readline()
        m = m + time_line
        # header
        while True:
            content = await self._reader.readline()
            m = m + content
            content = content.replace(b'\r\n', b'').replace(b' ', b'')
            if len(content) == 0:
                # blank line, to read body
                break
            # 尝试读取各种header
            header_line = content.split(self.__colon__, 1)
            if len(header_line) != 2:
                raise Exception("receive error response")
            header_key = header_line[0]
            header_value = header_line[1].decode(DEFAULT_CODING)
            # meta
            message.meta[header_key.decode(DEFAULT_CODING)] = header_value
            if header_key == self.__content_type__:
                message.set_body_codec(get_body_codec(header_value, codec.NONE_CODEC_ID))
                continue
            if header_key == self.__content_length__:
                body_size = int(header_value)
                size += body_size
                continue
            if header_key == self.__content_encoding__:
                filter = XferFilterMap.get_by_name(header_value)
                message.xfer_pipe.filters.append(filter)
                continue
            if header_key == self.__x_seq__:
                message.set_seq(int(header_value))
                continue
            if header_key == self.__x_mtype__:
                message.set_mtype(header_value)
                continue

        if body_size == 0:
            raise Exception("received response body size is zero")
        message.set_size(size)
        # body
        body_bytes = await self._reader.read(body_size)
        m = m + body_bytes
        body_bytes = message.xfer_pipe.on_unpack(body_bytes)
        message.set_body(message.un_marshal_body(body_bytes))
        if self._print_message:
            logger.info(f'receive HTTP Message:\n{m}')
        return message



class HttpProto(BaseProto):
    __get_method__ = 'GET'
    __post_method__ = 'POST'
    __http_version__ = 'HTTP/1.1'
    __crlf__ = '\r\n'

    __ok__ = b'200 OK'
    __biz_err__ = b'299 Business Error'

    __http_response_mark__ = b'HTTP/'
    __space__ = b' '
    __colon__ = b':'
    __content_type__ = b'Content-Type'
    __content_length__ = b'Content-Length'
    __content_encoding__ = b'Content-Encoding'
    __x_seq__ = b'X-Seq'
    __x_mtype__ = b'X-Mtype'
    __error_bad_http_msg__ = b'bad HTTP message'
    __error_unsupport_http_code__ = b'unsupport HTTP status code'

    def __init__(self, reader: 'StreamReader', writer: 'StreamWriter',
                 name: 'str' = "http", id: 'int' = 1, print_message: 'bool' = True):
        self._reader = reader
        self._writer = writer

        self._id = id
        self._name = name

        self._print_message = print_message

        self._parser = httptools.HttpResponseParser(self)

    def version(self) -> ['int', 'str']:
        return self._id, self._name

    async def pack(self, message: 'Message'):
        # marshal body
        body_bytes = message.marshal_body()
        # pack request
        http_request = self._pack_request(message, body_bytes)
        message.set_size(len(http_request))
        # write request
        self._writer.write(http_request)
        await self._writer.drain()
        if self._print_message:
            logger.info(f'Send HTTP Message:\n{http_request}')

    def _pack_request(self, message: 'Message',
                      body_bytes: 'bytearray') -> 'bytes':
        header = Args()
        parse_result = urlparse(message.service_method)
        if parse_result.netloc != "":
            header["Host"] = parse_result.netloc
        if "User-Agent" not in header:
            header["User-Agent"] = "sprite-httpproto/1.1"
        # do transfer pipe
        for filter in message.xfer_pipe.filters:
            if filter.id() != XFER_PIPE_GZIP:
                raise Exception(f'unsupport xfer filter: {filter.name()}')
            body_bytes = filter.on_pack(body_bytes)
            header["Content-Encoding"] = "gzip"
            header["Content-Encoding"] = filter.name()
        header["X-Seq"] = str(message.seq)
        header["X-Mtype"] = str(message.mtype)
        if message.http_method == HTTP_METHOD_POST:
            header["Content-Type"] = get_content_type(message.body_codec, "text/plain;charset=utf-8")
        header["Content-Length"] = str(len(body_bytes))
        header["Accept-Encoding"] = "gzip"
        # add arg
        for key, value in message.meta.items():
            header[key] = value
        http_request = self.http_request_first_line(message.http_method, parse_result)
        for key, value in header.items():
            http_request = http_request + f'{key}: {value}\r\n'
        http_request = http_request.encode(DEFAULT_CODING) + b'\r\n' + body_bytes
        return http_request

    @classmethod
    def http_request_first_line(cls, http_method: 'str', parse_result) -> 'str':
        if len(http_method) == 0:
            http_method = cls.__get_method__
        if len(parse_result.query) == 0:
            first_line = f'{http_method} {parse_result.path} {cls.__http_version__}{cls.__crlf__}'
        else:
            first_line = f'{http_method} {parse_result.path}?{parse_result.query} {cls.__http_version__}{cls.__crlf__}'
        return first_line

    async def un_pack(self, message: 'Message') -> 'Message':
        size = 5
        m = b''
        # read http mark
        http_mark = await self._reader.read(size)
        first_line = await self._reader.readline()
        size += len(first_line)
        first_line = http_mark + first_line
        m = m + first_line
        # request
        if self.__http_response_mark__ != http_mark:
            raise Exception("receive error response")
        message.set_mtype(TYPE_REPLY)
        # status line
        status_line = first_line.replace(b'\r\n', b'').split(self.__space__, 1)
        if len(status_line) != 2:
            raise Exception("receive error response")
        if status_line[1] == self.__ok__:
            message.set_status(200)
        elif status_line[1] == self.__biz_err__:
            raise Exception("unsupport http code")
        body_size = 0
        # time line
        time_line = await self._reader.readline()
        m = m + time_line
        # header
        while True:
            content = await self._reader.readline()
            m = m + content
            content = content.replace(b'\r\n', b'').replace(b' ', b'')
            if len(content) == 0:
                # blank line, to read body
                break
            # 尝试读取各种header
            header_line = content.split(self.__colon__, 1)
            if len(header_line) != 2:
                raise Exception("receive error response")
            header_key = header_line[0]
            header_value = header_line[1].decode(DEFAULT_CODING)
            # meta
            message.meta[header_key.decode(DEFAULT_CODING)] = header_value
            if header_key == self.__content_type__:
                message.set_body_codec(get_body_codec(header_value, codec.NONE_CODEC_ID))
                continue
            if header_key == self.__content_length__:
                body_size = int(header_value)
                size += body_size
                continue
            if header_key == self.__content_encoding__:
                filter = XferFilterMap.get_by_name(header_value)
                message.xfer_pipe.filters.append(filter)
                continue
            if header_key == self.__x_seq__:
                message.set_seq(int(header_value))
                continue
            if header_key == self.__x_mtype__:
                message.set_mtype(header_value)
                continue

        if body_size == 0:
            raise Exception("received response body size is zero")
        message.set_size(size)
        # body
        body_bytes = await self._reader.read(body_size)
        m = m + body_bytes
        body_bytes = message.xfer_pipe.on_unpack(body_bytes)
        message.set_body(message.un_marshal_body(body_bytes))
        if self._print_message:
            logger.info(f'receive HTTP Message:\n{m}')
        return message
