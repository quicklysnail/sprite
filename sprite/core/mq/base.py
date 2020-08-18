# -*- coding:utf-8 -*-


class BaseMQ:
    def put(self, data: 'bytes'):
        raise NotImplementedError("not implemented")

    def push(self) -> 'bytes':
        raise NotImplementedError("not implemented")