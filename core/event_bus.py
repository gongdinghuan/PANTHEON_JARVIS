"""
JARVIS 事件总线
轻量级异步事件系统，解耦模块间通信

Author: gngdingghuan
"""

import asyncio
from typing import Dict, List, Any, Optional, Callable, Set
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

from utils.logger import log


@dataclass
class Event:
    """事件对象"""
    type: str            # 事件类型 (如 "message.received")
    data: Dict[str, Any] # 事件数据
    source: str = ""     # 事件来源模块
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# 事件处理器类型
EventHandler = Callable[[Event], Any]


class EventBus:
    """
    异步事件总线
    
    支持:
    - 事件发布/订阅
    - 通配符订阅 (如 "tool.*")
    - 异步处理器
    - 事件历史记录
    
    预定义事件类型:
    - message.received     — 用户消息到达
    - message.response     — AI 回复生成
    - tool.start           — 工具开始执行
    - tool.complete        — 工具执行完成
    - tool.error           — 工具执行失败
    - memory.updated       — 记忆更新
    - evolution.insight     — 进化引擎产生洞察
    - heartbeat.tick       — 心跳触发
    - session.connected    — 用户会话连接
    - session.disconnected — 用户会话断开
    """
    
    def __init__(self, max_history: int = 100):
        self._handlers: Dict[str, List[EventHandler]] = defaultdict(list)
        self._wildcard_handlers: Dict[str, List[EventHandler]] = defaultdict(list)
        self._history: List[Event] = []
        self._max_history = max_history
        self._muted_types: Set[str] = set()
    
    def on(self, event_type: str, handler: EventHandler):
        """
        注册事件处理器
        
        Args:
            event_type: 事件类型 (支持 "*" 通配符, 如 "tool.*")
            handler: 处理函数 (sync 或 async)
        """
        if "*" in event_type:
            prefix = event_type.replace("*", "")
            self._wildcard_handlers[prefix].append(handler)
        else:
            self._handlers[event_type].append(handler)
    
    def off(self, event_type: str, handler: Optional[EventHandler] = None):
        """
        移除事件处理器
        
        Args:
            event_type: 事件类型
            handler: 要移除的处理函数。如果为 None，移除该类型的所有处理器
        """
        if handler is None:
            if "*" in event_type:
                prefix = event_type.replace("*", "")
                self._wildcard_handlers.pop(prefix, None)
            else:
                self._handlers.pop(event_type, None)
        else:
            if "*" in event_type:
                prefix = event_type.replace("*", "")
                if prefix in self._wildcard_handlers:
                    self._wildcard_handlers[prefix] = [
                        h for h in self._wildcard_handlers[prefix] if h != handler
                    ]
            else:
                if event_type in self._handlers:
                    self._handlers[event_type] = [
                        h for h in self._handlers[event_type] if h != handler
                    ]
    
    async def emit(self, event_type: str, data: Dict[str, Any] = None, source: str = ""):
        """
        发射事件
        
        Args:
            event_type: 事件类型
            data: 事件数据
            source: 事件来源
        """
        if event_type in self._muted_types:
            return
        
        event = Event(type=event_type, data=data or {}, source=source)
        
        # 记录历史
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
        
        # 收集匹配的处理器
        handlers = list(self._handlers.get(event_type, []))
        
        # 通配符匹配
        for prefix, wildcard_handlers in self._wildcard_handlers.items():
            if event_type.startswith(prefix):
                handlers.extend(wildcard_handlers)
        
        # 并行执行所有处理器
        if handlers:
            tasks = []
            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        tasks.append(handler(event))
                    else:
                        handler(event)
                except Exception as e:
                    log.debug(f"事件处理器异常 [{event_type}]: {e}")
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
    
    def emit_sync(self, event_type: str, data: Dict[str, Any] = None, source: str = ""):
        """同步发射事件 (在异步上下文中创建任务)"""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.emit(event_type, data, source))
        except RuntimeError:
            pass
    
    def mute(self, event_type: str):
        """静音某类事件"""
        self._muted_types.add(event_type)
    
    def unmute(self, event_type: str):
        """取消静音"""
        self._muted_types.discard(event_type)
    
    def get_history(self, event_type: Optional[str] = None, limit: int = 20) -> List[Event]:
        """获取事件历史"""
        if event_type:
            filtered = [e for e in self._history if e.type == event_type]
        else:
            filtered = list(self._history)
        return filtered[-limit:]
    
    def clear_history(self):
        """清空历史"""
        self._history.clear()
    
    @property
    def handler_count(self) -> int:
        """注册的处理器总数"""
        total = sum(len(h) for h in self._handlers.values())
        total += sum(len(h) for h in self._wildcard_handlers.values())
        return total


# 全局事件总线单例
_global_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """获取全局事件总线"""
    global _global_bus
    if _global_bus is None:
        _global_bus = EventBus()
    return _global_bus
