"""
简化的自我进化功能测试（不依赖 ChromaDB）

Author: gngdingghuan
"""

import asyncio
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent))

from cognitive.memory import MemoryManager
from cognitive.self_evolution import SelfEvolutionEngine


class MockMemory:
    """模拟记忆系统（不使用 ChromaDB）"""
    
    def __init__(self):
        self._collection = None
    
    def _init_chromadb(self):
        """不初始化 ChromaDB"""
        pass
    
    def get_stats(self):
        return {
            'short_term_count': 0,
            'long_term_count': 0
        }


async def test_experience_recording():
    """测试经验记录"""
    print("=== 测试经验记录 ===\n")
    
    mock_memory = MockMemory()
    engine = SelfEvolutionEngine(mock_memory)
    
    # 模拟一些经验
    experiences = [
        {
            "task_type": "文件管理",
            "user_input": "创建一个名为test.txt的文件",
            "response": "已成功创建文件 test.txt",
            "tools_used": ["file_manager"],
            "success": True,
            "execution_time": 1.2
        },
        {
            "task_type": "文件管理",
            "user_input": "打开记事本",
            "response": "已打开应用: notepad",
            "tools_used": ["system_control"],
            "success": True,
            "execution_time": 0.8
        },
        {
            "task_type": "网络浏览",
            "user_input": "搜索Python教程",
            "response": "为您找到以下Python教程...",
            "tools_used": ["web_browser"],
            "success": True,
            "execution_time": 2.5
        },
        {
            "task_type": "文件管理",
            "user_input": "删除不存在的文件",
            "response": "文件不存在，无法删除",
            "tools_used": ["file_manager"],
            "success": False,
            "execution_time": 0.5
        },
        {
            "task_type": "系统控制",
            "user_input": "调大音量",
            "response": "已将音量调高 10%",
            "tools_used": ["system_control"],
            "success": True,
            "execution_time": 0.6,
            "user_feedback": "好"
        },
    ]
    
    for exp in experiences:
        engine.record_experience(**exp)
        print(f"✓ 已记录: {exp['task_type']} - {exp['user_input'][:30]}")
    
    print()


async def test_prediction():
    """测试预测功能"""
    print("=== 测试预测功能 ===\n")
    
    mock_memory = MockMemory()
    engine = SelfEvolutionEngine(mock_memory)
    
    # 先记录一些经验
    for i in range(5):
        engine.record_experience(
            task_type="文件管理",
            user_input=f"创建文件{i}.txt",
            response="已创建",
            tools_used=["file_manager"],
            success=True
        )
    
    engine.record_experience(
        task_type="网络浏览",
        user_input="搜索新闻",
        response="找到结果",
        tools_used=["web_browser"],
        success=True
    )
    
    # 测试预测
    test_inputs = [
        "创建一个新文件",
        "搜索Python教程",
        "打开浏览器"
    ]
    
    for test_input in test_inputs:
        prediction = engine.predict_next_action(test_input)
        
        if prediction:
            print(f"输入: {test_input}")
            print(f"  预测任务: {prediction['task_type']}")
            print(f"  置信度: {prediction['confidence']:.1%}")
            print(f"  建议工具: {', '.join(prediction['suggested_tools'])}")
        else:
            print(f"输入: {test_input}")
            print(f"  无法预测（数据不足）")
        print()


async def test_preferences():
    """测试偏好学习"""
    print("=== 测试偏好学习 ===\n")
    
    mock_memory = MockMemory()
    engine = SelfEvolutionEngine(mock_memory)
    
    # 模拟用户偏好
    for i in range(5):
        engine.record_experience(
            task_type="文件管理",
            user_input="创建文件",
            response="已创建",
            tools_used=["file_manager"],
            success=True
        )
    
    engine.record_experience(
        task_type="文件管理",
        user_input="创建文件",
        response="已创建",
        tools_used=["file_manager"],
        success=True,
        user_feedback="很好"
    )
    
    # 获取统计
    stats = engine.get_evolution_stats()
    
    print(f"学习偏好数: {stats['preferences_learned']}")
    print(f"识别模式数: {stats['patterns_identified']}")
    print(f"总经验数: {stats['total_experiences']}")
    
    if stats['top_preferences'].get('tool'):
        print("\n工具偏好:")
        for pref in stats['top_preferences']['tool']:
            print(f"  - {pref.key} (置信度: {pref.confidence:.2f})")
    
    print()


async def test_optimization():
    """测试优化建议"""
    print("=== 测试优化建议 ===\n")
    
    mock_memory = MockMemory()
    engine = SelfEvolutionEngine(mock_memory)
    
    # 记录一些经验
    for i in range(10):
        engine.record_experience(
            task_type="测试",
            user_input=f"测试输入{i}",
            response="测试响应",
            tools_used=["test_tool"],
            success=True if i < 7 else False,
            execution_time=3.0 + (i * 0.2)
        )
    
    # 获取优化建议
    suggestions = engine.get_optimization_suggestions()
    
    print("优化建议:")
    for i, suggestion in enumerate(suggestions, 1):
        print(f"{i}. {suggestion}")
    
    print()


async def test_knowledge_export():
    """测试知识导出"""
    print("=== 测试知识导出 ===\n")
    
    mock_memory = MockMemory()
    engine = SelfEvolutionEngine(mock_memory)
    
    # 记录一些经验
    engine.record_experience(
        task_type="文件管理",
        user_input="创建文件",
        response="已创建",
        tools_used=["file_manager"],
        success=True
    )
    
    # 导出知识
    knowledge = engine.export_knowledge()
    
    print("导出的知识:")
    print(f"  偏好类型: {len(knowledge['preferences'])}")
    print(f"  模式类型: {len(knowledge['patterns'])}")
    print(f"  知识库: {len(knowledge['knowledge_base'])}")
    print(f"  导出时间: {knowledge['export_time']}")
    
    print()


async def main():
    """主函数"""
    print("JARVIS 自我进化功能测试\n")
    print("=" * 50)
    print()
    
    await test_experience_recording()
    await test_prediction()
    await test_preferences()
    await test_optimization()
    await test_knowledge_export()
    
    print("=" * 50)
    print("\n所有测试完成！")
    print("\n功能总结:")
    print("  ✓ 经验记录和学习")
    print("  ✓ 用户偏好识别")
    print("  ✓ 任务预测")
    print("  ✓ 模式识别")
    print("  ✓ 知识积累")
    print("  ✓ 优化建议生成")
    print("  ✓ 知识导出")


if __name__ == "__main__":
    asyncio.run(main())
