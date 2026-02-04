"""
JARVIS 智能助手 - 主入口
类似钢铁侠的 J.A.R.V.I.S. AI 助手

Author: gngdingghuan

使用方式:
    python main.py          # 命令行交互模式
    python main.py --voice  # 语音交互模式
"""

import asyncio
import sys
import warnings
from pathlib import Path
from datetime import datetime

# 抑制第三方库的警告
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pygame")
warnings.filterwarnings("ignore", category=UserWarning, module="pygame")

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from config import get_config, LLMProvider
from utils.logger import log
from utils.system_info import SystemInfo
from utils.compat import to_thread
from cognitive.llm_brain import LLMBrain
from cognitive.memory import MemoryManager
from cognitive.context_manager import ContextManager
from cognitive.planner import ReActPlanner
from cognitive.self_healing import SelfHealingEngine
from cognitive.self_evolution import SelfEvolutionEngine
from cognitive.continuous_evolution import ContinuousEvolutionEngine
from cognitive.heartbeat import HeartbeatEngine
from skills.system_control import SystemControlSkill
from skills.file_manager import FileManagerSkill
from skills.web_browser import WebBrowserSkill
from skills.terminal import TerminalSkill
from skills.scheduler import SchedulerSkill
from skills.iot_bridge import IoTBridgeSkill
from skills.background_task import BackgroundTaskSkill
from expression.tts import TTS
from security.confirmation import get_confirmation_handler


console = Console()


