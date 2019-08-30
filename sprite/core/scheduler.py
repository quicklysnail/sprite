# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019/8/16 19:45'

from typing import Union
from sprite.utils.queues import Queue
from sprite.http.request import Request
from sprite.utils.queues import PriorityQueue
from sprite.utils.pybloomfilter import ScalableBloomFilter
from sprite.settings import Settings


# 正在处理中的Request
class Slot:
    def __init__(self):
        self.process_request = Queue()

    async def addRequest(self, req: Request):
        await self.process_request.put(req)

    def getRequest(self) -> Request:
        return self.process_request.get_nowait()

    def has_pending_request(self) -> bool:
        return not self.process_request.empty()

    # 告诉队列，一个任务已经完成
    def toDone(self):
        self.process_request.task_done()

    async def join(self):
        self.process_request.join()


# 调度器
class Scheduler:
    def __init__(self, df=None, queue=None, long_save: bool = False, job_dir: str = None):
        self._priorityQueue = queue or PriorityQueue()
        self._df = df or ScalableBloomFilter()
        self._long_save = long_save
        self._job_dir = job_dir

    @classmethod
    def from_settings(cls, settings: Settings):
        initial_capacity = settings.getint("INITIAL_CAPACITY")
        error_rate = settings.getfloat("ERROR_RATE")
        long_save = settings.getbool("LONG_SAVE")
        job_dir = settings.get("JOB_DIR")
        obj = cls(df=ScalableBloomFilter(initial_capacity=initial_capacity),
                  queue=PriorityQueue(), long_save=long_save, job_dir=job_dir)
        return obj

    def has_pending_requests(self):
        return len(self._priorityQueue) > 0

    # 请求加入队列
    def enqueue_request(self, request: Request) -> bool:
        request_unique = request.toUniqueStr()
        if not request.dont_filter and request_unique in self._df:
            return True
        self._df.add(request_unique)
        self._priorityQueue.push(request, request.priority)
        return True

    # 取出request
    def next_request(self) -> Union[Request, None]:
        try:
            request, _ = self._priorityQueue.pop()
            return request
        except IndexError:
            # 队列为空
            return None

    def __len__(self):
        return len(self._priorityQueue)

    def close(self):
        pass
