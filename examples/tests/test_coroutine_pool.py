# -*- coding: utf-8 -*-
# @Time    : 2020-04-17 02:19
# @Author  : li
# @File    : test_coroutine_pool.py

import asyncio
import time
from sprite.utils.coroutinePool import coroutine_pool

async def sleepTask(task_id: int, sleep_time: int):
    print(f'在协程中启动任务 {task_id}')
    await asyncio.sleep(sleep_time)
    a = [1]
    print(f'{task_id} 任务结束')

start_time = time.time()
coroutine_pool.reset()
coroutine_pool.start()
for index in range(20):
    coroutine_pool.go(sleepTask(task_id=index, sleep_time=index))
end_time = time.time()
print(end_time -start_time)
print(coroutine_pool.is_running())
time.sleep(10)
print("主线程发出stop信号")
# coroutine_pool.go(stop_corountine(coroutine_pool))
coroutine_pool.stop()
index =0
while True:
    if coroutine_pool.isStoped():
        break
    else:
        index +=1
    print(index)
print(coroutine_pool.isStoped())

print("=======================")
