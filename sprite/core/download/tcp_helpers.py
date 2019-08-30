# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019/8/27 19:55'

import asyncio
import socket
from contextlib import suppress


def tcp_nodelay(transport: asyncio.Transport, value: bool) -> None:
    sock = transport.get_extra_info('socket')

    if sock is None:
        return

    if sock.family not in (socket.AF_INET, socket.AF_INET6):
        return

    value = bool(value)

    # socket may be closed already, on windows OSError get raised
    with suppress(OSError):
        sock.setsockopt(
            socket.IPPROTO_TCP, socket.TCP_NODELAY, value)
