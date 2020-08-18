# -*- coding:utf-8 -*-


import os
import struct
import threading
import time
from queue import Queue
from typing import Tuple


class EmptyMessageException(Exception): pass


class MessageTooLongException(Exception): pass


class DiskQueueClosedException(Exception): pass


class BackendQueue:

    def put(self, data: 'bytes'):
        """
        :return:ƒ
        插入消息
        :param data:
        """
        raise NotImplementedError("not implemented")

    def read(self) -> 'bytes':
        """
        读取一条消息
        :return:
        """
        raise NotImplementedError("not implemented")

    def delete(self):
        """
        删除队列
        :return:
        """
        raise NotImplementedError("not implemented")

    def close(self):
        """
        关闭队列
        :return:
        """
        raise NotImplementedError("not implemented")

    def depth(self) -> 'int':
        """
        返回消息数量
        :return:
        """
        raise NotImplementedError("not implemented")

    def empty(self):
        """
        清空消息
        :return:
        """
        raise NotImplementedError("not implemented")


"""
文件格式
    文件名："name" + ".diskqueue.%06d.dat"
    消息大小+body
metadata元数据
    文件名："name" + .diskqueue.meta.dat
    metadata 数据包含5个字段, 内容如下：
        depth\nreadFileNum,readPos\nwriteFileNum,writePos
"""
"""
需求分析
    重启系统
        1.读取元信息，并重置属性
    写入消息
        1.读取消息的大小
        2.验证消息的大小是否合法
        3.获取以追加方式打开的文件句柄，和文件末尾的位置
        4.写入4个字节文件长度，写入消息的body，消息数量+1，写入位置+4+len(消息body)
        5.检查文件的大小（写入位置）是否查过文件最大大小，超过则文件编号+1，并关闭目前的文件句柄，并根据新的文件编号创建新的文件句柄

    读取消息
        1.获取以读的方式打开的文件句柄，获取读取的位置
        2.从文件中读取出下一条消息的长度,读取位置+4
        3.读取出消息的body，读取位置+len(消息body)
        5.检查读取的位置是否超过文件的最大长度，否则读取的文件编号+1，并关闭目前的文件句柄，并更新新的文件编号创建新的读取句柄
    保存元信息
        将读取的文件编号，文件位置，写入的文件编号，文件位置，消息的数量，写入元信息文件中
    读取元信息
        尝试将读取的文件编号，文件位置，写入的文件编号，文件位置，消息的数量，从元信息文件中读取出来并返回（没有搜索到元文件则创建一个新的元文件）

类属性分析
    常量属性
        文件名称模版常量
        元文件名称模版常量
    实例属性
        文件读写目录
        写文件句柄，写入位置
        读取文件句柄，读取位置
        消息的数量
    实例方法
        写入消息
        读取消息
        保存元信息
        读取元信息
        启动队列
"""
DEFAULT_DATA_LENGTH_SIZE = 4
DEFAULT_DATA_LENGTH_PACK_TEMPLATE = "i"


