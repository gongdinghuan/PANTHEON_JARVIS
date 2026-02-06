
import sys
import os
import inspect

sys.path.append(os.getcwd())

import skills.background_task
from skills.background_task import BackgroundTaskSkill

print(f"Module file: {skills.background_task.__file__}")

source = inspect.getsource(BackgroundTaskSkill._long_running_task)
print("Source of _long_running_task:")
print(source)

if "import asyncio" in source:
    print("✅ 'import asyncio' found in source")
else:
    print("❌ 'import asyncio' NOT found in source")
