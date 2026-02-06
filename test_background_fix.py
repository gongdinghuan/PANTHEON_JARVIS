
import asyncio
import sys
import os
import functools
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from cognitive.task_manager import TaskManager
from skills.background_task import BackgroundTaskSkill
from utils.logger import log

async def test_fixes():
    print("=== Testing Background Task Fixes ===")
    
    # 1. Initialize logic
    task_manager = TaskManager()
    skill = BackgroundTaskSkill()
    
    # 2. Simulate the args that caused issues
    # "message" was the unexpected kwarg
    # "name" caused collision before partial fix
    arguments = {
        "action": "long_running_task",
        "duration": 2, 
        "name": "Test Task",
        "message": "This caused an error before" 
    }
    
    print(f"Submitting task with args: {arguments}")
    
    # 3. Mimic Planner's new submission logic (using partial)
    func_to_run = functools.partial(skill.execute, **arguments)
    
    task_id = await task_manager.submit_task(
        name="test_background_task",
        func=func_to_run,
        is_background=True,
        user_id="test_user"
    )
    
    print(f"Task submitted: {task_id}. Waiting for completion...")
    
    # 4. Wait for result
    try:
        result = await task_manager.wait_for_task(task_id, timeout=10)
        print("\n✅ Task Completed!")
        print(f"Result: {result}")
        
        if result.success:
             print("✅ Success flag is True")
        else:
             print(f"❌ Task failed with error: {result.error}")
             
    except Exception as e:
        print(f"\n❌ Exception during wait: {e}")

if __name__ == "__main__":
    # Configure basic logging to complete the loop
    import logging
    logging.basicConfig(level=logging.INFO)
    
    asyncio.run(test_fixes())