class DiskQueue(BackendQueue):
    __data_file_name_template = "{}.diskqueue.{}.dat"
    __meta_file_name_template = "{}.diskqueue.meta.dat"

    def __init__(self, dir_path: 'str', name: 'str', max_per_file_size: 'int' = 5 * 1024 * 1024,
                 max_message_size: 'int' = 1024):
        """
        基于磁盘的队列
        """
        self._dir_path = dir_path
        self._name = name
        self._max_per_file_size = max_per_file_size
        self._max_message_size = max_message_size

        self._meta_file_path = self._get_meta_file_path()

        self._reader_file_num = 0
        self._reader_file_position = 0
        self._reader_file_obj = None

        self._writer_file_num = 0
        self._writer_file_position = 0
        self._writer_file_obj = None

        self._read_file_skip_position = 0

        self._depth = 0

        self._lock = threading.Lock()
        self._running = True
        self._running_event = threading.Event()

        self._read_queue = Queue()
        self._read_event = threading.Event()
        self._read_event.set()

        self._init()

    @property
    def dir_path(self):
        return self._dir_path

    @property
    def name(self):
        return self._name

    def _read_meta_info_from_file(self, file_name: 'str'):
        with open(file_name, "rb") as f:
            self._unpack_meta_info(f.read())

    def _write_meta_info_to_file(self, file_name: 'str'):
        with open(file_name, 'wb') as f:
            meta_info = self._pack_meta_info()
            f.write(meta_info)

    def _pack_meta_info(self) -> 'bytes':
        return f'{self.depth}\n{self._reader_file_num},{self._reader_file_position}\n{self._writer_file_num},{self._writer_file_position}'.encode(
            "utf-8")

    def _unpack_meta_info(self, data: 'bytes'):
        depth, reader_file_num_reader_file_position, writer_file_num_writer_file_position = data.decode('utf-8').split(
            "\n")
        self._depth = int(depth)
        reader_file_num, reader_file_position = reader_file_num_reader_file_position.split(",")
        self._reader_file_num, self._reader_file_position = int(reader_file_num), int(reader_file_position)
        writer_file_num, writer_file_position = writer_file_num_writer_file_position.split(",")
        self._writer_file_num, self._writer_file_position = int(writer_file_num), int(writer_file_position)

    def _get_meta_file_path(self) -> 'str':
        return os.path.join(self.dir_path, self.__meta_file_name_template.format(self.name))

    def _get_data_file_path(self, file_num: 'int') -> 'str':
        return os.path.join(self.dir_path, self.__data_file_name_template.format(self.name, file_num))

    def _check_message_size(self, message_length: 'int'):
        if message_length > self._max_message_size:
            raise MessageTooLongException("too large message")

    def _init(self):
        # 1.判断元文件是否存在
        if os.path.exists(self._meta_file_path):
            self._read_meta_info_from_file(self._meta_file_path)
        else:
            self._write_meta_info_to_file(self._meta_file_path)
        # 2.初始化写文件句柄、读文件句柄
        self._writer_file_obj = open(self._get_data_file_path(self._writer_file_num), "ab")
        self._reader_file_obj = open(self._get_data_file_path(self._reader_file_num), "rb")

    def _io_loop(self):
        """
        消息预读取
        """
        while True:
            if self._running_event.is_set():
                break
            self._running_event.wait(timeout=5)
            if self._read_event.is_set():
                # 读取下一条消息
                self._lock.acquire()
                if (self._reader_file_num < self._writer_file_num) or (
                        self._reader_file_position < self._writer_file_position):
                    message_body, data_length = self._read_one_message()
                    self._read_file_skip_position = data_length
                    self._read_queue.put(message_body)
                    self._read_event.clear()
                self._lock.release()

    def put(self, data: 'bytes'):
        """
        插入消息
        :return:
        :param data:
        """
        self._lock.acquire()
        self._is_closed()
        data_length = self._write_one_message(data)
        self._update_meta_info("write", data_length)
        self._lock.release()

    def read(self) -> 'bytes':
        """
        读取一条消息
        :return:
        """
        self._lock.acquire()
        self._is_closed()
        # 先从内存队列里面读取消息
        if self._read_queue.qsize() != 0:
            # 从内存中消费一条消息
            message_body = self._read_queue.get()
            self._read_event.set()
            # 更新
            self._update_meta_info("read", self._read_file_skip_position)
        else:
            self._is_readable()
            message_body, data_length = self._read_one_message()
            self._update_meta_info("read", data_length)
        self._lock.release()
        return message_body

    @property
    def depth(self) -> 'int':
        self._lock.acquire()
        depth = self._depth
        self._lock.release()
        return depth

    def delete(self):
        pass

    def close(self):
        self._write_meta_info_to_file(self._meta_file_path)
        self._lock.acquire()
        self._reader_file_obj.close()
        self._writer_file_obj.close()
        self._running = False
        self._running_event.set()
        self._lock.release()

    def empty(self):
        pass

    def _read_one_message(self) -> Tuple['bytes', 'int']:
        data_length = DEFAULT_DATA_LENGTH_SIZE
        message_length = \
            struct.unpack(DEFAULT_DATA_LENGTH_PACK_TEMPLATE, self._reader_file_obj.read(DEFAULT_DATA_LENGTH_SIZE))[0]
        message_body = self._reader_file_obj.read(message_length)
        data_length += message_length
        return message_body, data_length

    def _write_one_message(self, data: 'bytes') -> 'int':
        data_length = DEFAULT_DATA_LENGTH_SIZE
        message_length = len(data)
        self._check_message_size(message_length)
        data_length += message_length

        self._writer_file_obj.write(struct.pack(DEFAULT_DATA_LENGTH_PACK_TEMPLATE, message_length))
        self._writer_file_obj.write(data)
        self._writer_file_obj.flush()
        return data_length

    def _is_readable(self):
        if self._reader_file_num == self._writer_file_num:
            if self._reader_file_position >= self._writer_file_position:
                raise EmptyMessageException("not message")
        elif self._reader_file_num > self._writer_file_num:
            raise EmptyMessageException("not message")

    def _is_closed(self):
        if not self._running:
            raise DiskQueueClosedException("disk queue is closed")

    def _update_meta_info(self, info_type: 'str', data_length: 'int'):
        if info_type == "read":
            self._reader_file_position += data_length
            self._depth -= 1
            if self._reader_file_position >= self._max_per_file_size:
                self._reader_file_num += 1
                self._reader_file_position = 0
                self._reader_file_obj.close()
                self._reader_file_obj = open(self._get_data_file_path(self._reader_file_num), "rb")
        elif info_type == "write":
            self._writer_file_position += data_length
            self._depth += 1
            if self._writer_file_position >= self._max_per_file_size:
                self._writer_file_num += 1
                self._writer_file_position = 0
                self._writer_file_obj.close()
                self._writer_file_obj = open(self._get_data_file_path(self._writer_file_num), "wb")


