#!/usr/bin/env python
"""测试 JARVIS 初始化"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from main import Jarvis

if __name__ == "__main__":
    print("创建 JARVIS 实例...")
    jarvis = Jarvis()
    print("\n✓ JARVIS 初始化成功！")
    
    print("\n系统信息:")
    print(jarvis.system_info.get_prompt_info())
    
    print("\n时间信息:")
    print(f"启动时间: {jarvis.heartbeat.get_init_time_formatted()}")
    print(f"启动时段: {jarvis.heartbeat.get_init_time_info().get('init_time_info', {}).get('period_cn', '')}")
