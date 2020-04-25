# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019-08-24 12:50'

import time
from asyncio import Task
from sprite import CoroutineDownloader
from sprite import Request
from sprite import PyCoroutinePool
from sprite import Settings
from sprite.utils.log import set_logger


headers = {'Accept': 'text/html, application/xhtml+xml, image/jxr, */*',
           'Accept - Encoding': 'gzip, deflate',
           'Accept-Language': 'zh-Hans-CN, zh-Hans; q=0.5',
           'Connection': 'Keep-Alive',
           'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36 Edge/15.15063'}


def parse(response):
    pass


if __name__ == '__main__':
    # 实例化一个自定义的settings对象
    settings = Settings(values={
        "MAX_DOWNLOAD_NUM": 1,
        "WORKER_NUM": 1,
        "DELAY": 0,
        "LOG_FILE_PATH": "test_spider_one.log",
        "JOB_DIR": "/Users/liyong/projects/open_source/sprite/examples/test_spider_one",
        "LONG_SAVE": True,
    })
    set_logger(settings)
    url = "https://www.douyu.com/japi/search/api/getHotList"
    request = Request(url=url, headers=headers, callback=parse,
                      meta={"proxy": "http://106.42.211.175:30007"}
                      )
    # request = Request(url=url, headers=headers, callback=parse,
    #                   )
    coroutine_pool = PyCoroutinePool()
    downloader = CoroutineDownloader(settings)
    coroutine_pool.start()
    start_time = time.time()
    request_task = coroutine_pool.go(downloader.download(request=request))
    print(f'等待获取下载好的response {time.time() - start_time}')
    while True:
        if request_task.done():
            print(request_task.result().body)
            break
        time.sleep(5)
    print(f'关闭协程池 {time.time() - start_time}')
    coroutine_pool.stop()
