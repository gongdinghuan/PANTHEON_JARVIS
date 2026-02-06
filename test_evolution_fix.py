
import asyncio
import sys
import os
from unittest.mock import MagicMock
from dataclasses import dataclass

sys.path.append(os.getcwd())

from cognitive.self_evolution import SelfEvolutionEngine
from cognitive.memory import MemoryManager

def test_evolution_fix():
    print("=== Testing Evolution Filter Fix ===")
    
    memory = MemoryManager()
    memory._collection = MagicMock()
    
    evolution = SelfEvolutionEngine(memory)
    
    # Test Case 1: With task_type
    print("\nCase 1: search(..., task_type='coding')")
    evolution.search_similar_experience("test", task_type="coding")
    
    call_args = memory._collection.query.call_args
    where_arg = call_args[1].get("where")
    
    print(f"Where Clause: {where_arg}")
    
    # Expected: {"$and": [{"type": "experience"}, {"success": "True"}, {"task_type": "coding"}]}
    # Order inside list might vary but structure matters
    if "$and" in where_arg and len(where_arg["$and"]) == 3:
        print("✅ Correct usage of $and operator")
    else:
        print("❌ Incorrect structure")
        
    # Test Case 2: Without task_type
    print("\nCase 2: search(..., task_type=None)")
    evolution.search_similar_experience("test", task_type=None)
    
    call_args = memory._collection.query.call_args
    where_arg = call_args[1].get("where")
    print(f"Where Clause: {where_arg}")
    
    if "$and" in where_arg and len(where_arg["$and"]) == 2:
         print("✅ Correct usage of $and operator with 2 args")
    else:
         print("❌ Incorrect structure")

if __name__ == "__main__":
    test_evolution_fix()
