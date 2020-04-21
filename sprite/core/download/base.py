# -*- coding: utf-8 -*-
# @Time    : 2020-04-21 13:52
# @Author  : li
# @File    : base.py

from sprite.utils.utils import SingletonMetaClass


class BaseDownloader(metaclass=SingletonMetaClass):
    def __init__(self):
        pass
