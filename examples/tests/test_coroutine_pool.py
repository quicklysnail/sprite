# -*- coding: utf-8 -*-
# @Time    : 2020-04-17 02:19
# @Author  : li
# @File    : test_coroutine_pool.py

import asyncio
import time
from sprite.utils.coroutinepool import coroutine_pool

async def sleepTask(task_id: int, sleep_time: int):
    print(f'在协程中启动任务 {task_id}')
    await asyncio.sleep(sleep_time)
    a = [1]
    print(f'{task_id} 任务结束')

class Test:

    def done_callback_func(self, index):

        print(f'协程任务[{index}]结束了，我开始执行了')
test_obj = Test()

start_time = time.time()
coroutine_pool.reset()
coroutine_pool.start()
for index in range(20):
    coroutine_pool.go(sleepTask(task_id=index, sleep_time=index), test_obj.done_callback_func, index)
end_time = time.time()
print(end_time -start_time)
print(coroutine_pool.is_running())
time.sleep(10)
print("主线程发出stop信号")
coroutine_pool.stop()
index =0
while True:
    if coroutine_pool.is_stopped():
        break
    else:
        index +=1
    print(index)
print(coroutine_pool.is_stopped())

print("=======================")
