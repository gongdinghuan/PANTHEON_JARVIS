"""
JARVIS IM 适配器管理器
统一管理所有 IM 平台适配器的生命周期

Author: gngdingghuan
"""

import asyncio
from typing import Dict, Optional, List

from utils.logger import log
from .base import BaseIMAdapter


class AdapterManager:
    """
    适配器管理器
    负责注册、启动和停止所有 IM 适配器
    """
    
    def __init__(self):
        self._adapters: Dict[str, BaseIMAdapter] = {}
    
    def register(self, adapter: BaseIMAdapter):
        """注册一个适配器"""
        self._adapters[adapter.name] = adapter
        log.info(f"已注册 IM 适配器: {adapter.name}")
    
    async def start_all(self):
        """启动所有已注册的适配器"""
        for name, adapter in self._adapters.items():
            try:
                await adapter.start()
                log.info(f"IM 适配器已启动: {name}")
            except Exception as e:
                log.error(f"启动 IM 适配器失败 [{name}]: {e}")
    
    async def stop_all(self):
        """停止所有适配器"""
        for name, adapter in self._adapters.items():
            try:
                await adapter.stop()
                log.info(f"IM 适配器已停止: {name}")
            except Exception as e:
                log.warning(f"停止 IM 适配器时出错 [{name}]: {e}")
    
    def get_adapter(self, name: str) -> Optional[BaseIMAdapter]:
        """获取指定适配器"""
        return self._adapters.get(name)
    
    def get_all_status(self) -> List[Dict]:
        """获取所有适配器状态"""
        return [
            {
                "name": name,
                "running": adapter.is_running,
                "type": adapter.__class__.__name__
            }
            for name, adapter in self._adapters.items()
        ]
    
    @property
    def adapters(self) -> Dict[str, BaseIMAdapter]:
        return self._adapters
