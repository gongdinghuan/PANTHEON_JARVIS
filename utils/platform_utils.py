"""
JARVIS 跨平台工具函数
处理 Windows 和 macOS 的差异

Author: gngdingghuan
"""

import os
import sys
import platform
from pathlib import Path
from typing import Optional


def get_platform() -> str:
    """获取当前操作系统"""
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    return system  # windows, linux


def is_windows() -> bool:
    """是否为 Windows 系统"""
    return get_platform() == "windows"


def is_macos() -> bool:
    """是否为 macOS 系统"""
    return get_platform() == "macos"


def is_linux() -> bool:
    """是否为 Linux 系统"""
    return get_platform() == "linux"


def get_home_dir() -> Path:
    """获取用户主目录"""
    return Path.home()


def get_desktop_path() -> Path:
    """获取桌面路径"""
    home = get_home_dir()
    if is_windows():
        return home / "Desktop"
    elif is_macos():
        return home / "Desktop"
    else:
        return home / "Desktop"


def get_documents_path() -> Path:
    """获取文档目录路径"""
    home = get_home_dir()
    if is_windows():
        return home / "Documents"
    elif is_macos():
        return home / "Documents"
    else:
        return home / "Documents"


def get_downloads_path() -> Path:
    """获取下载目录路径"""
    home = get_home_dir()
    if is_windows():
        return home / "Downloads"
    elif is_macos():
        return home / "Downloads"
    else:
        return home / "Downloads"


def get_shell() -> str:
    """获取默认 Shell"""
    if is_windows():
        return "powershell"
    else:
        return os.environ.get("SHELL", "/bin/bash")


def normalize_path(path: str) -> str:
    """标准化路径"""
    return str(Path(path).resolve())


def expand_path(path: str) -> str:
    """展开路径（处理 ~ 等）"""
    return str(Path(path).expanduser().resolve())


def get_app_data_dir() -> Path:
    """获取应用数据目录"""
    if is_windows():
        base = Path(os.environ.get("APPDATA", str(get_home_dir() / "AppData" / "Roaming")))
    elif is_macos():
        base = get_home_dir() / "Library" / "Application Support"
    else:
        base = get_home_dir() / ".config"
    
    jarvis_dir = base / "jarvis"
    jarvis_dir.mkdir(parents=True, exist_ok=True)
    return jarvis_dir


def open_file_with_default_app(filepath: str) -> bool:
    """使用默认应用打开文件"""
    import subprocess
    
    try:
        if is_windows():
            os.startfile(filepath)
        elif is_macos():
            subprocess.run(["open", filepath], check=True)
        else:
            subprocess.run(["xdg-open", filepath], check=True)
        return True
    except Exception:
        return False


def open_url_in_browser(url: str) -> bool:
    """在默认浏览器中打开 URL"""
    import webbrowser
    try:
        webbrowser.open(url)
        return True
    except Exception:
        return False


def get_active_window_title() -> Optional[str]:
    """获取当前活跃窗口标题"""
    try:
        if is_windows():
            import win32gui
            window = win32gui.GetForegroundWindow()
            return win32gui.GetWindowText(window)
        elif is_macos():
            import subprocess
            script = '''
            tell application "System Events"
                set frontApp to name of first application process whose frontmost is true
                tell process frontApp
                    set windowTitle to name of front window
                end tell
            end tell
            return windowTitle
            '''
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True
            )
            return result.stdout.strip()
        else:
            # Linux - 需要 xdotool
            import subprocess
            result = subprocess.run(
                ["xdotool", "getactivewindow", "getwindowname"],
                capture_output=True,
                text=True
            )
            return result.stdout.strip()
    except Exception:
        return None


def get_clipboard_text() -> Optional[str]:
    """获取剪贴板文本"""
    try:
        import pyperclip
        return pyperclip.paste()
    except Exception:
        return None


def set_clipboard_text(text: str) -> bool:
    """设置剪贴板文本"""
    try:
        import pyperclip
        pyperclip.copy(text)
        return True
    except Exception:
        return False
