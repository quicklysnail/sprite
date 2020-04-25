# -*- coding: utf-8 -*-
# @Time    : 2020-04-23 19:02
# @Author  : li
# @File    : args.py

from urllib.parse import urlparse


class Args(dict):
    def reset(self):
        self.clear()

    def __getitem__(self, key: 'str') -> 'str':
        return self.__getitem__(key)

    def __setitem__(self, key: 'str', value: 'str'):
        self.__setitem__(key, value)

    def __delitem__(self, key: 'str'):
        self.__delitem__(key)

    def parse(self, s: 'str'):
        if len(s) != 0:
            s = s.split("&")
            for arg in s:
                arg = arg.split("=")
                self[arg[0]] = arg[1]

    def parse_by_bytes(self, b: 'bytearray'):
        if len(b) != 0:
            s = b.decode("utf-8")
            s = s.split("&")
            for arg in s:
                arg = arg.split("=")
                self[arg[0]] = arg[1]

    def string(self) -> 'str':
        string = []
        for key, value in self.items():
            string.append(f'{key}={value}')
        return "&".join(string)


if __name__ == "__main__":
    result = urlparse("http://www.baidu.com/name?name=liyong")
    print(result)