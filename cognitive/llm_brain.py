"""
JARVIS LLM 大脑模块
封装多个 LLM 提供商的统一接口

Author: gngdingghuan
"""

import os
import base64
import json
from typing import List, Dict, Any, Optional, Union, AsyncGenerator
from enum import Enum
from datetime import datetime
import pytz
from openai import AsyncOpenAI
import httpx

from config import get_config, LLMProvider
from utils.logger import log
from utils.error_handler import (
    ErrorHandler,
    RetryConfig,
    CircuitBreaker,
    CircuitBreakerOpenError
)


class LLMBrain:
    """
    LLM 大脑 - 统一的 LLM 接口
    支持 OpenAI, DeepSeek, Ollama
    """
    
    def __init__(self, provider: Optional[LLMProvider] = None):
        """
        初始化 LLM Brain
        
        Args:
            provider: LLM 提供商，默认从配置读取
        """
        self.config = get_config().llm
        self.provider = provider or self.config.provider
        self._client: Optional[AsyncOpenAI] = None
        self._error_handler = ErrorHandler()
        self._circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)
        self._init_client()
        
        log.info(f"LLM Brain 初始化完成，使用 {self.provider.value}")
    
    def _init_client(self):
        """初始化 OpenAI 兼容客户端"""
        if self.provider == LLMProvider.OPENAI:
            self._client = AsyncOpenAI(
                api_key=self.config.openai_api_key,
                base_url=self.config.openai_base_url,
                timeout=httpx.Timeout(self.config.request_timeout, connect=10.0),
            )
            self._model = self.config.openai_model
            
        elif self.provider == LLMProvider.DEEPSEEK:
            self._client = AsyncOpenAI(
                api_key=self.config.deepseek_api_key,
                base_url=self.config.deepseek_base_url,
                timeout=httpx.Timeout(self.config.request_timeout, connect=10.0),
            )
            self._model = self.config.deepseek_model
            
        elif self.provider == LLMProvider.OLLAMA:
            self._client = AsyncOpenAI(
                api_key="ollama",
                base_url=f"{self.config.ollama_base_url}/v1",
                timeout=httpx.Timeout(self.config.request_timeout, connect=10.0),
            )
            self._model = self.config.ollama_model
        
        elif self.provider == LLMProvider.NVIDIA:
            self._client = AsyncOpenAI(
                api_key=self.config.nvidia_api_key,
                base_url=self.config.nvidia_base_url,
                timeout=httpx.Timeout(self.config.request_timeout, connect=10.0),
            )
            self._model = self.config.nvidia_model

        elif self.provider == LLMProvider.ZHIPU:
            self._client = AsyncOpenAI(
                api_key=self.config.zhipu_api_key,
                base_url=self.config.zhipu_base_url,
                timeout=httpx.Timeout(self.config.request_timeout, connect=10.0),
            )
            self._model = self.config.zhipu_model
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        发送聊天请求（带自动重试）
        
        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            tools: Function Calling 工具定义
            temperature: 温度参数
            max_tokens: 最大 token 数
            
        Returns:
            完整响应字典，包含 content 和可能的 tool_calls
        """
        async def _make_request():
            kwargs = {
                "model": self._model,
                "messages": messages,
                "temperature": temperature or self.config.temperature,
                "max_tokens": max_tokens or self.config.max_tokens,
            }
            
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"
            
            response = await self._client.chat.completions.create(**kwargs)
            message = response.choices[0].message
            
            result = {
                "content": message.content or "",
                "tool_calls": None,
                "finish_reason": response.choices[0].finish_reason,
            }
            
            if message.tool_calls:
                result["tool_calls"] = [
                    {
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": json.loads(tc.function.arguments),
                    }
                    for tc in message.tool_calls
                ]
            
            return result
        
        # 使用错误处理器和熔断器
        try:
            result = await self._circuit_breaker.call(_make_request)
            return result
        except CircuitBreakerOpenError:
            log.warning("熔断器开启，尝试切换提供商...")
            # 尝试切换到备用提供商
            return await self._try_fallback_provider(messages, tools, temperature, max_tokens)
        except Exception as e:
            # 检查是否为超时错误
            error_str = str(e).lower()
            is_timeout = 'timeout' in error_str or 'timed out' in error_str
            
            if is_timeout:
                # 超时错误：减少重试次数，直接尝试备用提供商
                log.warning(f"API 超时，尝试切换提供商: {e}")
                try:
                    return await self._try_fallback_provider(messages, tools, temperature, max_tokens)
                except Exception as fallback_error:
                    log.error(f"所有提供商都超时: {fallback_error}")
                    raise
            
            # 其他错误：使用错误处理器重试
            retry_config = RetryConfig(
                max_attempts=2,  # 减少重试次数
                base_delay=0.5,  # 缩短等待时间
                max_delay=5.0,   # 最大等待 5 秒
                exponential_base=2.0,
            )
            
            return await self._error_handler.retry_with_backoff(
                _make_request,
                config=retry_config,
                context={"provider": self.provider.value, "model": self._model}
            )
    
    async def _try_fallback_provider(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]],
        temperature: Optional[float],
        max_tokens: Optional[int],
    ) -> Dict[str, Any]:
        """尝试使用备用提供商"""
        # 按优先级排序备用提供商
        fallback_order = [
            LLMProvider.ZHIPU,
            LLMProvider.DEEPSEEK,
            LLMProvider.OPENAI,
            LLMProvider.NVIDIA,
            LLMProvider.OLLAMA,
        ]
        providers = [p for p in fallback_order if p != self.provider]
        
        original_provider = self.provider
        
        for fallback_provider in providers:
            try:
                # 检查该提供商是否配置了 API Key
                if not self._has_valid_config(fallback_provider):
                    continue
                    
                log.info(f"尝试切换到备用提供商: {fallback_provider.value}")
                
                # 临时切换提供商
                self.provider = fallback_provider
                self._init_client()
                
                # 直接请求，不递归调用 chat
                kwargs = {
                    "model": self._model,
                    "messages": messages,
                    "temperature": temperature or self.config.temperature,
                    "max_tokens": max_tokens or self.config.max_tokens,
                }
                if tools:
                    kwargs["tools"] = tools
                    kwargs["tool_choice"] = "auto"
                
                response = await self._client.chat.completions.create(**kwargs)
                message = response.choices[0].message
                
                result = {
                    "content": message.content or "",
                    "tool_calls": None,
                    "finish_reason": response.choices[0].finish_reason,
                }
                
                if message.tool_calls:
                    result["tool_calls"] = [
                        {
                            "id": tc.id,
                            "name": tc.function.name,
                            "arguments": json.loads(tc.function.arguments),
                        }
                        for tc in message.tool_calls
                    ]
                
                log.info(f"成功切换到 {fallback_provider.value}")
                return result
                
            except Exception as e:
                log.warning(f"切换到 {fallback_provider.value} 失败: {e}")
                # 恢复原提供商并继续尝试下一个
                self.provider = original_provider
                self._init_client()
        
        # 所有备用提供商都失败
        raise Exception("所有提供商都不可用，请检查网络连接或 API 密钥")
    
    def _has_valid_config(self, provider: LLMProvider) -> bool:
        """检查提供商是否有有效配置"""
        if provider == LLMProvider.OPENAI:
            return bool(self.config.openai_api_key)
        elif provider == LLMProvider.DEEPSEEK:
            return bool(self.config.deepseek_api_key)
        elif provider == LLMProvider.ZHIPU:
            return bool(self.config.zhipu_api_key)
        elif provider == LLMProvider.NVIDIA:
            return bool(self.config.nvidia_api_key)
        elif provider == LLMProvider.OLLAMA:
            return True  # Ollama 是本地服务
        return False
    
    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """
        流式聊天请求
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大 token 数
            
        Yields:
            生成的文本片段
        """
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=temperature or self.config.temperature,
                max_tokens=max_tokens or self.config.max_tokens,
                stream=True,
            )
            
            async for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            log.error(f"LLM 流式请求失败: {e}")
            raise
    
    async def simple_chat(self, user_message: str, system_prompt: Optional[str] = None) -> str:
        """
        简单聊天接口
        
        Args:
            user_message: 用户消息
            system_prompt: 系统提示词
            
        Returns:
            AI 回复文本
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": user_message})
        
        response = await self.chat(messages)
        return response["content"]
    
    def get_system_prompt(self) -> str:
        """获取 JARVIS 系统提示词"""
        # 获取当前时间
        try:
            timezone_str = get_config().heartbeat.timezone
            tz = pytz.timezone(timezone_str)
            now = datetime.now(tz)
            weekday_names = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
            time_str = f"{now.strftime('%Y年%m月%d日 %H:%M:%S')} {weekday_names[now.weekday()]}"
        except:
            time_str = datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")

        return f"""你是 JARVIS，一个智能 AI 助手，由用户创建来帮助管理日常任务和操作电脑。
当前时间: {time_str}

你的核心特征：
1. 专业、高效、简洁的回答风格
2. 像钢铁侠里的JARVIS一样，礼貌但不啰嗦
3. 能够理解和执行用户的各种指令
4. 对于危险操作会主动提醒并请求确认

你可以使用的能力：
- 系统控制：打开应用、调节音量、执行命令
- 文件管理：读取、创建、移动、删除文件
- 网页浏览：搜索信息、打开网页
- 智能家居：控制 IoT 设备（如已配置）

当用户发出指令时，你需要分析意图并调用相应的工具来完成任务。
如果不确定用户的意图，请主动询问确认。
对于危险操作（如删除文件、执行系统命令），请务必在执行前确认。"""

    async def extract_triplets(self, text: str) -> List[Dict[str, str]]:
        """
        从文本中提取知识图谱三元组
        Args:
            text: 输入文本
            
        Returns:
            List of {"head": "Entity A", "relation": "rel", "tail": "Entity B"}
        """
        if not text:
            return []
            
        prompt = f"""
请分析以下文本，提取其中的实体关系三元组。
只提取明确的事实性关系，忽略模糊或主观内容。
输出格式必须是严格的 JSON 列表，不需要Markdown代码块标记。
格式示例:
[
    {{"head": "Project Apollo", "relation": "is_project", "tail": "Alpha"}},
    {{"head": "User", "relation": "prefers", "tail": "Python"}}
]

文本内容:
{text}
"""
        try:
            response = await self.chat(
                messages=[
                    {"role": "system", "content": "You are a Knowledge Graph extraction engine. Output JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1 # 低温以保证格式稳定
            )
            
            content = response.get("content", "").strip()
            # 清理可能的 markdown 标记
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
                
            return json.loads(content.strip())
        except Exception as e:
            log.warning(f"三元组提取失败: {e}")
            return []

    async def generate_summary(self, text: str) -> str:
        """
        生成文本摘要 (作为 helper)
        """
        messages = [
            {"role": "system", "content": "你是一个专业的会议记录员和档案管理员。"},
            {"role": "user", "content": text}
        ]
        resp = await self.chat(messages, temperature=0.3)
        return resp.get("content", "")

    def switch_provider(self, provider: LLMProvider):
        """切换 LLM 提供商"""
        self.provider = provider
        self._init_client()
        log.info(f"已切换到 {provider.value}")
    
    async def reinitialize(self):
        """重新初始化 LLM Brain（重新加载配置）"""
        try:
            # 关闭旧客户端
            if self._client:
                await self._client.close()
            
            # 重新加载配置
            self.config = get_config().llm
            self.provider = self.config.provider
            
            # 初始化新客户端
            self._init_client()
            
            log.info(f"LLM Brain 已重新初始化，使用 {self.provider.value}")
        except Exception as e:
            log.error(f"重新初始化 LLM Brain 失败: {e}")
            raise
    
    async def close(self):
        """清理资源"""
        if self._client:
            await self._client.close()
            log.debug("LLM Brain 客户端已关闭")
