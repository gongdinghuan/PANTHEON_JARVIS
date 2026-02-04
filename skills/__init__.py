"""
JARVIS 技能层模块

Author: gngdingghuan
"""

from skills.base_skill import BaseSkill, SkillResult
from skills.system_control import SystemControlSkill
from skills.file_manager import FileManagerSkill
from skills.web_browser import WebBrowserSkill
from skills.terminal import TerminalSkill

__all__ = [
    "BaseSkill",
    "SkillResult",
    "SystemControlSkill",
    "FileManagerSkill",
    "WebBrowserSkill",
    "TerminalSkill",
]