class Jarvis:
    """
    JARVIS 主类
    整合所有模块，提供统一的交互接口
    """
    
    def __init__(self):
        self.config = get_config()
        
        # 初始化核心组件
        console.print("[cyan]正在初始化 JARVIS...[/cyan]")
        
        # 系统信息检测
        self.system_info = SystemInfo()
        console.print(f"[dim]  系统检测: {self.system_info.get_prompt_info()}[/dim]")
        
        # 中枢层
        self.brain = LLMBrain()
        self.memory = MemoryManager()
        self.context = ContextManager()
        self.self_healing = SelfHealingEngine(self.memory)
        self.evolution_engine = SelfEvolutionEngine(self.memory)
        
        # 持续进化引擎（后台学习）
        self.continuous_evolution = ContinuousEvolutionEngine(
            evolution_engine=self.evolution_engine,
            memory=self.memory,
            feedback_callback=self._evolution_feedback_callback
        )
        
        # 心跳引擎
        self.heartbeat = HeartbeatEngine(
            interval=self.config.heartbeat.interval,
            log_heartbeat=self.config.heartbeat.log_heartbeat,
            timezone=self.config.heartbeat.timezone
        )
        
        # 显示初始化时间信息
        if self.config.heartbeat.enable_greeting:
            init_time = self.heartbeat.get_init_time_formatted()
            init_period = self.heartbeat.get_init_time_info().get('init_time_info', {}).get('period_cn', '')
            console.print(f"[dim]  启动时间: {init_time} ({init_period})[/dim]")
        
        # 技能层
        self.skills = self._init_skills()
        
        # 规划器（带自我进化）
        self.planner = ReActPlanner(
            brain=self.brain,
            memory=self.memory,
            context=self.context,
            skills=self.skills,
            evolution_engine=self.evolution_engine
        )
        
        # 表达层
        self.tts = TTS()
        
        # 安全层
        self.confirmation_handler = get_confirmation_handler()
        
        # 设置确认回调
        self.planner.set_confirmation_callback(self._handle_confirmation)
        
        # 传递系统信息和时间信息给大脑中枢
        self._inform_brain_system_info()
        
        console.print("[green][OK] JARVIS 初始化完成[/green]")
    
    async def cleanup(self):
        """清理资源"""
        console.print("[dim]正在清理资源...[/dim]")
        
        try:
            # 停止持续进化
            await self.continuous_evolution.stop()
        except Exception as e:
            log.warning(f"停止持续进化时出错: {e}")
        
        try:
            # 停止心跳
            await self.heartbeat.stop()
        except Exception as e:
            log.warning(f"停止心跳时出错: {e}")
        
        try:
            # 关闭任务管理器
            task_manager = self.planner.get_task_manager()
            await task_manager.shutdown(wait=True)
        except Exception as e:
            log.warning(f"关闭任务管理器时出错: {e}")
        
        try:
            # 关闭 LLM Brain
            await self.brain.close()
        except Exception as e:
            log.warning(f"关闭 LLM Brain 时出错: {e}")
        
        console.print("[dim]资源清理完成[/dim]")
    
    def _init_skills(self) -> dict:
        """初始化所有技能"""
        skills = {}
        
        # 系统控制
        system_skill = SystemControlSkill()
        skills["system_control"] = system_skill
        
        # 文件管理
        file_skill = FileManagerSkill()
        skills["file_manager"] = file_skill
        
        # 网页浏览
        web_skill = WebBrowserSkill()
        skills["web_browser"] = web_skill
        
        # 终端命令
        terminal_skill = TerminalSkill()
        skills["terminal"] = terminal_skill
        
        # 定时任务（传递心跳引擎）
        scheduler_skill = SchedulerSkill(heartbeat_engine=self.heartbeat)
        skills["scheduler"] = scheduler_skill
        
        # 后台任务（演示）
        background_skill = BackgroundTaskSkill()
        skills["background_task"] = background_skill
        
        # IoT 控制（如果配置了）
        if self.config.iot.enabled:
            iot_skill = IoTBridgeSkill()
            skills["iot_bridge"] = iot_skill
        
        console.print(f"[dim]已加载 {len(skills)} 个技能[/dim]")
        
        return skills
    
    def _inform_brain_system_info(self):
        """通知大脑中枢当前系统信息和时间"""
        # 构建系统信息提示
        system_info_text = f"""【当前运行环境】
{self.system_info.get_prompt_info()}

【当前时间信息】
启动时间: {self.heartbeat.get_init_time_formatted()}
当前时段: {self.heartbeat.get_init_time_info().get('init_time_info', {}).get('period_cn', '')}
时区: {self.config.heartbeat.timezone}

JARVIS 在处理命令时会根据当前操作系统和时间做出合适的响应。"""
        
        # 将系统信息添加到记忆中
        self.memory.add_message(
            role="system",
            content=system_info_text,
            metadata={
                "type": "system_info",
                "platform": self.system_info.get_all_info()["platform"],
                "start_time": self.heartbeat.get_init_time_formatted()
            }
        )
        
        log.debug("系统信息已通知大脑中枢")
    
    async def _handle_confirmation(self, message: str) -> bool:
        """处理确认请求"""
        console.print(f"\n[yellow][WARNING] {message}[/yellow]")
        console.print("[dim]输入 y 确认，n 拒绝:[/dim]", end=" ")
        
        # 使用异步输入
        user_input = await to_thread(input)
        
        return user_input.strip().lower() in ['y', 'yes', '是', '确认']
    
    async def _evolution_feedback_callback(self, feedback: str):
        """处理进化反馈"""
        try:
            # 在命令行模式显示
            if not self.config.server.enabled:
                console.print(f"\n[cyan][进化反馈][/cyan]")
                console.print(feedback)
            
            # 在Web模式通过WebSocket发送
            # 这里需要通过server.py的WebSocket连接
            # 简单处理：保存到上下文，等待下次查询时返回
            self.context.set_variable("pending_evolution_feedback", feedback)
            
        except Exception as e:
            log.error(f"进化反馈处理失败: {e}")
    
    async def process(self, user_input: str) -> str:
        """
        处理用户输入
        
        Args:
            user_input: 用户输入文本
            
        Returns:
            AI 回复
        """
        import time
        start_time = time.time()
        
        # 记录活动
        self.heartbeat.record_activity()
        
        # 更新上下文
        self.context.set_current_task(user_input[:50])
        
        # 使用规划器处理
        response = await self.planner.plan_and_execute(user_input)
        
        # 清除当前任务
        self.context.clear_current_task()
        
        # 记录进化经验
        execution_time = time.time() - start_time
        try:
            self.evolution_engine.record_experience(
                task_type=self._classify_task(user_input),
                user_input=user_input,
                response=response,
                tools_used=self.planner._last_used_tools or [],
                success=True,
                execution_time=execution_time,
                context={"timestamp": datetime.now().isoformat()}
            )
        except Exception as e:
            log.warning(f"记录进化经验失败: {e}")
        
        return response
    
    def _classify_task(self, user_input: str) -> str:
        """分类任务类型"""
        user_input_lower = user_input.lower()
        
        if any(word in user_input_lower for word in ['文件', 'file', '目录', 'folder', '删除', 'delete']):
            return 'file_management'
        elif any(word in user_input_lower for word in ['命令', 'command', '终端', 'terminal', '执行']):
            return 'terminal_command'
        elif any(word in user_input_lower for word in ['搜索', 'search', '网页', 'web', '浏览']):
            return 'web_search'
        elif any(word in user_input_lower for word in ['时间', '定时', 'schedule', '提醒']):
            return 'scheduling'
        elif any(word in user_input_lower for word in ['系统', 'system', '状态', 'status']):
            return 'system_info'
        else:
            return 'general_query'
    
    async def speak(self, text: str):
        """语音输出"""
        await self.tts.speak(text)
    
    async def run_cli(self):
        """运行命令行交互模式"""
        self._print_welcome()
        
        # 启动持续进化（后台学习）
        await self.continuous_evolution.start()
        
        # 启动心跳
        if self.config.heartbeat.enabled:
            self.heartbeat.start()
        
        # 显示时间问候
        if self.config.heartbeat.enable_greeting:
            greeting = self.heartbeat.get_greeting()
            console.print(f"[cyan]{greeting}[/cyan]")
        
        try:
            while True:
                try:
                    # 获取用户输入
                    console.print("\n[bold cyan]You:[/bold cyan] ", end="")
                    user_input = await to_thread(input)
                    
                    if not user_input.strip():
                        continue
                    
                    # 退出命令
                    if user_input.strip().lower() in ['exit', 'quit', '退出', 'bye']:
                        console.print("\n[cyan]JARVIS: 再见，Sir。[/cyan]")
                        break
                    
                    # 特殊命令
                    if user_input.startswith('/'):
                        await self._handle_command(user_input)
                        continue
                    
                    # 处理请求
                    console.print("\n[bold green]JARVIS:[/bold green] ", end="")
                    
                    response = await self.process(user_input)
                    
                    # 输出回复
                    console.print(Markdown(response))
                    
                except KeyboardInterrupt:
                    console.print("\n\n[cyan]JARVIS: 收到中断信号，再见。[/cyan]")
                    break
                except Exception as e:
                    console.print(f"\n[red]错误: {e}[/red]")
                    log.error(f"处理请求时出错: {e}")
        finally:
            # 确保清理资源
            await self.cleanup()
    
    async def run_voice(self):
        """运行语音交互模式"""
        from senses.ears import Ears
        
        ears = Ears()
        
        if not ears.is_available():
            console.print("[red]语音识别不可用，请检查依赖安装[/red]")
            return
        
        self._print_welcome()
        console.print("[cyan]语音模式已启动，请说话...[/cyan]\n")
        
        # 启动心跳
        if self.config.heartbeat.enabled:
            self.heartbeat.start()
        
        # 语音问候
        if self.config.heartbeat.enable_greeting:
            greeting = self.heartbeat.get_greeting()
            await self.speak(greeting)
        else:
            await self.speak("JARVIS 已就绪，请说出您的指令。")
        
        try:
            while True:
                try:
                    # 监听语音
                    text = await ears.listen(timeout=10)
                    
                    if not text:
                        continue
                    
                    console.print(f"\n[bold cyan]You:[/bold cyan] {text}")
                    
                    # 退出命令
                    if any(word in text for word in ['退出', '再见', '关闭']):
                        await self.speak("再见，Sir。")
                        break
                    
                    # 处理请求
                    response = await self.process(text)
                    
                    console.print(f"\n[bold green]JARVIS:[/bold green] {response}")
                    
                    # 语音输出
                    await self.speak(response)
                    
                except KeyboardInterrupt:
                    await self.speak("收到中断信号，再见。")
                    break
                except Exception as e:
                    console.print(f"\n[red]错误: {e}[/red]")
                    log.error(f"语音模式错误: {e}")
        finally:
            # 确保清理资源
            await self.cleanup()
    
    async def _handle_command(self, command: str):
        """处理特殊命令"""
        cmd = command[1:].strip().lower()
        
        if cmd == 'help':
            self._print_help()
        elif cmd == 'clear':
            self.memory.clear_short_term()
            console.print("[dim]对话记忆已清空[/dim]")
        elif cmd == 'status':
            self._print_status()
        elif cmd == 'skills':
            self._print_skills()
        elif cmd == 'heartbeat':
            self._print_heartbeat()
        elif cmd == 'evolution':
            self._print_evolution()
        elif cmd == 'optimize':
            self._print_optimize()
        elif cmd == 'tasks':
            self._print_tasks()
        elif cmd.startswith('cancel '):
            task_id = cmd[7:].strip()
            await self._cancel_task(task_id)
        elif cmd.startswith('status '):
            task_id = cmd[7:].strip()
            self._print_task_status(task_id)
        elif cmd.startswith('voice '):
            voice_name = cmd[6:].strip()
            self.tts.set_voice(voice_name)
            console.print(f"[dim]语音已切换为: {voice_name}[/dim]")
        else:
            console.print(f"[yellow]未知命令: {command}[/yellow]")
    
    def _print_welcome(self):
        """打印欢迎信息"""
        welcome = """
   ╦╔═╗╦═╗╦  ╦╦╔═╗
   ║╠═╣╠╦╝╚╗╔╝║╚═╗
  ╚╝╩ ╩╩╚═ ╚╝ ╩╚═╝
        
  Just A Rather Very Intelligent System
        """
        
        console.print(Panel(
            welcome,
            title="[bold cyan]Welcome[/bold cyan]",
            border_style="cyan"
        ))
        
        console.print("[dim]输入 /help 查看帮助，输入 exit 退出[/dim]")
    
    def _print_help(self):
        """打印帮助信息"""
        help_text = """
## 可用命令

- `/help`      - 显示此帮助信息
- `/clear`     - 清空对话记忆
- `/status`    - 显示系统状态
- `/heartbeat` - 显示心跳状态
- `/skills`    - 显示可用技能
- `/tasks`     - 显示后台任务列表
- `/cancel <task_id>` - 取消指定任务
- `/status <task_id>` - 查看指定任务状态
- `/voice <name>` - 切换语音
- `/evolution` - 显示自我进化统计
- `/optimize`  - 显示优化建议
- `exit`       - 退出程序

## 示例指令

- "打开记事本"
- "搜索今天的新闻"
- "读取桌面上的文件列表"
- "帮我创建一个笔记文件"
- "创建一个定时任务"
- "查看所有定时任务"
- "后台执行一个10秒的倒计时任务"
- "模拟下载一个100MB的文件"
        """
        console.print(Markdown(help_text))
    
    def _print_status(self):
        """打印系统状态"""
        memory_stats = self.memory.get_stats()
        context = self.context.get_system_state()
        healing_stats = self.self_healing.get_error_stats()
        system_info = self.system_info.get_all_info()
        heartbeat_info = self.heartbeat.get_init_time_info()
        
        status = f"""
## 系统状态

### 运行环境
- **操作系统**: {system_info['os']}
- **平台**: {system_info['platform']}
- **架构**: {system_info['arch']}
- **主机名**: {system_info['hostname']}
- **用户**: {system_info['user']}
- **管理员权限**: {'是' if system_info['is_admin'] else '否'}

### 时间信息
- **启动时间**: {heartbeat_info.get('init_time_formatted', 'N/A')}
- **启动时段**: {heartbeat_info.get('init_time_info', {}).get('period_cn', 'N/A')}
- **时区**: {self.config.heartbeat.timezone}

### 大脑状态
- **LLM 提供商**: {self.brain.provider.value}
- **短期记忆**: {memory_stats['short_term_count']} 条
- **长期记忆**: {memory_stats['long_term_count']} 条

### 系统资源
- **活跃窗口**: {context.get('active_window', 'N/A')}
- **CPU 使用率**: {context.get('cpu_percent', 0):.1f}%
- **内存使用率**: {context.get('memory_percent', 0):.1f}%

## 自我修复统计

- **错误类型**: {healing_stats['total_error_types']}
- **总错误数**: {healing_stats['total_errors']}
- **恢复成功率**: {healing_stats['recovery_rate']:.1%}
        """
        
        if healing_stats['most_common_errors']:
            status += "\n\n### 常见错误\n"
            for error in healing_stats['most_common_errors']:
                status += f"- {error['error_type']}: {error['count']} 次\n"
        
        console.print(Markdown(status))
    
    def _print_skills(self):
        """打印可用技能"""
        console.print("\n## 可用技能\n")
        for name, skill in self.skills.items():
            console.print(f"- **{name}**: {skill.description}")
    
    def _print_evolution(self):
        """打印自我进化统计"""
        evolution_stats = self.evolution_engine.get_evolution_stats()
        
        evolution = f"""
## 自我进化统计

- **总经验数**: {evolution_stats['total_experiences']}
- **近期成功率**: {evolution_stats['recent_success_rate']:.1%}
- **平均执行时间**: {evolution_stats['avg_execution_time']:.2f}秒
- **学习偏好数**: {evolution_stats['preferences_learned']}
- **识别模式数**: {evolution_stats['patterns_identified']}
- **知识条目数**: {evolution_stats['knowledge_items']}
        """
        
        # 显示偏好
        if evolution_stats['top_preferences']:
            evolution += "\n\n### 顶部偏好\n"
            for pref_type, prefs in evolution_stats['top_preferences'].items():
                if prefs:
                    evolution += f"\n**{pref_type}**:\n"
                    for pref in prefs:
                        evolution += f"  - {pref.key} (置信度: {pref.confidence:.2f})\n"
        
        console.print(Markdown(evolution))
    
    def _print_optimize(self):
        """打印优化建议"""
        suggestions = self.evolution_engine.get_optimization_suggestions()
        
        if not suggestions:
            console.print("[dim]暂无足够数据提供优化建议[/dim]")
            return
        
        optimize_text = """
## 系统优化建议

基于您的使用模式和系统性能，JARVIS 建议以下优化：

"""
        
        for i, suggestion in enumerate(suggestions, 1):
            optimize_text += f"{i}. {suggestion}\n"
        
        console.print(Markdown(optimize_text))
    
    def _print_tasks(self):
        """打印后台任务列表"""
        task_manager = self.planner.get_task_manager()
        tasks = task_manager.get_all_tasks()
        
        if not tasks:
            console.print("[dim]当前没有后台任务[/dim]")
            return
        
        tasks_text = "## 后台任务列表\n\n"
        
        status_colors = {
            "pending": "[yellow]",
            "running": "[cyan]",
            "completed": "[green]",
            "failed": "[red]",
            "cancelled": "[dim]"
        }
        
        for task_id, task_info in tasks.items():
            status = task_info.get("status", "unknown")
            color = status_colors.get(status, "")
            progress = task_info.get("progress", 0.0)
            name = task_info.get("name", "unknown")
            
            tasks_text += f"- **{task_id}**: {color}{status}[/{color}] - {name} (进度: {progress * 100:.1f}%)\n"
        
        console.print(Markdown(tasks_text))
    
    async def _cancel_task(self, task_id: str):
        """取消指定任务"""
        task_manager = self.planner.get_task_manager()
        success = task_manager.cancel_task(task_id)
        
        if success:
            console.print(f"[green]任务 {task_id} 已取消[/green]")
        else:
            console.print(f"[red]无法取消任务 {task_id}（任务不存在或已完成）[/red]")
    
    def _print_task_status(self, task_id: str):
        """打印指定任务状态"""
        task_manager = self.planner.get_task_manager()
        task_info = task_manager.get_task_status(task_id)
        
        if not task_info:
            console.print(f"[red]任务 {task_id} 不存在[/red]")
            return
        
        status_colors = {
            "pending": "[yellow]",
            "running": "[cyan]",
            "completed": "[green]",
            "failed": "[red]",
            "cancelled": "[dim]"
        }
        
        status = task_info.get("status", "unknown")
        color = status_colors.get(status, "")
        progress = task_info.get("progress", 0.0)
        name = task_info.get("name", "unknown")
        is_background = task_info.get("is_background", True)
        
        task_text = f"""
## 任务详情

- **任务ID**: {task_id}
- **名称**: {name}
- **状态**: {color}{status}[/{color}]
- **进度**: {progress * 100:.1f}%
- **后台任务**: {'是' if is_background else '否'}
"""
        
        if "error" in task_info and task_info["error"]:
            task_text += f"- **错误**: {task_info['error']}\n"
        
        if "result" in task_info and task_info["result"]:
            task_text += f"- **结果**: {task_info['result']}\n"
        
        console.print(Markdown(task_text))
    
    def _print_heartbeat(self):
        """打印心跳状态"""
        heartbeat_status = self.heartbeat.get_heartbeat_status()
        console.print(Markdown(heartbeat_status))


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='JARVIS AI Assistant')
    parser.add_argument('--voice', action='store_true', help='启用语音交互模式')
    parser.add_argument('--web', action='store_true', help='启用 Web UI 模式')
    parser.add_argument('--provider', choices=['openai', 'deepseek', 'ollama'], 
                       help='LLM 提供商')
    args = parser.parse_args()
    
    # 设置 LLM 提供商
    if args.provider:
        from config import update_config, LLMConfig, LLMProvider
        config = get_config()
        config.llm.provider = LLMProvider(args.provider)
    
    # 创建 JARVIS 实例
    jarvis = Jarvis()
    
    # 运行
    if args.web:
        console.print("[cyan]启动 JARVIS Web UI...[/cyan]")
        console.print(f"[dim]访问地址: http://{get_config().server.host}:{get_config().server.port}[/dim]")
        console.print("[dim]提示: Web UI 模式会启动一个新的 Web 服务器进程[/dim]")
        
        # 启动心跳引擎
        if jarvis.config.heartbeat.enabled:
            jarvis.heartbeat.start()
        
        # 启动持续进化（后台学习）
        await jarvis.continuous_evolution.start()
        
        # 导入服务器设置 JARVIS 实例
        from server import set_jarvis_instance, app
        set_jarvis_instance(jarvis)
        
        # 使用 uvicorn 直接运行（不使用 asyncio.run）
        import uvicorn
        uvicorn.run(
            app,
            host=get_config().server.host,
            port=get_config().server.port,
            log_level="info"
        )
    elif args.voice:
        await jarvis.run_voice()
    else:
        await jarvis.run_cli()


