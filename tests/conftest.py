"""
JARVIS 测试配置
"""

import pytest
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(scope="session")
def event_loop():
    """共享的事件循环"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def event_bus():
    """创建干净的事件总线"""
    from core.event_bus import EventBus
    return EventBus()


@pytest.fixture
def container():
    """创建干净的 DI 容器"""
    from core.container import Container
    return Container()
