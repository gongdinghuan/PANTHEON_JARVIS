"""
JARVIS 错误处理和重试工具
提供自动重试、指数退避、智能降级等功能

Author: gngdingghuan
"""

import asyncio
import time
from typing import Type, Tuple, Callable, Optional, Any, Dict, List
from functools import wraps
from dataclasses import dataclass, field
from datetime import datetime

from utils.logger import log


@dataclass
class RetryConfig:
    """重试配置"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    backoff_multiplier: float = 1.5
    
    # 可重试的异常类型
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
    
    # 重试条件函数
    should_retry: Optional[Callable[[Exception], bool]] = None


@dataclass
class ErrorRecord:
    """错误记录"""
    error_type: str
    error_message: str
    timestamp: str
    context: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    recovery_strategy: Optional[str] = None
    success: bool = False


class ErrorHandler:
    """
    错误处理器
    - 自动重试
    - 指数退避
    - 错误记录
    - 恢复策略
    """
    
    def __init__(self):
        self._error_history: List[ErrorRecord] = []
        self._error_patterns: Dict[str, Dict[str, Any]] = {}
    
    async def retry_with_backoff(
        self,
        func: Callable,
        config: Optional[RetryConfig] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        带指数退避的自动重试
        
        Args:
            func: 要执行的异步函数
            config: 重试配置
            context: 错误上下文信息
            
        Returns:
            函数执行结果
            
        Raises:
            最后一次异常（如果所有重试都失败）
        """
        config = config or RetryConfig()
        context = context or {}
        
        last_exception = None
        
        for attempt in range(1, config.max_attempts + 1):
            try:
                result = await func()
                
                # 成功：记录错误修复
                if attempt > 1 and last_exception:
                    self._record_recovery(
                        last_exception,
                        attempt,
                        "retry_with_backoff",
                        context
                    )
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # 检查是否应该重试
                should_retry = self._should_retry(e, config)
                
                if not should_retry or attempt >= config.max_attempts:
                    # 记录最终错误
                    self._record_error(e, attempt, context)
                    raise
                
                # 计算退避延迟
                delay = self._calculate_delay(attempt, config)
                
                log.warning(
                    f"操作失败（尝试 {attempt}/{config.max_attempts}）: {str(e)}，"
                    f"{delay:.2f}秒后重试..."
                )
                
                await asyncio.sleep(delay)
    
    def _should_retry(self, exception: Exception, config: RetryConfig) -> bool:
        """判断是否应该重试"""
        # 检查异常类型
        if not isinstance(exception, config.retryable_exceptions):
            return False
        
        # 使用自定义重试条件
        if config.should_retry:
            return config.should_retry(exception)
        
        # 默认：所有异常都可重试
        return True
    
    def _calculate_delay(self, attempt: int, config: RetryConfig) -> float:
        """计算退避延迟"""
        if attempt == 1:
            return config.base_delay
        
        # 指数退避
        delay = config.base_delay * (
            config.exponential_base ** (attempt - 1)
        ) * config.backoff_multiplier
        
        # 限制最大延迟
        return min(delay, config.max_delay)
    
    def _record_error(self, exception: Exception, attempt: int, context: Dict[str, Any]):
        """记录错误"""
        record = ErrorRecord(
            error_type=type(exception).__name__,
            error_message=str(exception),
            timestamp=datetime.now().isoformat(),
            context=context,
            retry_count=attempt,
            success=False
        )
        
        self._error_history.append(record)
        log.error(f"错误已记录: {record.error_type} - {record.error_message}")
        
        # 更新错误模式
        self._update_error_pattern(record)
    
    def _record_recovery(
        self,
        exception: Exception,
        attempt: int,
        strategy: str,
        context: Dict[str, Any]
    ):
        """记录恢复"""
        record = ErrorRecord(
            error_type=type(exception).__name__,
            error_message=str(exception),
            timestamp=datetime.now().isoformat(),
            context=context,
            retry_count=attempt,
            recovery_strategy=strategy,
            success=True
        )
        
        self._error_history.append(record)
        log.info(f"成功恢复: {record.error_type} - {strategy}（{attempt}次重试）")
    
    def _update_error_pattern(self, record: ErrorRecord):
        """更新错误模式统计"""
        key = record.error_type
        
        if key not in self._error_patterns:
            self._error_patterns[key] = {
                "count": 0,
                "success_count": 0,
                "avg_attempts": 0.0,
                "last_seen": None
            }
        
        pattern = self._error_patterns[key]
        pattern["count"] += 1
        pattern["last_seen"] = record.timestamp
        
        if record.success:
            pattern["success_count"] += 1
            pattern["avg_attempts"] = (
                (pattern["avg_attempts"] * (pattern["success_count"] - 1) + record.retry_count)
                / pattern["success_count"]
            )
    
    def get_error_pattern(self, error_type: str) -> Optional[Dict[str, Any]]:
        """获取特定错误类型的模式"""
        return self._error_patterns.get(error_type)
    
    def get_recovery_strategy(self, exception: Exception) -> Optional[str]:
        """根据历史数据建议恢复策略"""
        error_type = type(exception).__name__
        pattern = self.get_error_pattern(error_type)
        
        if not pattern:
            return None
        
        # 如果成功恢复过，建议相同的策略
        if pattern["success_count"] > 0:
            avg_attempts = pattern["avg_attempts"]
            if avg_attempts <= 2:
                return "retry_with_backoff"
            elif avg_attempts <= 4:
                return "switch_provider"
            else:
                return "fallback_action"
        
        return None
    
    def get_recent_errors(self, limit: int = 10) -> List[ErrorRecord]:
        """获取最近的错误记录"""
        return self._error_history[-limit:]
    
    def get_error_stats(self) -> Dict[str, Any]:
        """获取错误统计"""
        if not self._error_history:
            return {
                "total_errors": 0,
                "successful_recoveries": 0,
                "by_type": {}
            }
        
        total = len(self._error_history)
        successful = sum(1 for r in self._error_history if r.success)
        
        by_type = {}
        for record in self._error_history:
            etype = record.error_type
            if etype not in by_type:
                by_type[etype] = {"total": 0, "recovered": 0}
            by_type[etype]["total"] += 1
            if record.success:
                by_type[etype]["recovered"] += 1
        
        return {
            "total_errors": total,
            "successful_recoveries": successful,
            "recovery_rate": successful / total if total > 0 else 0,
            "by_type": by_type
        }


