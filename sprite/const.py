# -*- coding: utf-8 -*-
# @Time    : 2020-04-18 14:50
# @Author  : li
# @File    : const.py

COROUTINE_SLEEP_TIME = 0.0001

THREAD_SLEEP_TIME = 0.001

STATE_RUNNING = "运行状态"

STATE_STOPPING = "即将停止"

STATE_STOPPED = "已经停止"

# 协程池运行
COROUTINE_POOL_STATE_RUNNING = 1

# 协程池关闭中
COROUTINE_POOL_STATE_STOPPING = 2

# 协程池关闭
COROUTINE_POOL_STATE_STOPPED = 3

# 引擎运行
ENGINE_STATE_RUNNING = 1

# 引擎暂停
ENGINE_STATE_PAUSE = 2

# 引擎关闭
ENGINE_STATE_STOPPED = 3

# 调度器开启
SCHEDULER_RUNNING = 1

# 调度器暂停
SCHEDULER_STOPPED = 3

# 开发环境
ENV_DEV = "dev"

ENV_PRODUCT = "product"
