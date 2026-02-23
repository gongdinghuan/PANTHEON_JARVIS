"""
JARVIS 配置管理模块
支持环境变量和配置文件

Author: gngdingghuan
"""

import os
import logging
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# 创建日志器（避免循环导入）
_logger = logging.getLogger("jarvis.config")
if not _logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s - %(message)s')
    handler.setFormatter(formatter)
    _logger.addHandler(handler)
    _logger.setLevel(logging.INFO)


class LLMProvider(Enum):
    """LLM 提供商枚举"""
    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    OLLAMA = "ollama"

    NVIDIA = "nvidia"
    ZHIPU = "zhipu"
    GEMINI = "gemini"


class SearchProvider(Enum):
    """搜索引擎提供商枚举"""
    BAIDU = "baidu"
    DUCKDUCKGO = "duckduckgo"
    GOOGLE = "google"
    TAVILY = "tavily"
    BRAVE = "brave"


class PermissionLevel(Enum):
    """权限级别枚举"""
    READ_ONLY = 1      # 只读操作，自动执行
    SAFE_WRITE = 2     # 安全写入，自动执行但记录日志
    CRITICAL = 3       # 危险操作，必须人工确认





@dataclass
class LLMConfig:
    """LLM 配置"""
    provider: LLMProvider = LLMProvider.DEEPSEEK
    
    # OpenAI 配置
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    openai_base_url: str = field(default_factory=lambda: os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"))
    openai_model: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o"))
    
    # DeepSeek 配置
    deepseek_api_key: str = field(default_factory=lambda: os.getenv("DEEPSEEK_API_KEY", ""))
    deepseek_base_url: str = field(default_factory=lambda: os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
    deepseek_model: str = field(default_factory=lambda: os.getenv("DEEPSEEK_MODEL", "deepseek-chat"))
    
    # Ollama 配置
    ollama_base_url: str = field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    ollama_model: str = field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "llama3"))
    
    # NVIDIA AI 配置
    nvidia_api_key: str = field(default_factory=lambda: os.getenv("NVIDIA_API_KEY", ""))
    nvidia_base_url: str = field(default_factory=lambda: os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"))
    nvidia_model: str = field(default_factory=lambda: os.getenv("NVIDIA_MODEL", "minimaxai/minimax-m2.1"))
    
    # Zhipu AI (BigModel) 配置
    zhipu_api_key: str = field(default_factory=lambda: os.getenv("ZHIPU_API_KEY", ""))
    zhipu_base_url: str = field(default_factory=lambda: os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"))
    zhipu_model: str = field(default_factory=lambda: os.getenv("ZHIPU_MODEL", "glm-4"))
    
    # Local Gemini 配置
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", "sk-9114341895db4f9780ede6d01d21f71a"))
    gemini_base_url: str = field(default_factory=lambda: os.getenv("GEMINI_BASE_URL", "http://localhost:8045/v1"))
    gemini_model: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-3-pro-high"))
    
    # 通用配置
    temperature: float = 0.7
    max_tokens: int = 8096
    stream: bool = True
    request_timeout: float = 120.0  # 增加超时时间，复杂请求需要更长时间


@dataclass
class VisionConfig:
    """视觉理解专用模型配置
    
    独立于主 LLM，用于图片分析。分析结果会注入到主模型的 Prompt 中。
    如果未配置，则回退到主 LLM 的 chat_with_vision() 模式。
    """
    # 是否启用独立视觉模型 (False = 回退到主 LLM)
    enabled: bool = field(default_factory=lambda: os.getenv("VISION_ENABLED", "true").lower() == "true")
    
    # 视觉模型提供商 (可与主 LLM 不同)
    provider: str = field(default_factory=lambda: os.getenv("VISION_PROVIDER", "openai"))
    
    # 视觉模型 API
    api_key: str = field(default_factory=lambda: os.getenv("VISION_API_KEY", ""))
    base_url: str = field(default_factory=lambda: os.getenv("VISION_BASE_URL", ""))
    model: str = field(default_factory=lambda: os.getenv("VISION_MODEL", "gpt-4o"))
    
    # 图片分析参数
    detail: str = field(default_factory=lambda: os.getenv("VISION_DETAIL", "high"))  # low / high / auto
    max_tokens: int = field(default_factory=lambda: int(os.getenv("VISION_MAX_TOKENS", "1024")))
    temperature: float = 0.3  # 低温度，提高描述精确度


@dataclass
class VoiceConfig:
    """语音配置"""
    # Whisper 配置
    whisper_model: str = "base"  # tiny, base, small, medium, large
    
    # TTS 配置
    tts_voice: str = "zh-CN-YunxiNeural"  # Edge-TTS 语音
    tts_rate: str = "+0%"  # 语速
    tts_volume: str = "+0%"  # 音量
    
    # VAD 配置
    vad_threshold: float = 0.5
    silence_duration: float = 0.8  # 静音多久后停止录音（秒）


@dataclass
class SecurityConfig:
    """安全配置"""
    # 允许操作的目录白名单
    allowed_directories: List[str] = field(default_factory=lambda: [
        str(Path.home() / "Desktop"),
        str(Path.home() / "Documents"),
        str(Path.home() / "Downloads"),
    ])
    
    # 禁止访问的目录黑名单
    forbidden_directories: List[str] = field(default_factory=lambda: [
        "C:\\Windows",
        "C:\\Program Files",
        "C:\\Program Files (x86)",
        "/System",
        "/usr",
        "/bin",
    ])
    
    # 允许的安全命令（只读类）
    safe_commands: List[str] = field(default_factory=lambda: [
        "dir", "ls", "cat", "type", "echo", "pwd", "cd",
        "whoami", "date", "time", "hostname",
        "python --version", "pip list", "node --version",
    ])
    
    # 用户学习的安全命令文件路径
    user_commands_file: str = field(default_factory=lambda: str(Path.home() / ".jarvis" / "safe_commands.json"))
    
    # 禁止的危险命令关键词
    forbidden_commands: List[str] = field(default_factory=lambda: [
        "rm -rf", "del /f", "format", "mkfs",
        "shutdown", "reboot", "halt",
        "DROP", "DELETE FROM", "TRUNCATE",
    ])
    
    # 是否需要确认危险操作
    require_confirmation: bool = True
    
    # 确认超时时间（秒）
    confirmation_timeout: int = 30
    
    def __post_init__(self):
        """初始化后加载用户学习的安全命令"""
        self._load_user_commands()
    
    def _load_user_commands(self):
        """从文件加载用户学习的安全命令"""
        try:
            import json
            file_path = Path(self.user_commands_file)
            
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    user_commands = json.load(f)
                    
                # 合并到安全命令列表
                for cmd in user_commands:
                    if cmd not in self.safe_commands:
                        self.safe_commands.append(cmd)
                
                _logger.info(f"已加载 {len(user_commands)} 个用户学习的安全命令")
        except Exception as e:
            _logger.warning(f"加载用户安全命令失败: {e}")
    
    def _save_user_commands(self, commands: List[str]):
        """保存用户学习的安全命令到文件"""
        try:
            import json
            file_path = Path(self.user_commands_file)
            
            # 确保目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 读取现有命令
            existing_commands = []
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    existing_commands = json.load(f)
            
            # 合并新命令
            for cmd in commands:
                if cmd not in existing_commands:
                    existing_commands.append(cmd)
            
            # 保存
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(existing_commands, f, ensure_ascii=False, indent=2)
            
            _logger.info(f"已保存 {len(commands)} 个用户学习的安全命令")
            return True
        except Exception as e:
            _logger.error(f"保存用户安全命令失败: {e}")
            return False
    
    def learn_safe_command(self, command: str) -> bool:
        """
        学习新的安全命令
        
        Args:
            command: 要学习的命令
            
        Returns:
            是否成功学习
        """
        command = command.strip()
        
        # 检查是否包含危险关键词
        command_lower = command.lower()
        for forbidden in self.forbidden_commands:
            if forbidden.lower() in command_lower:
                _logger.warning(f"拒绝学习危险命令: {command}")
                return False
        
        # 检查是否已经存在
        if command in self.safe_commands:
            _logger.info(f"命令已存在于安全列表: {command}")
            return True
        
        # 添加到安全命令列表
        self.safe_commands.append(command)
        
        # 保存到文件
        return self._save_user_commands([command])
    
    def get_learned_commands(self) -> List[str]:
        """获取用户学习的安全命令列表"""
        try:
            import json
            file_path = Path(self.user_commands_file)
            
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            log.warning(f"读取用户学习命令失败: {e}")
        
        return []


@dataclass
class MemoryConfig:
    """记忆系统配置"""
    # ChromaDB 存储路径
    chroma_persist_dir: str = field(default_factory=lambda: str(Path("data/memory_v2").absolute()))
    
    # Holo-Mem L3: 知识图谱路径
    graph_storage_path: str = field(default_factory=lambda: str(Path("data/memory_v2/kg_graph.graphml").absolute()))
    
    # Holo-Mem L2: 时间线摘要存储目录
    timeline_storage_dir: str = field(default_factory=lambda: str(Path("data/memory_v2/timeline").absolute()))

    # 短期记忆保留的对话轮数
    short_term_turns: int = 20
    
    # 长期记忆检索数量
    # 长期记忆检索数量
    retrieval_k: int = 1000
    
    # 嵌入模型
    embedding_model: str = field(default_factory=lambda: os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"))


@dataclass
class ServerConfig:
    """服务器配置"""
    host: str = field(default_factory=lambda: os.getenv("SERVER_HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("SERVER_PORT", "8765")))
    # 公网 IP 用于前端链接生成
    public_host: str = field(default_factory=lambda: os.getenv("PUBLIC_HOST", "43.135.129.25"))
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    enabled: bool = False  # 是否在 Web 模式下运行


@dataclass
class IoTConfig:
    """IoT 配置"""
    # Home Assistant 配置
    ha_url: Optional[str] = field(default_factory=lambda: os.getenv("HA_URL"))
    ha_token: Optional[str] = field(default_factory=lambda: os.getenv("HA_TOKEN"))
    enabled: bool = False


@dataclass
class WebConfig:
    """Web 配置"""
    # 搜索引擎提供商
    search_provider: SearchProvider = field(default_factory=lambda: SearchProvider.BAIDU)
    
    # 百度搜索配置
    baidu_max_results: int = 10
    
    # DuckDuckGo 搜索配置
    ddgs_max_results: int = 10
    
    # 搜索超时时间（秒）
    search_timeout: int = 30

    # 新增搜索 API Key
    tavily_api_key: str = field(default_factory=lambda: os.getenv("TAVILY_API_KEY", ""))
    brave_api_key: str = field(default_factory=lambda: os.getenv("BRAVE_API_KEY", ""))


@dataclass
class HeartbeatConfig:
    """心跳配置"""
    # 是否启用心跳
    enabled: bool = True
    
    # 心跳间隔（秒）
    interval: int = 1
    
    # 是否记录心跳日志
    log_heartbeat: bool = False
    
    # 时区
    timezone: str = "Asia/Shanghai"
    
    # 是否启用智能问候
    enable_greeting: bool = True



@dataclass
class BrowserConfig:
    """浏览器自动化配置"""
    headless: bool = True
    timeout: int = 30000  # ms
    viewport_width: int = 1280
    viewport_height: int = 720
    screenshot_dir: str = "generated_images"
    auto_close_minutes: int = 10


@dataclass
class LongPortConfig:
    """LongPort 配置"""
    app_key: str = field(default_factory=lambda: os.getenv("LONGPORT_APP_KEY", ""))
    app_secret: str = field(default_factory=lambda: os.getenv("LONGPORT_APP_SECRET", ""))
    access_token: str = field(default_factory=lambda: os.getenv("LONGPORT_ACCESS_TOKEN", ""))
    enabled: bool = field(default_factory=lambda: bool(os.getenv("LONGPORT_APP_KEY")))


@dataclass
class IMConfig:
    """即时通讯适配器配置"""
    # QQ (OneBot 11)
    qq_enabled: bool = field(default_factory=lambda: os.getenv("QQ_ENABLED", "false").lower() == "true")
    qq_onebot_ws_host: str = field(default_factory=lambda: os.getenv("QQ_ONEBOT_WS_HOST", "127.0.0.1"))
    qq_onebot_ws_port: int = field(default_factory=lambda: int(os.getenv("QQ_ONEBOT_WS_PORT", "8011")))
    qq_allowed_groups: str = field(default_factory=lambda: os.getenv("QQ_ALLOWED_GROUPS", ""))  # 逗号分隔
    qq_admin_qq: str = field(default_factory=lambda: os.getenv("QQ_ADMIN_QQ", ""))  # 逗号分隔
    
    # Telegram
    telegram_enabled: bool = field(default_factory=lambda: os.getenv("TELEGRAM_ENABLED", "false").lower() == "true")
    telegram_bot_token: str = field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", ""))
    
    # WeChat
    wechat_enabled: bool = field(default_factory=lambda: os.getenv("WECHAT_ENABLED", "false").lower() == "true")
    wechat_puppet_token: str = field(default_factory=lambda: os.getenv("WECHAT_PUPPET_TOKEN", ""))
    
    def get_qq_allowed_groups(self) -> list:
        """解析允许的群号列表"""
        if not self.qq_allowed_groups:
            return []
        return [int(g.strip()) for g in self.qq_allowed_groups.split(",") if g.strip()]
    
    def get_qq_admin_list(self) -> list:
        """解析管理员 QQ 列表"""
        if not self.qq_admin_qq:
            return []
        return [int(q.strip()) for q in self.qq_admin_qq.split(",") if q.strip()]


@dataclass
class JarvisConfig:
    """JARVIS 总配置"""
    llm: LLMConfig = field(default_factory=LLMConfig)
    vision: VisionConfig = field(default_factory=VisionConfig)
    voice: VoiceConfig = field(default_factory=VoiceConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    iot: IoTConfig = field(default_factory=IoTConfig)
    web: WebConfig = field(default_factory=WebConfig)
    heartbeat: HeartbeatConfig = field(default_factory=HeartbeatConfig)
    longport: LongPortConfig = field(default_factory=LongPortConfig)
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    im: 'IMConfig' = field(default_factory=lambda: IMConfig())
    
    # 日志配置
    log_level: str = "INFO"
    log_file: str = field(default_factory=lambda: str(Path.home() / ".jarvis" / "jarvis.log"))
    
    # 调试模式
    debug: bool = False


# 全局配置实例
config = JarvisConfig()


def get_config() -> JarvisConfig:
    """获取配置实例"""
    return config


def update_config(**kwargs) -> JarvisConfig:
    """更新配置"""
    global config
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)
    return config


def update_env_file(updates: Dict[str, str]) -> bool:
    """更新 .env 文件"""
    try:
        env_path = Path(".env")
        
        # 读取现有内容
        existing_lines = []
        if env_path.exists():
            with open(env_path, 'r', encoding='utf-8') as f:
                existing_lines = f.readlines()
        
        # 创建键值映射
        env_vars = {}
        for line in existing_lines:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
        
        # 更新值
        for key, value in updates.items():
            env_vars[key] = value
        
        # 写回文件
        with open(env_path, 'w', encoding='utf-8') as f:
            # 写入注释
            f.write("# JARVIS 环境变量配置\n")
            f.write("# 自动生成，请勿手动编辑\n\n")
            
            # 写入变量
            for key, value in env_vars.items():
                if value:  # 只写入非空值
                    f.write(f"{key}={value}\n")
        
        _logger.info(f"已更新 .env 文件，共 {len(updates)} 个变量")
        return True
    except Exception as e:
        _logger.error(f"更新 .env 文件失败: {e}")
        return False
