"""
Python 版本兼容性工具
提供 Python 3.8 与 3.9+ 之间的兼容性

Author: gngdingghuan
"""

import asyncio
import functools
import sys
from typing import TypeVar, Callable, Any

T = TypeVar('T')


def get_to_thread():
    """获取 to_thread 函数，兼容 Python 3.8"""
    if sys.version_info >= (3, 9):
        return asyncio.to_thread
    else:
        # Python 3.8 polyfill
        async def to_thread(func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
            """
            在单独的线程中运行同步函数
            这是 asyncio.to_thread 的 Python 3.8 兼容实现
            """
            loop = asyncio.get_running_loop()
            pfunc = functools.partial(func, *args, **kwargs)
            return await loop.run_in_executor(None, pfunc)
        
        return to_thread


# 导出 to_thread 函数
to_thread = get_to_thread()
