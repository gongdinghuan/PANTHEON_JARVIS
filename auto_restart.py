"""
JARVIS 自动重启启动器
监控文件变化，自动重启服务

Author: gngdingghuan
"""

import os
import sys
import time
import subprocess
from pathlib import Path
from typing import Set, Optional
from datetime import datetime

# 监控的文件扩展名
WATCH_EXTENSIONS = {".py", ".json", ".yaml", ".yml", ".env"}

# 忽略的目录
IGNORE_DIRS = {"__pycache__", ".git", "venv", "env", ".venv", "node_modules", "chroma_db", "data"}

# 忽略的文件
IGNORE_FILES = {"*.pyc", "*.pyo", "*.log"}


def get_file_mtime(path: Path) -> float:
    """获取文件修改时间"""
    try:
        return path.stat().st_mtime
    except:
        return 0


def scan_files(root: Path) -> dict:
    """扫描所有监控的文件"""
    files = {}
    for ext in WATCH_EXTENSIONS:
        for file_path in root.rglob(f"*{ext}"):
            # 检查是否在忽略目录中
            should_ignore = False
            for ignore_dir in IGNORE_DIRS:
                if ignore_dir in file_path.parts:
                    should_ignore = True
                    break
            
            if not should_ignore:
                files[str(file_path)] = get_file_mtime(file_path)
    
    return files


def detect_changes(old_files: dict, new_files: dict) -> Set[str]:
    """检测文件变化"""
    changed = set()
    
    # 检查新增或修改的文件
    for path, mtime in new_files.items():
        if path not in old_files:
            changed.add(f"新增: {path}")
        elif old_files[path] != mtime:
            changed.add(f"修改: {path}")
    
    # 检查删除的文件
    for path in old_files:
        if path not in new_files:
            changed.add(f"删除: {path}")
    
    return changed


def print_banner():
    """打印启动横幅"""
    print("\n" + "=" * 60)
    print("  🔄 JARVIS 自动重启模式")
    print("  监控文件变化，自动重启服务")
    print("  按 Ctrl+C 停止")
    print("=" * 60 + "\n")


def main():
    """主函数"""
    print_banner()
    
    root_dir = Path(__file__).parent
    python_exe = sys.executable
    main_script = root_dir / "main.py"
    
    # 初始扫描
    file_cache = scan_files(root_dir)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 监控 {len(file_cache)} 个文件")
    
    # 启动服务
    process: Optional[subprocess.Popen] = None
    
    def start_server():
        nonlocal process
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🚀 启动 JARVIS...")
        process = subprocess.Popen(
            [python_exe, str(main_script), "--web"],
            cwd=str(root_dir),
            stdout=None,  # 继承父进程的标准输出
            stderr=None,
        )
        return process
    
    def stop_server():
        nonlocal process
        if process and process.poll() is None:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🛑 停止 JARVIS...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            process = None
    
    def restart_server():
        stop_server()
        time.sleep(1)  # 等待端口释放
        start_server()
    
    # 首次启动
    start_server()
    
    try:
        check_interval = 2  # 检查间隔（秒）
        
        while True:
            time.sleep(check_interval)
            
            # 检查进程是否意外退出
            if process and process.poll() is not None:
                exit_code = process.returncode
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ⚠️ 服务意外退出 (代码: {exit_code})，3秒后重启...")
                time.sleep(3)
                start_server()
                continue
            
            # 扫描文件变化
            new_cache = scan_files(root_dir)
            changes = detect_changes(file_cache, new_cache)
            
            if changes:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 📁 检测到文件变化:")
                for change in list(changes)[:5]:  # 最多显示5个
                    print(f"   - {change}")
                if len(changes) > 5:
                    print(f"   ... 还有 {len(changes) - 5} 个变化")
                
                file_cache = new_cache
                restart_server()
            
    except KeyboardInterrupt:
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 👋 收到停止信号...")
        stop_server()
        print("JARVIS 自动重启模式已退出")
        sys.exit(0)


if __name__ == "__main__":
    main()
