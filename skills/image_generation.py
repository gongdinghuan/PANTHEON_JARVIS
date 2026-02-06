"""
JARVIS 图像生成技能
使用 OpenAI DALL-E API 生成图像

Author: gngdingghuan
"""

import base64
import httpx
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from skills.base_skill import BaseSkill, SkillResult, PermissionLevel, create_tool_schema
from config import get_config
from utils.logger import log
from utils.compat import to_thread


class ImageGenerationSkill(BaseSkill):
    """图像生成技能 - 使用 DALL-E 生成图像"""
    
    name = "image_generation"
    description = "根据文字描述生成图像，支持 DALL-E 3"
    permission_level = PermissionLevel.SAFE_WRITE
    
    def __init__(self):
        super().__init__()
        self.config = get_config().llm
        self.output_dir = Path("generated_images")
        self.output_dir.mkdir(exist_ok=True)
        
        # 支持的尺寸
        self.SIZES = ["1024x1024", "1792x1024", "1024x1792"]
        self.QUALITIES = ["standard", "hd"]
        self.STYLES = ["vivid", "natural"]
    
    async def execute(
        self,
        prompt: Optional[str] = None,
        size: str = "1024x1024",
        quality: str = "standard",
        style: str = "vivid",
        **params
    ) -> SkillResult:
        """生成图像"""
        
        if not prompt:
            return SkillResult(
                success=False,
                output=None,
                error="缺少必需参数: prompt (图像描述)"
            )
        
        # 验证参数
        if size not in self.SIZES:
            return SkillResult(
                success=False,
                output=None,
                error=f"不支持的尺寸: {size}，可选: {self.SIZES}"
            )
        
        if quality not in self.QUALITIES:
            quality = "standard"
        
        if style not in self.STYLES:
            style = "vivid"
        
        # 检查 API Key
        api_key = self.config.openai_api_key
        if not api_key:
            return SkillResult(
                success=False,
                output=None,
                error="OpenAI API Key 未配置，无法使用图像生成功能"
            )
        
        try:
            result = await self._generate_image(prompt, size, quality, style, api_key)
            return result
        except Exception as e:
            log.error(f"图像生成失败: {e}")
            return SkillResult(success=False, output=None, error=str(e))
    
    async def _generate_image(
        self,
        prompt: str,
        size: str,
        quality: str,
        style: str,
        api_key: str
    ) -> SkillResult:
        """调用 DALL-E API 生成图像"""
        
        url = f"{self.config.openai_base_url}/images/generations"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "dall-e-3",
            "prompt": prompt,
            "n": 1,
            "size": size,
            "quality": quality,
            "style": style,
            "response_format": "b64_json"  # 获取 base64 编码的图像
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            
            if response.status_code != 200:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", "未知错误")
                return SkillResult(
                    success=False,
                    output=None,
                    error=f"DALL-E API 错误: {error_msg}"
                )
            
            data = response.json()
            
            if "data" not in data or len(data["data"]) == 0:
                return SkillResult(
                    success=False,
                    output=None,
                    error="API 返回数据为空"
                )
            
            # 获取图像数据
            image_data = data["data"][0]
            b64_image = image_data.get("b64_json")
            revised_prompt = image_data.get("revised_prompt", prompt)
            
            # 保存图像
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"dalle_{timestamp}.png"
            filepath = self.output_dir / filename
            
            with open(filepath, "wb") as f:
                f.write(base64.b64decode(b64_image))
            
            log.info(f"图像已保存: {filepath}")
            
            return SkillResult(
                success=True,
                output={
                    "message": f"图像生成成功",
                    "file_path": str(filepath.absolute()),
                    "original_prompt": prompt,
                    "revised_prompt": revised_prompt,
                    "size": size,
                    "quality": quality,
                    "style": style
                },
                visualization={
                    "type": "image",
                    "path": str(filepath.absolute())
                }
            )
    
    def get_schema(self) -> Dict[str, Any]:
        return create_tool_schema(
            name=self.name,
            description=self.description,
            parameters={
                "prompt": {
                    "type": "string",
                    "description": "图像描述，详细描述你想要生成的图像内容"
                },
                "size": {
                    "type": "string",
                    "enum": self.SIZES,
                    "description": "图像尺寸",
                    "default": "1024x1024"
                },
                "quality": {
                    "type": "string",
                    "enum": self.QUALITIES,
                    "description": "图像质量 (hd 会更精细但更慢)",
                    "default": "standard"
                },
                "style": {
                    "type": "string",
                    "enum": self.STYLES,
                    "description": "图像风格 (vivid 更鲜艳, natural 更自然)",
                    "default": "vivid"
                }
            },
            required=["prompt"]
        )
