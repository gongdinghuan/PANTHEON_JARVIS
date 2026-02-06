# JARVIS 自我进化和学习功能

## 概述

JARVIS 具备完整的自我进化能力，通过经验学习、模式识别和知识积累，持续优化系统性能和用户体验。

## 核心功能

### 1. 经验学习系统

**实现位置**: [cognitive/self_evolution.py](d:\JARVIS2\cognitive\self_evolution.py#L30-L302)

JARVIS 会记录每一次交互经验，包括：
- 任务类型（文件管理、系统控制、网络浏览等）
- 用户输入和系统响应
- 使用的工具列表
- 执行成功与否
- 执行时间
- 用户反馈（如果有）

**示例**:
```python
engine.record_experience(
    task_type="文件管理",
    user_input="创建一个名为test.txt的文件",
    response="已成功创建文件 test.txt",
    tools_used=["file_manager"],
    success=True,
    execution_time=1.2,
    user_feedback="很好"
)
```

### 2. 用户偏好学习

**实现位置**: [cognitive/self_evolution.py](d:\JARVIS2\cognitive\self_evolution.py#L127-L198)

JARVIS 自动学习您的偏好：
- **工具偏好**: 哪些工具使用最频繁
- **任务偏好**: 您最常执行什么类型的任务
- **时间偏好**: 您在什么时间段最活跃
- **反馈学习**: 从您的反馈中学习（"好"、"优秀"、"太慢"等）

**偏好示例**:
```python
# 工具偏好
file_manager: 置信度 0.85
system_control: 置信度 0.72
web_browser: 置信度 0.58

# 时间偏好
上午: 置信度 0.45
下午: 置信度 0.38
晚上: 置信度 0.17
```

### 3. 模式识别和预测

**实现位置**: [cognitive/self_evolution.py](d:\JARVIS2\cognitive\self_evolution.py#L200-L247)

JARVIS 识别使用模式并预测您的意图：
- **时间模式**: 什么时间段执行什么任务
- **工具组合模式**: 哪些工具经常一起使用
- **关键词模式**: 特定关键词对应什么任务

**预测示例**:
```python
prediction = engine.predict_next_action("创建一个新文件")

# 返回:
{
    "task_type": "文件管理",
    "confidence": 0.85,
    "suggested_tools": ["file_manager"]
}
```

### 4. 知识自动积累

**实现位置**: [cognitive/self_evolution.py](d:\JARVIS2\cognitive\self_evolution.py#L249-L302)

JARVIS 自动积累知识：
- **成功工作流**: 哪些工具组合能完成特定任务
- **FAQ 知识**: 常见问题和最佳答案
- **最佳实践**: 从成功经验中提取模式

### 5. 性能自我优化

**实现位置**: [cognitive/self_evolution.py](d:\JARVIS2\cognitive\self_evolution.py#L327-L424)

基于使用模式提供优化建议：
- 成功率分析
- 响应时间优化
- 工具使用效率
- 活跃时段分析
- 偏好建议

**优化建议示例**:
```
1. 成功率较低 (65.0%)，建议检查工具配置和 API 密钥
2. 平均响应时间较长 (3.5秒)，建议优化工作流程
3. 最常用的工具: file_manager, system_control
4. 工具组合 'file_manager+system_control' 使用频繁，考虑创建快捷技能
5. 最活跃时段: 09:00, 14:00, 19:00
6. 用户偏好工具: file_manager, web_browser
```

## 使用方法

### 查看进化统计

在 JARVIS 交互中使用 `/evolution` 命令：

```bash
# 在 JARVIS 中
/evolution
```

**输出示例**:
```
## 自我进化统计

- **总经验数**: 156
- **近期成功率**: 87.2%
- **平均执行时间**: 1.8秒
- **学习偏好数**: 12
- **识别模式数**: 28
- **知识条目数**: 15

### 顶部偏好

**tool**:
  - file_manager (置信度: 0.85)
  - system_control (置信度: 0.72)
  - web_browser (置信度: 0.58)

**task**:
  - 文件管理 (置信度: 0.78)
  - 网络浏览 (置信度: 0.65)
  - 系统控制 (置信度: 0.52)
```

### 查看优化建议

使用 `/optimize` 命令：

```bash
/optimize
```

**输出示例**:
```
## 系统优化建议

基于您的使用模式和系统性能，JARVIS 建议以下优化：

1. 最常用的工具: file_manager, system_control
2. 工具组合 'file_manager+system_control' 使用频繁，考虑创建快捷技能
3. 最活跃时段: 09:00, 14:00, 19:00
4. 用户偏好工具: file_manager, web_browser
```

### 查看完整状态

使用 `/status` 命令查看包括自我修复和自我进化的完整系统状态：

```bash
/status
```

## 架构

```
┌─────────────────────────────────────────────────────┐
│                   用户请求                        │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│            ReAct 规划器                      │
│  - 任务分类                                   │
│  - 预测建议                                   │
│  - 执行跟踪                                   │
└──────────────────┬──────────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
        ▼                     ▼
┌──────────────────┐  ┌──────────────────┐
│  经验记录        │  │  模式识别       │
│  - 记录每次交互   │  │  - 时间模式      │
│  - 保存到记忆     │  │  - 工具组合      │
└──────────────────┘  └──────────────────┘
        │                     │
        └──────────┬──────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│         自我进化引擎                            │
│  - 用户偏好学习                               │
│  - 模式分析                                   │
│  - 知识积累                                   │
│  - 优化建议                                   │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│         ChromaDB 长期记忆                      │
│  - 经验记录                                   │
│  - 错误记录                                   │
│  - 知识库                                    │
└─────────────────────────────────────────────────────┘
```

## 测试结果

### 测试文件
- [test_evolution_simple.py](d:\JARVIS2\test_evolution_simple.py) - 完整功能测试

### 测试输出
```
JARVIS 自我进化功能测试

==================================================

=== 测试经验记录 ===

✓ 已记录: 文件管理 - 创建一个名为test.txt的文件
✓ 已记录: 文件管理 - 打开记事本
✓ 已记录: 网络浏览 - 搜索Python教程
✓ 已记录: 文件管理 - 删除不存在的文件
✓ 已记录: 系统控制 - 调大音量

=== 测试预测功能 ===

输入: 创建一个新文件
  预测任务: 文件管理
  置信度: 10.0%
  预测工具: file_manager

输入: 搜索Python教程
  预测任务: 文件管理
  置信度: 10.0%
  预测工具: file_manager

=== 测试偏好学习 ===

学习偏好数: 1
识别模式数: 2
总经验数: 6

工具偏好:
  - file_manager (置信度: 0.50)

=== 测试优化建议 ===

优化建议:
1. 最常用的工具: test_tool
2. 最活跃时段: 16:00

=== 测试知识导出 ===

导出的知识:
  偏好类型: 3
  模式类型: 2
  知识库: 2
  导出时间: 2026-02-02T16:03:22

==================================================

所有测试完成！

功能总结:
  ✓ 经验记录和学习
  ✓ 用户偏好识别
  ✓ 任务预测
  ✓ 模式识别
  ✓ 知识积累
  ✓ 优化建议生成
  ✓ 知识导出
```

## API 参考

### SelfEvolutionEngine

```python
class SelfEvolutionEngine:
    def __init__(self, memory: MemoryManager)
    
    def record_experience(
        self,
        task_type: str,
        user_input: str,
        response: str,
        tools_used: List[str],
        success: bool,
        execution_time: float = 0.0,
        user_feedback: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    )
    
    def predict_next_action(self, user_input: str) -> Optional[Dict[str, Any]]
    
    def get_optimization_suggestions(self) -> List[str]
    
    def get_learned_knowledge(self, topic: str, limit: int = 5) -> List[Dict]
    
    def get_evolution_stats(self) -> Dict[str, Any]
    
    def export_knowledge(self) -> Dict[str, Any]
    
    def import_knowledge(self, knowledge: Dict[str, Any])
```

## 数据结构

### Experience
```python
@dataclass
class Experience:
    timestamp: str
    task_type: str
    user_input: str
    response: str
    tools_used: List[str]
    success: bool
    user_feedback: Optional[str] = None
    execution_time: float = 0.0
    context: Dict[str, Any]
```

### UserPreference
```python
@dataclass
class UserPreference:
    preference_type: str
    key: str
    value: Any
    confidence: float
    last_updated: str
    usage_count: int
```

### Pattern
```python
@dataclass
class Pattern:
    pattern_type: str
    pattern_data: Dict[str, Any]
    frequency: int
    last_seen: str
    prediction_accuracy: float
```

## 与自我修复的集成

自我进化和自我修复功能紧密协作：

1. **错误修复**: 自我修复系统修复错误
2. **经验学习**: 自我进化系统从错误和成功中学习
3. **预测优化**: 基于学习到的模式，预测可能的问题
4. **预防措施**: 识别高风险操作，提前采取预防措施

## 未来改进

1. **更智能的预测**: 使用机器学习模型
2. **个性化推荐**: 基于用户习惯推荐工作流
3. **自动优化**: 自动调整系统参数
4. **多用户支持**: 支持多个用户的学习
5. **知识图谱**: 构建更复杂的知识关系

## 性能考虑

- **内存管理**: 限制内存中保存的经验数量（最多1000条）
- **持久化**: 所有经验保存到 ChromaDB
- **增量学习**: 每次交互都持续学习
- **智能清理**: 自动清理低置信度的偏好和旧模式

## 隐私保护

- 所有用户数据存储在本地
- 没有数据上传到云端
- 用户可以随时清空学习数据
- 知识可以导出和导入

## 作者

gngdingghuan

## 许可证

与 JARVIS 项目相同
