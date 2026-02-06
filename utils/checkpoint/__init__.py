"""
检查点和回滚功能系统
Checkpoint and Rollback System

功能：
1. 创建检查点 - 保存系统/任务状态
2. 恢复到检查点 - 回滚到之前的状态
3. 管理检查点 - 列出、删除、比较检查点
4. 自动检查点 - 定时保存状态
5. 状态追踪 - 记录状态变化历史

作者: JARVIS AI
版本: 1.0.0
"""

from .checkpoint_manager import CheckpointManager
from .checkpoint_types import Checkpoint, CheckpointStatus, RollbackResult

__all__ = [
    'CheckpointManager',
    'Checkpoint',
    'CheckpointStatus',
    'RollbackResult'
]

__version__ = '1.0.0'