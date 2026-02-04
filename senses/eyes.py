"""
JARVIS 视觉模块 (Eyes)
屏幕截图和图像分析

Author: gngdingghuan
"""

import base64
from typing import Optional, Tuple
from pathlib import Path
from datetime import datetime
import io

from config import get_config
from utils.logger import log

# 截图
try:
    import pyautogui
    from PIL import Image
    SCREENSHOT_AVAILABLE = True
except ImportError:
    SCREENSHOT_AVAILABLE = False

# 高性能截图（可选）
try:
    import mss
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False


class Eyes:
    """
    视觉模块
    - 屏幕截图
    - 区域截图
    - 图像编码（用于发送给多模态 LLM）
    """
    
    def __init__(self):
        if not SCREENSHOT_AVAILABLE:
            log.warning("pyautogui 或 Pillow 未安装，截图功能不可用")
        else:
            log.info("视觉模块初始化完成")
    
    def is_available(self) -> bool:
        """检查视觉功能是否可用"""
        return SCREENSHOT_AVAILABLE
    
    def capture_screen(self) -> Optional[Image.Image]:
        """
        截取全屏
        
        Returns:
            PIL Image 对象
        """
        if not SCREENSHOT_AVAILABLE:
            return None
        
        try:
            if MSS_AVAILABLE:
                # 使用 mss 更快
                with mss.mss() as sct:
                    monitor = sct.monitors[0]  # 整个屏幕
                    screenshot = sct.grab(monitor)
                    return Image.frombytes('RGB', screenshot.size, screenshot.rgb)
            else:
                return pyautogui.screenshot()
                
        except Exception as e:
            log.error(f"截图失败: {e}")
            return None
    
    def capture_region(
        self,
        x: int,
        y: int,
        width: int,
        height: int
    ) -> Optional[Image.Image]:
        """
        截取屏幕区域
        
        Args:
            x: 左上角 X 坐标
            y: 左上角 Y 坐标
            width: 宽度
            height: 高度
            
        Returns:
            PIL Image 对象
        """
        if not SCREENSHOT_AVAILABLE:
            return None
        
        try:
            return pyautogui.screenshot(region=(x, y, width, height))
        except Exception as e:
            log.error(f"区域截图失败: {e}")
            return None
    
    def save_screenshot(
        self,
        image: Image.Image,
        filepath: Optional[str] = None
    ) -> Optional[str]:
        """
        保存截图
        
        Args:
            image: PIL Image 对象
            filepath: 保存路径，默认保存到桌面
            
        Returns:
            保存的文件路径
        """
        if filepath is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filepath = str(Path.home() / "Desktop" / f"screenshot_{timestamp}.png")
        
        try:
            image.save(filepath)
            log.info(f"截图已保存: {filepath}")
            return filepath
        except Exception as e:
            log.error(f"保存截图失败: {e}")
            return None
    
    def image_to_base64(
        self,
        image: Image.Image,
        format: str = "PNG",
        quality: int = 85
    ) -> str:
        """
        将图像转换为 Base64 字符串
        用于发送给多模态 LLM
        
        Args:
            image: PIL Image 对象
            format: 图像格式 (PNG, JPEG)
            quality: JPEG 质量 (1-100)
            
        Returns:
            Base64 编码字符串
        """
        buffer = io.BytesIO()
        
        if format.upper() == "JPEG":
            # JPEG 需要 RGB 模式
            if image.mode == "RGBA":
                image = image.convert("RGB")
            image.save(buffer, format="JPEG", quality=quality)
        else:
            image.save(buffer, format="PNG")
        
        buffer.seek(0)
        base64_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return base64_str
    
    def get_screen_size(self) -> Tuple[int, int]:
        """获取屏幕尺寸"""
        if not SCREENSHOT_AVAILABLE:
            return (1920, 1080)  # 默认值
        
        try:
            return pyautogui.size()
        except:
            return (1920, 1080)
    
    async def describe_screen(self, brain) -> str:
        """
        使用多模态 LLM 描述屏幕内容
        
        Args:
            brain: LLM Brain 实例（需要支持多模态）
            
        Returns:
            屏幕内容描述
        """
        screenshot = self.capture_screen()
        if screenshot is None:
            return "无法截取屏幕"
        
        # 压缩图像
        screenshot.thumbnail((1280, 720))
        
        # 转换为 Base64
        image_base64 = self.image_to_base64(screenshot, format="JPEG", quality=70)
        
        # TODO: 调用多模态 LLM 描述
        # 需要 LLM Brain 支持 vision 能力
        
        return "屏幕描述功能需要多模态 LLM 支持"
    
    def find_on_screen(
        self,
        image_path: str,
        confidence: float = 0.9
    ) -> Optional[Tuple[int, int]]:
        """
        在屏幕上查找图像
        
        Args:
            image_path: 要查找的图像路径
            confidence: 置信度阈值
            
        Returns:
            找到的位置 (x, y)，未找到返回 None
        """
        if not SCREENSHOT_AVAILABLE:
            return None
        
        try:
            location = pyautogui.locateOnScreen(image_path, confidence=confidence)
            if location:
                center = pyautogui.center(location)
                return (center.x, center.y)
            return None
        except Exception as e:
            log.error(f"图像查找失败: {e}")
            return None
