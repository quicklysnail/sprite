# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019/7/3 19:28'

import inspect
import traceback
import time
import asyncio
import threading
from typing import Coroutine, Union, Callable
from asyncio import AbstractEventLoop, Task, Future
from threading import Thread, Event
from asyncio import Queue
from asyncio.locks import Lock
from functools import partial
from sprite.const import COROUTINE_SLEEP_TIME, THREAD_SLEEP_TIME
from sprite.settings import Settings
from sprite.utils.log import get_logger
from sprite.utils.utils import SingletonMetaClass
from sprite.const import *

logger = get_logger()

"""
协程池
"""

# 默认最大协程数量
Defaultmax_coroutine_amount = 256 * 1024
# 默认每一个协程的空闲时间
Defaultmax_coroutineIdle_time = 10

StopSignal = -1


class NotTooMangStartCorroutineException(Exception): pass


class NotStartCoroutineException(Exception): pass


class NotManyCoroutineException(Exception): pass


class NotReSetCoriutinePoolException(Exception): pass


class CoroutinePooolStuffedException(Exception): pass


class TaskQueue:
    def __init__(self):
        self._lastUseTime = time.time()
        # 协程的队列
        self._queue = Queue()

    async def addTask(self, task: 'Task'):
        await self._queue.put(task)

    async def getTask(self) -> Coroutine:
        return await self._queue.get()

    def updateTime(self):
        self._lastUseTime = time.time()

    @property
    def lastUseTime(self) -> float:
        return self._lastUseTime

    def __len__(self):
        return self._queue.qsize()


