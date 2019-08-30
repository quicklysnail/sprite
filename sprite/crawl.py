# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019-08-17 22:47'



import signal

from sprite.utils.log import get_logger,set_logger
from sprite.settings import Settings
from sprite.middlewaremanager import MiddlewareManager
from sprite.spider import Spider
from sprite.core.engine import Engine


logger = get_logger()





class Crawler:
    def __init__(self, spider:Spider, middlewareManager:MiddlewareManager, settings:Settings=None,server:str=None):
        self.spider = spider
        self._settings = settings or Settings()
        self._settings.freeze()
        self._engine = Engine.from_settings(settings=self._settings, spider=self.spider, middlewareManager=middlewareManager)
        self._server = server or f'{self._settings.get("SERVER_IP")}:{self._settings.getint("SERVER_PORT")}'


    def run(self):
        set_logger(self._settings)
        # self._register_crawl()
        logger.info(f'启动sprite')
        self._engine.start()
        signal.signal(signal.SIGTERM, self._close)  # SIGTERM 关闭程序信号
        signal.signal(signal.SIGINT, self._close)  # 接收ctrl+c 信号



    def _close(self, signal_num:int, frame):
        # 关闭引擎
        if self._engine.isClose():
            return
        logger.info(f'关闭sprite')
        self._engine.close()


    # def _register_crawl(self):
    #     client_call(self._server,"register_crawl", self)







# class CrawlerRunner:
#     def __init__(self):
#         self._crawlers = set
#         self._settings = None
#         self._rpc_server = SpritRPCServer()
#         self._running_event = threading.Event()
#         self._register_rpc()
#
#     def _register_rpc(self):
#         self._rpc_server.register_function(self.register_crawl, "register_crawl")
#
#
#     def register_crawl(self, crawler:Crawler):
#         if crawler.spider.name in self._crawlers:
#             return False
#         self._crawlers[crawler.spider.name] =crawler
#         return True
#
#     # 重新加载settings
#     def load_settings(self):
#         new_settings = import_settings()
#         self.settings = new_settings
#
#     def start(self):
#         self._running_event.wait()  # 主线程阻塞等待
#         self._rpc_server.shutdown()  # 关闭rpc服务
#
#
#     def close_crawl(self, crawl_name):
#         if crawl_name in self._crawlers:
#             pass
#
#
#
#
#
# # 导入当前目录下的setting模块！！！！，找不到会直接抛出异常！！
# def import_settings(priority: str = 'project'):
#     settings_ = Settings()
#     try:
#         import settings
#         for key in dir(settings):
#             # 只有大写的配置项名称才能被存储起来
#             if key.isupper():
#                 settings_.set(key, getattr(settings, key), priority)
#         return settings_
#     except ImportError as e:
#         logger.info(f'import settings failure, not start crawl')
#         raise e