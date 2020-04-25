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
        dict.__setitem__(self, socket_id, socket)

    def __getitem__(self, socket_id: 'str') -> 'BaseSocket':
        return dict.__getitem__(self, socket_id)

    def __delitem__(self, socket_id: 'str'):
        dict.__delitem__(self, socket_id)

    def random(self):
        return dict.__getitem__(self, random.choice(self.keys()))