class PyCoroutinePool(metaclass=SingletonMetaClass):
    def __init__(self, max_coroutine_amount: int = Defaultmax_coroutine_amount,
                 max_coroutineIdle_time: int = Defaultmax_coroutineIdle_time,
                 most_stop: bool = False, loop: AbstractEventLoop = None):
        self._max_coroutine_amount = max_coroutine_amount
        self._max_coroutineIdle_time = max_coroutineIdle_time
        self._most_stop = most_stop
        self._lock = Lock()
        self._ready = []
        self._loop = loop or asyncio.get_event_loop()

        self._state_signal = None
        self._state = COROUTINE_POOL_STATE_STOPPED
        self._state_lock = threading.Lock()

        self._coroutineCount = 0

    def reset(self, **kwargs):
        if self.is_running() or self._is_stopping():
            raise NotReSetCoriutinePoolException("协程池已经开启或者还未关闭")
        self._max_coroutine_amount = kwargs.get("max_coroutine_amount") if kwargs.get("max_coroutine_amount",
                                                                                      None) else Defaultmax_coroutine_amount
        self._max_coroutineIdle_time = kwargs.get("max_coroutineIdle_time") if kwargs.get("max_coroutineIdle_time",
                                                                                          None) else Defaultmax_coroutineIdle_time
        self._most_stop = kwargs.get("most_stop") if kwargs.get("most_stop", None) else False

        self._loop = kwargs.get("loop") if kwargs.get("loop", None) else asyncio.get_event_loop()

    @property
    def state(self):
        with self._state_lock:
            return self._state

    def is_running(self) -> bool:
        with self._state_lock:
            return (self._state == COROUTINE_POOL_STATE_RUNNING)

    def _is_stopping(self) -> bool:
        with self._state_lock:
            return (self._state == COROUTINE_POOL_STATE_STOPPING)

    def _is_stopped(self, waiting: bool = False) -> bool:
        state = False
        while True:
            with self._state_lock:
                state = self._state
            if state == COROUTINE_POOL_STATE_STOPPED:
                state = True
                break
            else:
                if not waiting:
                    state = False
                    break
                self._state_signal.wait()
                state = True
        return state

    # 线程阻塞判断协程池时候已经停止运行
    def is_stopped(self, waiting: bool = False) -> bool:
        return self._is_stopped(waiting)

    # 强制停止协程池,暂时不可用
    def force_stop(self):
        # if self._stopEvent is None:
        #     raise NotStartCoroutineException("协程池还未开启")
        # if self._stopEvent.is_set():
        #     logger.error("已经启动stop流程了，不用再发起了！！")
        #     return
        # self._stopEvent.set()
        # asyncio.run_coroutine_threadsafe(self._cancel_tasks(), self._loop)
        # self._stopEventLoopSignal.wait()
        # self._loop.close()
        pass

    # 软关闭协程池
    def stop(self):
        if not self.is_running():
            raise NotStartCoroutineException("协程池不在运行状态")
        with self._state_lock:
            self._state = COROUTINE_POOL_STATE_STOPPING
        asyncio.run_coroutine_threadsafe(self._stop(), self._loop)
        asyncio.run_coroutine_threadsafe(self._stop_on_wait(), self._loop)

    async def _stop(self):
        async with self._lock:
            # 对于已经完成任务的协程，进行退出
            self._most_stop = True
            for taskQueue in self._ready:
                # 没有完成的协程，提前发出通知，完成后，需要退出
                await taskQueue.addTask(StopSignal)

    async def _stop_on_wait(self):
        await self._cancel_tasks()
        self._loop.stop()
        logger.info(f'协程池关闭')
        with self._state_lock:
            self._state = COROUTINE_POOL_STATE_STOPPED
            self._state_signal.set()

    # 取消任务
    async def _cancel_tasks(self):
        tasks = []
        # 获取所有在事情循环中的协程
        for task in asyncio.Task.all_tasks():
            if not task.current_task() and not task.cancelled():
                # 取消协程
                tasks.append(task.cancel())
        await asyncio.gather(*tasks, return_exceptions=True)

    # 开始运行协程池，进行一些初始化工作
    def start(self, loop: AbstractEventLoop = None):
        if self.is_running() or self._is_stopping():
            raise NotTooMangStartCorroutineException("协程池已经开启或者还未关闭")
        with self._state_lock:
            self._state = COROUTINE_POOL_STATE_RUNNING
            self._state_signal = Event()
        logger.info("开启协程池")
        # 在子线程创建事件循环，并运行
        self._init()

    def _init(self):
        # 创建事件
        run_loop_thread = Thread(target=self._start_subthread_loop, args=(self._loop,))  # 在子线程运行事件循环
        # 开启子线程的协程时间循环
        run_loop_thread.start()
        asyncio.run_coroutine_threadsafe(self._daemon(), self._loop)

    def _start_subthread_loop(self, loop):
        asyncio.set_event_loop(loop)
        # 阻塞着一直运行事件循环，直到被调用stop    loop.stop()
        loop.run_forever()

    async def _clean(self):
        current_time = time.time()
        async with self._lock:
            for task_queue in self._ready:
                if self._is_clear(task_queue, current_time):
                    # 释放协程
                    await task_queue.addTask(StopSignal)

    def _is_clear(self, task_queue: TaskQueue, current_time: float = None) -> bool:
        if current_time is None:
            current_time = time.time()
        if len(task_queue) == 0:
            if current_time - task_queue.lastUseTime > self._max_coroutineIdle_time:
                return True
        return False

    async def _daemon(self):
        # 协程进行守护工作
        while self.is_running():
            await self._clean()
            await asyncio.sleep(self._max_coroutineIdle_time)

    # 添加任务执行
    def go(self, task: Coroutine, done_callback: 'Callable' = None, *args) -> 'Task':
        assert inspect.iscoroutine(task), "只能添加python协程实例"
        if not self.is_running():
            raise NotStartCoroutineException("协程池不在运行状态，无法提交任务！！")
        async_task = self._loop.create_task(task)
        if done_callback:
            async_task.add_done_callback(self.decorate_callback_func(done_callback, *args))
        asyncio.run_coroutine_threadsafe(self._goCoroutine(async_task), self._loop)
        return async_task

    def decorate_callback_func(self, callback: 'Callable', *args) -> 'Callable':
        """
        装饰asyncio.Task的done_callback回调函数
        :param callback: callback回调函数
        :param args: 回调函数参数
        :return:
        """

        def decorated_callback(future: "Future"):
            callback(*args)

        return decorated_callback

    async def _goCoroutine(self, task: 'Task'):
        taskQueue = await self._getIdleCoroutine()
        if taskQueue is None:
            raise NotManyCoroutineException("没有正在运行的协程")
        await taskQueue.addTask(task)

    # 获取空闲协程，不存在就新创建一个
    async def _getIdleCoroutine(self) -> TaskQueue:
        """
        协程未达到最大值之前，不断创建新的协程
        达到最大值之后，就取最可能空闲的协程来执行
        :return:
        """
        taskQueue = None
        createCoroutine = False
        async with self._lock:
            if self._coroutineCount < self._max_coroutine_amount:
                createCoroutine = True
                taskQueue = TaskQueue()
                self._ready.append(taskQueue)
            else:
                # 按照队列长度从小到大排序
                self._ready = sorted(self._ready, key=lambda x: len(x))
                taskQueue = self._ready[0]
            if createCoroutine:
                # 新创建协程
                asyncio.run_coroutine_threadsafe(self._executeTask(taskQueue), self._loop)
                self._coroutineCount += 1
        return taskQueue

    async def _executeTask(self, taskQueue: TaskQueue):
        while True:
            # 阻塞等待任务
            task = await taskQueue.getTask()
            if task == StopSignal:
                # 接收到停止信号
                break
            # 执行任务
            try:
                await task
            except:
                logger.error(f'find one error: {traceback.format_exc()}')
            # 更新任务完成时间
            taskQueue.updateTime()
            # 每一个协程完成任务后，是否需要停止这个协程
            if len(taskQueue) == 0 and await self._isRelease():
                # 停掉目前的协程
                break
        async with self._lock:
            # 去除无效任务队列
            self._ready.remove(taskQueue)
            self._coroutineCount -= 1

    async def _isRelease(self) -> bool:
        async with self._lock:
            if self._most_stop:
                return True
            return False

    @classmethod
    def from_setting(cls, settings: Settings):
        max_coroutine_amount = settings.getint("max_coroutine_amount")
        max_coroutineIdle_time = settings.getint("max_coroutineIdle_time")
        most_stop = settings.getbool("most_stop")
        obj = cls(max_coroutine_amount=max_coroutine_amount,
                  max_coroutineIdle_time=max_coroutineIdle_time,
                  most_stop=most_stop)
        return obj

    @property
    def loop(self) -> AbstractEventLoop:
        return self._loop


coroutine_pool = PyCoroutinePool()
