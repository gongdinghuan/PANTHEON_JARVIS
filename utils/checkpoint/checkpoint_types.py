"""
检查点类型定义
Checkpoint Types Definition

定义所有检查点和回滚相关的数据类型
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from enum import Enum
import hashlib
import json


class CheckpointStatus(Enum):
    """检查点状态枚举"""
    ACTIVE = "active"           # 活跃，可用于回滚
    FROZEN = "frozen"           # 冻结，保留但不建议回滚
    SUPERSEDED = "superseded"   # 已废弃，被更新的检查点替代
    CORRUPTED = "corrupted"     # 损坏，无法使用
    DELETED = "deleted"         # 已删除


class CheckpointType(Enum):
    """检查点类型枚举"""
    MANUAL = "manual"           # 手动创建
    AUTOMATIC = "automatic"     # 自动创建（定时/事件触发）
    SNAPSHOT = "snapshot"       # 完整快照
    INCREMENTAL = "incremental" # 增量检查点
    STATE_ONLY = "state_only"   # 仅状态（无数据）


class RollbackStatus(Enum):
    """回滚状态枚举"""
    SUCCESS = "success"         # 回滚成功
    PARTIAL = "partial"         # 部分成功
    FAILED = "failed"           # 回滚失败
    CANCELLED = "cancelled"     # 回滚取消


@dataclass
class CheckpointMetadata:
    """检查点元数据"""
    checkpoint_id: str
    name: str
    checkpoint_type: CheckpointType
    status: CheckpointStatus
    created_at: datetime
    parent_checkpoint_id: Optional[str] = None
    description: str = ""
    tags: List[str] = field(default_factory=list)
    creator: str = "system"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'checkpoint_id': self.checkpoint_id,
            'name': self.name,
            'checkpoint_type': self.checkpoint_type.value,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'parent_checkpoint_id': self.parent_checkpoint_id,
            'description': self.description,
            'tags': self.tags,
            'creator': self.creator
        }


@dataclass
class CheckpointState:
    """检查点状态数据"""
    state_data: Dict[str, Any]
    state_hash: str
    state_size: int  # 字节大小
    created_at: datetime
    
    @classmethod
    def create(cls, data: Dict[str, Any]) -> 'CheckpointState':
        """创建状态数据"""
        json_str = json.dumps(data, sort_keys=True, default=str)
        return cls(
            state_data=data,
            state_hash=hashlib.sha256(json_str.encode()).hexdigest(),
            state_size=len(json_str.encode()),
            created_at=datetime.now()
        )
    
    def verify_integrity(self) -> bool:
        """验证状态完整性"""
        json_str = json.dumps(self.state_data, sort_keys=True, default=str)
        new_hash = hashlib.sha256(json_str.encode()).hexdigest()
        return new_hash == self.state_hash


@dataclass
class Checkpoint:
    """检查点类"""
    metadata: CheckpointMetadata
    state: CheckpointState
    
    @property
    def id(self) -> str:
        return self.metadata.checkpoint_id
    
    @property
    def name(self) -> str:
        return self.metadata.name
    
    @property
    def created_at(self) -> datetime:
        return self.metadata.created_at
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'metadata': self.metadata.to_dict(),
            'state': {
                'state_hash': self.state.state_hash,
                'state_size': self.state.state_size,
                'created_at': self.state.created_at.isoformat()
            }
        }
    
    def to_full_dict(self) -> Dict[str, Any]:
        """转换为完整字典（包含状态数据）"""
        return {
            'metadata': self.metadata.to_dict(),
            'state': {
                'state_data': self.state.state_data,
                'state_hash': self.state.state_hash,
                'state_size': self.state.state_size,
                'created_at': self.state.created_at.isoformat()
            }
        }


@dataclass
class RollbackOperation:
    """回滚操作记录"""
    operation_id: str
    from_checkpoint_id: str
    to_checkpoint_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: RollbackStatus = RollbackStatus.SUCCESS
    changes: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'operation_id': self.operation_id,
            'from_checkpoint_id': self.from_checkpoint_id,
            'to_checkpoint_id': self.to_checkpoint_id,
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'status': self.status.value,
            'changes': self.changes,
            'errors': self.errors,
            'metrics': self.metrics
        }


@dataclass
class RollbackResult:
    """回滚结果"""
    success: bool
    operation: RollbackOperation
    restored_state: Optional[Dict[str, Any]] = None
    message: str = ""
    
    @classmethod
    def success_result(cls, operation: RollbackOperation, restored_state: Dict[str, Any]) -> 'RollbackResult':
        return cls(
            success=True,
            operation=operation,
            restored_state=restored_state,
            message="回滚成功完成"
        )
    
    @classmethod
    def partial_result(cls, operation: RollbackOperation, restored_state: Dict[str, Any], message: str) -> 'RollbackResult':
        return cls(
            success=True,
            operation=operation,
            restored_state=restored_state,
            message=message
        )
    
    @classmethod
    def failed_result(cls, operation: RollbackOperation, errors: List[str]) -> 'RollbackResult':
        return cls(
            success=False,
            operation=operation,
            message=f"回滚失败: {', '.join(errors)}"
        )


@dataclass
class CheckpointDiff:
    """检查点差异比较结果"""
    checkpoint_a_id: str
    checkpoint_b_id: str
    added_keys: List[str]
    removed_keys: List[str]
    modified_keys: List[str]
    unchanged_keys: List[str]
    diff_summary: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'checkpoint_a_id': self.checkpoint_a_id,
            'checkpoint_b_id': self.checkpoint_b_id,
            'added_keys': self.added_keys,
            'removed_keys': self.removed_keys,
            'modified_keys': self.modified_keys,
            'unchanged_keys': self.unchanged_keys,
            'diff_summary': self.diff_summary
        }