# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019/8/16 19:45'

import os
import pickle
import traceback
from sprite.utils.queues import Queue
from sprite.utils.http.request import Request
from sprite.utils.queues import PriorityQueue
from sprite.utils.log import get_logger
from sprite.utils.pybloomfilter import ScalableBloomFilter
from sprite.utils.request import request_to_dict, request_from_dict
from sprite.settings import Settings
from sprite.exceptions import TypeNotSupport, SchedulerEmptyException

logger = get_logger()


# 正在处理中的Request
class Slot:
    def __init__(self):
        self.process_request = Queue()

    def addRequest(self, req: Request):
        self.process_request.put_nowait(req)

    def getRequest(self) -> Request:
        return self.process_request.get_nowait()

    def has_pending_request(self) -> bool:
        return not self.process_request.empty()

    # 告诉队列，一个任务已经完成
    def toDone(self):
        self.process_request.task_done()

    async def join(self):
        await self.process_request.join()


# 调度器
class Scheduler:
    def __init__(self, spider: "Spider", df=None, queue=None, long_save: bool = False, job_dir: str = None):
        self._spider = spider
        self._priorityQueue = queue or PriorityQueue()
        self._df = df or ScalableBloomFilter()
        self._long_save = long_save
        self._job_dir = job_dir

    @classmethod
    def from_settings(cls, settings: Settings, spider: "Spider"):
        initial_capacity = settings.getint("INITIAL_CAPACITY")
        error_rate = settings.getfloat("ERROR_RATE")
        long_save = settings.getbool("LONG_SAVE")
        job_dir = settings.get("JOB_DIR")
        obj = cls(spider=spider, df=ScalableBloomFilter(initial_capacity=initial_capacity, error_rate=error_rate),
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
    def next_request(self) -> Request:
        try:
            request, _ = self._priorityQueue.pop()
        except IndexError:
            # 队列为空
            raise SchedulerEmptyException("scheduler is empty")
        return request

    def __len__(self):
        return len(self._priorityQueue)

    def close(self):
        try:
            self._save_requests()
        except:
            logger.info(
                f'close scheduler, find one error: \n{traceback.format_exc()}')

    def start(self):
        try:
            self._load_requests()
        except:
            logger.info(
                f'start scheduler, find one error: \n{traceback.format_exc()}')

    def _save_requests(self):
        if self._long_save and self._job_dir is not None and os.path.exists(
                self._job_dir) and self.has_pending_requests():
            logger.info(f'save request')
            requests = []
            while True:
                try:
                    request = self.next_request()
                except SchedulerEmptyException:
                    break
                try:
                    requests.append(request_to_dict(request))
                except TypeNotSupport:
                    logger.info(
                        f'find one error: \n{traceback.format_exc()}')

            requests_file_path = os.path.join(self._job_dir, "requests.pickle")
            with open(requests_file_path, "wb") as f:
                pickle.dump(requests, f)

    def _load_requests(self):
        if self._long_save and self._job_dir is not None:
            requests_file_path = os.path.join(self._job_dir, "requests.pickle")
            if os.path.exists(requests_file_path):
                logger.info(f'load request')
                with open(requests_file_path, "rb") as f:
                    requests = pickle.load(f)
                for request in requests:
                    try:
                        self.enqueue_request(
                            request_from_dict(self._spider, request))
                    except TypeNotSupport:
                        logger.info(
                            f'find one error: \n{traceback.format_exc()}')
                # 删除requests缓存
                os.remove(requests_file_path)