def retry_on_failure(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
):
    """
    重试装饰器
        
    Args:
        max_attempts: 最大尝试次数
        base_delay: 基础延迟（秒）
        max_delay: 最大延迟（秒）
        retryable_exceptions: 可重试的异常类型
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            handler = ErrorHandler()
            config = RetryConfig(
                max_attempts=max_attempts,
                base_delay=base_delay,
                max_delay=max_delay,
                retryable_exceptions=retryable_exceptions
            )
            
            async def _func():
                return await func(*args, **kwargs)
            
            return await handler.retry_with_backoff(_func, config)
        
        return wrapper
    return decorator


class CircuitBreaker:
    """
    熔断器模式
    防止连续失败时继续调用失败的依赖
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
    ):
        """
        Args:
            failure_threshold: 失败阈值
            recovery_timeout: 恢复超时（秒）
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        
        self._failure_count = 0
        self._last_failure_time = None
        self._state = "closed"  # closed, open, half-open
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        通过熔断器调用函数
        
        Args:
            func: 要调用的函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            函数执行结果
            
        Raises:
            CircuitBreakerOpenError: 熔断器开启时
        """
        if self._state == "open":
            if self._should_attempt_reset():
                self._state = "half-open"
                log.info("熔断器进入半开状态，尝试恢复...")
            else:
                raise CircuitBreakerOpenError(
                    f"熔断器开启，{self.recovery_timeout - self._time_since_failure():.1f}秒后重试"
                )
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """是否应该尝试重置"""
        if self._last_failure_time is None:
            return True
        return self._time_since_failure() >= self.recovery_timeout
    
    def _time_since_failure(self) -> float:
        """距离上次失败的秒数"""
        if self._last_failure_time is None:
            return 0
        return time.time() - self._last_failure_time
    
    def _on_success(self):
        """成功时更新状态"""
        self._failure_count = 0
        
        if self._state == "half-open":
            self._state = "closed"
            log.info("熔断器已恢复，状态: closed")
    
    def _on_failure(self):
        """失败时更新状态"""
        self._failure_count += 1
        self._last_failure_time = time.time()
        
        if self._failure_count >= self.failure_threshold:
            self._state = "open"
            log.warning(
                f"熔断器已开启（连续失败 {self._failure_count} 次）"
            )
    
    def get_state(self) -> str:
        """获取当前状态"""
        return self._state
    
    def reset(self):
        """手动重置熔断器"""
        self._failure_count = 0
        self._state = "closed"
        log.info("熔断器已手动重置")


class CircuitBreakerOpenError(Exception):
    """熔断器开启异常"""
    pass
