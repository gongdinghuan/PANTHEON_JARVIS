"""
JARVIS 自我修复模块
学习错误模式并提供智能恢复策略

Author: gngdingghuan
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from cognitive.memory import MemoryManager
from utils.logger import log


@dataclass
class ErrorPattern:
    """错误模式"""
    error_type: str
    count: int = 0
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    successful_recoveries: int = 0
    failed_recoveries: int = 0
    recovery_strategies: Dict[str, int] = field(default_factory=dict)
    avg_retry_count: float = 0.0
    context_snippets: List[str] = field(default_factory=list)


@dataclass
class RecoveryStrategy:
    """恢复策略"""
    strategy_type: str  # retry, fallback, skip, manual
    description: str
    applicable_errors: List[str]
    success_rate: float = 0.0
    avg_attempts: float = 0.0


class SelfHealingEngine:
    """
    自我修复引擎
    - 学习错误模式
    - 提供恢复策略
    - 记录修复结果
    """
    
    def __init__(self, memory: MemoryManager):
        self.memory = memory
        self._error_patterns: Dict[str, ErrorPattern] = {}
        self._recovery_strategies: Dict[str, RecoveryStrategy] = {}
        self._load_patterns()
        self._init_strategies()
    
    def _init_strategies(self):
        """初始化预设恢复策略"""
        self._recovery_strategies = {
            "network_timeout": RecoveryStrategy(
                strategy_type="retry",
                description="网络超时：自动重试（指数退避）",
                applicable_errors=["TimeoutError", "ConnectTimeout"],
                success_rate=0.7,
                avg_attempts=2.5
            ),
            "api_rate_limit": RecoveryStrategy(
                strategy_type="fallback",
                description="API 限流：切换到备用提供商",
                applicable_errors=["RateLimitError", "429Error"],
                success_rate=0.6,
                avg_attempts=2.0
            ),
            "authentication_failed": RecoveryStrategy(
                strategy_type="manual",
                description="认证失败：提示用户检查 API 密钥",
                applicable_errors=["AuthenticationError", "401Error"],
                success_rate=0.9,
                avg_attempts=1.0
            ),
            "resource_not_found": RecoveryStrategy(
                strategy_type="skip",
                description="资源不存在：跳过该操作并继续",
                applicable_errors=["FileNotFoundError", "404Error"],
                success_rate=1.0,
                avg_attempts=1.0
            ),
            "permission_denied": RecoveryStrategy(
                strategy_type="manual",
                description="权限拒绝：请求用户确认",
                applicable_errors=["PermissionError", "403Error"],
                success_rate=0.8,
                avg_attempts=1.5
            ),
            "skill_not_found": RecoveryStrategy(
                strategy_type="skip",
                description="技能不存在：告知用户并跳过",
                applicable_errors=["KeyError"],
                success_rate=1.0,
                avg_attempts=1.0
            ),
            "invalid_arguments": RecoveryStrategy(
                strategy_type="retry",
                description="参数无效：重试（可能需要修正参数）",
                applicable_errors=["ValueError", "400Error"],
                success_rate=0.5,
                avg_attempts=3.0
            ),
            "json_serialization": RecoveryStrategy(
                strategy_type="retry",
                description="JSON 序列化失败：转换为字符串后重试",
                applicable_errors=["TypeError", "ValueError"],
                success_rate=0.9,
                avg_attempts=2.0
            ),
        }
        
        log.info(f"已加载 {len(self._recovery_strategies)} 个预设恢复策略")
    
    def record_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        recovery_strategy: Optional[str] = None,
        success: bool = False
    ):
        """
        记录错误
        
        Args:
            error: 异常对象
            context: 错误上下文
            recovery_strategy: 使用的恢复策略
            success: 恢复是否成功
        """
        error_type = type(error).__name__
        
        if error_type not in self._error_patterns:
            self._error_patterns[error_type] = ErrorPattern(error_type=error_type)
        
        pattern = self._error_patterns[error_type]
        pattern.count += 1
        pattern.last_seen = datetime.now().isoformat()
        
        if pattern.first_seen is None:
            pattern.first_seen = pattern.last_seen
        
        if success:
            pattern.successful_recoveries += 1
            if recovery_strategy:
                pattern.recovery_strategies[recovery_strategy] = (
                    pattern.recovery_strategies.get(recovery_strategy, 0) + 1
                )
        else:
            pattern.failed_recoveries += 1
        
        # 记录到长期记忆
        self._save_error_to_memory(error, context, recovery_strategy, success)
        
        log.info(f"已记录错误: {error_type}, 策略: {recovery_strategy}, 成功: {success}")
    
    def _save_error_to_memory(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]],
        strategy: Optional[str],
        success: bool
    ):
        """保存错误到长期记忆"""
        # 检查 ChromaDB collection 是否可用
        if not self.memory._collection:
            return
        
        error_record = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.now().isoformat(),
            "context": context or {},
            "recovery_strategy": strategy,
            "recovery_success": success,
        }
        
        try:
            self.memory._collection.add(
                documents=[json.dumps(error_record, ensure_ascii=False)],
                metadatas=[{
                    "type": "error_record",
                    "error_type": error_record["error_type"],
                    "timestamp": error_record["timestamp"],
                    "recovery_success": str(success)
                }],
                ids=[f"error_{datetime.now().timestamp()}"]
            )
        except Exception as e:
            log.warning(f"保存错误到记忆失败: {e}")
    
    def get_recovery_strategy(self, error: Exception) -> Optional[Dict[str, Any]]:
        """
        获取推荐的恢复策略
        
        Args:
            error: 异常对象
            
        Returns:
            策略字典，包含 strategy_type, description, confidence
        """
        error_type = type(error).__name__
        
        # 1. 检查预设策略
        for strategy_name, strategy in self._recovery_strategies.items():
            if error_type in strategy.applicable_errors:
                return {
                    "strategy_type": strategy.strategy_type,
                    "description": strategy.description,
                    "confidence": strategy.success_rate,
                    "source": "predefined"
                }
        
        # 2. 检查历史模式
        if error_type in self._error_patterns:
            pattern = self._error_patterns[error_type]
            
            # 找出最成功的策略
            if pattern.recovery_strategies:
                best_strategy = max(
                    pattern.recovery_strategies.items(),
                    key=lambda x: x[1]
                )
                
                success_rate = best_strategy[1] / sum(pattern.recovery_strategies.values())
                
                return {
                    "strategy_type": best_strategy[0],
                    "description": f"基于历史（{best_strategy[1]}次成功）",
                    "confidence": success_rate,
                    "source": "historical"
                }
        
        # 3. 默认策略
        return {
            "strategy_type": "retry",
            "description": "未知错误，尝试重试",
            "confidence": 0.3,
            "source": "default"
        }
    
    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计"""
        stats = {
            "total_error_types": len(self._error_patterns),
            "total_errors": 0,
            "total_successful_recoveries": 0,
            "total_failed_recoveries": 0,
            "patterns": {},
            "most_common_errors": []
        }
        
        for error_type, pattern in self._error_patterns.items():
            stats["total_errors"] += pattern.count
            stats["total_successful_recoveries"] += pattern.successful_recoveries
            stats["total_failed_recoveries"] += pattern.failed_recoveries
            
            stats["patterns"][error_type] = {
                "count": pattern.count,
                "success_rate": (
                    pattern.successful_recoveries / pattern.count
                    if pattern.count > 0 else 0
                ),
                "avg_attempts": pattern.avg_retry_count,
                "best_strategy": (
                    max(pattern.recovery_strategies.items(), key=lambda x: x[1])[0]
                    if pattern.recovery_strategies else None
                )
            }
        
        # 计算整体恢复成功率
        total_recovery_attempts = stats["total_successful_recoveries"] + stats["total_failed_recoveries"]
        stats["recovery_rate"] = (
            stats["total_successful_recoveries"] / total_recovery_attempts
            if total_recovery_attempts > 0 else 0.0
        )
        
        # 找出最常见的错误
        sorted_patterns = sorted(
            self._error_patterns.items(),
            key=lambda x: x[1].count,
            reverse=True
        )
        
        stats["most_common_errors"] = [
            {"error_type": etype, "count": pattern.count}
            for etype, pattern in sorted_patterns[:5]
        ]
        
        return stats
    
    def get_recent_errors(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        获取最近的错误
        
        Args:
            hours: 查询最近几小时的错误
            
        Returns:
            错误列表
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            results = self.memory._collection.query(
                query_texts=["error"],
                n_results=50
            )
            
            if not results.get("metadatas"):
                return []
            
            recent_errors = []
            for i, metadata in enumerate(results["metadatas"][0]):
                if metadata.get("type") == "error_record":
                    error_time = datetime.fromisoformat(metadata.get("timestamp", ""))
                    
                    if error_time > cutoff_time:
                        recent_errors.append({
                            "error_type": metadata.get("error_type"),
                            "timestamp": metadata.get("timestamp"),
                            "recovery_strategy": metadata.get("recovery_strategy"),
                            "success": metadata.get("recovery_success") == "True"
                        })
            
            return recent_errors[:20]
            
        except Exception as e:
            log.warning(f"获取最近错误失败: {e}")
            return []
    
    def _load_patterns(self):
        """从记忆加载历史模式"""
        # 检查 ChromaDB collection 是否可用
        if not self.memory._collection:
            return
        
        try:
            results = self.memory._collection.get(include=["metadatas"])
            
            if not results.get("metadatas"):
                return
            
            for metadata in results["metadatas"]:
                if metadata.get("type") == "error_record":
                    error_type = metadata.get("error_type")
                    
                    if error_type not in self._error_patterns:
                        self._error_patterns[error_type] = ErrorPattern(error_type=error_type)
                    
                    pattern = self._error_patterns[error_type]
                    pattern.count += 1
                    pattern.last_seen = metadata.get("timestamp")
                    
                    if pattern.first_seen is None:
                        pattern.first_seen = metadata.get("timestamp")
                    
                    if metadata.get("recovery_success") == "True":
                        pattern.successful_recoveries += 1
                        strategy = metadata.get("recovery_strategy")
                        if strategy:
                            pattern.recovery_strategies[strategy] = (
                                pattern.recovery_strategies.get(strategy, 0) + 1
                            )
                    else:
                        pattern.failed_recoveries += 1
            
            log.info(f"从记忆加载了 {len(self._error_patterns)} 个错误模式")
            
        except Exception as e:
            log.warning(f"加载历史模式失败: {e}")
    
    def should_skip_error(self, error: Exception) -> bool:
        """
        判断是否应该跳过此错误（不重试）
        
        Args:
            error: 异常对象
            
        Returns:
            是否应该跳过
        """
        error_type = type(error).__name__
        strategy = self.get_recovery_strategy(error)
        
        if strategy.get("strategy_type") == "skip":
            return True
        
        # 如果连续失败超过 5 次，建议跳过
        if error_type in self._error_patterns:
            pattern = self._error_patterns[error_type]
            if pattern.count >= 5 and pattern.successful_recoveries == 0:
                log.warning(f"错误 {error_type} 已连续失败 {pattern.count} 次，建议跳过")
                return True
        
        return False
    
    def get_healing_suggestions(self) -> List[str]:
        """
        获取自我修复建议
        
        Returns:
            建议列表
        """
        suggestions = []
        
        for error_type, pattern in self._error_patterns.items():
            if pattern.count >= 3:
                # 错误发生频繁
                if pattern.successful_recoveries / pattern.count < 0.5:
                    # 恢复率低
                    suggestions.append(
                        f"错误 '{error_type}' 恢复率低 ({pattern.successful_recoveries}/{pattern.count}），"
                        f"建议检查相关配置或 API 密钥"
                    )
                
                # 找出最佳策略
                if pattern.recovery_strategies:
                    best_strategy = max(pattern.recovery_strategies.items(), key=lambda x: x[1])
                    suggestions.append(
                        f"对于 '{error_type}'，最佳策略是 '{best_strategy[0]}' "
                        f"（{best_strategy[1]} 次成功）"
                    )
        
        return suggestions[:10]
