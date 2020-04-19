# -*- coding: utf-8 -*-
# @Time    : 2020-04-16 22:03
# @Author  : li
# @File    : utils.py

import traceback
import json
from sprite.const import *


# 单例元类
class SingletonMetaClass(type):
    def __call__(cls, *args, **kwargs):
        if not hasattr(cls, "_instance"):
            cls._instance = super().__call__(*args, **kwargs)
        return cls._instance


def get_str(data, default_str: str = "Blank Str"):
    try:
        return str(data)
    except Exception:
        return default_str


class Result(dict):
    def __init__(self, msg: str, data=None):
        self.msg = get_str(msg)
        self.data = data
        super(Result, self).__init__()

    def serialize(self):

        try:
            return json.dumps(self)
        except Exception:
            return f'find one exception: \n{traceback.format_exc()}'

    def __getattr__(self, item):
        return self[item]

    def __setattr__(self, key, value):
        self[key] = value


def transformation_state_to_str(state_num):
    state_msg = "未知状态"
    if state_num == 1:
        state_msg = STATE_RUNNING
    elif state_num == 2:
        state_msg = STATE_STOPPING
    elif state_num == 3:
        state_msg = STATE_STOPPED
    return state_msg
