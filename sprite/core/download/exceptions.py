# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019-08-17 20:17'


# 不合理的响应内容
class InvalidResponseException(Exception):
    pass


# 连接超时
class OpenConnectionFailed(Exception):
    pass
