import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from cognitive.heartbeat import HeartbeatEngine


async def test_heartbeat():
    """测试心跳引擎"""
    print("=== 测试心跳引擎 ===\n")
    
    # 创建心跳引擎
    heartbeat = HeartbeatEngine(interval=10, log_heartbeat=True)
    
    # 启动心跳
    print("1. 启动心跳...")
    heartbeat.start()
    
    # 等待一下看心跳
    print("2. 等待心跳（15秒）...\n")
    await asyncio.sleep(15)
    
    # 获取当前时间
    print("\n3. 当前时间信息:")
    current_time = heartbeat.get_current_time()
    for key, value in current_time.items():
        print(f"   {key}: {value}")
    
    # 获取问候
    print(f"\n4. 问候语: {heartbeat.get_greeting()}")
    
    # 记录一些活动
    print("\n5. 模拟用户活动...")
    for i in range(3):
        heartbeat.record_activity()
        await asyncio.sleep(1)
    
    # 获取会话统计
    print("\n6. 会话统计:")
    stats = heartbeat.get_session_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # 心跳状态
    print("\n7. 心跳状态:")
    status = heartbeat.get_heartbeat_status()
    print(status)
    
    # 停止心跳
    print("\n8. 停止心跳...")
    await heartbeat.stop()
    print("✓ 测试完成")


if __name__ == "__main__":
    asyncio.run(test_heartbeat())
