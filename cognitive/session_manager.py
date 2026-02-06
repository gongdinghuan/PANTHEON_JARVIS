"""
JARVIS 用户会话管理器
支持 IP 区分用户，离线任务执行，重连结果推送

Author: gngdingghuan
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict

from fastapi import WebSocket
from utils.logger import log


@dataclass
class TaskResult:
    """任务结果"""
    task_id: str
    success: bool
    output: Any
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    delivered: bool = False  # 是否已推送给用户


@dataclass
class UserSession:
    """用户会话"""
    user_id: str  # IP 地址
    created_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)
    websocket: Optional[WebSocket] = None
    is_online: bool = False
    
    # 任务相关
    pending_tasks: List[str] = field(default_factory=list)  # 执行中的任务 ID
    pending_results: List[TaskResult] = field(default_factory=list)  # 待推送的结果
    
    # 用户上下文 (简化的记忆)
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    max_history: int = 20
    
    def add_message(self, role: str, content: str):
        """添加消息到对话历史"""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        # 保持历史在限制内
        if len(self.conversation_history) > self.max_history * 2:
            self.conversation_history = self.conversation_history[-self.max_history:]
    
    def get_recent_messages(self, count: int = 10) -> List[Dict[str, str]]:
        """获取最近的消息"""
        messages = self.conversation_history[-count:]
        return [{"role": m["role"], "content": m["content"]} for m in messages]
    
    def touch(self):
        """更新最后活跃时间"""
        self.last_active = datetime.now()


class UserSessionManager:
    """
    用户会话管理器
    - 基于 IP 地址识别用户
    - 管理用户会话和 WebSocket 连接
    - 支持离线任务执行
    - 支持重连后结果推送
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._sessions: Dict[str, UserSession] = {}
        self._task_to_user: Dict[str, str] = {}  # task_id -> user_id 映射
        self._lock = asyncio.Lock()
        self._initialized = True
        log.info("UserSessionManager 初始化完成")
    
    async def get_or_create_session(self, user_id: str) -> UserSession:
        """获取或创建用户会话"""
        async with self._lock:
            if user_id not in self._sessions:
                session = UserSession(user_id=user_id)
                self._sessions[user_id] = session
                log.info(f"创建新会话: {user_id}")
            else:
                session = self._sessions[user_id]
                session.touch()
            return session
    
    async def connect_user(self, user_id: str, websocket: WebSocket) -> UserSession:
        """
        用户连接
        
        Returns:
            用户会话 (包含待推送的结果)
        """
        session = await self.get_or_create_session(user_id)
        session.websocket = websocket
        session.is_online = True
        session.touch()
        
        log.info(f"用户连接: {user_id}, 待推送结果: {len(session.pending_results)}")
        return session
    
    async def disconnect_user(self, user_id: str):
        """用户断开连接 (但保留会话)"""
        if user_id in self._sessions:
            session = self._sessions[user_id]
            session.websocket = None
            session.is_online = False
            log.info(f"用户断开: {user_id}, 会话保留, 待执行任务: {len(session.pending_tasks)}")
    
    def get_session(self, user_id: str) -> Optional[UserSession]:
        """获取会话 (不创建)"""
        return self._sessions.get(user_id)
    
    def is_user_online(self, user_id: str) -> bool:
        """检查用户是否在线"""
        session = self._sessions.get(user_id)
        return session is not None and session.is_online
    
    def register_task(self, user_id: str, task_id: str):
        """注册任务到用户"""
        self._task_to_user[task_id] = user_id
        session = self._sessions.get(user_id)
        if session:
            session.pending_tasks.append(task_id)
            log.debug(f"任务 {task_id} 已注册到用户 {user_id}")
    
    def get_user_for_task(self, task_id: str) -> Optional[str]:
        """获取任务所属用户"""
        return self._task_to_user.get(task_id)
    
    async def store_result(self, user_id: str, task_id: str, result: Dict[str, Any]):
        """
        存储任务结果
        如果用户在线，立即推送；否则存储待推送
        """
        session = self._sessions.get(user_id)
        if not session:
            log.warning(f"存储结果失败: 会话不存在 {user_id}")
            return
        
        # 从待执行列表移除
        if task_id in session.pending_tasks:
            session.pending_tasks.remove(task_id)
        
        task_result = TaskResult(
            task_id=task_id,
            success=result.get("success", True),
            output=result.get("output"),
            error=result.get("error")
        )
        
        if session.is_online and session.websocket:
            # 在线: 立即推送
            try:
                await session.websocket.send_json({
                    "type": "task_result",
                    "task_id": task_id,
                    "result": result,
                    "timestamp": task_result.timestamp
                })
                task_result.delivered = True
                log.info(f"结果已推送: {task_id} -> {user_id}")
            except Exception as e:
                log.warning(f"推送失败，存储待推送: {e}")
                session.pending_results.append(task_result)
        else:
            # 离线: 存储待推送
            session.pending_results.append(task_result)
            log.info(f"结果已存储待推送: {task_id} -> {user_id}")
    
    async def deliver_pending_results(self, user_id: str) -> int:
        """
        推送所有待推送结果
        
        Returns:
            推送的数量
        """
        session = self._sessions.get(user_id)
        if not session or not session.websocket:
            return 0
        
        delivered_count = 0
        pending = session.pending_results.copy()
        
        for result in pending:
            if not result.delivered:
                try:
                    await session.websocket.send_json({
                        "type": "task_result",
                        "task_id": result.task_id,
                        "result": {
                            "success": result.success,
                            "output": result.output,
                            "error": result.error
                        },
                        "timestamp": result.timestamp,
                        "offline_completed": True  # 标记为离线完成
                    })
                    result.delivered = True
                    delivered_count += 1
                except Exception as e:
                    log.error(f"推送待推送结果失败: {e}")
                    break
        
        # 清理已推送的结果
        session.pending_results = [r for r in session.pending_results if not r.delivered]
        
        if delivered_count > 0:
            log.info(f"已推送 {delivered_count} 个待推送结果到 {user_id}")
        
        return delivered_count
    
    def get_all_sessions(self) -> Dict[str, Dict[str, Any]]:
        """获取所有会话状态"""
        return {
            user_id: {
                "user_id": user_id,
                "is_online": session.is_online,
                "created_at": session.created_at.isoformat(),
                "last_active": session.last_active.isoformat(),
                "pending_tasks": len(session.pending_tasks),
                "pending_results": len(session.pending_results),
                "conversation_count": len(session.conversation_history)
            }
            for user_id, session in self._sessions.items()
        }
    
    def get_online_users(self) -> List[str]:
        """获取在线用户列表"""
        return [uid for uid, s in self._sessions.items() if s.is_online]
    
    async def cleanup_inactive_sessions(self, max_inactive_hours: int = 24):
        """清理不活跃的会话"""
        now = datetime.now()
        to_remove = []
        
        for user_id, session in self._sessions.items():
            inactive_hours = (now - session.last_active).total_seconds() / 3600
            if inactive_hours > max_inactive_hours and not session.is_online:
                to_remove.append(user_id)
        
        for user_id in to_remove:
            del self._sessions[user_id]
            log.info(f"清理不活跃会话: {user_id}")
        
        return len(to_remove)


# 全局实例
_session_manager: Optional[UserSessionManager] = None


def get_session_manager() -> UserSessionManager:
    """获取全局会话管理器实例"""
    global _session_manager
    if _session_manager is None:
        _session_manager = UserSessionManager()
    return _session_manager
