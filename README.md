# JARVIS AI Assistant

一个类似钢铁侠 J.A.R.V.I.S. 的智能 AI 助手，基于 Python 实现。

## 核心特性 (v2.0)

### 🧠 Holo-Mem 仿生记忆
- **L3 语义图谱**: 基于 NetworkX 构建实体关系网络，解决跨上下文关联问题。
- **L2 记忆固化**: "Nightly Consolidation" 机制，每日自动生成 Markdown 摘要并提取知识三元组。
- **混合检索**: 结合向量相似度 (ChromaDB) 与图谱关联度 (Graph) 的双重检索。

### 🧬 自我进化引擎
- **经验学习**:自动记录成功/失败的操作路径，形成"经验向量"。
- **主动预测**: 在执行任务前参考过往类似经验，优化工具选择。
- **自我反思**: 任务失败时进行 Reflexion，自我修正错误。

### 💻 现代化交互
- **Web UI**: 基于 FastAPI + WebSocket 的现代化界面，支持 ECharts 图表渲染。
- **后台任务**: 支持长耗时任务的异步执行与状态推送。
- **多用户支持**: 基于 IP/Session 的用户上下文隔离。

### 🛠️ 增强技能库
- **金融分析**: 集成 **LongPort SDK**，支持实时行情、K线图绘制与市场分析。
- **智能调度**: 支持自然语言创建定时任务 ("每天早上8点叫我")，支持内存级函数调度。
- **原有能力**: 系统控制、文件管理、网页浏览、代码解释器等。

## 快速开始

### 1. 安装依赖

```bash
cd JARVIS

# 1. 确保安装了 Visual C++ Redistributable (onnxruntime 需要)
# 下载地址: https://aka.ms/vs/17/release/vc_redist.x64.exe

# 2. 安装 Python 依赖 (推荐 Python 3.11+)
pip install -r requirements.txt

# 3. 解决 onnxruntime 兼容性问题 (如果遇到 DLL load failed)
# 降级 NumPy 以兼容 onnxruntime 1.18.0
pip install "numpy<2"
```

### 2. 配置环境变量

```bash
# 复制示例配置
cp .env.example .env

# 编辑 .env 文件，填入你的 API Key
# 推荐使用 DeepSeek（性价比高）
DEEPSEEK_API_KEY=your_api_key_here
```

### 3. 运行

```bash
# 命令行交互模式
python main.py

# 语音交互模式
python main.py --voice

# Web UI 模式 (推荐)
python main.py --web

# 指定 LLM 提供商
python main.py --provider deepseek
```

## 使用示例

```
You: 帮我打开记事本
JARVIS: 好的，正在为您打开记事本...
        已打开应用: notepad

You: 列出桌面上的文件
JARVIS: 桌面文件列表：
        - 项目文档.docx
        - 截图.png
        - 新建文件夹/

You: 搜索今天的科技新闻
JARVIS: 为您搜索到以下结果：
        1. [标题1](URL)
        2. [标题2](URL)
        ...
```

## 命令

| 命令 | 说明 |
|------|------|
| `/help` | 显示帮助信息 |
| `/clear` | 清空对话记忆 |
| `/status` | 显示系统状态 |
| `/skills` | 显示可用技能 |
| `/tasks` | 显示后台任务列表 |
| `/cancel <id>` | 取消指定任务 |
| `/evolution` | 查看自我进化统计 |
| `/optimize` | 查看系统优化建议 |
| `/voice <name>` | 切换 TTS 语音 |
| `exit` | 退出程序 |

## 项目结构

```
JARVIS/
├── main.py                   # 主入口 (CLI/Voice/Web)
├── config.py                 # 全局配置
├── cognitive/                # 中枢层 (Brain)
│   ├── llm_brain.py          # LLM 统一接口
│   ├── memory.py             # Memory 2.0 (Vector+Graph)
│   ├── graph_storage.py      # L3 语义图谱存储 [NEW]
│   ├── planner.py            # ReAct 规划器 (带经验注入)
│   ├── self_evolution.py     # 进化引擎 (经验学习)
│   ├── continuous_evolution.py # 持续进化引擎 (后台学习)
│   └── heartbeat.py          # 心跳引擎 (Time-aware)
├── skills/                   # 技能层 (Skills)
│   ├── system_control.py     # 系统控制
│   ├── file_manager.py       # 文件管理
│   ├── web_browser.py        # 网页浏览
│   ├── scheduler.py          # 智能调度 (升级版)
│   ├── longport_skill.py     # 金融分析 (LongPort) [NEW]
│   ├── code_interpreter.py   # 代码解释器
│   └── image_generation.py   # 图像生成
├── static/                   # Web 资源
│   ├── js/                   # ECharts & App Logic
│   └── css/                  # Styles
└── security/                 # 安全层
    └── confirmation.py       # 危险操作拦截
```

## 安全说明

JARVIS 对危险操作有严格的安全限制：

- **只读操作**: 自动执行（如读取文件、搜索）
- **安全写入**: 自动执行但记录日志（如打开应用）
- **危险操作**: 必须用户确认（如删除文件、执行命令）

系统命令和文件路径都有黑名单限制，可在 `config.py` 中配置。

## 扩展开发

### 添加新技能

1. 在 `skills/` 目录创建新文件
2. 继承 `BaseSkill` 类
3. 实现 `execute()` 和 `get_schema()` 方法
4. 在 `main.py` 中注册技能

```python
from skills.base_skill import BaseSkill, SkillResult

class MySkill(BaseSkill):
    name = "my_skill"
    description = "我的自定义技能"
    
    async def execute(self, action: str, **params) -> SkillResult:
        # 实现逻辑
        return SkillResult(success=True, output="完成")
    
    def get_schema(self):
        # 返回 Function Calling 格式
        pass
```

## 故障排除

### 1. onnxruntime DLL load failed
错误信息：`ImportError: DLL load failed while importing onnxruntime_pybind11_state`
**解决**：安装 [Microsoft Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe)。

### 2. NumPy 兼容性错误
错误信息：`A module that was compiled using NumPy 1.x cannot be run in NumPy 2.x`
**解决**：降级 NumPy：
```bash
pip install "numpy<2"
```

### 3. ChromaDB 初始化失败
错误信息：`'type' object is not subscriptable`
**解决**：这是 Python 3.8 的兼容性问题，建议升级到 Python 3.9+ (推荐 3.11)。

## License

MIT
