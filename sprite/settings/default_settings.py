# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019-07-19 23:28'

# 项目名称
PROJECT_NAME = "spirit"

ENV = "dev"

SERVER_IP = "localhost"

SERVER_PORT = 8088

# 同时并发的请求数量
WORKER_NUM = 3

# engine是否在完成工作后自动退出
ENGINE_MOST_STOP = True

# 记录日志的文件的path，如果为空则，不保存日志。直接输出
LOG_FILE_PATH = ""

# download
# 运行同时执行的下载任务的数量
MAX_DOWNLOAD_NUM = 3
# 请求的默认http头部
HEADERS = {
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Connection': 'keep-alive',
    'User-Agent': "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36",
    'X-Requested-With': 'XMLHttpRequest',
}
# 是否运行跳转
FOLLOW_REDIRECTS = False
# 最大跳转次数
MAX_REDIRECTS = 3
# 是否是流式数据
STREAM = False

DECODE = True

SSL = None
# 是否长连接
KEEP_ALIVE = True
#
PREFIX = ""
# 超时时间
TIMEOUT = 5
# 每一个下载请求之间是的延迟时间
DELAY = 1
# 限流的策略
LIMITS = None

# schedule
# 布隆过滤器的容量
INITIAL_CAPACITY = 100000
# 布隆过滤器的错误率
ERROR_RATE = 0.001
# 队列中的请求是否长期保存
LONG_SAVE = False
# 队列中的请求若长期保存的话，需指定保存的目录
JOB_DIR = ""

# PyCoroutinePool
# 协程池中最大运行的协程数量
MAX_COROUTINE_AMOUNT = 256 * 1024
# 协程的空闲时间
MAX_COROUTINE_IDLE_TIME = 10
# 每一个协程运行完毕之后是否立即退出，
MOST_STOP = True

ITEM_COUNTER_UNIT = 60

RESPONSE_COUNTER_UNIT = 60
