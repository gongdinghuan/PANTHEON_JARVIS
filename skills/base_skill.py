"""
JARVIS 技能基类
定义技能的统一接口

Author: gngdingghuan
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum


class PermissionLevel(Enum):
    """权限级别"""
    READ_ONLY = 1      # 只读，自动执行
    SAFE_WRITE = 2     # 安全写入，自动执行但记录
    CRITICAL = 3       # 危险操作，需要确认


@dataclass
class SkillResult:
    """技能执行结果"""
    success: bool
    output: Any
    error: Optional[str] = None
    needs_confirmation: bool = False
    confirmation_message: Optional[str] = None
    is_background: bool = False
    task_id: Optional[str] = None
    visualization: Optional[Dict[str, Any]] = None
    attachments: Optional[List[Dict[str, Any]]] = None  # 文件附件列表
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "needs_confirmation": self.needs_confirmation,
            "confirmation_message": self.confirmation_message,
            "is_background": self.is_background,
            "task_id": self.task_id,
            "visualization": self.visualization,
            "attachments": self.attachments
        }


class BaseSkill(ABC):
    """
    技能基类
    所有技能必须继承此类
    """
    
    # 子类必须定义这些属性
    name: str = "base_skill"
    description: str = "基础技能"
    permission_level: PermissionLevel = PermissionLevel.READ_ONLY
    supports_background: bool = False
    
    def __init__(self):
        self._progress_callback: Optional[Callable[[float], None]] = None
        self._task_id: Optional[str] = None
    
    @abstractmethod
    async def execute(self, **params) -> SkillResult:
        """
        执行技能
        
        Args:
            **params: 技能参数
            
        Returns:
            SkillResult 执行结果
        """
        pass
    
    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """
        获取 Function Calling Schema
        
        Returns:
            OpenAI 格式的工具定义
        """
        pass
    
    def needs_confirmation(self, params: Dict[str, Any]) -> bool:
        """
        检查是否需要用户确认
        
        Args:
            params: 执行参数
            
        Returns:
            是否需要确认
        """
        return self.permission_level == PermissionLevel.CRITICAL
    
    def validate_params(self, params: Dict[str, Any]) -> Optional[str]:
        """
        验证参数
        
        Args:
            params: 执行参数
            
        Returns:
            错误信息，None 表示验证通过
        """
        return None
    
    def set_progress_callback(self, callback: Callable[[float], None]):
        """
        设置进度回调函数
        
        Args:
            callback: 进度回调函数，参数为进度 (0.0-1.0)
        """
        self._progress_callback = callback
    
    def update_progress(self, progress: float):
        """
        更新进度
        
        Args:
            progress: 进度 (0.0-1.0)
        """
        if self._progress_callback:
            self._progress_callback(max(0.0, min(1.0, progress)))
    
    def set_task_id(self, task_id: str):
        """
        设置任务 ID
        
        Args:
            task_id: 任务 ID
        """
        self._task_id = task_id
    
    def can_run_background(self) -> bool:
        """
        检查是否可以后台运行
        
        Returns:
            是否支持后台运行
        """
        return self.supports_background
    
    def __repr__(self) -> str:
        return f"<Skill: {self.name}>"


def create_tool_schema(
    name: str,
    description: str,
    parameters: Dict[str, Any],
    required: Optional[List[str]] = None,
    supports_background: bool = False
) -> Dict[str, Any]:
    """
    创建 OpenAI Function Calling 格式的工具定义
    
    Args:
        name: 工具名称
        description: 工具描述
        parameters: 参数定义
        required: 必需参数列表
        supports_background: 是否支持后台运行
        
    Returns:
        工具定义字典
    """
    schema = {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": parameters,
                "required": required or []
            }
        }
    }
    
    if supports_background:
        schema["function"]["parameters"]["properties"]["run_in_background"] = {
            "type": "boolean",
            "description": "是否在后台运行此任务（不阻塞主线程）",
            "default": False
        }
    
    return schema
