# -*- coding:utf-8 -*-
__author__ = 'liyong'
__date__ = '2019/8/31 16:37'

from typing import Callable, Coroutine
from types import AsyncGeneratorType, GeneratorType


async def detailCallable(callable_obj, result_detail_func: Callable):
    call_result = callable_obj()
    if isinstance(call_result, AsyncGeneratorType):
        async for callback_result in call_result:
            detail_result = result_detail_func(callback_result)
            if isinstance(detail_result, Coroutine):
                await detail_result
    elif isinstance(call_result, Coroutine):
        callback_result = await call_result
        result = result_detail_func(callback_result)
        if isinstance(result, Coroutine):
            await result

    elif isinstance(call_result, GeneratorType):
        for callback_result in call_result:
            detail_result = result_detail_func(callback_result)
            if isinstance(detail_result, Coroutine):
                await detail_result
    else:
        detail_result = result_detail_func(call_result)
        if isinstance(detail_result, Coroutine):
            await detail_result
