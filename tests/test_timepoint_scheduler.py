"""
测试时间点定时任务功能
结合心跳引擎和调度器
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from cognitive.heartbeat import HeartbeatEngine
from skills.scheduler import SchedulerSkill
from utils.logger import log


async def test_timepoint_scheduler():
    """测试时间点调度功能"""
    print("=" * 60)
    print("测试时间点定时任务功能")
    print("=" * 60)
    
    # 1. 创建心跳引擎（短间隔用于测试）
    print("\n1. 创建心跳引擎...")
    heartbeat = HeartbeatEngine(interval=10, log_heartbeat=True)
    
    # 2. 创建调度器（连接心跳引擎）
    print("2. 创建调度器...")
    scheduler = SchedulerSkill(heartbeat_engine=heartbeat)
    
    # 3. 启动心跳
    print("3. 启动心跳引擎...")
    heartbeat.start()
    
    # 4. 创建一个时间点任务（设置为2分钟后执行）
    print("\n4. 创建时间点任务...")
    from datetime import datetime, timedelta
    
    # 计算2分钟后的时间
    test_time = datetime.now() + timedelta(minutes=2)
    time_str = test_time.strftime("%H:%M")
    
    print(f"   设置任务在 {time_str} 执行")
    
    result = await scheduler.execute(
        action="create_task",
        name="测试时间点任务",
        command="echo '时间点任务执行成功！'",
        schedule_type="timepoint",
        time_str=time_str,
        enabled=True
    )
    
    if result.success:
        print(f"   ✓ 任务创建成功: {result.output.get('task_id')}")
        print(f"   下次执行: {result.output.get('next_run', 'N/A')}")
    else:
        print(f"   ✗ 任务创建失败: {result.error}")
        return
    
    # 5. 启动调度器
    print("\n5. 启动调度器...")
    result = await scheduler.execute(action="start_scheduler")
    if result.success:
        print(f"   ✓ {result.output.get('message')}")
        print(f"   运行中任务: {result.output.get('running_tasks', 0)}")
    
    # 6. 查看已注册的事件
    print("\n6. 查看心跳引擎中的已注册事件...")
    events = heartbeat.get_registered_events()
    print(f"   小时级事件: {events.get('hourly_events', {})}")
    print(f"   时间点事件: {len(events.get('timepoint_events', []))} 个")
    for event in events.get('timepoint_events', []):
        print(f"     - {event.get('name')}: {event.get('time')}")
    
    # 7. 查看所有任务
    print("\n7. 查看所有定时任务...")
    result = await scheduler.execute(action="list_tasks", show_all=True)
    if result.success:
        tasks = result.output.get('tasks', [])
        print(f"   总任务数: {len(tasks)}")
        for task in tasks:
            print(f"   - {task.get('name')} ({task.get('schedule_type')}) @ {task.get('time', 'N/A')}")
    
    # 8. 等待任务执行（等待2分钟）
    print(f"\n8. 等待任务执行（最多等待130秒）...")
    print("   提示: 如果不想等待，可以按 Ctrl+C 退出")
    
    try:
        # 等待2分钟多一点，确保任务执行
        await asyncio.sleep(130)
        
        # 检查任务是否执行
        print("\n9. 检查任务执行情况...")
        result = await scheduler.execute(action="list_tasks", show_all=True)
        if result.success:
            tasks = result.output.get('tasks', [])
            for task in tasks:
                if task.get('name') == '测试时间点任务':
                    last_run = task.get('last_run', 'N/A')
                    print(f"   任务最后执行时间: {last_run}")
                    if last_run != 'N/A':
                        print(f"   ✓ 任务已成功执行！")
                    else:
                        print(f"   ✗ 任务尚未执行")
    
    except KeyboardInterrupt:
        print("\n\n用户中断，停止测试...")
    
    # 10. 清理
    print("\n10. 清理资源...")
    await scheduler.execute(action="stop_scheduler")
    await heartbeat.stop()
    print("   ✓ 测试完成")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(test_timepoint_scheduler())
