"""
JARVIS IM 适配器基类
所有 IM 平台适配器必须继承此类

Author: gngdingghuan
"""

import asyncio
import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime

from utils.logger import log


class BaseIMAdapter(ABC):
    """
    IM 适配器抽象基类
    
    所有 IM 平台（QQ、微信、Telegram 等）必须实现此接口。
    适配器负责：
      1. 连接 IM 平台
      2. 接收消息并调用 Jarvis.process()
      3. 将 JARVIS 回复发送回 IM 平台
    """
    
    name: str = "base"
    
    def __init__(self, jarvis_instance):
        """
        Args:
            jarvis_instance: JARVIS 主实例，用于调用 process()
        """
        self.jarvis = jarvis_instance
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    @abstractmethod
    async def start(self):
        """启动适配器，连接 IM 平台"""
        pass
    
    @abstractmethod
    async def stop(self):
        """停止适配器，断开 IM 平台连接"""
        pass
    
    @abstractmethod
    async def send_message(self, user_id: str, content: str, 
                           attachments: Optional[List[Dict[str, Any]]] = None):
        """
        向 IM 用户发送消息
        
        Args:
            user_id: 平台用户 ID
            content: 文本内容
            attachments: 附件列表 [{"type": "image", "path": "..."}, ...]
        """
        pass
    
    async def handle_message(self, user_id: str, content: str, 
                             raw_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        统一消息处理入口 — 调用 Jarvis.process()
        
        Args:
            user_id: 平台用户 ID
            content: 用户消息文本
            raw_data: 原始平台数据（可选，用于调试）
            
        Returns:
            JARVIS 响应数据
        """
        # 加平台前缀区分来源
        jarvis_user_id = f"{self.name}:{user_id}"
        
        log.info(f"[{self.name}] 收到消息 - 用户: {user_id}, 内容: {content[:50]}...")
        
        try:
            response = await self.jarvis.process(content, user_id=jarvis_user_id)
            
            # 提取文本内容和附件
            text, attachments = self._extract_response(response)
            
            # 通过 IM 平台回复
            await self.send_message(user_id, text, attachments)
            
            log.info(f"[{self.name}] 已回复用户 {user_id}")
            return {"success": True, "text": text}
            
        except Exception as e:
            error_msg = f"处理消息时出错: {e}"
            log.error(f"[{self.name}] {error_msg}")
            
            try:
                await self.send_message(user_id, f"⚠️ {error_msg}")
            except Exception:
                pass
            
            return {"success": False, "error": str(e)}
    
    def _extract_response(self, response: Any) -> tuple:
        """
        从 JARVIS 响应中提取文本和附件
        
        Returns:
            (text, attachments)
        """
        attachments = []
        
        if isinstance(response, dict):
            text = response.get("content", "")
            if not text and "output" in response:
                text = str(response["output"])
            
            # 收集附件
            if response.get("attachments"):
                attachments = response["attachments"]
        elif isinstance(response, str):
            text = response
        else:
            text = str(response)
        
        return text, attachments
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    def __repr__(self) -> str:
        status = "运行中" if self._running else "已停止"
        return f"<{self.__class__.__name__} [{status}]>"
