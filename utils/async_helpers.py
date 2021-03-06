# coding=utf-8
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import asyncio
from functools import partial


# noinspection PyIncorrectDocstring
async def wrap_in_async(func, *args, **kwargs):
    """
    Wraps a function as async with a loop.run_in_executor call.

    :param func: Function to execute: must be a synchronous function.
    :param args: Args to pass to the function.
    :param thread_pool: If this keyword argument exists, its value will determine whether a thread pool or process
                        pool is used.
    :param kwargs: Keyword arguments to pass to the function.
    :return: Whatever the function returns.
    """
    if "thread_pool" in kwargs:
        thread_pool = kwargs["thread_pool"]
        kwargs.pop("thread_pool")
    else:
        thread_pool = True

    pool = ThreadPoolExecutor(1) if thread_pool else ProcessPoolExecutor(1)

    loop = asyncio.get_event_loop()
    return_value = await loop.run_in_executor(pool, partial(func, *args, **kwargs))
    return return_value
