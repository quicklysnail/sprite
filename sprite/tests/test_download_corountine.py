# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019-08-24 12:50'


import time
import asyncio
from sprite.core.download.session import Session
from sprite.core.download import Downloader
from sprite.utils.coroutinePool import PyCoroutinePool
from sprite.http.request import Request


headers = {'Accept': 'text/html, application/xhtml+xml, image/jxr, */*',
               'Accept - Encoding': 'gzip, deflate',
               'Accept-Language': 'zh-Hans-CN, zh-Hans; q=0.5',
               'Connection': 'Keep-Alive',
               'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36 Edge/15.15063'}



def parse(response):
    pass



if __name__ == '__main__':
    url = "https://www.bilibili.com/index/recommend.json"
    request = Request(url=url, headers=headers, callback=parse, meta={"proxy":"http://127.0.0.1:8802"})
    coroutine_pool = PyCoroutinePool()
    downloader = Downloader(coroutine_pool=coroutine_pool,loop=coroutine_pool.loop)
    coroutine_pool.start()
    start_time = time.time()
    coroutine_pool.go(downloader.request(request=request))
    print(f'等待获取下载好的response {time.time()-start_time}')
    response = downloader.getResponse()
    print(response.body)
    print(f'关闭下载器 {time.time()-start_time}')
    downloader.close()
    print(f'关闭协程池 {time.time() - start_time}')
    coroutine_pool.stop()