if __name__ == "__main__":
    # 对于 Web 模式，不使用 asyncio.run，直接同步运行
    import sys
    import argparse
    
    if '--web' in sys.argv:
        # 同步运行 main 函数（uvicorn 会处理事件循环）
        import asyncio
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        # 创建新的事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # 同步运行 main（只初始化部分）
        parser = argparse.ArgumentParser(description='JARVIS AI Assistant')
        parser.add_argument('--voice', action='store_true', help='启用语音交互模式')
        parser.add_argument('--web', action='store_true', help='启用 Web UI 模式')
        parser.add_argument('--provider', choices=['openai', 'deepseek', 'ollama'], 
                           help='LLM 提供商')
        args = parser.parse_args()
        
        # 设置 LLM 提供商
        if args.provider:
            from config import update_config, LLMConfig, LLMProvider
            config = get_config()
            config.llm.provider = LLMProvider(args.provider)
        
        # 创建 JARVIS 实例
        jarvis = Jarvis()
        
        # 设置服务器实例（在启动心跳之前）
        from server import set_jarvis_instance, app
        set_jarvis_instance(jarvis)
        
        # 启动服务器
        console.print("[cyan]启动 JARVIS Web UI...[/cyan]")
        console.print(f"[dim]访问地址: http://{get_config().server.host}:{get_config().server.port}[/dim]")
        
        # 使用 uvicorn 直接运行（会处理事件循环）
        import uvicorn
        
        # 配置启动事件来启动心跳
        async def startup():
            if jarvis.config.heartbeat.enabled:
                jarvis.heartbeat.start()
        
        app.add_event_handler("startup", startup)
        
        uvicorn.run(
            app,
            host=get_config().server.host,
            port=get_config().server.port,
            log_level="info"
        )
    else:
        # 其他模式使用 asyncio.run
        asyncio.run(main())