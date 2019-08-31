# sprite
基于python协程池、用法灵活的轻量级高性能爬虫框架

# overview
sprite is an python 3.6+ web scraping micro-framework based on asyncio coroutine pool.



## quick start
```
import sprite
from sprite import Spider
from sprite import Response
from sprite import Crawler


class TestSpider(sprite.Spider):
    name = "test_spider"

    async def start_request(self):
        headers = {
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Connection': 'keep-alive',
            'User-Agent': "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36",
            'X-Requested-With': 'XMLHttpRequest',
        }
        start_requests = ["https://www.python.org/"]*5
        for url in start_requests:
            yield sprite.Request(url=url, headers=headers, callback=self.parse, dont_filter=True)

	async def parse(self, response: Response):
        self.logger.info("执行parse")
        self.logger.info(f'response body {response.body}')    

if __name__ == '__main__':
    # 实例化spider
    spider = TestSpider()
    # 构造一个crawler对象
    crawler = Crawler(
        spider=spider, middlewareManager=None, settings=None)
    # 启动crawler
    crawler.run()
```

## define middleware

```
from sprite.middlewaremanager import MiddlewareManager

test_middleware = MiddlewareManager()


# 增加下载中间件，在下载request之前执行
@test_middleware.add_download_middleware(isBefore=True)
async def test_downloader_middleware(request, spider=None):
    spider.logger.info("这是下载中间件  before")
    spider.logger.info(f'捕获request   {request.url}')


# 增加下载中间件，在下载request之后执行
@test_middleware.add_download_middleware(isBefore=False)
async def test_downloader_middleware(response=None, spider=None):
    spider.logger.info("这是下载中间件 after")
    spider.logger.info(f'捕获response   {response.status}')


# 增加处理item中间件，获取item之后执行
@test_middleware.add_pipeline_middleware()
async def test_downloader_middleware(item=None, spider=None):
    spider.logger.info("这是管道中间件")
    spider.logger.info(f'捕获item   {item}')


# 增加spider中间件，在启动spider之前执行
@test_middleware.add_spider_middleware(isBefore=True)
async def test_downloader_middleware(spider=None):
    spider.logger.info("这是spider中间件 before")


# 增加spider中间件，在启动spider之后执行
@test_middleware.add_spider_middleware(isBefore=False)
async def test_downloader_middleware(spider=None):
    spider.logger.info("这是spdier中间件 after")
```
## define settings

```
# 实例化一个自定义的settings对象
from sprite import Settings

settings = Settings(values={
        "MAX_DOWNLOAD_NUM": 100,
        "WORKER_NUM": 100,
        "DELAY": 0,
        "LOG_FILE_PATH": "test_spider_one.log",
    })
```
更加详细的配置信息，请查看**sprite.settings.defaut_settings.py**
## define item

```
import sprite

class TestItem(sprite.Item):
    body = sprite.Field()
```
# Individual use downloader module

```
import time
from sprite import Downloader
from sprite import Request
from sprite import PyCoroutinePool
from sprite.settings import Settings

headers = {'Accept': 'text/html, application/xhtml+xml, image/jxr, */*',
           'Accept - Encoding': 'gzip, deflate',
           'Accept-Language': 'zh-Hans-CN, zh-Hans; q=0.5',
           'Connection': 'Keep-Alive',
           'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36 Edge/15.15063'}


def parse(response):
    pass


if __name__ == '__main__':
    settings = Settings(values={
        "MAX_DOWNLOAD_NUM": 100,
        "WORKER_NUM": 100,
        "DELAY": 0,
        "LOG_FILE_PATH": "test_spider_one.log",
    })

    url = ""https://www.python.org/""

    request = Request(url=url, headers=headers, callback=parse,
                      meta={"proxy": "http://252.9.9.6:8890"}
                      )

    coroutine_pool = PyCoroutinePool()
    downloader = Downloader.from_settings(settings=settings, coroutine_pool=coroutine_pool)

    coroutine_pool.start()
    start_time = time.time()

    coroutine_pool.go(downloader.request(request=request))
    coroutine_pool.go(downloader.request(request=request))
    coroutine_pool.go(downloader.request(request=request))
    coroutine_pool.go(downloader.request(request=request))
    coroutine_pool.go(downloader.request(request=request))
    coroutine_pool.go(downloader.request(request=request))

    time.sleep(3)
    print(f'await response {time.time() - start_time}')
    response = downloader.getResponse()
    print(response.body)
    print(response.error)
    print(response.status)

    print(f'close downloader {time.time() - start_time}')
    downloader.close()
    print(f'close coroutine_pool {time.time() - start_time}')
    coroutine_pool.stop()
```


