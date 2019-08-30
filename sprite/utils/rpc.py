# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019/7/31 19:20'

from xmlrpc.server import SimpleXMLRPCServer
import socketserver
from xmlrpc.client import ServerProxy
import threading
import socket
from typing import Callable


# 远程调用默认重试次数
RETRY_TIMES = 10



class SpritRPCServer(socketserver.ThreadingMixIn, SimpleXMLRPCServer):
    def __init__(self, *args, **kwargs):
        SimpleXMLRPCServer.__init__(self, *args, **kwargs)
        self.allow_none = True
        self.allow_reuse_address = True

    # 注册远程方法
    def register_function(self, function:Callable, name:str=None, prefix:str=None):
        if prefix is not None:
            if name is None:
                name = function.__name__
            prefix = prefix + "_" if not prefix.endswith('_') else prefix
            SimpleXMLRPCServer.register_function(self, function, name=prefix + name)
        else:
            SimpleXMLRPCServer.register_function(self, function, name=name)


class ThreadSpriteRPCServer:
    def __init__(self, *args, **kwargs):
        self.rpc_server = SpritRPCServer(*args, **kwargs)
        self._t = threading.Thread(target=self.rpc_server.serve_forever)
        # self._t.setDaemon(True)
        self._t.start()

    def register_function(self, function:Callable, name:str=None, prefix:str=None):
        self.rpc_server.register_function(function, name=name, prefix=prefix)

    # 停止远程调用的服务
    def shutdown(self):
        self.rpc_server.shutdown()
        self._t.join()


# 发起远程调用
def client_call(server: str, func_name: str, *args, **kwargs):
    serv = ServerProxy(f'http://{server}')
    ignore = kwargs.get('ignore', False)
    # 调用失败是否重试
    if not ignore:
        err = None
        retry_times = 0
        while retry_times <= RETRY_TIMES:
            try:
                return getattr(serv, func_name)(*args)
            except socket.error as e:
                retry_times += 1
                err = e
            except Exception as e:
                err = e
                raise err
        raise err
    else:
        try:
            return getattr(serv, func_name)(*args)
        except socket.error as e:
            err = e
            raise err
        except Exception as e:
            err = e
            raise err
