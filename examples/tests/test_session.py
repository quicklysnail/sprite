# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019-08-17 12:23'


import asyncio
from sprite.core.download.session import Session


headers = {'Accept': 'text/html, application/xhtml+xml, image/jxr, */*',
               'Accept - Encoding': 'gzip, deflate',
               'Accept-Language': 'zh-Hans-CN, zh-Hans; q=0.5',
               'Connection': 'Keep-Alive',
               'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36 Edge/15.15063'}



async def get_http_data(url:str):
    s = Session()
    resp = await s.get(url, headers=headers)
    print(resp.content.decode("utf-8")[:10])
    # print(resp.json())

def parse(response):
    pass



if __name__ == '__main__':
    url = "https://www.bilibili.com/index/recommend.json"
    # request = Request(url=url, headers=headers, callback=parse)
    # coroutine_pool = PyCoroutinePool()
    # downloader = Downloader(coroutine_pool=coroutine_pool,loop=coroutine_pool.loop)
    # coroutine_pool.stop()
    # coroutine_pool.go(downloader.request(request=request))
    # # resp = requests.get(url, headers=headers)
    # # print(resp.text)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(get_http_data(url))
