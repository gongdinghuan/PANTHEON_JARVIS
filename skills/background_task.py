"""
JARVIS 后台任务技能
演示后台任务执行功能

Author: gngdingghuan
"""

import asyncio
import time
from typing import Dict, Any, Optional

from skills.base_skill import BaseSkill, SkillResult, PermissionLevel, create_tool_schema
from utils.logger import log


class BackgroundTaskSkill(BaseSkill):
    """后台任务演示技能"""
    
    name = "background_task"
    description = "执行后台任务（演示用）"
    permission_level = PermissionLevel.READ_ONLY
    supports_background = True  # 支持后台执行
    
    def __init__(self):
        super().__init__()
    
    async def execute(self, action: str, **params) -> SkillResult:
        """执行后台操作"""
        actions = {
            "long_running_task": self._long_running_task,
            "countdown": self._countdown,
            "simulate_download": self._simulate_download,
        }
        
        if action not in actions:
            return SkillResult(success=False, output=None, error=f"未知的操作: {action}")
        
        try:
            result = await actions[action](**params)
            return result
        except Exception as e:
            log.error(f"后台任务失败: {action}, 错误: {e}")
            return SkillResult(success=False, output=None, error=str(e))
    
    async def _long_running_task(
        self,
        duration: int = 10,
        name: str = "长时间任务"
    ) -> SkillResult:
        """模拟长时间运行的任务"""
        log.info(f"开始执行长时间任务: {name}, 预计 {duration} 秒")
        
        total_steps = duration
        for i in range(total_steps):
            await asyncio.sleep(1)
            progress = (i + 1) / total_steps
            self.update_progress(progress)
            log.debug(f"任务进度: {progress * 100:.1f}%")
        
        result = {
            "name": name,
            "duration": duration,
            "message": f"{name} 已完成"
        }
        
        return SkillResult(
            success=True,
            output=result,
            is_background=True
        )
    
    async def _countdown(
        self,
        seconds: int = 5,
        message: str = "倒计时"
    ) -> SkillResult:
        """倒计时任务"""
        log.info(f"开始倒计时: {message}, {seconds} 秒")
        
        for i in range(seconds, 0, -1):
            await asyncio.sleep(1)
            progress = 1 - (i / seconds)
            self.update_progress(progress)
            log.debug(f"{message} 剩余: {i} 秒")
        
        result = {
            "message": f"{message} 完成",
            "seconds": seconds
        }
        
        return SkillResult(
            success=True,
            output=result,
            is_background=True
        )
    
    async def _simulate_download(
        self,
        filename: str = "example.txt",
        size_mb: int = 100,
        speed_mbps: int = 10
    ) -> SkillResult:
        """模拟文件下载"""
        log.info(f"开始模拟下载: {filename}, 大小: {size_mb}MB, 速度: {speed_mbps}MB/s")
        
        total_chunks = size_mb * 10
        downloaded_mb = 0
        
        for i in range(total_chunks):
            await asyncio.sleep(0.1)  # 模拟下载延迟
            downloaded_mb += 0.1
            progress = downloaded_mb / size_mb
            self.update_progress(progress)
            log.debug(f"下载进度: {downloaded_mb:.1f}/{size_mb}MB ({progress * 100:.1f}%)")
        
        result = {
            "filename": filename,
            "size_mb": size_mb,
            "message": f"下载完成: {filename} ({size_mb}MB)"
        }
        
        return SkillResult(
            success=True,
            output=result,
            is_background=True
        )
    
    def get_schema(self) -> Dict[str, Any]:
        """获取 Function Calling Schema"""
        return create_tool_schema(
            name="background_task",
            description="执行后台任务，适合长时间运行的操作",
            parameters={
                "action": {
                    "type": "string",
                    "enum": ["long_running_task", "countdown", "simulate_download"],
                    "description": "操作类型"
                },
                "run_in_background": {
                    "type": "boolean",
                    "description": "是否在后台运行（默认为 true）",
                    "default": True
                },
                "duration": {
                    "type": "integer",
                    "description": "持续时间（秒），用于 long_running_task"
                },
                "name": {
                    "type": "string",
                    "description": "任务名称"
                },
                "seconds": {
                    "type": "integer",
                    "description": "倒计时秒数，用于 countdown"
                },
                "message": {
                    "type": "string",
                    "description": "消息文本"
                },
                "filename": {
                    "type": "string",
                    "description": "文件名，用于 simulate_download"
                },
                "size_mb": {
                    "type": "integer",
                    "description": "文件大小（MB），用于 simulate_download"
                },
                "speed_mbps": {
                    "type": "integer",
                    "description": "下载速度（MB/s），用于 simulate_download"
                }
            },
            required=["action"]
        )
