# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019/10/12 19:16'


class RingWheelTask:

    def __init__(self, timeout: int):
        self._timeout = timeout
        self._index = 0

    @property
    def timeout(self) -> int:
        return self._timeout

    @property
    def index(self) -> int:
        return self._index

    def run(self):
        pass

    def init(self, ring_size: int):
        self._index = self._timeout % ring_size


class RingBufferWheel:
    def __init__(self, ring_size: int, ):
        self._ring_size = ring_size
        self._ring_units = [[] for _ in range(self._ring_size)]
        self._current_index = 0

    def addTask(self, task: 'RingWheelTask'):
        task.init(self._ring_size)
        target_index = task.index
        self._ring_units[target_index].append(task)

    def _run_current_index_task(self, current_index: int):
        tasks = self._ring_units[current_index]
        for task in tasks:
            task.run()

    def start(self):

