# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019-08-17 22:47'

from sprite.http.request import Request
from sprite.http.response import Response
from sprite.utils.log import get_logger


class Spider:
    name = "sprite"
    start_requests:list = None
    metadata:dict = {}

    def __init__(self):
        self.logger = get_logger()

    async def start_request(self):
        pass

    async def parse(self, response: Response):
        pass
