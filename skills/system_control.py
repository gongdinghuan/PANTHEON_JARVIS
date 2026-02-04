"""
JARVIS 系统控制技能
打开应用、调节音量、键鼠控制等

Author: gngdingghuan
"""

import os
import subprocess
from typing import Dict, Any, Optional, List

import psutil
import pyautogui

from skills.base_skill import BaseSkill, SkillResult, PermissionLevel, create_tool_schema
from utils.logger import log
from utils.platform_utils import is_windows, is_macos, open_file_with_default_app, open_url_in_browser


# 禁用 pyautogui 的安全暂停（可选）
pyautogui.PAUSE = 0.1


class SystemControlSkill(BaseSkill):
    """系统控制技能集合"""
    
    name = "system_control"
    description = "系统控制：打开应用、调节音量、键鼠操作"
    permission_level = PermissionLevel.SAFE_WRITE
    
    # Windows 常用应用映射
    WINDOWS_APPS = {
        "记事本": "notepad.exe",
        "notepad": "notepad.exe",
        "计算器": "calc.exe",
        "calculator": "calc.exe",
        "画图": "mspaint.exe",
        "paint": "mspaint.exe",
        "资源管理器": "explorer.exe",
        "explorer": "explorer.exe",
        "cmd": "cmd.exe",
        "命令提示符": "cmd.exe",
        "powershell": "powershell.exe",
        "浏览器": "msedge.exe",
        "edge": "msedge.exe",
        "chrome": "chrome.exe",
        "vscode": "code",
        "code": "code",
    }
    
    # macOS 常用应用映射
    MACOS_APPS = {
        "finder": "Finder",
        "safari": "Safari",
        "chrome": "Google Chrome",
        "terminal": "Terminal",
        "终端": "Terminal",
        "备忘录": "Notes",
        "notes": "Notes",
        "vscode": "Visual Studio Code",
        "code": "Visual Studio Code",
    }
    
    async def execute(self, action: str, **params) -> SkillResult:
        """
        执行系统控制操作
        
        Args:
            action: 操作类型
            **params: 操作参数
        """
        actions = {
            "open_application": self._open_application,
            "close_application": self._close_application,
            "get_running_apps": self._get_running_apps,
            "set_volume": self._set_volume,
            "type_text": self._type_text,
            "press_key": self._press_key,
            "click": self._click,
            "screenshot": self._screenshot,
            "open_url": self._open_url,
        }
        
        if action not in actions:
            return SkillResult(
                success=False,
                output=None,
                error=f"未知的操作: {action}"
            )
        
        try:
            result = await actions[action](**params)
            return result
        except Exception as e:
            log.error(f"系统控制操作失败: {action}, 错误: {e}")
            return SkillResult(success=False, output=None, error=str(e))
    
    async def _open_application(self, app_name: str) -> SkillResult:
        """打开应用程序"""
        log.info(f"打开应用: {app_name}")
        
        app_lower = app_name.lower()
        
        try:
            if is_windows():
                # 检查映射表
                exe_name = self.WINDOWS_APPS.get(app_lower, app_name)
                subprocess.Popen(exe_name, shell=True)
                
            elif is_macos():
                # macOS 使用 open 命令
                mac_app = self.MACOS_APPS.get(app_lower, app_name)
                subprocess.Popen(["open", "-a", mac_app])
            
            else:
                # Linux
                subprocess.Popen([app_name], shell=True)
            
            return SkillResult(
                success=True,
                output=f"已打开应用: {app_name}"
            )
            
        except Exception as e:
            return SkillResult(
                success=False,
                output=None,
                error=f"无法打开应用 {app_name}: {e}"
            )
    
    async def _close_application(self, app_name: str) -> SkillResult:
        """关闭应用程序"""
        log.info(f"关闭应用: {app_name}")
        
        closed = False
        for proc in psutil.process_iter(['name', 'pid']):
            try:
                if app_name.lower() in proc.info['name'].lower():
                    proc.terminate()
                    closed = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        if closed:
            return SkillResult(success=True, output=f"已关闭应用: {app_name}")
        else:
            return SkillResult(success=False, output=None, error=f"未找到应用: {app_name}")
    
    async def _get_running_apps(self) -> SkillResult:
        """获取运行中的应用列表"""
        apps = set()
        for proc in psutil.process_iter(['name']):
            try:
                name = proc.info['name']
                if name and not name.startswith('_'):
                    apps.add(name)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # 过滤系统进程，只保留常见应用
        common_apps = sorted([a for a in apps if not a.startswith('svchost')])[:30]
        
        return SkillResult(
            success=True,
            output=common_apps
        )
    
    async def _set_volume(self, level: int) -> SkillResult:
        """设置系统音量 (0-100)"""
        level = max(0, min(100, level))
        
        try:
            if is_windows():
                # 使用 nircmd 或 PowerShell 设置音量
                # 这里使用 pyautogui 的按键方式作为后备
                from ctypes import cast, POINTER
                from comtypes import CLSCTX_ALL
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = cast(interface, POINTER(IAudioEndpointVolume))
                volume.SetMasterVolumeLevelScalar(level / 100, None)
                
            elif is_macos():
                subprocess.run(
                    ["osascript", "-e", f"set volume output volume {level}"],
                    check=True
                )
            
            return SkillResult(success=True, output=f"音量已设置为 {level}%")
            
        except ImportError:
            # pycaw 未安装，使用简单方式
            return SkillResult(
                success=False,
                output=None,
                error="音量控制需要安装 pycaw 库"
            )
        except Exception as e:
            return SkillResult(success=False, output=None, error=str(e))
    
    async def _type_text(self, text: str, interval: float = 0.02) -> SkillResult:
        """输入文字"""
        try:
            pyautogui.typewrite(text, interval=interval) if text.isascii() else pyautogui.write(text)
            return SkillResult(success=True, output=f"已输入文字: {text[:50]}...")
        except Exception as e:
            return SkillResult(success=False, output=None, error=str(e))
    
    async def _press_key(self, key: str) -> SkillResult:
        """按下按键"""
        try:
            if '+' in key:
                # 组合键
                keys = key.split('+')
                pyautogui.hotkey(*keys)
            else:
                pyautogui.press(key)
            return SkillResult(success=True, output=f"已按下: {key}")
        except Exception as e:
            return SkillResult(success=False, output=None, error=str(e))
    
    async def _click(self, x: int, y: int, button: str = "left") -> SkillResult:
        """点击指定位置"""
        try:
            pyautogui.click(x, y, button=button)
            return SkillResult(success=True, output=f"已点击: ({x}, {y})")
        except Exception as e:
            return SkillResult(success=False, output=None, error=str(e))
    
    async def _screenshot(self, filepath: Optional[str] = None) -> SkillResult:
        """截取屏幕"""
        try:
            if filepath is None:
                from datetime import datetime
                from pathlib import Path
                filepath = str(Path.home() / "Desktop" / f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            
            screenshot = pyautogui.screenshot()
            screenshot.save(filepath)
            
            return SkillResult(success=True, output=f"截图已保存: {filepath}")
        except Exception as e:
            return SkillResult(success=False, output=None, error=str(e))
    
    async def _open_url(self, url: str) -> SkillResult:
        """在浏览器中打开 URL"""
        try:
            success = open_url_in_browser(url)
            if success:
                return SkillResult(success=True, output=f"已打开: {url}")
            else:
                return SkillResult(success=False, output=None, error="无法打开浏览器")
        except Exception as e:
            return SkillResult(success=False, output=None, error=str(e))
    
    def get_schema(self) -> Dict[str, Any]:
        """获取 Function Calling Schema"""
        return create_tool_schema(
            name="system_control",
            description="系统控制操作：打开/关闭应用、调节音量、键鼠操作、截图等",
            parameters={
                "action": {
                    "type": "string",
                    "enum": [
                        "open_application",
                        "close_application", 
                        "get_running_apps",
                        "set_volume",
                        "type_text",
                        "press_key",
                        "click",
                        "screenshot",
                        "open_url"
                    ],
                    "description": "要执行的操作类型"
                },
                "app_name": {
                    "type": "string",
                    "description": "应用程序名称（用于 open/close_application）"
                },
                "level": {
                    "type": "integer",
                    "description": "音量级别 0-100（用于 set_volume）"
                },
                "text": {
                    "type": "string",
                    "description": "要输入的文字（用于 type_text）"
                },
                "key": {
                    "type": "string",
                    "description": "按键名称，组合键用+连接如 ctrl+c（用于 press_key）"
                },
                "x": {
                    "type": "integer",
                    "description": "点击 X 坐标（用于 click）"
                },
                "y": {
                    "type": "integer",
                    "description": "点击 Y 坐标（用于 click）"
                },
                "url": {
                    "type": "string", 
                    "description": "要打开的 URL（用于 open_url）"
                },
                "filepath": {
                    "type": "string",
                    "description": "保存路径（用于 screenshot）"
                }
            },
            required=["action"]
        )
