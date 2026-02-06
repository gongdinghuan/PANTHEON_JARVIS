
import asyncio
import sys
import os
import functools
import time

# Add project root to path
sys.path.append(os.getcwd())

from cognitive.task_manager import TaskManager
from skills.background_task import BackgroundTaskSkill
from utils.logger import log, setup_logger

# Setup logging
setup_logger()

async def test_sync_execution():
    print("=== Testing Synchronous Background Task ===")
    
    # 1. Initialize
    task_manager = TaskManager()
    skill = BackgroundTaskSkill()
    
    # 2. Prepare arguments
    arguments = {
        "action": "long_running_task",
        "duration": 2, 
        "name": "Sync Test Task",
        "message": "Extra argument" 
    }
    
    # 3. Simulate correct submission via Planner (using partial)
    # Note: skill.execute is ASYNC, but internally calls SYNC method
    # task_manager should handle the async wrapper, run it in new loop, 
    # and the sync internal call should block that new loop (which is fine, it's a thread)
    func_to_run = functools.partial(skill.execute, **arguments)
    
    print("Submitting task...")
    task_id = await task_manager.submit_task(
        name="sync_test_task",
        func=func_to_run,
        is_background=True,
        user_id="test_user"
    )
    
    print(f"Task submitted: {task_id}")
    
    # 4. Wait for result
    try:
        # Wait up to 5 seconds
        result = await task_manager.wait_for_task(task_id, timeout=5)
        print("\n✅ Task Completed!")
        print(f"Result: {result}")
        
    except Exception as e:
        print(f"\n❌ Task execution failed: {e}")
        # Print status
        status = task_manager.get_task_status(task_id)
        print(f"Final Status: {status}")

if __name__ == "__main__":
    asyncio.run(test_sync_execution())
