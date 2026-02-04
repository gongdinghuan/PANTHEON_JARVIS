# JARVIS AI Assistant

一个类似钢铁侠 J.A.R.V.I.S. 的智能 AI 助手，基于 Python 实现。

## 功能特性

- 🧠 **智能对话**: 基于大语言模型的自然语言理解
- 🎯 **任务执行**: ReAct 工作流，自动规划和执行任务
- 🖥️ **系统控制**: 打开应用、调节音量、键鼠操作
- 📁 **文件管理**: 读写、移动、删除文件
- 🌐 **网页浏览**: 搜索信息、读取网页
- 🔊 **语音交互**: 语音识别和语音合成
- 🔒 **安全机制**: 权限分级和危险操作确认

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
| `exit` | 退出程序 |

## 项目结构

```
JARVIS/
├── main.py              # 主入口
├── config.py            # 配置管理
├── cognitive/           # 中枢层（大脑）
│   ├── llm_brain.py     # LLM 接口
│   ├── memory.py        # 记忆系统
│   ├── context_manager.py # 上下文管理
│   └── planner.py       # ReAct 规划器
├── senses/              # 感官层
│   ├── ears.py          # 语音识别
│   └── eyes.py          # 视觉/截图
├── skills/              # 技能层
│   ├── system_control.py # 系统控制
│   ├── file_manager.py  # 文件管理
│   ├── web_browser.py   # 网页浏览
│   ├── terminal.py      # 终端命令
│   └── iot_bridge.py    # IoT 控制
├── expression/          # 表达层
│   └── tts.py           # 语音合成
└── security/            # 安全层
    ├── permission.py    # 权限管理
    └── confirmation.py  # 确认机制
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
