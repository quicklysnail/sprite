# -*- coding: utf-8 -*-
# @Time    : 2020-04-18 00:41
# @Author  : li
# @File    : test_crawler_runner.py

from sprite.utils.rpc import client_call

if __name__ == "__main__":
    addr = "localhost:8088"
    result = client_call(addr, "get_all_crawler_name")
    print(result)
    result = client_call(addr, "stop_server")
    print(result)
    # result = client_call(addr, "stop_server")
    # print(result)