"""
简单测试时间点定时任务功能
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from cognitive.heartbeat import HeartbeatEngine
from skills.scheduler import SchedulerSkill
from datetime import datetime, timedelta


async def test_simple():
    """简单测试"""
    print("=" * 60)
    print("简单测试时间点调度")
    print("=" * 60)
    
    # 1. 创建心跳引擎（30秒间隔）
    print("\n1. 创建心跳引擎（30秒间隔）...")
    heartbeat = HeartbeatEngine(interval=30, log_heartbeat=True)
    
    # 2. 创建调度器
    print("2. 创建调度器...")
    scheduler = SchedulerSkill(heartbeat_engine=heartbeat)
    
    # 3. 启动心跳
    print("3. 启动心跳引擎...")
    heartbeat.start()
    
    # 4. 创建一个时间点任务（30秒后执行）
    print("\n4. 创建时间点任务（30秒后执行）...")
    test_time = datetime.now() + timedelta(seconds=30)
    time_str = test_time.strftime("%H:%M")
    
    print(f"   设置任务在 {time_str} 执行（约30秒后）")
    
    result = await scheduler.execute(
        action="create_task",
        name="快速测试任务",
        command="echo '任务执行成功！'",
        schedule_type="timepoint",
        time_str=time_str,
        enabled=True
    )
    
    if result.success:
        print(f"   ✓ 任务创建成功: {result.output.get('task_id')}")
    else:
        print(f"   ✗ 任务创建失败: {result.error}")
        return
    
    # 5. 启动调度器
    print("\n5. 启动调度器...")
    result = await scheduler.execute(action="start_scheduler")
    print(f"   {result.output.get('message')}")
    
    # 6. 查看事件
    print("\n6. 已注册的时间点事件:")
    events = heartbeat.get_registered_events()
    for event in events.get('timepoint_events', []):
        print(f"   - {event.get('name')}: {event.get('time')}")
    
    # 7. 等待执行
    print("\n7. 等待任务执行（35秒）...")
    try:
        await asyncio.sleep(35)
        
        print("\n8. 检查执行情况:")
        result = await scheduler.execute(action="list_tasks", show_all=True)
        if result.success:
            tasks = result.output.get('tasks', [])
            for task in tasks:
                if task.get('name') == '快速测试任务':
                    last_run = task.get('last_run', 'N/A')
                    if last_run != 'N/A':
                        print(f"   ✓ 任务已执行！最后执行: {last_run}")
                    else:
                        print(f"   ✗ 任务尚未执行")
    
    except KeyboardInterrupt:
        print("\n\n用户中断")
    
    # 9. 清理
    print("\n9. 清理...")
    await scheduler.execute(action="stop_scheduler")
    await heartbeat.stop()
    print("   ✓ 测试完成")


if __name__ == "__main__":
    asyncio.run(test_simple())
