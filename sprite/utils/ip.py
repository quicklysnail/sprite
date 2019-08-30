# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019/7/31 19:27'


import socket


# 获取本机的ip地址
def get_ip():
    localIP = socket.gethostbyname(socket.gethostname())
    ex = socket.gethostbyname_ex(socket.gethostname())[2]
    if len(ex) == 1:
        return ex[0]
    for ip in ex:
        if ip != localIP:
            return ip