"""
JARVIS 上下文管理器
追踪系统状态和任务上下文

Author: gngdingghuan
"""

import psutil
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

from utils.logger import log
from utils.platform_utils import (
    get_active_window_title,
    get_clipboard_text,
    get_platform,
)


@dataclass
class SystemState:
    """系统状态快照"""
    active_window: Optional[str] = None
    clipboard_content: Optional[str] = None
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    running_apps: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class TaskContext:
    """任务上下文"""
    current_task: Optional[str] = None
    task_history: List[str] = field(default_factory=list)
    working_directory: Optional[str] = None
    open_files: List[str] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)


class ContextManager:
    """
    上下文管理器
    - 追踪系统状态（活跃窗口、剪贴板等）
    - 维护任务上下文（当前任务、工作目录等）
    """
    
    def __init__(self):
        self._system_state = SystemState()
        self._task_context = TaskContext()
        self._platform = get_platform()
        
        log.info(f"上下文管理器初始化完成，平台: {self._platform}")
    
    def get_system_state(self, refresh: bool = True) -> Dict[str, Any]:
        """
        获取当前系统状态
        
        Args:
            refresh: 是否刷新状态
            
        Returns:
            系统状态字典
        """
        if refresh:
            self._refresh_system_state()
        
        return {
            "active_window": self._system_state.active_window,
            "clipboard_preview": self._get_clipboard_preview(),
            "cpu_percent": self._system_state.cpu_percent,
            "memory_percent": self._system_state.memory_percent,
            "running_apps_count": len(self._system_state.running_apps),
            "platform": self._platform,
            "timestamp": self._system_state.timestamp,
        }
    
    def _refresh_system_state(self):
        """刷新系统状态"""
        try:
            # 活跃窗口
            self._system_state.active_window = get_active_window_title()
            
            # 剪贴板
            self._system_state.clipboard_content = get_clipboard_text()
            
            # 系统资源
            self._system_state.cpu_percent = psutil.cpu_percent(interval=0.1)
            self._system_state.memory_percent = psutil.virtual_memory().percent
            
            # 运行中的应用
            self._system_state.running_apps = self._get_running_apps()
            
            # 时间戳
            self._system_state.timestamp = datetime.now().isoformat()
            
        except Exception as e:
            log.warning(f"刷新系统状态失败: {e}")
    
    def _get_running_apps(self) -> List[str]:
        """获取运行中的应用列表"""
        apps = set()
        try:
            for proc in psutil.process_iter(['name']):
                try:
                    name = proc.info['name']
                    if name and not name.startswith('_'):
                        apps.add(name)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception:
            pass
        return sorted(list(apps))[:50]  # 限制数量
    
    def _get_clipboard_preview(self) -> Optional[str]:
        """获取剪贴板预览（截断长文本）"""
        content = self._system_state.clipboard_content
        if not content:
            return None
        if len(content) > 200:
            return content[:197] + "..."
        return content
    
    def get_active_window(self) -> Optional[str]:
        """获取当前活跃窗口"""
        return get_active_window_title()
    
    def get_clipboard(self) -> Optional[str]:
        """获取剪贴板内容"""
        return get_clipboard_text()
    
    # ===== 任务上下文管理 =====
    
    def set_current_task(self, task: str):
        """设置当前任务"""
        if self._task_context.current_task:
            self._task_context.task_history.append(self._task_context.current_task)
        
        self._task_context.current_task = task
        log.debug(f"当前任务设置为: {task}")
    
    def get_current_task(self) -> Optional[str]:
        """获取当前任务"""
        return self._task_context.current_task
    
    def clear_current_task(self):
        """清除当前任务"""
        if self._task_context.current_task:
            self._task_context.task_history.append(self._task_context.current_task)
        self._task_context.current_task = None
    
    def set_working_directory(self, path: str):
        """设置工作目录"""
        self._task_context.working_directory = path
    
    def get_working_directory(self) -> Optional[str]:
        """获取工作目录"""
        return self._task_context.working_directory
    
    def add_open_file(self, filepath: str):
        """添加打开的文件"""
        if filepath not in self._task_context.open_files:
            self._task_context.open_files.append(filepath)
    
    def remove_open_file(self, filepath: str):
        """移除打开的文件"""
        if filepath in self._task_context.open_files:
            self._task_context.open_files.remove(filepath)
    
    def get_open_files(self) -> List[str]:
        """获取打开的文件列表"""
        return self._task_context.open_files.copy()
    
    def set_variable(self, key: str, value: Any):
        """设置上下文变量"""
        self._task_context.variables[key] = value
    
    def get_variable(self, key: str, default: Any = None) -> Any:
        """获取上下文变量"""
        return self._task_context.variables.get(key, default)
    
    def get_task_context(self) -> Dict[str, Any]:
        """获取完整任务上下文"""
        return {
            "current_task": self._task_context.current_task,
            "task_history": self._task_context.task_history[-5:],  # 最近5个
            "working_directory": self._task_context.working_directory,
            "open_files": self._task_context.open_files,
            "variables": self._task_context.variables,
        }
    
    def get_context_summary(self) -> str:
        """
        获取上下文摘要（用于注入 LLM）
        
        Returns:
            人类可读的上下文描述
        """
        parts = []
        
        # 系统状态
        state = self.get_system_state()
        if state["active_window"]:
            parts.append(f"当前活跃窗口: {state['active_window']}")
        
        # 任务上下文
        if self._task_context.current_task:
            parts.append(f"当前任务: {self._task_context.current_task}")
        
        if self._task_context.working_directory:
            parts.append(f"工作目录: {self._task_context.working_directory}")
        
        if self._task_context.open_files:
            files = ", ".join(self._task_context.open_files[-3:])
            parts.append(f"打开的文件: {files}")
        
        if not parts:
            return "暂无特殊上下文信息"
        
        return "\n".join(parts)
    
    def reset(self):
        """重置所有上下文"""
        self._system_state = SystemState()
        self._task_context = TaskContext()
        log.info("上下文已重置")
