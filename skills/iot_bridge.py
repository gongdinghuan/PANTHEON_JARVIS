"""
JARVIS IoT 智能家居技能
通过 Home Assistant API 控制设备

Author: gngdingghuan
"""

from typing import Dict, Any, Optional, List

import httpx

from skills.base_skill import BaseSkill, SkillResult, PermissionLevel, create_tool_schema
from config import get_config
from utils.logger import log


class IoTBridgeSkill(BaseSkill):
    """IoT 智能家居控制技能"""
    
    name = "iot_bridge"
    description = "智能家居控制：获取设备列表、控制设备"
    permission_level = PermissionLevel.SAFE_WRITE
    
    def __init__(self):
        super().__init__()
        self.iot_config = get_config().iot
        self._client: Optional[httpx.AsyncClient] = None
        
        if self.iot_config.enabled and self.iot_config.ha_url:
            self._init_client()
    
    def _init_client(self):
        """初始化 HTTP 客户端"""
        self._client = httpx.AsyncClient(
            base_url=self.iot_config.ha_url,
            headers={
                "Authorization": f"Bearer {self.iot_config.ha_token}",
                "Content-Type": "application/json"
            },
            timeout=30.0
        )
        log.info("IoT Bridge 已连接到 Home Assistant")
    
    async def execute(self, action: str, **params) -> SkillResult:
        """执行 IoT 操作"""
        if not self._client:
            return SkillResult(
                success=False,
                output=None,
                error="IoT 功能未配置或未启用。请在配置中设置 Home Assistant URL 和 Token。"
            )
        
        actions = {
            "get_devices": self._get_devices,
            "get_device_state": self._get_device_state,
            "control_device": self._control_device,
            "turn_on": self._turn_on,
            "turn_off": self._turn_off,
        }
        
        if action not in actions:
            return SkillResult(success=False, output=None, error=f"未知的操作: {action}")
        
        try:
            result = await actions[action](**params)
            return result
        except Exception as e:
            log.error(f"IoT 操作失败: {action}, 错误: {e}")
            return SkillResult(success=False, output=None, error=str(e))
    
    async def _get_devices(self, domain: Optional[str] = None) -> SkillResult:
        """获取设备列表"""
        try:
            response = await self._client.get("/api/states")
            response.raise_for_status()
            
            states = response.json()
            
            devices = []
            for state in states:
                entity_id = state.get("entity_id", "")
                
                # 过滤域
                if domain and not entity_id.startswith(f"{domain}."):
                    continue
                
                devices.append({
                    "entity_id": entity_id,
                    "state": state.get("state"),
                    "name": state.get("attributes", {}).get("friendly_name", entity_id),
                })
            
            return SkillResult(
                success=True,
                output={
                    "count": len(devices),
                    "devices": devices[:50]  # 限制数量
                }
            )
            
        except httpx.HTTPError as e:
            return SkillResult(success=False, output=None, error=f"HTTP 错误: {e}")
    
    async def _get_device_state(self, entity_id: str) -> SkillResult:
        """获取设备状态"""
        try:
            response = await self._client.get(f"/api/states/{entity_id}")
            response.raise_for_status()
            
            state = response.json()
            
            return SkillResult(
                success=True,
                output={
                    "entity_id": entity_id,
                    "state": state.get("state"),
                    "attributes": state.get("attributes", {}),
                    "last_changed": state.get("last_changed"),
                }
            )
            
        except httpx.HTTPError as e:
            return SkillResult(success=False, output=None, error=f"HTTP 错误: {e}")
    
    async def _control_device(self, entity_id: str, service: str, data: Optional[Dict] = None) -> SkillResult:
        """控制设备"""
        domain = entity_id.split(".")[0]
        
        try:
            payload = {"entity_id": entity_id}
            if data:
                payload.update(data)
            
            response = await self._client.post(
                f"/api/services/{domain}/{service}",
                json=payload
            )
            response.raise_for_status()
            
            log.info(f"IoT 控制: {entity_id}, 服务: {service}")
            
            return SkillResult(
                success=True,
                output=f"已执行 {service} on {entity_id}"
            )
            
        except httpx.HTTPError as e:
            return SkillResult(success=False, output=None, error=f"HTTP 错误: {e}")
    
    async def _turn_on(self, entity_id: str) -> SkillResult:
        """打开设备"""
        return await self._control_device(entity_id, "turn_on")
    
    async def _turn_off(self, entity_id: str) -> SkillResult:
        """关闭设备"""
        return await self._control_device(entity_id, "turn_off")
    
    async def close(self):
        """关闭客户端"""
        if self._client:
            await self._client.aclose()
    
    def get_schema(self) -> Dict[str, Any]:
        """获取 Function Calling Schema"""
        return create_tool_schema(
            name="iot_bridge",
            description="智能家居控制（Home Assistant）：获取设备、查看状态、开关控制",
            parameters={
                "action": {
                    "type": "string",
                    "enum": ["get_devices", "get_device_state", "control_device", "turn_on", "turn_off"],
                    "description": "要执行的操作类型"
                },
                "entity_id": {
                    "type": "string",
                    "description": "设备实体 ID，如 light.living_room"
                },
                "domain": {
                    "type": "string",
                    "description": "设备域，如 light, switch, sensor（用于 get_devices 过滤）"
                },
                "service": {
                    "type": "string",
                    "description": "服务名称，如 turn_on, turn_off（用于 control_device）"
                },
                "data": {
                    "type": "object",
                    "description": "额外参数，如亮度、颜色（用于 control_device）"
                }
            },
            required=["action"]
        )
