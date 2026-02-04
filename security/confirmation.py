"""
JARVIS 确认处理模块
危险操作的人工确认机制

Author: gngdingghuan
"""

import asyncio
from typing import Dict, Any, Optional, Callable
from datetime import datetime

from config import get_config
from utils.logger import log


class ConfirmationRequest:
    """确认请求"""
    
    def __init__(
        self,
        action: str,
        details: Dict[str, Any],
        timeout: int = 30
    ):
        self.id = f"confirm_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        self.action = action
        self.details = details
        self.timeout = timeout
        self.created_at = datetime.now()
        self.result: Optional[bool] = None
        self._event = asyncio.Event()
    
    def confirm(self):
        """确认操作"""
        self.result = True
        self._event.set()
    
    def reject(self):
        """拒绝操作"""
        self.result = False
        self._event.set()
    
    async def wait(self) -> bool:
        """等待确认结果"""
        try:
            await asyncio.wait_for(self._event.wait(), timeout=self.timeout)
            return self.result
        except asyncio.TimeoutError:
            log.warning(f"确认请求超时: {self.action}")
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "action": self.action,
            "details": self.details,
            "timeout": self.timeout,
            "created_at": self.created_at.isoformat(),
        }


class ConfirmationHandler:
    """
    确认处理器
    - 创建确认请求
    - 等待用户响应
    - 支持多种确认方式（命令行、语音、WebSocket）
    """
    
    def __init__(self):
        self.config = get_config().security
        
        # 待处理的确认请求
        self._pending_requests: Dict[str, ConfirmationRequest] = {}
        
        # 确认通知回调
        self._notification_callback: Optional[Callable] = None
        
        # WebSocket 连接（用于 Web UI 确认）
        self._websocket = None
        
        log.info("确认处理器初始化完成")
    
    def set_notification_callback(self, callback: Callable):
        """
        设置确认通知回调
        当有新的确认请求时调用
        
        Args:
            callback: async def callback(request: ConfirmationRequest)
        """
        self._notification_callback = callback
    
    def set_websocket(self, websocket):
        """
        设置 WebSocket 连接（用于 Web UI 确认）
        
        Args:
            websocket: WebSocket 连接对象
        """
        self._websocket = websocket
        log.debug("已设置 WebSocket 连接到确认处理器")
    
    async def send_websocket_notification(self, request: ConfirmationRequest):
        """
        通过 WebSocket 发送确认通知到 Web UI
        
        Args:
            request: 确认请求对象
        """
        if not self._websocket:
            log.warning("WebSocket 连接未设置，无法发送确认通知")
            return False
        
        try:
            await self._websocket.send_json({
                "type": "confirmation",
                "request_id": request.id,
                "action": request.action,
                "details": request.details,
                "timeout": request.timeout,
                "timestamp": request.created_at.isoformat(),
            })
            log.info(f"已通过 WebSocket 发送确认通知: {request.id}")
            return True
        except Exception as e:
            log.error(f"发送 WebSocket 确认通知失败: {e}")
            return False
    
    async def request_confirmation(
        self,
        action: str,
        details: Dict[str, Any],
        timeout: Optional[int] = None
    ) -> bool:
        """
        请求用户确认
        
        Args:
            action: 操作描述
            details: 操作详情
            timeout: 超时时间（秒）
            
        Returns:
            是否确认
        """
        if not self.config.require_confirmation:
            log.debug(f"确认已禁用，自动批准: {action}")
            return True
        
        timeout = timeout or self.config.confirmation_timeout
        
        # 创建确认请求
        request = ConfirmationRequest(action, details, timeout)
        self._pending_requests[request.id] = request
        
        log.info(f"创建确认请求: {request.id} - {action}")
        
        # 通知用户
        await self._notify_user(request)
        
        # 等待确认
        try:
            result = await request.wait()
            log.info(f"确认结果: {request.id} - {'允许' if result else '拒绝'}")
            return result
        finally:
            # 清理请求
            self._pending_requests.pop(request.id, None)
    
    async def _notify_user(self, request: ConfirmationRequest):
        """通知用户有确认请求"""
        # 打印到控制台
        message = self._format_confirmation_message(request)
        print("\n" + "=" * 50)
        print("⚠️  需要确认的操作")
        print("=" * 50)
        print(message)
        print(f"\n请输入 'y' 确认或 'n' 拒绝 (超时: {request.timeout}秒)")
        print("=" * 50 + "\n")
        
        # 尝试通过 WebSocket 发送通知
        websocket_sent = await self.send_websocket_notification(request)
        
        # 如果 WebSocket 发送失败，调用传统回调
        if not websocket_sent and self._notification_callback:
            try:
                await self._notification_callback(request)
            except Exception as e:
                log.error(f"通知回调失败: {e}")
    
    def _format_confirmation_message(self, request: ConfirmationRequest) -> str:
        """格式化确认消息"""
        lines = [f"操作: {request.action}"]
        
        for key, value in request.details.items():
            lines.append(f"  {key}: {value}")
        
        return "\n".join(lines)
    
    def confirm(self, request_id: str) -> bool:
        """确认请求"""
        if request_id in self._pending_requests:
            self._pending_requests[request_id].confirm()
            return True
        return False
    
    def reject(self, request_id: str) -> bool:
        """拒绝请求"""
        if request_id in self._pending_requests:
            self._pending_requests[request_id].reject()
            return True
        return False
    
    def get_pending_requests(self) -> list:
        """获取待处理的确认请求"""
        return [r.to_dict() for r in self._pending_requests.values()]
    
    def handle_cli_input(self, user_input: str) -> bool:
        """
        处理命令行输入
        
        Args:
            user_input: 用户输入 ('y', 'n', 或请求ID)
            
        Returns:
            是否处理成功
        """
        user_input = user_input.strip().lower()
        
        # 如果只有一个待处理请求，简化处理
        if len(self._pending_requests) == 1:
            request_id = list(self._pending_requests.keys())[0]
            
            if user_input in ['y', 'yes', '是', '确认', 'ok']:
                return self.confirm(request_id)
            elif user_input in ['n', 'no', '否', '拒绝', 'cancel']:
                return self.reject(request_id)
        
        # 否则检查是否是请求ID
        if user_input.startswith('confirm_'):
            # 格式: confirm_xxx:y 或 confirm_xxx:n
            if ':' in user_input:
                request_id, action = user_input.rsplit(':', 1)
                if action in ['y', 'yes']:
                    return self.confirm(request_id)
                elif action in ['n', 'no']:
                    return self.reject(request_id)
        
        return False


# 全局确认处理器实例
_confirmation_handler: Optional[ConfirmationHandler] = None


def get_confirmation_handler() -> ConfirmationHandler:
    """获取确认处理器单例"""
    global _confirmation_handler
    if _confirmation_handler is None:
        _confirmation_handler = ConfirmationHandler()
    return _confirmation_handler
