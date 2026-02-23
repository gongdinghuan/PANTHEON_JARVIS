"""
JARVIS MCP (Model Context Protocol) 客户端
支持连接外部 MCP Server，动态加载工具到 JARVIS 技能系统

支持传输协议:
- stdio: 通过子进程通信
- sse: 通过 HTTP SSE 流

Author: gngdingghuan
"""

import asyncio
import json
import os
import sys
import signal
import uuid
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from pathlib import Path

from skills.base_skill import BaseSkill, SkillResult, create_tool_schema
from utils.logger import log


@dataclass
class MCPServerConfig:
    """MCP 服务器配置"""
    name: str
    transport: str = "stdio"  # "stdio" 或 "sse"
    # stdio 配置
    command: Optional[str] = None
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    # sse 配置  
    url: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    # 通用
    enabled: bool = True
    timeout: float = 30.0


@dataclass
class MCPTool:
    """MCP 工具定义"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    server_name: str


class MCPServerConnection:
    """
    与单个 MCP Server 的连接
    """
    
    def __init__(self, config: MCPServerConfig):
        self.config = config
        self._process: Optional[asyncio.subprocess.Process] = None
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._request_id = 0
        self._pending_requests: Dict[int, asyncio.Future] = {}
        self._tools: List[MCPTool] = []
        self._connected = False
        self._read_task: Optional[asyncio.Task] = None
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    async def connect(self):
        """连接到 MCP Server"""
        if self.config.transport == "stdio":
            await self._connect_stdio()
        elif self.config.transport == "sse":
            await self._connect_sse()
        else:
            raise ValueError(f"不支持的传输协议: {self.config.transport}")
    
    async def _connect_stdio(self):
        """通过 stdio 连接"""
        try:
            cmd = self.config.command
            if not cmd:
                raise ValueError(f"MCP Server {self.config.name} 未配置 command")
            
            # 合并环境变量
            env = {**os.environ, **self.config.env}
            
            log.info(f"启动 MCP Server: {cmd} {' '.join(self.config.args)}")
            
            self._process = await asyncio.create_subprocess_exec(
                cmd, *self.config.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            
            self._reader = self._process.stdout
            self._writer_raw = self._process.stdin
            
            # 启动读取循环
            self._read_task = asyncio.create_task(self._read_loop())
            
            # 发送 initialize 请求
            result = await self._send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "JARVIS",
                    "version": "3.0.0",
                }
            })
            
            # 发送 initialized 通知
            await self._send_notification("notifications/initialized", {})
            
            self._connected = True
            log.info(f"MCP Server {self.config.name} 连接成功")
            
            # 发现工具
            await self._discover_tools()
            
        except Exception as e:
            log.error(f"连接 MCP Server {self.config.name} 失败: {e}")
            await self.disconnect()
            raise
    
    async def _connect_sse(self):
        """通过 SSE 连接 (简化实现)"""
        try:
            import httpx
            
            if not self.config.url:
                raise ValueError(f"MCP Server {self.config.name} 未配置 url")
            
            # SSE 连接需要保持长连接
            self._http_client = httpx.AsyncClient(
                base_url=self.config.url,
                headers=self.config.headers,
                timeout=httpx.Timeout(self.config.timeout, connect=10.0),
            )
            
            self._connected = True
            log.info(f"MCP Server {self.config.name} (SSE) 连接成功")
            
            await self._discover_tools()
            
        except Exception as e:
            log.error(f"连接 MCP Server {self.config.name} (SSE) 失败: {e}")
            raise
    
    async def _read_loop(self):
        """读取 stdout 消息循环"""
        try:
            while self._process and self._process.returncode is None:
                # 读取 JSON-RPC 消息 (以换行分隔)
                line = await self._reader.readline()
                if not line:
                    break
                
                try:
                    message = json.loads(line.decode('utf-8').strip())
                    await self._handle_message(message)
                except json.JSONDecodeError:
                    continue
                    
        except asyncio.CancelledError:
            pass
        except Exception as e:
            log.error(f"MCP 读取循环异常: {e}")
    
    async def _handle_message(self, message: Dict):
        """处理接收到的消息"""
        if "id" in message and message["id"] in self._pending_requests:
            # 这是一个响应
            future = self._pending_requests.pop(message["id"])
            if "error" in message:
                future.set_exception(Exception(message["error"].get("message", "Unknown error")))
            else:
                future.set_result(message.get("result"))
    
    async def _send_request(self, method: str, params: Dict = None) -> Any:
        """发送 JSON-RPC 请求"""
        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
        }
        if params:
            request["params"] = params
        
        future = asyncio.get_running_loop().create_future()
        self._pending_requests[self._request_id] = future
        
        if self.config.transport == "stdio":
            data = json.dumps(request) + "\n"
            self._writer_raw.write(data.encode('utf-8'))
            await self._writer_raw.drain()
        elif self.config.transport == "sse":
            # 通过 HTTP POST 发送
            response = await self._http_client.post("/", json=request)
            return response.json().get("result")
        
        try:
            result = await asyncio.wait_for(future, timeout=self.config.timeout)
            return result
        except asyncio.TimeoutError:
            self._pending_requests.pop(self._request_id, None)
            raise TimeoutError(f"MCP 请求超时: {method}")
    
    async def _send_notification(self, method: str, params: Dict = None):
        """发送 JSON-RPC 通知 (无 id，不期望响应)"""
        notification = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if params:
            notification["params"] = params
        
        if self.config.transport == "stdio":
            data = json.dumps(notification) + "\n"
            self._writer_raw.write(data.encode('utf-8'))
            await self._writer_raw.drain()
    
    async def _discover_tools(self):
        """发现 MCP Server 提供的工具"""
        try:
            result = await self._send_request("tools/list", {})
            tools = result.get("tools", []) if result else []
            
            self._tools = []
            for tool_def in tools:
                self._tools.append(MCPTool(
                    name=tool_def["name"],
                    description=tool_def.get("description", ""),
                    input_schema=tool_def.get("inputSchema", {}),
                    server_name=self.config.name,
                ))
            
            log.info(f"MCP Server {self.config.name} 发现 {len(self._tools)} 个工具: {[t.name for t in self._tools]}")
            
        except Exception as e:
            log.error(f"MCP 工具发现失败: {e}")
    
    async def call_tool(self, tool_name: str, arguments: Dict) -> Any:
        """调用 MCP 工具"""
        result = await self._send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments,
        })
        return result
    
    async def disconnect(self):
        """断开连接"""
        self._connected = False
        
        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass
        
        if self._process:
            try:
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except (asyncio.TimeoutError, ProcessLookupError):
                try:
                    self._process.kill()
                except ProcessLookupError:
                    pass
        
        if hasattr(self, '_http_client'):
            await self._http_client.aclose()
        
        log.info(f"MCP Server {self.config.name} 已断开")


class MCPToolSkill(BaseSkill):
    """
    MCP 工具的 JARVIS Skill 包装器
    
    将一个 MCP 工具包装为 JARVIS 可以调用的 BaseSkill
    """
    
    def __init__(self, mcp_tool: MCPTool, connection: MCPServerConnection):
        super().__init__()
        self.mcp_tool = mcp_tool
        self.connection = connection
        self.name = f"mcp_{mcp_tool.server_name}_{mcp_tool.name}"
        self.description = f"[MCP:{mcp_tool.server_name}] {mcp_tool.description}"
    
    async def execute(self, **params) -> SkillResult:
        """执行 MCP 工具"""
        try:
            if not self.connection.is_connected:
                return SkillResult(
                    success=False,
                    output=None,
                    error=f"MCP Server {self.mcp_tool.server_name} 未连接"
                )
            
            result = await self.connection.call_tool(self.mcp_tool.name, params)
            
            # 解析 MCP 响应
            if isinstance(result, dict):
                content_parts = result.get("content", [])
                text_parts = []
                for part in content_parts:
                    if part.get("type") == "text":
                        text_parts.append(part.get("text", ""))
                
                output = "\n".join(text_parts) if text_parts else str(result)
                is_error = result.get("isError", False)
                
                return SkillResult(
                    success=not is_error,
                    output=output,
                    error=output if is_error else None,
                )
            
            return SkillResult(success=True, output=str(result))
            
        except Exception as e:
            log.error(f"MCP 工具执行失败 [{self.mcp_tool.name}]: {e}")
            return SkillResult(success=False, output=None, error=str(e))
    
    def get_schema(self) -> Dict[str, Any]:
        """获取 Function Calling Schema"""
        # 将 MCP inputSchema 转为 OpenAI tools 格式
        input_schema = self.mcp_tool.input_schema or {}
        
        properties = input_schema.get("properties", {})
        required = input_schema.get("required", [])
        
        return create_tool_schema(
            name=self.name,
            description=self.description,
            parameters=properties,
            required=required,
        )


class MCPClient:
    """
    MCP 客户端管理器
    
    管理多个 MCP Server 连接，自动发现和注册工具。
    
    用法:
        client = MCPClient()
        client.load_config(config_list)
        await client.connect_all()
        skills = client.get_skills()  # 注册到 planner
    """
    
    def __init__(self):
        self._connections: Dict[str, MCPServerConnection] = {}
        self._skills: Dict[str, MCPToolSkill] = {}
    
    def load_config(self, servers: List[Dict[str, Any]]):
        """
        从配置列表加载 MCP Server
        
        Args:
            servers: 服务器配置列表
                [{"name": "fs", "command": "npx", "args": [...], "transport": "stdio"}, ...]
        """
        for server_cfg in servers:
            if not server_cfg.get("enabled", True):
                continue
            
            config = MCPServerConfig(
                name=server_cfg["name"],
                transport=server_cfg.get("transport", "stdio"),
                command=server_cfg.get("command"),
                args=server_cfg.get("args", []),
                env=server_cfg.get("env", {}),
                url=server_cfg.get("url"),
                headers=server_cfg.get("headers", {}),
                timeout=server_cfg.get("timeout", 30.0),
            )
            
            self._connections[config.name] = MCPServerConnection(config)
            log.info(f"MCP Server 配置已加载: {config.name} ({config.transport})")
    
    async def connect_all(self):
        """连接所有配置的 MCP Server"""
        tasks = []
        for name, connection in self._connections.items():
            tasks.append(self._connect_one(name, connection))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # 注册所有发现的工具
        self._register_all_skills()
    
    async def _connect_one(self, name: str, connection: MCPServerConnection):
        """连接单个 Server"""
        try:
            await connection.connect()
        except Exception as e:
            log.warning(f"MCP Server {name} 连接失败（跳过）: {e}")
    
    def _register_all_skills(self):
        """将所有 MCP 工具注册为 JARVIS 技能"""
        self._skills.clear()
        
        for name, conn in self._connections.items():
            if not conn.is_connected:
                continue
            
            for tool in conn._tools:
                skill = MCPToolSkill(tool, conn)
                self._skills[skill.name] = skill
                log.info(f"注册 MCP 技能: {skill.name}")
        
        log.info(f"共注册 {len(self._skills)} 个 MCP 技能")
    
    def get_skills(self) -> Dict[str, MCPToolSkill]:
        """获取所有 MCP 技能 (用于注册到 Planner)"""
        return dict(self._skills)
    
    async def disconnect_all(self):
        """断开所有连接"""
        tasks = []
        for conn in self._connections.values():
            tasks.append(conn.disconnect())
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        self._skills.clear()
        log.info("所有 MCP 连接已断开")
    
    def get_status(self) -> Dict[str, Any]:
        """获取所有 MCP Server 状态"""
        status = {}
        for name, conn in self._connections.items():
            status[name] = {
                "connected": conn.is_connected,
                "transport": conn.config.transport,
                "tools_count": len(conn._tools),
                "tools": [t.name for t in conn._tools],
            }
        return status
