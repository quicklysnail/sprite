# -*- coding: utf-8 -*-
# @Time    : 2020-04-16 22:03
# @Author  : li
# @File    : utils.py

import inspect
import traceback
import json
import importlib
import inspect
import os
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
        return dict.__getitem__(self, item)

    def __setattr__(self, key, value):
        dict.__setitem__(self, key, value)


def transformation_state_to_str(state_num):
    state_msg = "未知状态"
    if state_num == 1:
        state_msg = STATE_RUNNING
    elif state_num == 2:
        state_msg = STATE_STOPPING
    elif state_num == 3:
        state_msg = STATE_STOPPED
    return state_msg


def import_module(module_name: str):
    root, module = module_name.rsplit('.', 1)
    module_object = getattr(__import__(root, fromlist=['']), module)
    return module_object


class ClassLoader:
    def __init__(self, base_class, root_dir, reload=False, allow_duplicate=False):
        assert os.path.exists(root_dir), "root_dir not exist"
        self.__root_dir = root_dir
        self.__base_class = base_class
        self.__allow_duplicate = allow_duplicate
        self.__reload = reload
        self.__unique_class_object_name = set()
        self.__class_object = {}

    def load_from_file(self, path):
        module_path = path.replace(self.__root_dir, "").replace(".py", "").split("/")
        user_module = importlib.import_module(".".join(filter(lambda item: item.strip() not in ("", "."), module_path)))
        if self.__reload is True: importlib.reload(user_module)
        for name, cls in inspect.getmembers(user_module):
            # 自定义的对比函数
            if inspect.isclass(cls):
                if not issubclass(cls, self.__base_class):
                    continue
                else:
                    if name in self.__unique_class_object_name and self.__allow_duplicate is False:
                        raise Exception("found duplicated class %s" % name)
                self.__unique_class_object_name.add(name)
                self.__class_object[name] = cls

    @property
    def class_object(self):
        return self.__class_object

    def clear(self):
        self.__class_object.clear()
        self.__unique_class_object_name.clear()
