# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019/7/3 19:28'

from typing import Coroutine, Callable, Union
import time
import asyncio
from asyncio import AbstractEventLoop
from threading import Thread, Event
from asyncio import Queue
from asyncio.locks import Lock
import traceback
from sprite.settings import Settings
from sprite.utils.log import get_logger

logger = get_logger()

"""
协程池
"""

# 默认最大协程数量
DefaultMaxCoroutinesAmount = 256 * 1024
# 默认每一个协程的空闲时间
DefaultMaxCoroutineIdleTime = 10

StopSingal = -1


class NotTooMangStartCorroutineException(Exception):
    pass


class NotStartCoroutineException(Exception):
    pass


class NotManyCoroutineException(Exception):
    pass


class CoroutineTask:
    def __init__(self, *args, **kwargs):
        pass

    @staticmethod
    def task(coroutine_func: Callable):
        async def dosomething(*args, **kwargs):
            await coroutine_func(*args, **kwargs)

        return dosomething


class TaskQueue:
    def __init__(self):
        self._lastUseTime = time.time()
        self._queue = Queue()  # 协程的队列

    async def addTask(self, task: Coroutine):
        await self._queue.put(task)

    async def getTask(self) -> Coroutine:
        return await self._queue.get()

    def updateTime(self):
        self._lastUseTime = time.time()

    @property
    def lastUseTime(self) -> float:
        return self._lastUseTime


"""
每一个协程完成后，会自动加入准备队列，守护协程，会不断的检查这个队列，看准备队列里面的等待协程是否等待时候过长，等待时候过长的协程会被停掉
"""


