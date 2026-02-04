"""测试心跳引擎初始化时的时间感知"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from cognitive.heartbeat import HeartbeatEngine

print("测试心跳引擎初始化时的时间感知\n")
print("=" * 60)

# 创建心跳引擎
heartbeat = HeartbeatEngine(interval=30, log_heartbeat=False)

print("\n1. 初始化时的时间信息:")
init_info = heartbeat.get_init_time_info()
print(f"   启动时间: {init_info.get('init_time_formatted')}")
print(f"   初始化问候: {init_info.get('init_greeting')}")

time_info = init_info.get('init_time_info', {})
print(f"\n2. 详细时间信息:")
print(f"   时间: {time_info.get('time')}")
print(f"   日期: {time_info.get('date')}")
print(f"   星期: {time_info.get('weekday_cn')}")
print(f"   时段: {time_info.get('period_cn')}")
print(f"   小时: {time_info.get('hour')}")
print(f"   分钟: {time_info.get('minute')}")

print(f"\n3. 当前获取的问候语:")
print(f"   {heartbeat.get_init_greeting()}")

print(f"\n4. 会话统计:")
stats = heartbeat.get_session_stats()
print(f"   初始化时间: {stats.get('init_time')}")

print("\n" + "=" * 60)
print("✓ 测试完成")
