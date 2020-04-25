# -*- coding: utf-8 -*-
# @Time    : 2020-04-25 00:10
# @Author  : li
# @File    : sockethub.py

import random
from sprite.core.download.socket import BaseSocket


class SocketHub(dict):
    def __setitem__(self, socket_id: 'str', socket: 'BaseSocket'):
        if socket_id in self:
            return
        self.__setitem__(socket_id, socket)

    def __getitem__(self, socket_id: 'str') -> 'BaseSocket':
        return self.__getitem__(socket_id)

    def __delitem__(self, socket_id: 'str'):
        self.__delitem__(socket_id)

    def random(self):
        return self.__getitem__(random.choice(self.keys()))