# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019/8/16 19:58'

import collections
from collections import defaultdict, deque
from itertools import chain
from asyncio import coroutine, events, locks, QueueEmpty, QueueFull



# 实现优先队列
# deque 双向队列
class PriorityQueue:
    def __init__(self):
        self.negitems = defaultdict(deque)
        self.pzero = deque()
        self.positems = defaultdict(deque)

    def push(self, item, priority:int=0):  # 压入元素
        # 同样的权重，需按先进先出的原则来，不同的权重按权重大小来
        if priority == 0:
            self.pzero.appendleft(item)
        elif priority < 0:  # 权重大于或者小于0
            self.negitems[priority].appendleft(item)  # 权重小于0
        else:
            self.positems[priority].appendleft(item)  # 权重大于0

    def pop(self):  # 弹出元素
        # 弹出顺序:  先从权重小于0的开始选择
        #           再从权重等于0的开始选择
        #           最后从权重大于0的开始选择
        if self.negitems:
            priorities = list(self.negitems.keys())
            priorities.sort()  # 默认是升序排序，
            for priority in priorities:  # 从最小的权重开始遍历，看对应的双端队列是否为空
                deq = self.negitems[priority]
                if deq:  # 不为空，就弹出一个元素
                    t = (deq.pop(), priority)
                    if not deq:
                        del self.negitems[priority]  # 弹出元素为空后，删除掉双端队列
                    return t  # 返回值是由 值和权重组成的元组
        elif self.pzero:
            return (self.pzero.pop(), 0)
        else:
            priorities = list(self.positems.keys())
            priorities.sort()
            for priority in priorities:
                deq = self.positems[priority]
                if deq:
                    t = (deq.pop(), priority)
                    if not deq:
                        del self.positems[priority]
                    return t
        raise IndexError("pop from an empty queue")  # 优先队列为空

    def __len__(self):
        total = sum(len(v) for v in self.negitems.values()) + \
                len(self.pzero) + \
                sum(len(v) for v in self.positems.values())
        return total

    def __iter__(self):  # 优先队列遍历方法
        gen_negs = ((i, priority)
                    for priority in sorted(self.negitems.keys())
                    for i in reversed(self.negitems[priority]))
        gen_zeros = ((item, 0) for item in self.pzero)
        gen_pos = ((i, priority)
                   for priority in sorted(self.positems.keys())
                   for i in reversed(self.positems[priority]))
        return chain(gen_negs, gen_zeros, gen_pos)

    def __nonzero__(self):
        return bool(self.negitems or self.pzero or self.positems)




class Queue:
    """
    对标准库中的协程队列的细微改造
    """

    def __init__(self, maxsize=0, *, loop=None):
        if loop is None:
            self._loop = events.get_event_loop()
        else:
            self._loop = loop
        self._maxsize = maxsize

        # Futures.
        self._getters = collections.deque()
        # Futures.
        self._putters = collections.deque()
        self._unfinished_tasks = 0
        self._finished = locks.Event(loop=self._loop)
        self._finished.set()
        self._init(maxsize)


    def _init(self, maxsize):
        self._queue = collections.deque()

    def _get(self):
        return self._queue.popleft()

    def _put(self, item):
        self._queue.append(item)


    def _wakeup_next(self, waiters):
        while waiters:
            waiter = waiters.popleft()
            if not waiter.done():
                waiter.set_result(None)
                break

    def __repr__(self):
        return '<{} at {:#x} {}>'.format(
            type(self).__name__, id(self), self._format())

    def __str__(self):
        return '<{} {}>'.format(type(self).__name__, self._format())

    def _format(self):
        result = 'maxsize={!r}'.format(self._maxsize)
        if getattr(self, '_queue', None):
            result += ' _queue={!r}'.format(list(self._queue))
        if self._getters:
            result += ' _getters[{}]'.format(len(self._getters))
        if self._putters:
            result += ' _putters[{}]'.format(len(self._putters))
        if self._unfinished_tasks:
            result += ' tasks={}'.format(self._unfinished_tasks)
        return result

    def qsize(self):
        return len(self._queue)

    @property
    def maxsize(self):
        return self._maxsize

    def empty(self):
        if self._unfinished_tasks>0:
            return False
        return True

    def full(self):
        if self._maxsize <= 0:
            return False
        else:
            return self.qsize() >= self._maxsize

    @coroutine
    def put(self, item):
        while self.full():
            putter = self._loop.create_future()
            self._putters.append(putter)
            try:
                yield from putter
            except:
                putter.cancel()  # Just in case putter is not done yet.
                if not self.full() and not putter.cancelled():
                    # We were woken up by get_nowait(), but can't take
                    # the call.  Wake up the next in line.
                    self._wakeup_next(self._putters)
                raise
        return self.put_nowait(item)

    def put_nowait(self, item):
        if self.full():
            raise QueueFull
        self._put(item)
        self._unfinished_tasks += 1
        self._finished.clear()
        self._wakeup_next(self._getters)

    @coroutine
    def get(self):
        while self.empty():
            getter = self._loop.create_future()
            self._getters.append(getter)
            try:
                yield from getter
            except:
                getter.cancel()  # Just in case getter is not done yet.

                try:
                    self._getters.remove(getter)
                except ValueError:
                    pass

                if not self.empty() and not getter.cancelled():
                    # We were woken up by put_nowait(), but can't take
                    # the call.  Wake up the next in line.
                    self._wakeup_next(self._getters)
                raise
        return self.get_nowait()

    def get_nowait(self):
        if self.empty():
            raise QueueEmpty
        item = self._get()
        self._wakeup_next(self._putters)
        return item

    def task_done(self):
        if self._unfinished_tasks <= 0:
            raise ValueError('task_done() called too many times')
        self._unfinished_tasks -= 1
        if self._unfinished_tasks == 0:
            self._finished.set()

    @coroutine
    def join(self):
        if self._unfinished_tasks > 0:
            yield from self._finished.wait()


if __name__ == '__main__':
    



    test_queue = Queue()
    test_queue.put_nowait("test")
    print(test_queue.empty())
    print("========================")
    test_queue.get_nowait()
    print(test_queue.empty())
    print("========================")
    test_queue.task_done()
    print(test_queue.empty())




