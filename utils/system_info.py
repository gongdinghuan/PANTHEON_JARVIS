"""
JARVIS 系统信息检测模块
自动检测运行环境信息

Author: gngdingghuan
"""

import platform
import os
import sys
from datetime import datetime
from typing import Dict, Any
from utils.logger import log


class SystemInfo:
    """系统信息检测器"""
    
    def __init__(self):
        """初始化并检测系统信息"""
        self._info = self._detect_all()
        log.info(f"系统检测完成: {self._info['platform']} {self._info['arch']}")
    
    def _detect_all(self) -> Dict[str, Any]:
        """检测所有系统信息"""
        info = {
            "platform": self._get_platform(),
            "os": self._get_os_info(),
            "arch": self._get_arch(),
            "python": self._get_python_info(),
            "hostname": self._get_hostname(),
            "user": self._get_user(),
            "is_admin": self._is_admin(),
            "timezone": self._get_timezone(),
        }
        return info
    
    def _get_platform(self) -> str:
        """获取操作系统平台"""
        system = platform.system()
        if system == "Windows":
            return "Windows"
        elif system == "Darwin":
            return "macOS"
        elif system == "Linux":
            return "Linux"
        else:
            return system
    
    def _get_os_info(self) -> str:
        """获取详细操作系统信息"""
        system = platform.system()
        
        if system == "Windows":
            version = platform.win32_ver()
            return f"Windows {version[0]} (Build {version[2]})"
        elif system == "Darwin":
            version = platform.mac_ver()
            return f"macOS {version[0]}"
        elif system == "Linux":
            try:
                with open("/etc/os-release", "r") as f:
                    content = f.read()
                    for line in content.split("\n"):
                        if line.startswith("PRETTY_NAME="):
                            return line.split("=")[1].strip('"')
            except:
                return platform.platform()
        return platform.platform()
    
    def _get_arch(self) -> str:
        """获取系统架构"""
        machine = platform.machine()
        if machine == "AMD64":
            return "x86_64"
        elif machine in ["ARM64", "aarch64"]:
            return "ARM64"
        elif machine in ["armv7l", "armv6l"]:
            return "ARM"
        return machine
    
    def _get_python_info(self) -> str:
        """获取Python版本信息"""
        return f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    
    def _get_hostname(self) -> str:
        """获取主机名"""
        return platform.node()
    
    def _get_user(self) -> str:
        """获取当前用户名"""
        try:
            if platform.system() == "Windows":
                return os.environ.get("USERNAME", "unknown")
            else:
                return os.environ.get("USER", "unknown")
        except:
            return "unknown"
    
    def _is_admin(self) -> bool:
        """检测是否具有管理员权限"""
        try:
            if platform.system() == "Windows":
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin() != 0
            else:
                return os.geteuid() == 0
        except:
            return False
    
    def _get_timezone(self) -> str:
        """获取时区信息"""
        try:
            import time
            return time.tzname[time.daylight]
        except:
            return "Unknown"
    
    def get_all_info(self) -> Dict[str, Any]:
        """获取所有系统信息"""
        return self._info.copy()
    
    def get_prompt_info(self) -> str:
        """获取用于系统提示词的系统信息"""
        return (
            f"操作系统: {self._info['os']}\n"
            f"平台: {self._info['platform']}\n"
            f"架构: {self._info['arch']}\n"
            f"Python: {self._info['python']}\n"
            f"主机名: {self._info['hostname']}\n"
            f"用户: {self._info['user']}\n"
            f"管理员权限: {'是' if self._info['is_admin'] else '否'}\n"
            f"时区: {self._info['timezone']}"
        )
    
    def __repr__(self) -> str:
        return f"SystemInfo(platform={self._info['platform']}, arch={self._info['arch']})"
