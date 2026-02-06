# JARVIS 自我修复功能

## 概述

JARVIS 现在具备完整的自我修复能力，能够自动检测、学习和从错误中恢复，提高系统的可靠性和用户体验。

## 功能特性

### 1. 自动重试机制

**实现位置**: [utils/error_handler.py](d:\JARVIS2\utils\error_handler.py#L36-L107)

- **指数退避**: 每次重试间隔按指数增长，避免雪崩
- **智能延迟**: 基础延迟 + 指数倍数 + 随机抖动
- **可配置参数**: 最大尝试次数、延迟范围、重试条件

**使用示例**:
```python
handler = ErrorHandler()
result = await handler.retry_with_backoff(
    func,
    config=RetryConfig(
        max_attempts=3,
        base_delay=1.0,
        max_delay=30.0,
        exponential_base=2.0,
    )
)
```

### 2. 熔断器模式

**实现位置**: [utils/error_handler.py](d:\JARVIS2\utils\error_handler.py#L183-L257)

- **防止级联故障**: 连续失败达到阈值后自动开启熔断
- **自动恢复**: 超时后自动进入半开状态尝试恢复
- **状态管理**: Closed → Open → Half-Open → Closed

**使用示例**:
```python
circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60.0
)
result = await circuit_breaker.call(func)
```

### 3. LLM 自动重试

**实现位置**: [cognitive/llm_brain.py](d:\JARVIS2\cognitive\llm_brain.py#L28-L42)

- **API 请求失败时自动重试**（最多3次）
- **熔断器保护**: 连续失败5次后暂停请求
- **提供商自动切换**: 主提供商失败时尝试备用提供商

### 4. 提供商自动切换

**实现位置**: [cognitive/llm_brain.py](d:\JARVIS2\cognitive\llm_brain.py#L147-L186)

支持多个 LLM 提供商自动切换：
- DeepSeek (默认)
- OpenAI
- Ollama (本地)

当主提供商不可用时，自动尝试备用提供商。

### 5. 技能级错误处理

**实现位置**: [cognitive/planner.py](d:\JARVIS2\cognitive\planner.py#L209-L347)

- **每个技能独立的熔断器**: 防止单个技能失败影响其他技能
- **智能重试**: 基于历史数据决定重试策略
- **错误记录**: 所有技能执行错误都被记录和分析

### 6. 错误学习引擎

**实现位置**: [cognitive/self_healing.py](d:\JARVIS2\cognitive\self_healing.py#L30-L302)

**核心功能**:
- **错误模式识别**: 自动识别错误类型和发生频率
- **恢复策略学习**: 记录哪些策略对哪些错误有效
- **长期记忆存储**: 将错误模式存储到 ChromaDB
- **智能建议**: 基于历史数据提供修复建议

**预设恢复策略**:
| 策略 | 适用错误 | 成功率 |
|------|---------|--------|
| retry (重试) | TimeoutError, ConnectTimeout | 70% |
| fallback (切换) | RateLimitError, 429Error | 60% |
| manual (手动) | AuthenticationError, PermissionError | 80-90% |
| skip (跳过) | FileNotFoundError, KeyError | 100% |

### 7. 系统状态监控

**实现位置**: [main.py](d:\JARVIS2\main.py#L292-L317)

使用 `/status` 命令查看：
- LLM 提供商状态
- 记忆系统统计
- 自我修复统计
- 常见错误列表
- 恢复成功率

## 测试结果

### 测试文件
- [test_simple_healing.py](d:\JARVIS2\test_simple_healing.py) - 基础功能测试

### 测试输出
```
JARVIS 自我修复功能 - 简单测试

========================================

=== 测试自动重试 ===

尝试 1... 失败
操作失败（尝试 1/5）: 模拟失败，0.20秒后重试...
尝试 2... 失败
操作失败（尝试 2/5）: 模拟失败，0.60秒后重试...
尝试 3... 成功！
成功恢复: Exception - retry_with_backoff（3次重试）

结果: 第 3 次成功
总耗时: 0.85秒
错误统计: {'total_errors': 1, 'successful_recoveries': 1, 'recovery_rate': 1.0}

=== 测试失败恢复 ===

操作失败（尝试 1/3）: 总是失败，0.10秒后重试...
操作失败（尝试 2/3）: 总是失败，0.30秒后重试...
错误已记录: Exception - 总是失败
最终失败: 总是失败
统计: {'total_errors': 1, 'successful_recoveries': 0, 'recovery_rate': 0.0}

========================================

测试完成！
```

## 架构概览

```
┌─────────────────────────────────────────────────────┐
│                   用户请求                        │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│            ReAct 规划器                         │
│  - 技能级熔断器                               │
│  - 智能重试                                   │
│  - 错误记录                                    │
└──────────────────┬──────────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
        ▼                     ▼
┌──────────────────┐  ┌──────────────────┐
│  LLM 大脑        │  │  技能执行       │
│  - API 重试      │  │  - 技能熔断器   │
│  - 提供商切换    │  │  - 错误处理     │
│  - 熔断器        │  │  - 自动重试     │
└──────────────────┘  └──────────────────┘
        │                     │
        └──────────┬──────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│         自我修复引擎                            │
│  - 错误模式学习                               │
│  - 恢复策略推荐                               │
│  - 长期记忆存储                               │
│  - 智能建议                                   │
└─────────────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│         ChromaDB 长期记忆                      │
└─────────────────────────────────────────────────────┘
```

## 使用方法

### 查看错误统计
```bash
# 在 JARVIS 交互中
/status
```

输出示例：
```
## 系统状态

- **LLM 提供商**: deepseek
- **短期记忆**: 5 条
- **长期记忆**: 123 条
- **CPU 使用率**: 25.3%
- **内存使用率**: 45.7%

## 自我修复统计

- **错误类型**: 3
- **总错误数**: 15
- **恢复成功率**: 86.7%

### 常见错误

- TimeoutError: 8 次
- FileNotFoundError: 5 次
- ValueError: 2 次
```

### 获取修复建议

错误学习引擎会自动分析错误模式并提供修复建议：

```
- 错误 'TimeoutError' 恢复率低 (3/8），建议检查网络连接
- 对于 'FileNotFoundError'，最佳策略是 'skip'（5 次成功）
```

## 配置

### 重试配置
在 `utils/error_handler.py` 中修改默认配置：

```python
RetryConfig(
    max_attempts=3,        # 最大尝试次数
    base_delay=1.0,       # 基础延迟（秒）
    max_delay=30.0,       # 最大延迟（秒）
    exponential_base=2.0,   # 指数基数
    backoff_multiplier=1.5, # 退避倍数
)
```

### 熔断器配置
在 `cognitive/llm_brain.py` 和 `cognitive/planner.py` 中：

```python
# LLM 熔断器
CircuitBreaker(
    failure_threshold=5,   # 失败阈值
    recovery_timeout=60.0   # 恢复超时（秒）
)

# 技能熔断器
CircuitBreaker(
    failure_threshold=3,
    recovery_timeout=30.0
)
```

## 未来改进

1. **更智能的错误预测**: 基于机器学习预测错误发生
2. **自动配置调优**: 根据错误统计自动调整重试参数
3. **分布式支持**: 多实例间的错误经验共享
4. **可视化面板**: 实时错误监控和修复统计

## 技术细节

### 错误处理流程
```
1. 检测错误
   ↓
2. 查询恢复策略（预设/历史）
   ↓
3. 执行恢复策略
   ├─ retry: 指数退避重试
   ├─ fallback: 切换提供商
   ├─ skip: 跳过并继续
   └─ manual: 请求用户确认
   ↓
4. 记录结果
   ↓
5. 更新错误模式
   ↓
6. 存储到长期记忆
```

### 数据结构
```python
@dataclass
class ErrorRecord:
    error_type: str
    error_message: str
    timestamp: str
    context: Dict[str, Any]
    retry_count: int
    recovery_strategy: Optional[str]
    success: bool
```

## 依赖

- asyncio - 异步支持
- chromadb - 长期记忆存储
- openai - LLM API

## 作者

gngdingghuan

## 许可证

与 JARVIS 项目相同
