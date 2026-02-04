"""
JARVIS 权限管理模块
实现权限分级和路径/命令检查

Author: gngdingghuan
"""

from enum import Enum
from pathlib import Path
from typing import Dict, Any, List, Optional

from config import get_config, PermissionLevel
from utils.logger import log


class PermissionManager:
    """
    权限管理器
    - 检查路径是否安全
    - 检查命令是否允许
    - 记录操作日志
    """
    
    def __init__(self):
        self.config = get_config().security
        
        # 操作日志
        self._operation_log: List[Dict[str, Any]] = []
        
        log.info("权限管理器初始化完成")
    
    def check_permission(
        self,
        skill_name: str,
        action: str,
        params: Dict[str, Any],
        permission_level: PermissionLevel
    ) -> Dict[str, Any]:
        """
        检查操作权限
        
        Args:
            skill_name: 技能名称
            action: 操作名称
            params: 操作参数
            permission_level: 权限级别
            
        Returns:
            {
                "allowed": bool,
                "needs_confirmation": bool,
                "reason": str
            }
        """
        result = {
            "allowed": True,
            "needs_confirmation": False,
            "reason": ""
        }
        
        # 检查路径参数
        for key in ["path", "source", "destination", "filepath"]:
            if key in params:
                path = params[key]
                if not self.is_path_allowed(path):
                    result["allowed"] = False
                    result["reason"] = f"路径不在允许范围内: {path}"
                    return result
        
        # 检查命令参数
        if "command" in params:
            command = params["command"]
            if not self.is_command_allowed(command):
                result["allowed"] = False
                result["reason"] = f"命令被禁止: {command}"
                return result
        
        # 根据权限级别决定是否需要确认
        if permission_level == PermissionLevel.CRITICAL:
            result["needs_confirmation"] = self.config.require_confirmation
            result["reason"] = "危险操作，需要用户确认"
        
        # 记录操作
        self._log_operation(skill_name, action, params, permission_level)
        
        return result
    
    def is_path_allowed(self, path: str) -> bool:
        """
        检查路径是否允许访问
        
        Args:
            path: 文件或目录路径
            
        Returns:
            是否允许
        """
        try:
            path_obj = Path(path).expanduser().resolve()
            path_str = str(path_obj)
            
            # 检查黑名单
            for forbidden in self.config.forbidden_directories:
                forbidden_path = Path(forbidden).resolve()
                if path_str.startswith(str(forbidden_path)):
                    log.warning(f"路径被拒绝（黑名单）: {path}")
                    return False
            
            # 如果白名单为空，允许所有非黑名单路径
            if not self.config.allowed_directories:
                return True
            
            # 检查白名单
            for allowed in self.config.allowed_directories:
                allowed_path = Path(allowed).expanduser().resolve()
                if path_str.startswith(str(allowed_path)):
                    return True
            
            log.warning(f"路径被拒绝（不在白名单）: {path}")
            return False
            
        except Exception as e:
            log.error(f"路径检查失败: {e}")
            return False
    
    def is_command_allowed(self, command: str) -> bool:
        """
        检查命令是否允许执行
        
        Args:
            command: 命令字符串
            
        Returns:
            是否允许
        """
        command_lower = command.lower().strip()
        
        # 检查禁止的命令
        for forbidden in self.config.forbidden_commands:
            if forbidden.lower() in command_lower:
                log.warning(f"命令被拒绝（黑名单）: {command}")
                return False
        
        return True
    
    def is_command_safe(self, command: str) -> bool:
        """
        检查命令是否为安全（只读）命令
        
        Args:
            command: 命令字符串
            
        Returns:
            是否安全
        """
        command_lower = command.lower().strip()
        first_word = command_lower.split()[0] if command_lower.split() else ""
        
        for safe_cmd in self.config.safe_commands:
            if command_lower.startswith(safe_cmd.lower()):
                return True
            if first_word == safe_cmd.lower().split()[0]:
                return True
        
        return False
    
    def _log_operation(
        self,
        skill_name: str,
        action: str,
        params: Dict[str, Any],
        permission_level: PermissionLevel
    ):
        """记录操作日志"""
        from datetime import datetime
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "skill": skill_name,
            "action": action,
            "params": params,
            "permission_level": permission_level.name,
        }
        
        self._operation_log.append(log_entry)
        
        # 限制日志大小
        if len(self._operation_log) > 1000:
            self._operation_log = self._operation_log[-500:]
        
        # 危险操作特别记录
        if permission_level == PermissionLevel.CRITICAL:
            log.warning(f"危险操作: {skill_name}.{action} - {params}")
    
    def get_operation_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取操作日志"""
        return self._operation_log[-limit:]
    
    def add_allowed_directory(self, path: str):
        """添加允许的目录"""
        path_resolved = str(Path(path).expanduser().resolve())
        if path_resolved not in self.config.allowed_directories:
            self.config.allowed_directories.append(path_resolved)
            log.info(f"已添加允许目录: {path_resolved}")
    
    def remove_allowed_directory(self, path: str):
        """移除允许的目录"""
        path_resolved = str(Path(path).expanduser().resolve())
        if path_resolved in self.config.allowed_directories:
            self.config.allowed_directories.remove(path_resolved)
            log.info(f"已移除允许目录: {path_resolved}")
    
    def get_security_summary(self) -> Dict[str, Any]:
        """获取安全配置摘要"""
        return {
            "allowed_directories": self.config.allowed_directories,
            "forbidden_directories": self.config.forbidden_directories,
            "safe_commands_count": len(self.config.safe_commands),
            "forbidden_commands_count": len(self.config.forbidden_commands),
            "require_confirmation": self.config.require_confirmation,
            "recent_operations": len(self._operation_log),
        }
