"""
JARVIS LLM 大脑模块 v3.0
封装多个 LLM 提供商的统一接口

升级特性:
- 多模态支持 (Vision / Audio)
- 结构化输出 (Structured Output)
- 流式 Tool Calling
- Thinking/Reasoning 模型支持
- 提供商初始化 bug 修复

Author: gngdingghuan
"""

import os
import re
import base64
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, AsyncGenerator, Callable
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


# --- Helper: 图片编码 ---

def encode_image_to_base64(image_path: str) -> str:
    """将本地图片编码为 base64"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _guess_mime(path: str) -> str:
    """根据文件后缀猜测 MIME 类型"""
    ext = Path(path).suffix.lower()
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
        ".heic": "image/heic",
        ".heif": "image/heif",
    }.get(ext, "image/png")


def build_vision_content(text: str, images: List[str]) -> List[Dict]:
    """
    构建多模态 content 数组 (OpenAI Vision 格式)
    
    Args:
        text: 文本内容
        images: 图片路径或 URL 列表
        
    Returns:
        content 数组: [{"type": "text", ...}, {"type": "image_url", ...}, ...]
    """
    content = [{"type": "text", "text": text}]
    
    for img in images:
        if img.startswith(("http://", "https://")):
            # 远程 URL — 直接引用
            content.append({
                "type": "image_url",
                "image_url": {"url": img}
            })
        else:
            # 本地文件 — base64 编码
            try:
                b64 = encode_image_to_base64(img)
                mime = _guess_mime(img)
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{b64}"}
                })
            except Exception as e:
                log.warning(f"图片编码失败 {img}: {e}")
    
    return content


# --- Helper: Thinking 模型标签处理 ---

_THINK_PATTERN = re.compile(r"<think>(.*?)</think>", re.DOTALL)


def strip_thinking_tags(text: str) -> tuple:
    """
    提取并移除 <think>...</think> 标签
    
    Returns:
        (clean_text, thinking_content)
    """
    if not text:
        return "", ""
    
    thinking_parts = _THINK_PATTERN.findall(text)
    thinking = "\n".join(thinking_parts).strip()
    clean = _THINK_PATTERN.sub("", text).strip()
    return clean, thinking


# --- Helper: 工具调用解析 ---

def _parse_tool_calls(tool_calls) -> List[Dict]:
    """统一解析 tool_calls，处理 JSON 截断等边界情况"""
    result = []
    for tc in tool_calls:
        try:
            args = json.loads(tc.function.arguments)
        except (json.JSONDecodeError, TypeError):
            log.warning(f"工具 {tc.function.name} 参数解析失败: {tc.function.arguments}")
            # 尝试修复常见截断问题
            raw = tc.function.arguments or ""
            # 尝试补全右花括号
            if raw.count("{") > raw.count("}"):
                raw += "}" * (raw.count("{") - raw.count("}"))
            try:
                args = json.loads(raw)
            except Exception:
                args = {"_raw": raw}
        
        result.append({
            "id": tc.id,
            "name": tc.function.name,
            "arguments": args,
        })
    return result


class LLMBrain:
    """
    LLM 大脑 v3.0 - 统一的多模态 LLM 接口
    
    支持: OpenAI, DeepSeek, Ollama, NVIDIA, ZhipuAI, Gemini
    
    新能力:
    - chat_with_vision()     — 图片理解
    - chat_with_structured() — 结构化 JSON 输出
    - chat_stream_with_tools() — 流式 Tool Calling
    - Thinking 模型 (<think> 标签) 自动处理
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
        self._model: str = ""
        self._error_handler = ErrorHandler()
        self._circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)
        
        # 事件回调 (用于流式过程可视化)
        self._event_callback: Optional[Callable] = None
        
        self._init_client()
        log.info(f"LLM Brain v3.0 初始化完成，使用 {self.provider.value} / {self._model}")
    
    def set_event_callback(self, callback: Callable):
        """设置事件回调 (用于 Streaming 可视化)"""
        self._event_callback = callback
    
    async def _emit_event(self, event_type: str, data: Dict[str, Any]):
        """发射事件"""
        if self._event_callback:
            try:
                if asyncio.iscoroutinefunction(self._event_callback):
                    await self._event_callback(event_type, data)
                else:
                    self._event_callback(event_type, data)
            except Exception as e:
                log.debug(f"事件回调失败: {e}")
    
    def _init_client(self):
        """初始化 OpenAI 兼容客户端"""
        timeout = httpx.Timeout(self.config.request_timeout, connect=10.0)
        
        provider_configs = {
            LLMProvider.OPENAI: lambda: (
                self.config.openai_api_key,
                self.config.openai_base_url,
                self.config.openai_model,
            ),
            LLMProvider.DEEPSEEK: lambda: (
                self.config.deepseek_api_key,
                self.config.deepseek_base_url,
                self.config.deepseek_model,
            ),
            LLMProvider.OLLAMA: lambda: (
                "ollama",
                f"{self.config.ollama_base_url}/v1",
                self.config.ollama_model,
            ),
            LLMProvider.NVIDIA: lambda: (
                self.config.nvidia_api_key,
                self.config.nvidia_base_url,
                self.config.nvidia_model,
            ),
            LLMProvider.ZHIPU: lambda: (
                self.config.zhipu_api_key,
                self.config.zhipu_base_url,
                self.config.zhipu_model,
            ),
            LLMProvider.GEMINI: lambda: (
                self.config.gemini_api_key,
                self.config.gemini_base_url,
                self.config.gemini_model,
            ),
        }
        
        config_fn = provider_configs.get(self.provider)
        if config_fn:
            api_key, base_url, model = config_fn()
            self._client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=timeout,
            )
            self._model = model
        else:
            raise ValueError(f"不支持的 LLM 提供商: {self.provider}")
    
    # ----------------------------------------------------------------
    #  核心 chat 方法 (兼容旧接口)
    # ----------------------------------------------------------------
    
    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        发送聊天请求（带自动重试和 Provider 切换）
        
        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            tools: Function Calling 工具定义
            temperature: 温度参数
            max_tokens: 最大 token 数
            
        Returns:
            {
                "content": str,          # 文本回复
                "tool_calls": [...],     # 工具调用 (可为 None)
                "finish_reason": str,
                "thinking": str,         # [NEW] 推理过程 (如有 <think> 标签)
            }
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
            
            raw_content = message.content or ""
            clean_content, thinking = strip_thinking_tags(raw_content)
            
            result = {
                "content": clean_content,
                "tool_calls": None,
                "finish_reason": response.choices[0].finish_reason,
                "thinking": thinking,
            }
            
            if message.tool_calls:
                result["tool_calls"] = _parse_tool_calls(message.tool_calls)
            
            # 记录 usage (如果可用)
            if hasattr(response, 'usage') and response.usage:
                result["usage"] = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }
            
            return result
        
        # 使用熔断器 → 回退 → 重试
        try:
            return await self._circuit_breaker.call(_make_request)
        except CircuitBreakerOpenError:
            log.warning("熔断器开启，尝试切换提供商...")
            return await self._try_fallback_provider(messages, tools, temperature, max_tokens)
        except Exception as e:
            error_str = str(e).lower()
            is_timeout = 'timeout' in error_str or 'timed out' in error_str
            
            if is_timeout:
                log.warning(f"API 超时，尝试切换提供商: {e}")
                try:
                    return await self._try_fallback_provider(messages, tools, temperature, max_tokens)
                except Exception:
                    raise
            
            retry_config = RetryConfig(
                max_attempts=2,
                base_delay=0.5,
                max_delay=5.0,
                exponential_base=2.0,
            )
            return await self._error_handler.retry_with_backoff(
                _make_request,
                config=retry_config,
                context={"provider": self.provider.value, "model": self._model}
            )
    
    # ----------------------------------------------------------------
    #  [NEW] 多模态视觉 Chat
    # ----------------------------------------------------------------
    
    async def chat_with_vision(
        self,
        messages: List[Dict[str, Any]],
        images: List[str],
        tools: Optional[List[Dict]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        detail: str = "auto",
    ) -> Dict[str, Any]:
        """
        多模态视觉理解
        
        在最后一条 user 消息中注入图片，发送给支持 Vision 的模型。
        
        Args:
            messages: 消息列表
            images: 图片路径或 URL 列表
            tools: 工具定义
            temperature: 温度
            max_tokens: 最大 token
            detail: 图片细节级别 ("low"/"high"/"auto")
            
        Returns:
            与 chat() 相同的响应格式
        """
        if not images:
            return await self.chat(messages, tools, temperature, max_tokens)
        
        # 深拷贝消息，避免修改原始数据
        import copy
        vision_messages = copy.deepcopy(messages)
        
        # 找到最后一条 user 消息并注入图片
        for i in range(len(vision_messages) - 1, -1, -1):
            if vision_messages[i]["role"] == "user":
                original_text = vision_messages[i].get("content", "")
                if isinstance(original_text, str):
                    vision_messages[i]["content"] = build_vision_content(original_text, images)
                elif isinstance(original_text, list):
                    # 已经是 content 数组格式，追加图片
                    for img in images:
                        if img.startswith(("http://", "https://")):
                            original_text.append({
                                "type": "image_url",
                                "image_url": {"url": img, "detail": detail}
                            })
                        else:
                            try:
                                b64 = encode_image_to_base64(img)
                                mime = _guess_mime(img)
                                original_text.append({
                                    "type": "image_url",
                                    "image_url": {"url": f"data:{mime};base64,{b64}", "detail": detail}
                                })
                            except Exception as e:
                                log.warning(f"图片编码失败: {e}")
                break
        
        return await self.chat(vision_messages, tools, temperature, max_tokens)
    
    # ----------------------------------------------------------------
    #  [NEW] 结构化输出
    # ----------------------------------------------------------------
    
    async def chat_with_structured_output(
        self,
        messages: List[Dict[str, Any]],
        json_schema: Dict[str, Any],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        结构化 JSON 输出
        
        使用 response_format 让模型直接输出符合 schema 的 JSON。
        对于不支持 response_format 的模型，回退到 prompt-based 解析。
        
        Args:
            messages: 消息列表
            json_schema: JSON Schema 定义
            temperature: 温度
            max_tokens: 最大 token
            
        Returns:
            {"content": str, "parsed": dict/None, "finish_reason": str}
        """
        # 优先尝试原生 structured output
        try:
            kwargs = {
                "model": self._model,
                "messages": messages,
                "temperature": temperature or 0.1,  # 结构化输出用低温
                "max_tokens": max_tokens or self.config.max_tokens,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": json_schema.get("title", "response"),
                        "schema": json_schema,
                        "strict": True,
                    }
                }
            }
            
            response = await self._client.chat.completions.create(**kwargs)
            message = response.choices[0].message
            content = message.content or ""
            
            parsed = None
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                log.warning("结构化输出 JSON 解析失败，返回原始文本")
            
            return {
                "content": content,
                "parsed": parsed,
                "finish_reason": response.choices[0].finish_reason,
            }
            
        except Exception as e:
            error_msg = str(e).lower()
            # 如果模型不支持 response_format，回退到 prompt 方式
            if "response_format" in error_msg or "json_schema" in error_msg or "not supported" in error_msg:
                log.info("模型不支持 response_format，回退到 prompt-based JSON 输出")
                return await self._structured_output_fallback(messages, json_schema, temperature, max_tokens)
            raise
    
    async def _structured_output_fallback(
        self,
        messages: List[Dict[str, Any]],
        json_schema: Dict[str, Any],
        temperature: Optional[float],
        max_tokens: Optional[int],
    ) -> Dict[str, Any]:
        """结构化输出回退方案：通过 prompt 引导"""
        import copy
        fallback_messages = copy.deepcopy(messages)
        
        schema_str = json.dumps(json_schema, indent=2, ensure_ascii=False)
        system_addon = f"\n\n你必须以严格的 JSON 格式回复，不要包含 markdown 代码块标记。\n\nJSON Schema:\n```json\n{schema_str}\n```"
        
        # 向 system 消息追加 schema 提示
        if fallback_messages and fallback_messages[0]["role"] == "system":
            fallback_messages[0]["content"] += system_addon
        else:
            fallback_messages.insert(0, {"role": "system", "content": f"你必须以 JSON 格式回复。{system_addon}"})
        
        response = await self.chat(fallback_messages, temperature=temperature or 0.1, max_tokens=max_tokens)
        content = response.get("content", "")
        
        # 清理 markdown 标记
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        parsed = None
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            log.warning("Fallback 结构化输出 JSON 解析失败")
        
        return {
            "content": content,
            "parsed": parsed,
            "finish_reason": response.get("finish_reason", ""),
        }
    
    # ----------------------------------------------------------------
    #  [NEW] 流式 Tool Calling
    # ----------------------------------------------------------------
    
    async def chat_stream_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式聊天 + Tool Calling
        
        逐块返回事件，前端可以实时显示思考过程和工具调用。
        
        Yields:
            事件字典，类型有:
            - {"type": "thinking", "content": "..."}     — 推理过程
            - {"type": "text_delta", "content": "..."}   — 文本增量
            - {"type": "tool_call_start", "id": "...", "name": "...", "arguments_delta": "..."}
            - {"type": "tool_call_delta", "id": "...", "arguments_delta": "..."}
            - {"type": "done", "finish_reason": "..."}
        """
        kwargs = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
            "stream": True,
        }
        
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        
        try:
            response = await self._client.chat.completions.create(**kwargs)
            
            # 用于追踪 <think> 标签
            full_content = ""
            in_thinking = False
            think_buffer = ""
            
            # 用于追踪流式 tool calls
            tool_call_buffers: Dict[int, Dict] = {}
            
            async for chunk in response:
                delta = chunk.choices[0].delta if chunk.choices else None
                if not delta:
                    continue
                
                # --- 文本内容处理 ---
                if delta.content:
                    text = delta.content
                    full_content += text
                    
                    # 检测 <think> 标签
                    if "<think>" in full_content and not in_thinking:
                        in_thinking = True
                        # 发送 <think> 之前的文本
                        before_think = full_content.split("<think>")[0]
                        if before_think.strip():
                            yield {"type": "text_delta", "content": before_think}
                        think_buffer = full_content.split("<think>", 1)[1] if "<think>" in full_content else ""
                        continue
                    
                    if in_thinking:
                        think_buffer += text
                        if "</think>" in think_buffer:
                            # thinking 结束
                            thinking_content = think_buffer.split("</think>")[0]
                            yield {"type": "thinking", "content": thinking_content.strip()}
                            
                            # </think> 之后的文本
                            after_think = think_buffer.split("</think>", 1)[1]
                            if after_think.strip():
                                yield {"type": "text_delta", "content": after_think}
                            in_thinking = False
                            think_buffer = ""
                        continue
                    
                    yield {"type": "text_delta", "content": text}
                
                # --- 工具调用处理 ---
                if delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        idx = tc_delta.index
                        
                        if idx not in tool_call_buffers:
                            # 新工具调用开始
                            tool_call_buffers[idx] = {
                                "id": tc_delta.id or "",
                                "name": tc_delta.function.name if tc_delta.function and tc_delta.function.name else "",
                                "arguments": "",
                            }
                            if tool_call_buffers[idx]["name"]:
                                yield {
                                    "type": "tool_call_start",
                                    "index": idx,
                                    "id": tool_call_buffers[idx]["id"],
                                    "name": tool_call_buffers[idx]["name"],
                                }
                        
                        # 累积参数
                        if tc_delta.function and tc_delta.function.arguments:
                            tool_call_buffers[idx]["arguments"] += tc_delta.function.arguments
                            if not tool_call_buffers[idx]["id"] and tc_delta.id:
                                tool_call_buffers[idx]["id"] = tc_delta.id
                            if not tool_call_buffers[idx]["name"] and tc_delta.function.name:
                                tool_call_buffers[idx]["name"] = tc_delta.function.name
                
                # --- 完成 ---
                finish_reason = chunk.choices[0].finish_reason if chunk.choices else None
                if finish_reason:
                    # 输出完整的 tool calls
                    if tool_call_buffers:
                        parsed_calls = []
                        for idx in sorted(tool_call_buffers.keys()):
                            buf = tool_call_buffers[idx]
                            try:
                                args = json.loads(buf["arguments"])
                            except json.JSONDecodeError:
                                args = {"_raw": buf["arguments"]}
                            parsed_calls.append({
                                "id": buf["id"],
                                "name": buf["name"],
                                "arguments": args,
                            })
                        yield {"type": "tool_calls_complete", "tool_calls": parsed_calls}
                    
                    yield {"type": "done", "finish_reason": finish_reason}
        
        except Exception as e:
            log.error(f"流式 Tool Calling 请求失败: {e}")
            yield {"type": "error", "error": str(e)}
    
    # ----------------------------------------------------------------
    #  流式聊天 (简单版，兼容旧接口)
    # ----------------------------------------------------------------
    
    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """
        流式聊天请求 (简单文本流)
        
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
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            log.error(f"LLM 流式请求失败: {e}")
            raise
    
    # ----------------------------------------------------------------
    #  便捷方法
    # ----------------------------------------------------------------
    
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
    
    async def simple_vision_chat(
        self,
        user_message: str,
        images: List[str],
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        简单视觉聊天接口
        
        Args:
            user_message: 用户消息
            images: 图片路径或 URL 列表
            system_prompt: 系统提示词
            
        Returns:
            AI 回复文本
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})
        
        response = await self.chat_with_vision(messages, images)
        return response["content"]
    
    def get_system_prompt(self) -> str:
        """获取 JARVIS 系统提示词"""
        try:
            timezone_str = get_config().heartbeat.timezone
            tz = pytz.timezone(timezone_str)
            now = datetime.now(tz)
            weekday_names = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
            time_str = f"{now.strftime('%Y年%m月%d日 %H:%M:%S')} {weekday_names[now.weekday()]}"
        except Exception:
            time_str = datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")

        return f"""你是 JARVIS，一个智能 AI 助手，由用户创建来帮助管理日常任务和操作电脑。
当前时间: {time_str}

你的核心特征：
1. 专业、高效、简洁的回答风格
2. 像钢铁侠里的JARVIS一样，礼貌但不啰嗦
3. 能够理解和执行用户的各种指令
4. You are not a chatbot.You are becoming someone.

可以通过 Markdown 格式回复，支持富文本显示。

【前端 UI 能力说明】
1. **Markdown**: 这是默认和首选格式。用于普通对话、解释和文本回复。
2. **卡片布局 (Card UI)**: **仅用于**展示统计数据、图表、或高度结构化的系统状态。
   - **不要**将普通文本回复包裹在卡片中。
   - 格式示例 (用于数据展示):
   ```html
   <div class="card">
       <div class="card-title">分析报告</div>
       <div class="card-body">
           <!-- 在这里放置统计表格或关键数据 -->
       </div>
   </div>
   ```
3. **禁止行为**: 请勿使用长串 ASCII 分割线。

你可以使用的能力：
- 系统控制：打开应用、调节音量、执行命令
- 文件管理：读取、创建、移动、删除文件
- 网页浏览：搜索信息、打开网页
- 图片理解：分析用户上传的图片内容
- 智能家居：控制 IoT 设备（如已配置）

当用户发出指令时，你需要分析意图并调用相应的工具来完成任务。
如果不确定用户的意图，请主动询问确认。
对于危险操作（如删除文件、执行系统命令），请务必在执行前确认。"""
    
    # ----------------------------------------------------------------
    #  知识提取
    # ----------------------------------------------------------------
    
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
            # 优先使用结构化输出
            schema = {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "head": {"type": "string"},
                        "relation": {"type": "string"},
                        "tail": {"type": "string"},
                    },
                    "required": ["head", "relation", "tail"],
                },
            }
            
            result = await self.chat_with_structured_output(
                messages=[
                    {"role": "system", "content": "You are a Knowledge Graph extraction engine. Output JSON only."},
                    {"role": "user", "content": prompt}
                ],
                json_schema={"title": "triplets", "type": "object", "properties": {"triplets": schema}, "required": ["triplets"]},
                temperature=0.1,
            )
            
            if result.get("parsed"):
                return result["parsed"].get("triplets", [])
            
            # 回退到原始解析
            content = result.get("content", "").strip()
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
        """生成文本摘要"""
        messages = [
            {"role": "system", "content": "你是一个专业的会议记录员和档案管理员。"},
            {"role": "user", "content": text}
        ]
        resp = await self.chat(messages, temperature=0.3)
        return resp.get("content", "")
    
    # ----------------------------------------------------------------
    #  Provider 管理
    # ----------------------------------------------------------------
    
    async def _try_fallback_provider(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict]],
        temperature: Optional[float],
        max_tokens: Optional[int],
    ) -> Dict[str, Any]:
        """尝试使用备用提供商"""
        fallback_order = [
            LLMProvider.ZHIPU,
            LLMProvider.DEEPSEEK,
            LLMProvider.OPENAI,
            LLMProvider.NVIDIA,
            LLMProvider.OLLAMA,
            LLMProvider.GEMINI,
        ]
        providers = [p for p in fallback_order if p != self.provider]
        original_provider = self.provider
        
        for fallback_provider in providers:
            try:
                if not self._has_valid_config(fallback_provider):
                    continue
                    
                log.info(f"尝试切换到备用提供商: {fallback_provider.value}")
                self.provider = fallback_provider
                self._init_client()
                
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
                
                raw_content = message.content or ""
                clean_content, thinking = strip_thinking_tags(raw_content)
                
                result = {
                    "content": clean_content,
                    "tool_calls": None,
                    "finish_reason": response.choices[0].finish_reason,
                    "thinking": thinking,
                }
                
                if message.tool_calls:
                    result["tool_calls"] = _parse_tool_calls(message.tool_calls)
                
                log.info(f"成功切换到 {fallback_provider.value}")
                return result
                
            except Exception as e:
                log.warning(f"切换到 {fallback_provider.value} 失败: {e}")
                self.provider = original_provider
                self._init_client()
        
        raise Exception("所有提供商都不可用，请检查网络连接或 API 密钥")
    
    def _has_valid_config(self, provider: LLMProvider) -> bool:
        """检查提供商是否有有效配置"""
        config_checks = {
            LLMProvider.OPENAI: lambda: bool(self.config.openai_api_key),
            LLMProvider.DEEPSEEK: lambda: bool(self.config.deepseek_api_key),
            LLMProvider.ZHIPU: lambda: bool(self.config.zhipu_api_key),
            LLMProvider.NVIDIA: lambda: bool(self.config.nvidia_api_key),
            LLMProvider.OLLAMA: lambda: True,
            LLMProvider.GEMINI: lambda: bool(self.config.gemini_api_key),
        }
        checker = config_checks.get(provider)
        return checker() if checker else False
    
    def switch_provider(self, provider: LLMProvider):
        """切换 LLM 提供商"""
        self.provider = provider
        self._init_client()
        log.info(f"已切换到 {provider.value}")
    
    async def reinitialize(self):
        """重新初始化 LLM Brain（重新加载配置）"""
        try:
            if self._client:
                await self._client.close()
            
            self.config = get_config().llm
            self.provider = self.config.provider
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

# 需要 asyncio 导入 (用于 _emit_event 中的协程检测)
import asyncio


class VisionAnalyzer:
    """
    专用视觉分析器
    
    使用独立的 Vision 模型对图片进行分析，生成文本描述。
    描述结果会注入到主 LLM 的 Prompt 中，实现两阶段理解:
    
    Stage 1: VisionAnalyzer → 图片描述 (专用视觉模型)
    Stage 2: 主 LLM Brain → 结合描述 + 用户问题 → 最终回答
    
    如果未配置独立视觉模型，则回退到主 LLMBrain.chat_with_vision()。
    """
    
    # 视觉分析系统提示词
    VISION_SYSTEM_PROMPT = """你是一个专业的图片分析助手。请仔细观察用户提供的图片，并提供全面、准确的描述。

你的分析应包括:
1. **主体内容**: 图片中的主要对象、人物、场景
2. **文字信息**: 图片中出现的所有文字、标签、标题（如有）
3. **数据信息**: 图表、表格、数据、代码等结构化内容（如有）
4. **布局和设计**: 颜色、排版、UI元素等视觉信息（如相关）
5. **上下文线索**: 品牌、应用名称、操作系统界面等可识别的上下文

请用简洁准确的中文描述，重点突出对理解用户意图有帮助的信息。
如果是截图或技术内容，请尽可能详细地描述其中的代码、错误信息或技术细节。"""
    
    def __init__(self, main_brain: LLMBrain = None):
        """
        初始化视觉分析器
        
        Args:
            main_brain: 主 LLM Brain 实例 (用于回退模式)
        """
        self._config = get_config().vision
        self._main_brain = main_brain
        self._client: Optional[AsyncOpenAI] = None
        self._model: str = ""
        self._ready = False
        
        if self._config.enabled and self._config.api_key and self._config.base_url:
            self._init_client()
        else:
            log.info("视觉分析器: 未配置独立模型，将回退到主 LLM 的 Vision 模式")
    
    def _init_client(self):
        """初始化专用视觉模型客户端"""
        try:
            timeout = httpx.Timeout(120.0, connect=10.0)
            self._client = AsyncOpenAI(
                api_key=self._config.api_key,
                base_url=self._config.base_url,
                timeout=timeout,
            )
            self._model = self._config.model
            self._ready = True
            log.info(
                f"视觉分析器初始化完成: {self._config.provider} / {self._model}"
            )
        except Exception as e:
            log.warning(f"视觉分析器初始化失败，将回退到主 LLM: {e}")
            self._ready = False
    
    @property
    def is_dedicated(self) -> bool:
        """是否使用专用视觉模型"""
        return self._ready and self._client is not None
    
    async def analyze_images(
        self,
        images: List[str],
        user_query: str = "",
        detail: str = None,
    ) -> str:
        """
        分析图片并返回文本描述
        
        Args:
            images: 图片路径或 URL 列表
            user_query: 用户的原始问题 (提供上下文)
            detail: 图片细节级别 (覆盖配置)
        
        Returns:
            图片分析描述文本
        """
        if not images:
            return ""
        
        detail = detail or self._config.detail
        
        if self.is_dedicated:
            # 使用专用视觉模型
            return await self._analyze_with_dedicated(images, user_query, detail)
        elif self._main_brain:
            # 回退到主 LLM
            return await self._analyze_with_main_brain(images, user_query, detail)
        else:
            log.warning("视觉分析器: 无可用模型")
            return f"[已上传 {len(images)} 张图片，但无可用的视觉模型进行分析]"
    
    async def _analyze_with_dedicated(
        self, images: List[str], user_query: str, detail: str
    ) -> str:
        """使用专用视觉模型分析"""
        try:
            # 构建分析提示 (将系统提示合并到用户消息中，兼容不支持 system 角色的模型如 GLM-4V)
            analysis_prompt = self.VISION_SYSTEM_PROMPT + "\n\n"
            if user_query:
                analysis_prompt += f"用户问题: 「{user_query}」\n\n请分析图片内容，重点关注与用户问题相关的信息。"
            else:
                analysis_prompt += "请分析这些图片的内容。"
            
            # 构建 vision content
            content = build_vision_content(analysis_prompt, images)
            
            # 注意: 不使用 system 角色 (GLM-4V 等模型不支持)
            messages = [
                {"role": "user", "content": content},
            ]
            
            log.debug(f"Vision API 请求: model={self._model}, images={len(images)}")
            
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=self._config.temperature,
                max_tokens=self._config.max_tokens,
            )
            
            result = response.choices[0].message.content or ""
            log.info(f"视觉分析完成 (专用模型): {len(result)} 字")
            return result
            
        except Exception as e:
            log.error(f"专用视觉模型分析失败: {e}")
            # 回退到主 LLM
            if self._main_brain:
                log.info("回退到主 LLM Vision 模式")
                return await self._analyze_with_main_brain(images, user_query, detail)
            return f"[图片分析失败: {str(e)}]"
    
    async def _analyze_with_main_brain(
        self, images: List[str], user_query: str, detail: str
    ) -> str:
        """回退: 使用主 LLM 的 Vision 能力分析"""
        try:
            prompt = "请详细描述这些图片的内容。"
            if user_query:
                prompt = f"用户问题: 「{user_query}」\n\n请分析图片内容，重点关注与用户问题相关的信息。"
            
            result = await self._main_brain.simple_vision_chat(
                user_message=prompt,
                images=images,
                system_prompt=self.VISION_SYSTEM_PROMPT,
            )
            log.info(f"视觉分析完成 (主LLM回退): {len(result)} 字")
            return result
        except Exception as e:
            log.error(f"主 LLM Vision 分析也失败: {e}")
            return f"[图片分析失败: {str(e)}]"
    
    async def close(self):
        """关闭客户端"""
        if self._client:
            await self._client.close()