class PyCoroutinePool:
    def __init__(self, maxCoroutineAmount: int = DefaultMaxCoroutinesAmount,
                 maxCoroutineIdleTime: int = DefaultMaxCoroutineIdleTime,
                 mostStop: bool = False, loop: AbstractEventLoop = None):
        self._maxCoroutineAmount = maxCoroutineAmount
        self._maxCoroutineIdleTime = maxCoroutineIdleTime
        self._mostStop = mostStop
        self._lock = Lock()
        self._ready = []
        self._loop = loop or asyncio.get_event_loop()
        self._stopEventLoopSingal = Event()
        self._stopEvent = None
        self._coroutinesCount = 0

    # 强制停止协程池,暂时不可用
    def force_stop(self):
        if self._stopEvent is None:
            raise NotStartCoroutineException("协程池还未开启")
        if self._stopEvent.is_set():
            logger.error("已经启动stop流程了，不用再发起了！！")
            return
        self._stopEvent.set()
        asyncio.run_coroutine_threadsafe(self._cancel_tasks(), self._loop)
        # self._stopEventLoopSingal.wait()
        # self._loop.close()

    async def _cancel_tasks(self):  # 取消任务
        tasks = []
        for task in asyncio.Task.all_tasks():  # 获取所有在事情循环中的task
            if not task.current_task() and not task.cancelled():
                tasks.append(task.cancel())  # 取消task
        # print("开始取消任务")
        await asyncio.gather(*tasks, return_exceptions=True)


    # 线程阻塞判断协程池时候已经停止运行
    def isStoped(self) -> bool:
        self._stopEventLoopSingal.wait()
        return True

    # 软关闭协程池
    def stop(self):
        if self._stopEvent is None:
            raise NotStartCoroutineException("协程池还未开启")
        if self._stopEvent.is_set():
            # logger.error("已经启动stop流程了，不用再发起了！！")
            return
        self._stopEvent.set()
        asyncio.run_coroutine_threadsafe(self._stop(), self._loop)
        asyncio.run_coroutine_threadsafe(self._stop_on_wait(), self._loop)

    async def _stop(self):
        async with self._lock:
            # 对于已经完成任务的协程，进行退出
            for taskQueue in self._ready:
                await taskQueue.addTask(None)
            # 没有完成的协程，提前发出通知，完成后，需要退出
            self._mostStop = True
            # print("发送信号完毕！！")

    async def _stop_on_wait(self):
        # while len(self._ready) > 0:
        #     asyncio.sleep(0.001)
        await self._cancel_tasks()
        self._loop.stop()
        self._stopEventLoopSingal.set()
        logger.info(f'协程池关闭')

    # 开始运行协程池，进行一些初始化工作
    def start(self, loop=None):
        if self._stopEvent is not None:
            raise NotTooMangStartCorroutineException("不能多次开启协程池")
        logger.info("开启协程池")
        self._stopEvent = Event()  # 创建事件
        # if self._loop is None:
        #     self._loop = loop or asyncio.get_event_loop()

        self._start()

    def _start(self):
        # asyncio.run_coroutine_threadsafe(self._daemon(), loop)
        self._init()  # 在子线程创建事件循环，并运行
        asyncio.run_coroutine_threadsafe(self._daemon(), self._loop)  # 开启协程

    def _init(self):
        run_loop_thread = Thread(
            target=self._start_subthread_loop, args=(self._loop,))  # 在子线程运行事件循环
        run_loop_thread.start()

    def _start_subthread_loop(self, loop):
        asyncio.set_event_loop(loop)
        # print("开启协程事件循环")
        loop.run_forever()  # 阻塞着一直运行事件循环，直到被调用stop    loop.stop()
        # print("退出事件循环监听！！")

    async def _clean(self):
        scratch = []
        maxCoroutineIdleTime = self._maxCoroutineIdleTime
        currentTime = time.time()
        async with self._lock:
            n = len(self._ready)
            i = 0
            while i < n:
                # 比较时间
                if currentTime - self._ready[i].lastUseTime > maxCoroutineIdleTime:
                    i += 1
                else:
                    break
            if i > 0:
                # 选出没有空闲的协程,抛弃空闲过久的协程
                scratch = self._ready[:i]
                self._ready = self._ready[i:]  # 第i位不满足
                # for index in range(0, i):
                #     self._ready.pop(index)
            # 停掉空闲过久的协程
            for taskQueue in scratch:
                await taskQueue.addTask(None)
        # print("清理一次完毕")

    async def _daemon(self):
        # 协程进行守护工作
        # print("开启更新协程")
        while not self._stopEvent.is_set():
            await self._clean()
            await asyncio.sleep(self._maxCoroutineIdleTime)
        # print("退出清理任务")

    # 添加任务执行
    def go(self, task: Coroutine) -> bool:
        try:
            asyncio.run_coroutine_threadsafe(
                self._goCoroutine(task), self._loop)
            return True
        except NotManyCoroutineException as e:
            print(e)
            return False

    async def _goCoroutine(self, task: Coroutine):
        taskQueue = await self._getIdleCoroutine()
        # print("获取到一个任务队列实例")
        if taskQueue is None:
            # print("发生错误")
            raise NotManyCoroutineException("没有更多协程了")

        await taskQueue.addTask(task)
        # print("向一个任务队列实例添加任务成功")

    # 获取空闲协程，不存在就新创建一个
    async def _getIdleCoroutine(self) -> Union[TaskQueue, None]:
        taskQueue = None
        createCoroutine = False
        async with self._lock:
            n = len(self._ready) - 1
            if n < 0:
                if self._coroutinesCount < self._maxCoroutineAmount:
                    createCoroutine = True
                    self._coroutinesCount += 1
            else:
                # taskQueue = self._ready[n]
                # self._ready.pop(n)  # 去掉这个task

                taskQueue = self._ready.pop(n)  # 去掉这个task
        if taskQueue is None:
            if not createCoroutine:
                return None
            taskQueue = TaskQueue()
            # await self._executeTask(newTaskQueue) # 在协程中执行任务
            # 新开启一个协程并让这个协程进入准备阶段
            asyncio.run_coroutine_threadsafe(
                self._executeTask(taskQueue), self._loop)
        return taskQueue

    async def _executeTask(self, taskQueue):
        while True:
            # print("开始接受协程任务！！！")
            task = await taskQueue.getTask()  # 阻塞等待任务
            if task is None:
                # 接收到停止信号
                # print("接收到停止信号！")
                break
            # 执行任务
            # print("接收到一个协程任务")
            try:
                await task
            except:
                logger.error("find one error: ")
                traceback.print_exc()
            # 每一个协程完成任务后，是否需要停止这个协程
            if await self._isRelease(taskQueue):
                # 停掉目前的协程
                # print("接收到stop的命令")
                break
        async with self._lock:
            # print("正在运行的协程数量—1")
            self._coroutinesCount -= 1

    async def _isRelease(self, taskQueue: TaskQueue) -> bool:
        taskQueue.updateTime()  # 更新任务完成时间
        async with self._lock:
            if self._mostStop:
                return True
            # 任务完成的协程就加入到准备队列里面
            self._ready.append(taskQueue)
            return False

    @classmethod
    def from_setting(cls, settings: Settings):
        maxCoroutineAmount = settings.getint("MAXCOROUTINEAMOUNT")
        maxCoroutineIdleTime = settings.getint("MAXCOROUTINEIDLETIME")
        mostStop = settings.getbool("MOSTSTOP")
        obj = cls(maxCoroutineAmount=maxCoroutineAmount,
                  maxCoroutineIdleTime=maxCoroutineIdleTime,
                  mostStop=mostStop)
        return obj

    @property
    def loop(self):
        return self._loop


if __name__ == '__main__':
    @CoroutineTask.task
    async def sleepTask(task_id: int, sleep_time: int):
        print(f'在协程中启动任务 {task_id}')
        await asyncio.sleep(sleep_time)
        a = [1]
        print(a[9])
        print(f'{task_id} 任务结束')

    async def stop_corountine(coroutine_pool: PyCoroutinePool):
        coroutine_pool.stop()

    coroutine_pool = PyCoroutinePool()
    coroutine_pool.start()
    for index in range(10):
        coroutine_pool.go(sleepTask(task_id=index, sleep_time=index))

    time.sleep(3)
    print("主线程发出stop信号")
    # coroutine_pool.go(stop_corountine(coroutine_pool))
    coroutine_pool.stop()
