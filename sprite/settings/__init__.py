# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019-07-19 23:28'

from typing import Union, List, Dict
import json
import copy
from collections import MutableMapping
from importlib import import_module
from pprint import pformat

from . import default_settings  # 用的相对路径，便于相对导入

SETTINGS_PRIORITIES = {
    'default': 0,
    'command': 10,
    'project': 20,
    'spider': 30,
    'cmdline': 40,
}


# 优先级等级名称与等级数值直接的转换
def get_settings_priority(priority: Union[str, int]) -> int:
    if isinstance(priority, str):
        return SETTINGS_PRIORITIES[priority]
    else:
        return priority


class SettingsAttribute(object):

    def __init__(self, value, priority):
        self.value = value
        if isinstance(self.value, BaseSettings):
            self.priority = max(self.value.maxpriority(), priority)
        else:
            self.priority = priority

    def set(self, value, priority):
        """Sets value if priority is higher or equal than current priority."""
        if priority >= self.priority:
            if isinstance(self.value, BaseSettings):
                value = BaseSettings(value, priority=priority)
            self.value = value
            self.priority = priority

    def __str__(self):
        return "<SettingsAttribute value={self.value!r} " \
               "priority={self.priority}>".format(self=self)

    __repr__ = __str__


class BaseSettings(MutableMapping):
    def __init__(self, values=None, priority='project'):
        self.frozen = False
        self.attributes = {}
        self.update(values, priority)

    def __getitem__(self, opt_name):
        if opt_name not in self:
            return None
        return self.attributes[opt_name].value

    def __contains__(self, name):
        return name in self.attributes

    def get(self, name, default=None):

        return self[name] if self[name] is not None else default

    def getbool(self, name, default=False):

        got = self.get(name, default)
        try:
            return bool(int(got))
        except ValueError:
            if got in ("True", "true"):
                return True
            if got in ("False", "false"):
                return False
            raise ValueError("Supported values for boolean settings "
                             "are 0/1, True/False, '0'/'1', "
                             "'True'/'False' and 'true'/'false'")

    def getint(self, name, default=0):
        return int(self.get(name, default))

    def getfloat(self, name, default=0.0):

        return float(self.get(name, default))

    def getlist(self, name, default=None):

        value = self.get(name, default or [])
        if isinstance(value, str):
            value = value.split(',')
        return list(value)

    def getdict(self, name, default=None):

        value = self.get(name, default or {})
        if isinstance(value, str):
            value = json.loads(value)
        return dict(value)

    def getwithbase(self, name):

        compbs = BaseSettings()
        compbs.update(self[name + '_BASE'])
        compbs.update(self[name])
        return compbs

    def getpriority(self, name):

        if name not in self:
            return None
        return self.attributes[name].priority

    def maxpriority(self):

        if len(self) > 0:
            return max(self.getpriority(name) for name in self)
        else:
            return get_settings_priority('default')

    def __setitem__(self, name, value):
        self.set(name, value)

    def set(self, name, value, priority='project'):
        # 设置存储键值对
        self._assert_mutability()
        # 把优先级名称转换为数值
        priority = get_settings_priority(priority)
        if name not in self:
            if isinstance(value, SettingsAttribute):
                self.attributes[name] = value
            else:
                # 用value实例化一个SettingsAttribute
                self.attributes[name] = SettingsAttribute(value, priority)
        else:
            self.attributes[name].set(value, priority)

    def setdict(self, values, priority='project'):
        self.update(values, priority)

    # 传入一个模块对象，或者模块的导入路径
    def setmodule(self, module, priority='project'):
        # 将一个模块里面的配置项存储起来
        self._assert_mutability()
        if isinstance(module, str):
            module = import_module(module)
        for key in dir(module):
            # 只有大写的配置项名称才能被存储起来
            if key.isupper():
                self.set(key, getattr(module, key), priority)

    def update(self, values, priority='project'):
        # 判断是否可修改
        self._assert_mutability()
        if isinstance(values, str):
            # 如果values是字符串类型，则序列化陈json对象
            values = json.loads(values)
        if values is not None:
            if isinstance(values, BaseSettings):
                # six.iteritems返回可迭代对象
                for name, value in values.items():
                    self.set(name, value, values.getpriority(name))
            else:
                for name, value in values.items():
                    self.set(name, value, priority)

    def delete(self, name, priority='project'):
        self._assert_mutability()
        priority = get_settings_priority(priority)
        if priority >= self.getpriority(name):
            del self.attributes[name]

    def __delitem__(self, name):
        self._assert_mutability()
        del self.attributes[name]

    def _assert_mutability(self):
        if self.frozen:
            raise TypeError("Trying to modify an immutable Settings object")

    def copy(self):
        return copy.deepcopy(self)

    def freeze(self):
        self.frozen = True

    def frozencopy(self):
        copy = self.copy()
        copy.freeze()
        return copy

    def __iter__(self):
        return iter(self.attributes)

    def __len__(self):
        return len(self.attributes)

    def _to_dict(self):
        return {k: (v._to_dict() if isinstance(v, BaseSettings) else v)
                for k, v in self.items()}

    def copy_to_dict(self):

        settings = self.copy()
        return settings._to_dict()

    def _repr_pretty_(self, p, cycle):
        if cycle:
            p.text(repr(self))
        else:
            p.text(pformat(self.copy_to_dict()))


class _DictProxy(MutableMapping):

    def __init__(self, settings, priority):
        self.o = {}
        self.settings = settings
        self.priority = priority

    def __len__(self):
        return len(self.o)

    def __getitem__(self, k):
        return self.o[k]

    def __setitem__(self, k, v):
        self.settings.set(k, v, priority=self.priority)
        self.o[k] = v

    def __delitem__(self, k):
        del self.o[k]

    def __iter__(self, k, v):
        return iter(self.o)


class Settings(BaseSettings):

    def __init__(self, values=None, priority='project'):
        super(Settings, self).__init__()
        # 配置对象加载的时候，优先加载项目的默认配置
        self.setmodule(default_settings, 'default')
        for name, val in self.items():
            # 把配置项是字典的单独拿出来
            if isinstance(val, dict):
                self.set(name, BaseSettings(val, 'default'), 'default')
        self.update(values, priority)


def iter_default_settings():
    for name in dir(default_settings):
        if name.isupper():
            return name, getattr(default_settings, name)


def overridden_settings(settings):
    for name, defvalue in iter_default_settings():
        value = settings[name]
        if not isinstance(defvalue, dict) and value != defvalue:
            return name, value
