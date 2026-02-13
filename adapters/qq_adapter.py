"""
JARVIS QQ 适配器
通过 OneBot 11 协议（反向 WebSocket）对接 NapCat / Lagrange

工作原理:
  1. JARVIS 作为 WebSocket Server 监听指定端口
  2. NapCat/Lagrange 作为 Client 连接进来
  3. 收到 QQ 消息 → 转发到 Jarvis.process()
  4. 将回复通过 OneBot API 发回 QQ

配置 NapCat:
  在 NapCat 的 setting.json 中配置反向 WebSocket:
  {
    "reverseWs": {
      "urls": ["ws://127.0.0.1:8011/onebot/v11/ws"]
    }
  }

Author: gngdingghuan
"""

import asyncio
import json
import base64
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from utils.logger import log
from .base import BaseIMAdapter

try:
    import websockets
    from websockets.server import serve as ws_serve
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False


class QQAdapter(BaseIMAdapter):
    """
    QQ 适配器 — 基于 OneBot 11 反向 WebSocket
    
    JARVIS 作为 WS Server，等待 NapCat/Lagrange 连接。
    这种模式下 JARVIS 不需要主动连接任何外部服务。
    """
    
    name = "qq"
    
    def __init__(self, jarvis_instance, 
                 host: str = "127.0.0.1", 
                 port: int = 8011,
                 allowed_groups: Optional[List[int]] = None,
                 admin_qq: Optional[List[int]] = None):
        """
        Args:
            jarvis_instance: JARVIS 主实例
            host: WebSocket 监听地址
            port: WebSocket 监听端口
            allowed_groups: 允许响应的群号列表（None = 不响应群消息）
            admin_qq: 管理员 QQ 号列表（拥有最高权限）
        """
        super().__init__(jarvis_instance)
        self._host = host
        self._port = port
        self._allowed_groups = set(allowed_groups) if allowed_groups else set()
        self._admin_qq = set(admin_qq) if admin_qq else set()
        
        self._ws_server = None
        self._connections: List = []  # 活跃的 OneBot 连接
        self._self_info: Dict = {}   # 机器人自身信息
        
        # 消息处理锁（防止并发处理同一用户消息）
        self._processing_locks: Dict[str, asyncio.Lock] = {}
    
    async def start(self):
        """启动 OneBot 反向 WebSocket 服务器"""
        if not WEBSOCKETS_AVAILABLE:
            raise RuntimeError(
                "websockets 库未安装。请运行: pip install websockets"
            )
        
        self._running = True
        
        # 启动 WS 服务器
        self._ws_server = await ws_serve(
            self._handle_connection,
            self._host,
            self._port,
            ping_interval=30,
            ping_timeout=10
        )
        
        log.info(
            f"[QQ] OneBot WebSocket Server 已启动: "
            f"ws://{self._host}:{self._port}/onebot/v11/ws"
        )
        log.info(
            f"[QQ] 等待 NapCat/Lagrange 连接..."
        )
    
    async def stop(self):
        """停止服务器"""
        self._running = False
        
        # 关闭所有连接
        for ws in self._connections:
            try:
                await ws.close()
            except Exception:
                pass
        self._connections.clear()
        
        # 关闭服务器
        if self._ws_server:
            self._ws_server.close()
            await self._ws_server.wait_closed()
            self._ws_server = None
        
        log.info("[QQ] 适配器已停止")
    
    async def send_message(self, user_id: str, content: str,
                           attachments: Optional[List[Dict[str, Any]]] = None):
        """
        发送消息到 QQ
        
        支持私聊和群聊，通过 user_id 格式区分:
          - "private:123456" → 私聊
          - "group:654321:123456" → 群聊
        """
        if not self._connections:
            log.warning("[QQ] 无可用的 OneBot 连接，消息无法发送")
            return
        
        ws = self._connections[0]  # 使用第一个可用连接
        
        # 构建 CQ 消息段
        message_segments = []
        
        # 文本消息
        if content:
            message_segments.append({
                "type": "text",
                "data": {"text": content}
            })
        
        # 附件（图片）
        if attachments:
            for att in attachments:
                if att.get("type") == "image":
                    img_segment = self._build_image_segment(att.get("path", ""))
                    if img_segment:
                        message_segments.append(img_segment)
        
        if not message_segments:
            return
        
        # 解析发送目标
        parts = user_id.split(":")
        
        if parts[0] == "group" and len(parts) >= 2:
            # 群消息
            api_data = {
                "action": "send_group_msg",
                "params": {
                    "group_id": int(parts[1]),
                    "message": message_segments
                }
            }
        else:
            # 私聊消息
            qq_id = parts[-1]  # 最后一段是 QQ 号
            api_data = {
                "action": "send_private_msg",
                "params": {
                    "user_id": int(qq_id),
                    "message": message_segments
                }
            }
        
        try:
            await ws.send(json.dumps(api_data))
        except Exception as e:
            log.error(f"[QQ] 发送消息失败: {e}")
    
    def _build_image_segment(self, path: str) -> Optional[Dict]:
        """构建图片消息段"""
        filepath = Path(path)
        if not filepath.exists():
            log.warning(f"[QQ] 图片文件不存在: {path}")
            return None
        
        try:
            with open(filepath, "rb") as f:
                img_data = base64.b64encode(f.read()).decode()
            return {
                "type": "image",
                "data": {"file": f"base64://{img_data}"}
            }
        except Exception as e:
            log.error(f"[QQ] 读取图片失败: {e}")
            return None
    
    # ─── WebSocket 连接处理 ────────────────────────
    
    async def _handle_connection(self, websocket):
        """处理来自 NapCat/Lagrange 的 WebSocket 连接"""
        self._connections.append(websocket)
        remote = websocket.remote_address
        log.info(f"[QQ] OneBot 客户端已连接: {remote}")
        
        try:
            async for raw_message in websocket:
                try:
                    data = json.loads(raw_message)
                    await self._dispatch_event(data, websocket)
                except json.JSONDecodeError:
                    log.warning(f"[QQ] 收到无效 JSON: {raw_message[:100]}")
                except Exception as e:
                    log.error(f"[QQ] 处理事件时出错: {e}")
        except Exception as e:
            log.warning(f"[QQ] 连接断开: {remote} - {e}")
        finally:
            if websocket in self._connections:
                self._connections.remove(websocket)
            log.info(f"[QQ] OneBot 客户端已断开: {remote}")
    
    async def _dispatch_event(self, data: Dict, websocket):
        """分发 OneBot 事件"""
        post_type = data.get("post_type")
        
        if post_type == "meta_event":
            await self._handle_meta_event(data)
        elif post_type == "message":
            await self._handle_message_event(data)
        elif post_type == "notice":
            await self._handle_notice_event(data)
        elif post_type == "request":
            log.debug(f"[QQ] 收到请求事件: {data.get('request_type')}")
        # 忽略 API 响应 (echo)
    
    async def _handle_meta_event(self, data: Dict):
        """处理元事件（生命周期、心跳）"""
        meta_type = data.get("meta_event_type")
        
        if meta_type == "lifecycle":
            sub_type = data.get("sub_type")
            self_id = data.get("self_id")
            self._self_info = {"qq": self_id}
            log.info(f"[QQ] 生命周期事件: {sub_type}, Bot QQ: {self_id}")
            
        elif meta_type == "heartbeat":
            # OneBot 心跳，无需处理
            pass
    
    async def _handle_message_event(self, data: Dict):
        """
        处理消息事件
        
        OneBot 11 消息格式:
        {
            "post_type": "message",
            "message_type": "private" | "group",
            "user_id": 123456,
            "group_id": 654321,  (群消息时存在)
            "raw_message": "纯文本内容",
            "message": [{"type": "text", "data": {"text": "..."}}]
        }
        """
        message_type = data.get("message_type")
        user_id = data.get("user_id")
        group_id = data.get("group_id")
        raw_message = data.get("raw_message", "")
        
        # 提取纯文本内容
        text = self._extract_text(data.get("message", []), raw_message)
        
        if not text or not text.strip():
            return
        
        # ─── 消息过滤 ───
        
        if message_type == "group":
            # 群消息：检查是否在允许列表中
            if self._allowed_groups and group_id not in self._allowed_groups:
                return
            
            # 群消息：需要 @机器人 或以特定前缀开头才响应
            bot_qq = self._self_info.get("qq")
            is_at_me = False
            
            for seg in data.get("message", []):
                if seg.get("type") == "at" and str(seg.get("data", {}).get("qq")) == str(bot_qq):
                    is_at_me = True
                    break
            
            # 移除 @机器人 的文本部分
            if is_at_me:
                text = text.strip()
                # 清理可能的 [CQ:at] 残留
                import re
                text = re.sub(r'\[CQ:at,qq=\d+\]\s*', '', text).strip()
            
            # 群消息触发条件：被 @ 或以 "jarvis" / "贾维斯" 开头
            triggers = ["jarvis", "贾维斯", "j.", "/j"]
            text_lower = text.lower().strip()
            
            if not is_at_me and not any(text_lower.startswith(t) for t in triggers):
                return  # 不满足触发条件，忽略
            
            # 清理触发前缀
            for t in triggers:
                if text_lower.startswith(t):
                    text = text[len(t):].strip()
                    break
            
            # 构建用户 ID（包含群号）
            adapter_user_id = f"group:{group_id}:{user_id}"
        else:
            # 私聊消息：直接响应
            adapter_user_id = f"private:{user_id}"
        
        # ─── 防并发处理 ───
        lock_key = adapter_user_id
        if lock_key not in self._processing_locks:
            self._processing_locks[lock_key] = asyncio.Lock()
        
        if self._processing_locks[lock_key].locked():
            log.debug(f"[QQ] 用户 {user_id} 的消息正在处理中，跳过")
            return
        
        async with self._processing_locks[lock_key]:
            log.info(
                f"[QQ] {'群' if message_type == 'group' else '私聊'}消息 - "
                f"用户: {user_id}, "
                f"{'群: ' + str(group_id) + ', ' if group_id else ''}"
                f"内容: {text[:80]}"
            )
            
            # 调用基类的统一处理方法
            await self.handle_message(
                user_id=adapter_user_id,
                content=text,
                raw_data=data
            )
    
    async def _handle_notice_event(self, data: Dict):
        """处理通知事件（加群、退群等）"""
        notice_type = data.get("notice_type")
        log.debug(f"[QQ] 通知事件: {notice_type}")
    
    def _extract_text(self, message_segments: list, fallback: str = "") -> str:
        """从 OneBot 消息段中提取纯文本"""
        if not message_segments:
            return fallback
        
        parts = []
        for seg in message_segments:
            if seg.get("type") == "text":
                parts.append(seg.get("data", {}).get("text", ""))
        
        return " ".join(parts).strip() if parts else fallback
    
    # ─── OneBot API 调用 ────────────────────────
    
    async def _call_api(self, action: str, params: Dict = None) -> Optional[Dict]:
        """
        调用 OneBot API
        
        Args:
            action: API 动作名
            params: 参数
            
        Returns:
            API 响应数据
        """
        if not self._connections:
            log.warning("[QQ] 无可用连接")
            return None
        
        ws = self._connections[0]
        request = {
            "action": action,
            "params": params or {},
            "echo": f"{action}_{id(asyncio.current_task())}"
        }
        
        try:
            await ws.send(json.dumps(request))
            return {"status": "sent"}
        except Exception as e:
            log.error(f"[QQ] API 调用失败 [{action}]: {e}")
            return None
    
    async def get_bot_info(self) -> Optional[Dict]:
        """获取机器人自身信息"""
        return await self._call_api("get_login_info")
