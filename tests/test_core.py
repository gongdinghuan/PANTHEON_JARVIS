"""
Tests for core/event_bus.py
"""

import asyncio
import pytest
from core.event_bus import EventBus, Event


@pytest.mark.asyncio
class TestEventBus:
    """事件总线单元测试"""
    
    async def test_basic_emit_and_subscribe(self, event_bus):
        """测试基本的发布/订阅"""
        received = []
        
        async def handler(event: Event):
            received.append(event.data)
        
        event_bus.on("test.event", handler)
        await event_bus.emit("test.event", {"value": 42})
        
        assert len(received) == 1
        assert received[0]["value"] == 42
    
    async def test_wildcard_subscribe(self, event_bus):
        """测试通配符订阅"""
        received = []
        
        async def handler(event: Event):
            received.append(event.type)
        
        event_bus.on("tool.*", handler)
        await event_bus.emit("tool.start", {"name": "search"})
        await event_bus.emit("tool.complete", {"name": "search"})
        await event_bus.emit("message.received", {})
        
        assert len(received) == 2
        assert "tool.start" in received
        assert "tool.complete" in received
    
    async def test_unsubscribe(self, event_bus):
        """测试取消订阅"""
        received = []
        
        async def handler(event: Event):
            received.append(1)
        
        event_bus.on("test.event", handler)
        await event_bus.emit("test.event")
        assert len(received) == 1
        
        event_bus.off("test.event", handler)
        await event_bus.emit("test.event")
        assert len(received) == 1  # 不再增加
    
    async def test_mute_and_unmute(self, event_bus):
        """测试静音"""
        received = []
        
        async def handler(event: Event):
            received.append(1)
        
        event_bus.on("noisy.event", handler)
        event_bus.mute("noisy.event")
        await event_bus.emit("noisy.event")
        assert len(received) == 0
        
        event_bus.unmute("noisy.event")
        await event_bus.emit("noisy.event")
        assert len(received) == 1
    
    async def test_event_history(self, event_bus):
        """测试事件历史"""
        await event_bus.emit("a", {"v": 1})
        await event_bus.emit("b", {"v": 2})
        await event_bus.emit("a", {"v": 3})
        
        all_history = event_bus.get_history()
        assert len(all_history) == 3
        
        a_history = event_bus.get_history(event_type="a")
        assert len(a_history) == 2
    
    async def test_sync_handler(self, event_bus):
        """测试同步处理器"""
        received = []
        
        def sync_handler(event: Event):
            received.append(event.data)
        
        event_bus.on("sync.test", sync_handler)
        await event_bus.emit("sync.test", {"ok": True})
        
        assert len(received) == 1


@pytest.mark.asyncio
class TestContainer:
    """DI 容器单元测试"""
    
    async def test_register_and_get(self, container):
        """测试注册和获取"""
        container.register("greeting", lambda: "hello")
        assert container.get("greeting") == "hello"
    
    async def test_singleton(self, container):
        """测试单例"""
        call_count = 0
        
        def factory():
            nonlocal call_count
            call_count += 1
            return {"id": call_count}
        
        container.register("service", factory, singleton=True)
        a = container.get("service")
        b = container.get("service")
        
        assert a is b
        assert call_count == 1
    
    async def test_register_instance(self, container):
        """测试直接注册实例"""
        obj = {"key": "value"}
        container.register_instance("config", obj)
        assert container.get("config") is obj
    
    async def test_missing_component(self, container):
        """测试获取未注册组件"""
        with pytest.raises(KeyError):
            container.get("nonexistent")
    
    async def test_has(self, container):
        """测试 has 方法"""
        assert not container.has("service")
        container.register("service", lambda: 1)
        assert container.has("service")
