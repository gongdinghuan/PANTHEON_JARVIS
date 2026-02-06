"""
后台任务管理器
支持技能在后台运行，不阻塞主线程

Author: gngdingghuan
"""

import asyncio
import threading
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed

from utils.logger import log


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BackgroundTask:
    """后台任务"""
    task_id: str
    name: str
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    progress: float = 0.0
    is_background: bool = True
    user_id: Optional[str] = None  # 发起任务的用户


class TaskManager:
    """
    任务管理器
    - 支持同步和异步任务
    - 支持后台运行
    - 支持任务取消
    - 支持进度跟踪
    - 支持完成通知
    """
    
    def __init__(self, max_workers: int = 5):
        """
        初始化任务管理器
        
        Args:
            max_workers: 最大工作线程数
        """
        self.max_workers = max_workers
        self._tasks: Dict[str, BackgroundTask] = {}
        self._task_counter = 0
        
        # 线程池
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # 异步事件循环
        self._loop = None
        self._async_tasks: Dict[str, asyncio.Task] = {}
        
        # 通知回调 (user_id, task_id, result_dict)
        self._notification_callback: Optional[Callable[[str, str, Dict], Any]] = None
        
        log.info(f"任务管理器初始化完成，最大工作线程: {max_workers}")

    def set_notification_callback(self, callback: Callable[[str, str, Dict], Any]):
        """设置完成通知回调"""
        self._notification_callback = callback
    
    async def submit_task(
        self,
        name: str,
        func: Callable,
        *args,
        is_background: bool = True,
        user_id: str = "default",  # 默认用户
        **kwargs
    ) -> str:
        """
        提交任务
        
        Args:
            name: 任务名称
            func: 要执行的函数
            *args: 位置参数
            is_background: 是否后台运行
            user_id: 发起用户 ID
            **kwargs: 关键字参数
            
        Returns:
            任务 ID
        """
        self._task_counter += 1
        task_id = f"task_{self._task_counter}"
        
        task = BackgroundTask(
            task_id=task_id,
            name=name,
            func=func,
            args=args,
            kwargs=kwargs,
            is_background=is_background,
            user_id=user_id
        )
        
        self._tasks[task_id] = task
        
        if is_background:
            # 获取当前事件循环
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                #如果没有运行的 loop (极少见情况)，则无法调度回调
                log.warning(f"无法获取事件循环，任务 {name} 完成后可能无法触发异步通知")
                loop = None

            # 后台任务：在线程池中运行
            future = self._executor.submit(self._run_task, task)
            
            def done_callback(f):
                if loop and loop.is_running():
                    asyncio.run_coroutine_threadsafe(
                        self._on_task_complete(task_id, f),
                        loop
                    )
            
            future.add_done_callback(done_callback)
            log.info(f"后台任务已提交: {name} (ID: {task_id}, User: {user_id})")
        else:
            # 前台任务：在事件循环中运行
            task = asyncio.create_task(self._run_async_task(task))
            self._async_tasks[task_id] = task
            log.info(f"前台任务已提交: {name} (ID: {task_id}, User: {user_id})")
        
        return task_id
    
    def _run_task(self, task: BackgroundTask) -> Any:
        """
        在线程中运行同步任务
        """
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now().isoformat()
        
        try:
            result = task.func(*task.args, **task.kwargs)
            
            # 如果结果是协程 (例如 async 函数或 partial(async_func))，则在独立事件循环中运行
            if asyncio.iscoroutine(result):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(result)
                finally:
                    loop.close()
            
            task.status = TaskStatus.COMPLETED
            task.result = result
            return result
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            log.error(f"任务执行失败: {task.name}, 错误: {e}")
            raise
        finally:
            task.completed_at = datetime.now().isoformat()
    
    async def _run_async_task(self, task: BackgroundTask) -> Any:
        """
        运行异步任务
        """
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now().isoformat()
        
        try:
            if asyncio.iscoroutinefunction(task.func):
                result = await task.func(*task.args, **task.kwargs)
            else:
                # 如果是同步函数，在线程中运行
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(
                    self._executor,
                    lambda: task.func(*task.args, **task.kwargs)
                )
            
            task.status = TaskStatus.COMPLETED
            task.result = result
            return result
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            log.error(f"任务执行失败: {task.name}, 错误: {e}")
            raise
        finally:
            task.completed_at = datetime.now().isoformat()
            # 异步任务手动触发完成回调 (对于 submit 放在 async_tasks 中的情况)
            # 注意: 这里简单起见，不重复触发，因为 caller 一般会 await.
            # 但为了统一通知，我们可以在这里调用 _notify
            await self._notify_completion(task)
    
    async def _on_task_complete(self, task_id: str, future):
        """任务完成回调 (线程池任务)"""
        try:
            result = future.result()
            if task_id in self._tasks:
                task = self._tasks[task_id]
                task.result = result
                log.info(f"任务完成: {task.name} (ID: {task_id})")
                
                # 触发通知
                await self._notify_completion(task)
                
        except Exception as e:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                task.error = str(e)
                log.error(f"任务异常: {task.name}, 错误: {e}")
                # 失败也通知
                await self._notify_completion(task)
                
    async def _notify_completion(self, task: BackgroundTask):
        """发送完成通知"""
        if self._notification_callback and task.user_id:
            try:
                result_data = {
                    "success": task.status == TaskStatus.COMPLETED,
                    "output": task.result,
                    "error": task.error,
                    "name": task.name
                }
                await self._notification_callback(task.user_id, task.task_id, result_data)
            except Exception as e:
                log.error(f"发送任务通知失败: {e}")
    
    def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务 ID
            
        Returns:
            是否成功取消
        """
        if task_id not in self._tasks:
            return False
        
        task = self._tasks[task_id]
        
        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            return False
        
        task.status = TaskStatus.CANCELLED
        
        # 取消异步任务
        if task_id in self._async_tasks:
            self._async_tasks[task_id].cancel()
            del self._async_tasks[task_id]
        
        log.info(f"任务已取消: {task.name} (ID: {task_id})")
        return True
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态
        
        Args:
            task_id: 任务 ID
            
        Returns:
            任务状态信息
        """
        if task_id not in self._tasks:
            return None
        
        task = self._tasks[task_id]
        
        return {
            "task_id": task.task_id,
            "name": task.name,
            "status": task.status.value,
            "created_at": task.created_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "result": task.result,
            "error": task.error,
            "progress": task.progress,
            "is_background": task.is_background
        }
    
    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        列出任务
        
        Args:
            status: 按状态筛选
            limit: 返回数量限制
            
        Returns:
            任务列表
        """
        tasks = []
        
        for task in self._tasks.values():
            if status is None or task.status == status:
                tasks.append({
                    "task_id": task.task_id,
                    "name": task.name,
                    "status": task.status.value,
                    "created_at": task.created_at,
                    "started_at": task.started_at,
                    "completed_at": task.completed_at,
                    "is_background": task.is_background
                })
        
        # 按创建时间倒序
        tasks.sort(key=lambda x: x["created_at"], reverse=True)
        
        return tasks[:limit]
    
    def update_progress(self, task_id: str, progress: float):
        """
        更新任务进度
        
        Args:
            task_id: 任务 ID
            progress: 进度 (0.0 - 1.0)
        """
        if task_id in self._tasks:
            self._tasks[task_id].progress = max(0.0, min(1.0, progress))
    
    def get_active_tasks_count(self) -> int:
        """获取活跃任务数"""
        return sum(
            1 for task in self._tasks.values()
            if task.status == TaskStatus.RUNNING
        )
    
    def get_completed_tasks_count(self) -> int:
        """获取已完成任务数"""
        return sum(
            1 for task in self._tasks.values()
            if task.status == TaskStatus.COMPLETED
        )
    
    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """
        清理旧任务
        
        Args:
            max_age_hours: 最大保留时间（小时）
        """
        cutoff = datetime.now().timestamp() - (max_age_hours * 3600)
        to_remove = []
        
        for task_id, task in self._tasks.items():
            created_time = datetime.fromisoformat(task.created_at).timestamp()
            
            if (
                task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
                and created_time < cutoff
            ):
                to_remove.append(task_id)
        
        for task_id in to_remove:
            del self._tasks[task_id]
        
        if to_remove:
            log.info(f"已清理 {len(to_remove)} 个旧任务")
    
    async def wait_for_task(self, task_id: str, timeout: Optional[float] = None) -> Any:
        """
        等待任务完成
        
        Args:
            task_id: 任务 ID
            timeout: 超时时间（秒）
            
        Returns:
            任务结果
            
        Raises:
            TimeoutError: 超时
            Exception: 任务失败
        """
        if task_id not in self._tasks:
            raise ValueError(f"任务不存在: {task_id}")
        
        task = self._tasks[task_id]
        
        # 等待任务完成
        while task.status == TaskStatus.RUNNING or task.status == TaskStatus.PENDING:
            await asyncio.sleep(0.1)
            
            # 检查超时
            if timeout:
                elapsed = (
                    datetime.now().timestamp()
                    - datetime.fromisoformat(task.started_at).timestamp()
                    if task.started_at
                    else 0
                )
                
                if elapsed > timeout:
                    self.cancel_task(task_id)
                    raise TimeoutError(f"任务超时: {task.name}")
        
        # 检查任务状态
        if task.status == TaskStatus.COMPLETED:
            return task.result
        elif task.status == TaskStatus.FAILED:
            raise Exception(f"任务失败: {task.error}")
        elif task.status == TaskStatus.CANCELLED:
            raise Exception("任务已取消")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取任务统计
        
        Returns:
            统计信息
        """
        total = len(self._tasks)
        pending = sum(1 for t in self._tasks.values() if t.status == TaskStatus.PENDING)
        running = sum(1 for t in self._tasks.values() if t.status == TaskStatus.RUNNING)
        completed = sum(1 for t in self._tasks.values() if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in self._tasks.values() if t.status == TaskStatus.FAILED)
        cancelled = sum(1 for t in self._tasks.values() if t.status == TaskStatus.CANCELLED)
        
        return {
            "total_tasks": total,
            "pending": pending,
            "running": running,
            "completed": completed,
            "failed": failed,
            "cancelled": cancelled,
            "active_tasks_count": self.get_active_tasks_count(),
            "completed_tasks_count": self.get_completed_tasks_count()
        }
    
    async def shutdown(self, wait: bool = True):
        """
        关闭任务管理器
        
        Args:
            wait: 是否等待所有任务完成
        """
        log.info("正在关闭任务管理器...")
        
        # 取消所有运行中的异步任务
        for task_id, async_task in list(self._async_tasks.items()):
            if not async_task.done():
                async_task.cancel()
        
        # 取消所有运行中的任务
        for task_id, task in list(self._tasks.items()):
            if task.status == TaskStatus.RUNNING:
                task.status = TaskStatus.CANCELLED
        
        if wait:
            # 等待所有异步任务完成
            for task_id, async_task in list(self._async_tasks.items()):
                try:
                    await asyncio.wait_for(asyncio.shield(async_task), timeout=2.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
        
        # 清空异步任务
        self._async_tasks.clear()
        
        # 关闭线程池
        self._executor.shutdown(wait=wait)
        
        log.info("任务管理器已关闭")


# 全局任务管理器实例
_global_task_manager: Optional[TaskManager] = None


def get_task_manager(max_workers: int = 5) -> TaskManager:
    """
    获取全局任务管理器实例
    
    Args:
        max_workers: 最大工作线程数
        
    Returns:
        任务管理器实例
    """
    global _global_task_manager
    
    if _global_task_manager is None:
        _global_task_manager = TaskManager(max_workers=max_workers)
    
    return _global_task_manager
