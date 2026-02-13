"""
JARVIS IM 适配器包
支持 QQ、微信、Telegram 等即时通讯平台接入
"""

from .base import BaseIMAdapter
from .manager import AdapterManager

__all__ = [
    "BaseIMAdapter",
    "AdapterManager",
]
