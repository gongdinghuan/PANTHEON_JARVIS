"""
JARVIS 终端命令技能
执行系统命令（带安全限制）

Author: gngdingghuan
"""

import asyncio
import os
import subprocess
from typing import Dict, Any, Optional, List

from skills.base_skill import BaseSkill, SkillResult, PermissionLevel, create_tool_schema
from config import get_config
from utils.logger import log
from utils.platform_utils import is_windows, get_shell


class TerminalSkill(BaseSkill):
    """终端命令执行技能"""
    
    name = "terminal"
    description = "执行终端命令（受安全限制）"
    permission_level = PermissionLevel.CRITICAL  # 危险操作，需要确认
    
    def __init__(self):
        super().__init__()
        self.security_config = get_config().security
        self._shell = get_shell()
    
    def _is_command_safe(self, command: str) -> bool:
        """检查命令是否安全"""
        command_lower = command.lower().strip()
        
        # 检查禁止的命令
        for forbidden in self.security_config.forbidden_commands:
            if forbidden.lower() in command_lower:
                return False
        
        return True
    
    def _is_command_readonly(self, command: str) -> bool:
        """检查命令是否为只读命令"""
        command_lower = command.lower().strip()
        
        # 获取命令的第一个词
        first_word = command_lower.split()[0] if command_lower.split() else ""
        
        # 检查是否在安全命令列表中
        for safe_cmd in self.security_config.safe_commands:
            if command_lower.startswith(safe_cmd.lower()):
                return True
            if first_word == safe_cmd.lower().split()[0]:
                return True
        
        return False
    
    def needs_confirmation(self, params: Dict[str, Any]) -> bool:
        """检查是否需要确认"""
        command = params.get("command", "")
        
        # 只读命令不需要确认
        if self._is_command_readonly(command):
            return False
        
        # 其他命令需要确认
        return True
    
    async def execute(self, action: str, **params) -> SkillResult:
        """执行终端操作"""
        actions = {
            "run_command": self._run_command,
            "run_safe_command": self._run_safe_command,
            "learn_command": self._learn_command,
            "list_safe_commands": self._list_safe_commands,
        }
        
        if action not in actions:
            return SkillResult(success=False, output=None, error=f"未知的操作: {action}")
        
        try:
            result = await actions[action](**params)
            return result
        except Exception as e:
            log.error(f"终端操作失败: {action}, 错误: {e}")
            return SkillResult(success=False, output=None, error=str(e))
    
    async def _run_command(
        self,
        command: str,
        cwd: Optional[str] = None,
        timeout: int = 30
    ) -> SkillResult:
        """执行命令"""
        # 安全检查
        if not self._is_command_safe(command):
            return SkillResult(
                success=False,
                output=None,
                error=f"命令被拒绝：包含禁止的操作"
            )
        
        log.info(f"执行命令: {command}")
        
        try:
            # 根据平台选择 shell
            if is_windows():
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=cwd,
                    shell=True,
                )
            else:
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=cwd,
                    shell=True,
                    executable="/bin/bash"
                )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                return SkillResult(
                    success=False,
                    output=None,
                    error=f"命令执行超时（{timeout}秒）"
                )
            
            # 解码输出
            stdout_str = stdout.decode('utf-8', errors='replace').strip()
            stderr_str = stderr.decode('utf-8', errors='replace').strip()
            
            # 限制输出长度
            if len(stdout_str) > 5000:
                stdout_str = stdout_str[:5000] + "\n...(输出已截断)"
            
            if process.returncode == 0:
                return SkillResult(
                    success=True,
                    output={
                        "returncode": process.returncode,
                        "stdout": stdout_str,
                        "stderr": stderr_str
                    }
                )
            else:
                return SkillResult(
                    success=False,
                    output={
                        "returncode": process.returncode,
                        "stdout": stdout_str,
                        "stderr": stderr_str
                    },
                    error=f"命令返回非零状态码: {process.returncode}"
                )
                
        except Exception as e:
            return SkillResult(success=False, output=None, error=str(e))
    
    async def _run_safe_command(
        self,
        command: str,
        cwd: Optional[str] = None,
        timeout: int = 30
    ) -> SkillResult:
        """执行安全命令（只读类）"""
        if not self._is_command_readonly(command):
            return SkillResult(
                success=False,
                output=None,
                error=f"命令不在安全列表中: {command}"
            )
        
        # 安全命令直接执行
        return await self._run_command(command, cwd, timeout)
    
    def get_schema(self) -> Dict[str, Any]:
        """获取 Function Calling Schema"""
        return create_tool_schema(
            name="terminal",
            description="执行终端命令。危险命令会被拒绝，需要用户确认才能执行",
            parameters={
                "action": {
                    "type": "string",
                    "enum": ["run_command", "run_safe_command", "learn_command", "list_safe_commands"],
                    "description": "操作类型：run_command 需要确认，run_safe_command 仅执行只读命令，learn_command 学习新的安全命令，list_safe_commands 列出所有安全命令"
                },
                "command": {
                    "type": "string",
                    "description": "要执行的命令或要学习的命令（list_safe_commands 不需要此参数）"
                },
                "cwd": {
                    "type": "string",
                    "description": "工作目录（可选）"
                },
                "timeout": {
                    "type": "integer",
                    "description": "超时时间（秒）"
                }
            },
            required=["action"]
        )
    
    async def _learn_command(self, command: str) -> SkillResult:
        """
        学习新的安全命令
        
        将命令添加到安全命令列表，以后执行该命令不需要确认
        
        Args:
            command: 要学习的命令
            
        Returns:
            SkillResult
        """
        command = command.strip()
        
        if not command:
            return SkillResult(
                success=False,
                output=None,
                error="命令不能为空"
            )
        
        # 尝试学习命令
        success = self.security_config.learn_safe_command(command)
        
        if success:
            return SkillResult(
                success=True,
                output={
                    "message": f"已将命令添加到安全列表: {command}",
                    "command": command
                }
            )
        else:
            return SkillResult(
                success=False,
                output=None,
                error=f"无法学习命令，可能包含危险操作: {command}"
            )
    
    async def _list_safe_commands(self) -> SkillResult:
        """
        列出所有安全命令
        
        Returns:
            SkillResult
        """
        # 获取内置的安全命令
        built_in_commands = self.security_config.safe_commands[:10]  # 前10个是内置的
        
        # 获取用户学习的命令
        learned_commands = self.security_config.get_learned_commands()
        
        return SkillResult(
            success=True,
            output={
                "built_in_count": len([c for c in self.security_config.safe_commands if c not in learned_commands]),
                "learned_count": len(learned_commands),
                "total_count": len(self.security_config.safe_commands),
                "learned_commands": learned_commands,
                "sample_built_in": built_in_commands
            }
        )
