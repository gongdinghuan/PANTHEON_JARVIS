"""
JARVIS 技能单元测试

Author: gngdingghuan
"""

import asyncio
import pytest
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestSystemControlSkill:
    """系统控制技能测试"""
    
    @pytest.fixture
    def skill(self):
        from skills.system_control import SystemControlSkill
        return SystemControlSkill()
    
    @pytest.mark.asyncio
    async def test_get_running_apps(self, skill):
        """测试获取运行中应用"""
        result = await skill.execute(action="get_running_apps")
        assert result.success
        assert isinstance(result.output, list)
    
    @pytest.mark.asyncio
    async def test_screenshot(self, skill):
        """测试截图"""
        import tempfile
        filepath = str(Path(tempfile.gettempdir()) / "test_screenshot.png")
        result = await skill.execute(action="screenshot", filepath=filepath)
        
        if result.success:
            assert Path(filepath).exists()
            Path(filepath).unlink()  # 清理
    
    def test_get_schema(self, skill):
        """测试获取 Schema"""
        schema = skill.get_schema()
        assert schema["type"] == "function"
        assert "system_control" in schema["function"]["name"]


class TestFileManagerSkill:
    """文件管理技能测试"""
    
    @pytest.fixture
    def skill(self):
        from skills.file_manager import FileManagerSkill
        return FileManagerSkill()
    
    @pytest.mark.asyncio
    async def test_list_directory(self, skill):
        """测试列出目录"""
        result = await skill.execute(
            action="list_directory",
            path=str(Path.home() / "Desktop")
        )
        assert result.success
        assert isinstance(result.output, list)
    
    @pytest.mark.asyncio
    async def test_create_read_delete_file(self, skill):
        """测试创建、读取、删除文件"""
        import tempfile
        test_file = str(Path(tempfile.gettempdir()) / "jarvis_test.txt")
        test_content = "Hello, JARVIS!"
        
        # 创建文件
        result = await skill.execute(
            action="write_file",
            path=test_file,
            content=test_content
        )
        assert result.success
        
        # 读取文件
        result = await skill.execute(
            action="read_file",
            path=test_file
        )
        assert result.success
        assert result.output == test_content
        
        # 删除文件
        Path(test_file).unlink()
    
    @pytest.mark.asyncio
    async def test_file_info(self, skill):
        """测试获取文件信息"""
        result = await skill.execute(
            action="file_info",
            path=str(Path.home())
        )
        assert result.success
        assert "name" in result.output
        assert "type" in result.output
    
    @pytest.mark.asyncio
    async def test_forbidden_path(self, skill):
        """测试禁止的路径"""
        result = await skill.execute(
            action="read_file",
            path="C:\\Windows\\System32\\config"
        )
        assert not result.success
        assert "拒绝" in result.error


class TestWebBrowserSkill:
    """网页浏览技能测试"""
    
    @pytest.fixture
    def skill(self):
        from skills.web_browser import WebBrowserSkill
        return WebBrowserSkill()
    
    @pytest.mark.asyncio
    async def test_search(self, skill):
        """测试搜索"""
        result = await skill.execute(
            action="search",
            query="Python programming",
            max_results=3
        )
        
        # 搜索可能因网络问题失败
        if result.success:
            assert "results" in result.output
    
    @pytest.mark.asyncio
    async def test_read_webpage(self, skill):
        """测试读取网页"""
        result = await skill.execute(
            action="read_webpage",
            url="https://example.com"
        )
        
        if result.success:
            assert "content" in result.output


class TestTerminalSkill:
    """终端技能测试"""
    
    @pytest.fixture
    def skill(self):
        from skills.terminal import TerminalSkill
        return TerminalSkill()
    
    @pytest.mark.asyncio
    async def test_safe_command(self, skill):
        """测试安全命令"""
        # Windows 用 dir，其他用 ls
        import platform
        cmd = "dir" if platform.system() == "Windows" else "ls"
        
        result = await skill.execute(
            action="run_safe_command",
            command=cmd
        )
        assert result.success
    
    @pytest.mark.asyncio
    async def test_forbidden_command(self, skill):
        """测试禁止的命令"""
        result = await skill.execute(
            action="run_command",
            command="rm -rf /"
        )
        assert not result.success


class TestMemoryManager:
    """记忆管理器测试"""
    
    @pytest.fixture
    def memory(self):
        from cognitive.memory import MemoryManager
        return MemoryManager()
    
    def test_add_and_get_messages(self, memory):
        """测试添加和获取消息"""
        memory.add_message("user", "Hello")
        memory.add_message("assistant", "Hi there!")
        
        context = memory.get_recent_context()
        assert len(context) == 2
        assert context[0]["role"] == "user"
        assert context[1]["role"] == "assistant"
    
    def test_get_stats(self, memory):
        """测试获取统计信息"""
        stats = memory.get_stats()
        assert "short_term_count" in stats
        assert "long_term_count" in stats


class TestContextManager:
    """上下文管理器测试"""
    
    @pytest.fixture
    def context(self):
        from cognitive.context_manager import ContextManager
        return ContextManager()
    
    def test_system_state(self, context):
        """测试系统状态"""
        state = context.get_system_state()
        assert "cpu_percent" in state
        assert "memory_percent" in state
    
    def test_task_context(self, context):
        """测试任务上下文"""
        context.set_current_task("Test task")
        assert context.get_current_task() == "Test task"
        
        context.set_variable("key", "value")
        assert context.get_variable("key") == "value"
        
        context.clear_current_task()
        assert context.get_current_task() is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
