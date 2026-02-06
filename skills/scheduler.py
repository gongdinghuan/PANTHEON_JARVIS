"""
JARVIS 定时任务技能
创建、管理、执行定时任务
支持与心跳引擎集成的时间点调度

Author: JARVIS AI
"""

import asyncio
import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable, Union
from pathlib import Path

from skills.base_skill import BaseSkill, SkillResult, PermissionLevel, create_tool_schema
from utils.logger import log


class SchedulerSkill(BaseSkill):
    """定时任务技能"""
    
    name = "scheduler"
    description = "定时任务管理：创建、查看、删除定时任务，支持时间点调度"
    permission_level = PermissionLevel.SAFE_WRITE
    
    def __init__(self, heartbeat_engine=None):
        """
        初始化调度器技能
        
        Args:
            heartbeat_engine: 心跳引擎实例（可选，用于时间点调度）
        """
        super().__init__()
        self.tasks_file = Path.home() / ".jarvis" / "scheduled_tasks.json"
        self.tasks_file.parent.mkdir(parents=True, exist_ok=True)
        self.running_tasks = {}
        self.heartbeat = heartbeat_engine
        self.timepoint_events = {}
        self.load_tasks()
    
    def set_heartbeat_engine(self, heartbeat_engine):
        """
        设置心跳引擎（用于时间点调度）
        
        Args:
            heartbeat_engine: 心跳引擎实例
        """
        self.heartbeat = heartbeat_engine
        log.info("已设置心跳引擎，时间点调度已启用")
    
    def load_tasks(self):
        """加载保存的任务"""
        try:
            if self.tasks_file.exists():
                with open(self.tasks_file, 'r', encoding='utf-8') as f:
                    self.saved_tasks = json.load(f)
            else:
                self.saved_tasks = []
        except Exception as e:
            log.error(f"加载任务失败: {e}")
            self.saved_tasks = []
    
    def save_tasks(self):
        """保存任务到文件 (已排除非持久化任务)"""
        try:
            # 只保存 persistent != False 的任务
            # (处理旧数据默认没有 persistent 字段的情况，视为 True)
            tasks_to_save = [
                task for task in self.saved_tasks 
                if task.get("persistent", True) and not callable(task.get("command"))
            ]
            
            with open(self.tasks_file, 'w', encoding='utf-8') as f:
                json.dump(tasks_to_save, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            log.error(f"保存任务失败: {e}")
            return False
    
    def set_planner(self, planner):
        """注入 Planner 实例"""
        self.planner = planner
        log.info("已注入 Planner，定时任务支持自然语言指令")

    async def execute(self, action: str, **params) -> SkillResult:
        """
        执行定时任务操作
        
        Args:
            action: 操作类型
            **params: 操作参数
        """
        actions = {
            "create_task": self._create_task,
            "list_tasks": self._list_tasks,
            "delete_task": self._delete_task,
            "run_task": self._run_task,
            "start_scheduler": self._start_scheduler,
            "stop_scheduler": self._stop_scheduler,
        }
        
        if action not in actions:
            return SkillResult(
                success=False,
                output=None,
                error=f"未知的操作: {action}"
            )
        
        try:
            result = await actions[action](**params)
            return result
        except Exception as e:
            log.error(f"定时任务操作失败: {action}, 错误: {e}")
            return SkillResult(success=False, output=None, error=str(e))
    
    async def register_task(self, *args, **kwargs):
        """register_task 是 _create_task 的别名，供外部直接调用"""
        return await self._create_task(*args, **kwargs)

    async def _create_task(
        self,
        name: str,
        command: Union[str, Callable],
        schedule_type: str = "once",
        time_str: Optional[str] = None,
        interval_minutes: Optional[int] = None,
        days_of_week: Optional[List[str]] = None,
        enabled: bool = True,
        execution_mode: str = "brain",
        description: str = "",
        persistent: bool = True
    ) -> SkillResult:
        """创建定时任务"""
        log.info(f"创建定时任务: {name}, 模式: {execution_mode}, 持久化: {persistent}")
        
        task_id = f"task_{int(time.time())}_{len(self.saved_tasks)}"
        
        task = {
            "id": task_id,
            "name": name,
            "command": command,
            "schedule_type": schedule_type,
            "enabled": enabled,
            "execution_mode": execution_mode,
            "persistent": persistent,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "last_run": None,
            "next_run": None
        }
        
        # 设置调度参数
        if schedule_type == "once":
            if not time_str:
                return SkillResult(
                    success=False,
                    output=None,
                    error="一次性任务需要指定执行时间"
                )
            task["time"] = time_str
        
        elif schedule_type == "interval":
            if not interval_minutes or interval_minutes <= 0:
                return SkillResult(
                    success=False,
                    output=None,
                    error="间隔任务需要指定有效的间隔时间（分钟）"
                )
            task["interval_minutes"] = interval_minutes
        
        elif schedule_type == "daily":
            if not time_str:
                return SkillResult(
                    success=False,
                    output=None,
                    error="每日任务需要指定执行时间"
                )
            task["time"] = time_str
        
        elif schedule_type == "weekly":
            if not time_str or not days_of_week:
                return SkillResult(
                    success=False,
                    output=None,
                    error="每周任务需要指定执行时间和星期几"
                )
            task["time"] = time_str
            task["days_of_week"] = days_of_week
        
        elif schedule_type == "timepoint":
            # 精确时间点调度（使用心跳引擎）
            if not time_str:
                return SkillResult(
                    success=False,
                    output=None,
                    error="时间点任务需要指定执行时间（HH:MM格式）"
                )
            
            # 如果没有心跳引擎，给出警告但仍创建任务
            if not self.heartbeat:
                log.warning("未设置心跳引擎，时间点调度可能无法正常工作")
            
            task["time"] = time_str
            task["use_heartbeat"] = True
        
        else:
            return SkillResult(
                success=False,
                output=None,
                error=f"不支持的调度类型: {schedule_type}"
            )
        
        # 计算下次运行时间
        task["next_run"] = self._calculate_next_run(task)
        
        # 保存任务
        self.saved_tasks.append(task)
        self.save_tasks()
        
        return SkillResult(
            success=True,
            output={
                "task_id": task_id,
                "message": f"定时任务 '{name}' 创建成功",
                "next_run": task["next_run"]
            }
        )
    
    async def _list_tasks(self, show_all: bool = False) -> SkillResult:
        """列出所有定时任务"""
        if show_all:
            tasks = self.saved_tasks
        else:
            tasks = [t for t in self.saved_tasks if t.get("enabled", True)]
        
        return SkillResult(
            success=True,
            output={
                "tasks": tasks,
                "count": len(tasks)
            }
        )
    
    async def _delete_task(self, task_id: str) -> SkillResult:
        """删除定时任务"""
        log.info(f"删除定时任务: {task_id}")
        
        for i, task in enumerate(self.saved_tasks):
            if task["id"] == task_id:
                # 停止正在运行的任务
                if task_id in self.running_tasks:
                    self.running_tasks[task_id].cancel()
                    del self.running_tasks[task_id]
                
                # 从列表中删除
                deleted_task = self.saved_tasks.pop(i)
                self.save_tasks()
                
                return SkillResult(
                    success=True,
                    output={
                        "message": f"任务 '{deleted_task['name']}' 已删除",
                        "task_id": task_id
                    }
                )
        
        return SkillResult(
            success=False,
            output=None,
            error=f"未找到任务: {task_id}"
        )
    
    async def _run_task(self, task_id: str) -> SkillResult:
        """立即运行任务"""
        log.info(f"运行定时任务: {task_id}")
        
        for task in self.saved_tasks:
            if task["id"] == task_id:
                result = await self._execute_task_command(task)
                
                # 更新最后运行时间
                task["last_run"] = datetime.now().isoformat()
                self.save_tasks()
                
                return SkillResult(
                    success=True,
                    output={
                        "message": f"任务 '{task['name']}' 执行完成",
                        "result": result
                    }
                )
        
        return SkillResult(
            success=False,
            output=None,
            error=f"未找到任务: {task_id}"
        )
    
    async def _start_scheduler(self) -> SkillResult:
        """启动任务调度器"""
        log.info("启动任务调度器")
        
        # 启动后台任务
        for task in self.saved_tasks:
            if task.get("enabled", True):
                await self._schedule_task(task)
        
        # 注册时间点任务到心跳引擎
        if self.heartbeat:
            await self._register_timepoint_tasks()
        
        return SkillResult(
            success=True,
            output={
                "message": "任务调度器已启动",
                "running_tasks": len(self.running_tasks)
            }
        )
    
    async def _stop_scheduler(self) -> SkillResult:
        """停止任务调度器"""
        log.info("停止任务调度器")
        
        # 停止所有运行中的任务
        for task_id, task in self.running_tasks.items():
            task.cancel()
        
        self.running_tasks.clear()
        
        return SkillResult(
            success=True,
            output={
                "message": "任务调度器已停止",
                "stopped_tasks": len(self.running_tasks)
            }
        )
    
    async def _schedule_task(self, task: Dict[str, Any]):
        """调度单个任务"""
        task_id = task["id"]
        
        # 跳过时间点任务（这些由心跳引擎处理）
        if task.get("schedule_type") == "timepoint":
            log.debug(f"跳过时间点任务的调度: {task['name']}（由心跳引擎处理）")
            return
        
        async def task_runner():
            while True:
                try:
                    now = datetime.now()
                    next_run = datetime.fromisoformat(task["next_run"])
                    
                    # 等待到执行时间
                    wait_seconds = (next_run - now).total_seconds()
                    if wait_seconds > 0:
                        await asyncio.sleep(wait_seconds)
                    
                    # 执行任务
                    log.info(f"执行定时任务: {task['name']}")
                    await self._execute_task_command(task)
                    
                    # 更新最后运行时间
                    task["last_run"] = datetime.now().isoformat()
                    
                    # 计算下次运行时间
                    task["next_run"] = self._calculate_next_run(task)
                    self.save_tasks()
                    
                    # 如果是一次性任务，停止调度
                    if task["schedule_type"] == "once":
                        break
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    log.error(f"任务执行失败: {task['name']}, 错误: {e}")
                    await asyncio.sleep(60)  # 出错后等待1分钟再重试
        
        # 创建并运行任务
        runner_task = asyncio.create_task(task_runner())
        self.running_tasks[task_id] = runner_task
    
    async def _execute_task_command(self, task_data: Any) -> Dict[str, Any]:
        """执行任务命令"""
        
        # 解析参数
        if isinstance(task_data, str):
            command = task_data
            execution_mode = "shell"
        else:
            command = task_data.get("command", "")
            execution_mode = task_data.get("execution_mode", "shell")
            
        # 模式1: 大脑执行 (调用 Planner)
        if execution_mode == "brain":
            if hasattr(self, 'planner') and self.planner:
                log.info(f"通过大脑执行指令: {command}")
                try:
                    # 调用 Planner 执行自然语言指令
                    result = await self.planner.plan_and_execute(command, user_id="scheduler")
                    return result
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"大脑执行失败: {str(e)}"
                    }
            else:
                return {
                    "success": False, 
                    "error": "无法执行指令：未连接到大脑 (Planner not set)"
                }

        # 模式2: 函数直接执行 (In-Memory Callable)
        if execution_mode == "function":
            if callable(command):
                log.info(f"执行内部函数任务: {task_data.get('name', 'Unknown')}")
                try:
                    if asyncio.iscoroutinefunction(command) or (isinstance(command, functools.partial) and asyncio.iscoroutinefunction(command.func)):
                        await command()
                    else:
                        await asyncio.to_thread(command)
                    return {"success": True, "output": "Function executed successfully"}
                except Exception as e:
                    log.error(f"函数执行失败: {e}")
                    return {"success": False, "error": str(e)}
            else:
                return {"success": False, "error": "Command is not callable"}
        
        # 模式3: Shell 执行 (原有逻辑)
        try:
            import subprocess
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "任务执行超时"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _calculate_next_run(self, task: Dict[str, Any]) -> str:
        """计算下次运行时间"""
        now = datetime.now()
        
        if task["schedule_type"] == "once":
            # 一次性任务
            try:
                run_time = datetime.fromisoformat(task["time"])
                return run_time.isoformat()
            except:
                # 如果时间格式不对，设置为现在
                return now.isoformat()
        
        elif task["schedule_type"] == "interval":
            # 间隔任务
            interval = task.get("interval_minutes", 60)
            next_run = now + timedelta(minutes=interval)
            return next_run.isoformat()
        
        elif task["schedule_type"] == "daily":
            # 每日任务
            try:
                time_str = task["time"]
                hour, minute = map(int, time_str.split(":"))
                next_run = datetime(now.year, now.month, now.day, hour, minute)
                
                # 如果今天的时间已经过了，设置为明天
                if next_run < now:
                    next_run += timedelta(days=1)
                
                return next_run.isoformat()
            except:
                # 默认明天同一时间
                return (now + timedelta(days=1)).isoformat()
        
        elif task["schedule_type"] == "weekly":
            # 每周任务
            try:
                time_str = task["time"]
                days = task.get("days_of_week", [])
                hour, minute = map(int, time_str.split(":"))
                
                # 找到下一个符合条件的日期
                for i in range(8):  # 最多检查8天
                    next_date = now + timedelta(days=i)
                    weekday = next_date.strftime("%A").lower()
                    
                    if weekday in [d.lower() for d in days]:
                        next_run = datetime(
                            next_date.year,
                            next_date.month,
                            next_date.day,
                            hour,
                            minute
                        )
                        return next_run.isoformat()
                
                # 如果没有找到，返回一周后
                return (now + timedelta(days=7)).isoformat()
            except:
                return (now + timedelta(days=7)).isoformat()
        
        # 默认返回现在
        return now.isoformat()
    
    async def _register_timepoint_tasks(self):
        """注册时间点任务到心跳引擎"""
        for task in self.saved_tasks:
            if task.get("schedule_type") == "timepoint" and task.get("enabled", True):
                await self._register_timepoint_task(task)
    
    async def _register_timepoint_task(self, task: Dict[str, Any]):
        """注册单个时间点任务到心跳引擎"""
        if not self.heartbeat:
            log.warning(f"无法注册时间点任务 {task['name']}：未设置心跳引擎")
            return
        
        time_str = task.get("time", "")
        if not time_str:
            return
        
        try:
            hour, minute = map(int, time_str.split(":"))
            task_id = task["id"]
            
            # 创建回调函数
            async def task_callback():
                log.info(f"执行时间点任务: {task['name']}")
                result = await self._execute_task_command(task)
                task["last_run"] = datetime.now().isoformat()
                self.save_tasks()
                return result
            
            # 注册到心跳引擎
            event = self.heartbeat.register_timepoint_event(
                hour=hour,
                minute=minute,
                callback=task_callback,
                name=f"task_{task['name']}"
            )
            
            # 保存事件引用以便后续取消
            self.timepoint_events[task_id] = event
            log.info(f"已注册时间点任务到心跳引擎: {task['name']} @ {time_str}")
            
        except Exception as e:
            log.error(f"注册时间点任务失败: {task['name']}, 错误: {e}")
    
    def _unregister_timepoint_task(self, task_id: str):
        """取消注册时间点任务"""
        if task_id in self.timepoint_events and self.heartbeat:
            event = self.timepoint_events[task_id]
            self.heartbeat.unregister_timepoint_event(event)
            del self.timepoint_events[task_id]
            log.info(f"已取消时间点任务: {task_id}")
    
    def get_schema(self) -> Dict[str, Any]:
        """获取 Function Calling Schema"""
        return create_tool_schema(
            name="scheduler",
            description="定时任务管理：创建、查看、删除定时任务",
            parameters={
                "action": {
                    "type": "string",
                    "enum": [
                        "create_task",
                        "list_tasks", 
                        "delete_task",
                        "run_task",
                        "start_scheduler",
                        "stop_scheduler"
                    ],
                    "description": "要执行的操作类型"
                },
                "name": {
                    "type": "string",
                    "description": "任务名称（用于 create_task）"
                },
                "command": {
                    "type": "string",
                    "description": "要执行的命令（用于 create_task）"
                },
                "schedule_type": {
                    "type": "string",
                    "enum": ["once", "interval", "daily", "weekly", "timepoint"],
                    "description": "调度类型：once(一次性), interval(间隔), daily(每日), weekly(每周), timepoint(时间点，使用心跳引擎)（用于 create_task）"
                },
                "time_str": {
                    "type": "string",
                    "description": "执行时间，格式 HH:MM（用于 once, daily, weekly 类型）"
                },
                "interval_minutes": {
                    "type": "integer",
                    "description": "间隔时间（分钟）（用于 interval 类型）"
                },
                "days_of_week": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "星期几，如 ['Monday', 'Wednesday', 'Friday']（用于 weekly 类型）"
                },
                "enabled": {
                    "type": "boolean",
                    "description": "是否启用任务（用于 create_task）"
                },
                "task_id": {
                    "type": "string",
                    "description": "任务ID（用于 delete_task, run_task）"
                },
                "show_all": {
                    "type": "boolean",
                    "description": "是否显示所有任务（包括禁用的）（用于 list_tasks）"
                }
            },
            required=["action"]
        )