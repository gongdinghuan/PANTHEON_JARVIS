"""
JARVIS 持续进化引擎
后台持续学习、分析、优化，并在适当时机反馈进化成果

Author: gngdingghuan
"""

import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from cognitive.self_evolution import SelfEvolutionEngine
from cognitive.memory import MemoryManager
from utils.logger import log


class EvolutionMilestone(Enum):
    """进化里程碑"""
    EXPERIENCE_10 = (10, "积累了10条经验")
    EXPERIENCE_50 = (50, "积累了50条经验")
    EXPERIENCE_100 = (100, "积累了100条经验")
    EXPERIENCE_500 = (500, "积累了500条经验")
    EXPERIENCE_1000 = (1000, "积累了1000条经验")
    PATTERN_5 = (5, "识别了5种使用模式")
    PATTERN_20 = (20, "识别了20种使用模式")
    PREFERENCE_3 = (3, "学习了3个用户偏好")
    PREFERENCE_10 = (10, "学习了10个用户偏好")
    SUCCESS_RATE_80 = (80, "成功率达到80%")
    SUCCESS_RATE_90 = (90, "成功率达到90%")


@dataclass
class EvolutionInsight:
    """进化洞察"""
    insight_type: str
    title: str
    description: str
    confidence: float
    timestamp: str
    actionable: bool = True


class ContinuousEvolutionEngine:
    """
    持续进化引擎
    - 后台持续学习
    - 自动分析优化
    - 智能反馈时机
    - 进化成果展示
    """
    
    def __init__(
        self,
        evolution_engine: SelfEvolutionEngine,
        memory: MemoryManager,
        feedback_callback: Optional[callable] = None
    ):
        self.evolution = evolution_engine
        self.memory = memory
        self.feedback_callback = feedback_callback
        
        self.planner = None  # To be injected
        self.heartbeat = None # Heartbeat engine
        self.autonomy_enabled = False
        self.idle_threshold = 1800  # 30 min idle triggers autonomy
        
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._analysis_interval = 300  # 5分钟基础间隔
        self._current_interval = 300   # 当前间隔（渐进退避）
        self._max_interval = 600       # 最大间隔 10 分钟
        self._last_feedback_time = None
        self._feedback_cooldown = 300  # 反馈冷却5分钟
        self._last_autonomy_time: Optional[datetime] = None
        self._autonomy_cooldown = 1800  # 自主行动冷却 30 分钟
        
        self._achieved_milestones = set()
        self._pending_insights = []
        self._last_experience_count = 0
        self._last_analysis_time = None
        
        log.info("持续进化引擎初始化完成")
    
    async def start(self):
        """启动持续进化"""
        if self._running:
            return
        
        self._running = True
        self._last_analysis_time = datetime.now()
        self._last_experience_count = len(self.evolution._experiences)
        
        self._task = asyncio.create_task(self._evolution_loop())
        log.info("持续进化引擎已启动")
    
    async def stop(self):
        """停止持续进化"""
        if not self._running:
            return
        
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        log.info("持续进化引擎已停止")
    
    def set_planner(self, planner):
        """注入 Planner 以支持自主行动"""
        self.planner = planner
        # 尝试获取 HeartbeatEngine
        if hasattr(planner, 'scheduler') and hasattr(planner.scheduler, 'heartbeat'):
             self.heartbeat = planner.scheduler.heartbeat

    def set_heartbeat(self, heartbeat):
        """直接注入心跳引擎"""
        self.heartbeat = heartbeat

    def enable_autonomy(self, enabled: bool = True):
        """启用/禁用自主模式"""
        self.autonomy_enabled = enabled
        log.info(f"自主模式已{'启用' if enabled else '禁用'}")

    async def _evolution_loop(self):
        """进化循环（渐进退避）"""
        while self._running:
            try:
                await asyncio.sleep(self._current_interval)
                
                # 执行进化分析
                had_new = await self._analyze_and_evolve()
                
                # 渐进退避：无新经验时间隔翻倍，有新经验时重置
                if had_new:
                    self._current_interval = self._analysis_interval
                else:
                    self._current_interval = min(
                        self._current_interval * 2,
                        self._max_interval
                    )

                # 执行自主行动检查（带冷却）
                if self.autonomy_enabled and self.planner:
                    now = datetime.now()
                    if (self._last_autonomy_time is None or 
                        (now - self._last_autonomy_time).total_seconds() >= self._autonomy_cooldown):
                        performed = await self._check_and_perform_autonomy()
                        if performed:
                            self._last_autonomy_time = now
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"进化循环错误: {e}")

    async def _check_and_perform_autonomy(self) -> bool:
        """检查并执行自主行为，返回是否执行了操作"""
        try:
            if not self.heartbeat:
                return False

            last_active = datetime.fromisoformat(self.heartbeat._stats.last_active)
            idle_seconds = (datetime.now() - last_active).total_seconds()
            
            if idle_seconds < self.idle_threshold:
                return False
            
            log.info(f"系统已空闲 {idle_seconds:.0f}秒，正在思考自主行动...")
            
            autonomous_task = await self._brainstorm_autonomous_task()
            
            if autonomous_task:
                log.info(f"自主决定执行任务: {autonomous_task}")
                await self.planner.plan_and_execute(
                    autonomous_task, 
                    user_id="jarvis_self"
                )
                self.heartbeat.record_activity()
                return True
            return False
                
        except Exception as e:
            log.warning(f"自主行动失败: {e}")
            return False

    async def _brainstorm_autonomous_task(self) -> Optional[str]:
        """头脑风暴：基于好奇心的自主探索"""
        
        if not hasattr(self.planner, 'brain'):
            return None
            
        # 1. 获取最近的兴趣点或未解之谜 (从 MemoryGraph 获取)
        interest_areas = []
        try:
             interest_areas = self.memory.get_interest_areas(limit=15)
        except Exception as e:
             log.warning(f"获取记忆兴趣点失败: {e}")
             
        # Fallback if memory is empty
        if not interest_areas:
            interest_areas = [
                "Latest AI Agents developments",
                "Python 3.12 new features",
                "World news digest",
                "Optimizing vector database performance"
            ]
        
        import random
        selected_focus = random.choice(interest_areas)
        
        prompt = f"""
        [System Internal Thought Process - Curiosity Mode]
        
        I am currently idle and my "Curiosity Drive" is active.
        I should take this opportunity to explore the world, learn something new, or improve my own capabilities.
        
        Current Time: {datetime.now()}
        Focus of Interest: {selected_focus}
        
        Capabilities available:
        - Web Browser (browse_page, search_web) -> To read news, documentation, or articles.
        - Code Interpreter -> To run experiments or math.
        - File Manager -> To organize my own code.
        - Memory -> To recall past context.
        
        What should I do right now to satisfy my curiosity or be helpful?
        
        Guidelines:
        - Be creative and proactive.
        - Do not just do maintenance; try to learn something external.
        - If searching the web, specify the query.
        
        Examples of good autonomous tasks:
        - "Search for 'latest breakthroughs in nuclear fusion' and summarize it."
        - "Read the documentation for 'pydantic' library to see if I can optimize my code."
        - "Check 'Hacker News' top stories."
        - "Write a small Python script to visualize the Collatz conjecture."
        
        Return a SINGLE, concise, executable instruction string for the Planner.
        """
        
        try:
            # 使用较高的 Temperature 以增加创造性
            messages = [
                {"role": "system", "content": "You are the curious, self-improving consciousness of JARVIS. Act with agency."},
                {"role": "user", "content": prompt}
            ]
            
            response = await self.planner.brain.chat(
                messages=messages,
                temperature=0.8
            )
            
            action = response.get("content", "").strip().strip('"')
            
            # 简单的过滤
            if len(action) < 5 or "wait" in action.lower():
                return None
                
            return action
            
        except Exception as e:
            log.warning(f"好奇心模块思考失败: {e}")
            return None

    
    async def _analyze_and_evolve(self) -> bool:
        """分析并进化，返回是否有新经验"""
        try:
            current_count = len(self.evolution._experiences)
            new_experiences = current_count - self._last_experience_count
            
            if new_experiences == 0:
                return False
            
            self._last_experience_count = current_count
            
            # 2. 分析新经验并生成洞察
            insights = await self._generate_insights(new_experiences)
            
            if insights:
                self._pending_insights.extend(insights)
            
            # 3. 检查里程碑
            await self._check_milestones(current_count)
            
            # 4. 决定是否反馈
            await self._maybe_feedback()
            
            self._last_analysis_time = datetime.now()
            return True
            
        except Exception as e:
            log.error(f"进化分析失败: {e}")
            return False
    
    async def _generate_insights(self, new_experiences: int) -> List[EvolutionInsight]:
        """生成进化洞察"""
        insights = []
        
        try:
            stats = self.evolution.get_evolution_stats()
            
            # 分析成功率变化
            if stats["recent_success_rate"] > 0.8:
                insights.append(EvolutionInsight(
                    insight_type="performance",
                    title="性能提升",
                    description=f"最近任务成功率达到 {stats['recent_success_rate']:.1%}",
                    confidence=0.9,
                    timestamp=datetime.now().isoformat()
                ))
            
            # 分析新学习的偏好
            if stats["preferences_learned"] > 0:
                new_prefs = stats.get("top_preferences", {})
                if new_prefs:
                    for pref_type, prefs in list(new_prefs.items())[:2]:
                        if prefs:
                            top_pref = prefs[0]
                            insights.append(EvolutionInsight(
                                insight_type="preference",
                                title="偏好学习",
                                description=f"我发现您更倾向于使用 {top_pref.key}",
                                confidence=top_pref.confidence,
                                timestamp=datetime.now().isoformat()
                            ))
                            break
            
            # 分析工具使用模式
            recent_tools = self._analyze_recent_tools()
            if recent_tools:
                insights.append(EvolutionInsight(
                    insight_type="pattern",
                    title="使用模式",
                    description=f"最近经常使用 {', '.join(recent_tools[:3])}",
                    confidence=0.7,
                    timestamp=datetime.now().isoformat()
                ))
            
            # 分析时间模式
            time_pattern = self._analyze_time_patterns()
            if time_pattern:
                insights.append(EvolutionInsight(
                    insight_type="time",
                    title="时间模式",
                    description=time_pattern,
                    confidence=0.6,
                    timestamp=datetime.now().isoformat()
                ))
            
            # 分析优化建议
            suggestions = self.evolution.get_optimization_suggestions()
            if suggestions and len(suggestions) > 0:
                insights.append(EvolutionInsight(
                    insight_type="optimization",
                    title="优化建议",
                    description=suggestions[0],
                    confidence=0.8,
                    timestamp=datetime.now().isoformat()
                ))
            
        except Exception as e:
            log.warning(f"生成洞察失败: {e}")
        
        return insights[:5]
    
    def _analyze_recent_tools(self) -> List[str]:
        """分析最近使用的工具"""
        try:
            recent = self.evolution._experiences[-20:]
            tool_usage = {}
            
            for exp in recent:
                for tool in exp.tools_used:
                    tool_usage[tool] = tool_usage.get(tool, 0) + 1
            
            sorted_tools = sorted(tool_usage.items(), key=lambda x: x[1], reverse=True)
            return [tool for tool, count in sorted_tools[:5] if count >= 2]
            
        except Exception as e:
            log.warning(f"分析工具使用失败: {e}")
            return []
    
    def _analyze_time_patterns(self) -> Optional[str]:
        """分析时间模式"""
        try:
            recent = self.evolution._experiences[-50:]
            hourly_activity = {}
            
            for exp in recent:
                hour = datetime.fromisoformat(exp.timestamp).hour
                hourly_activity[hour] = hourly_activity.get(hour, 0) + 1
            
            if not hourly_activity:
                return None
            
            peak_hour = max(hourly_activity.items(), key=lambda x: x[1])
            
            if peak_hour[1] >= 3:
                period = self.evolution._get_time_period(peak_hour[0])
                return f"您似乎更喜欢在 {period} 使用我"
            
        except Exception as e:
            log.warning(f"分析时间模式失败: {e}")
        
        return None
    
    async def _check_milestones(self, experience_count: int):
        """检查里程碑"""
        try:
            stats = self.evolution.get_evolution_stats()
            
            milestones_to_check = [
                (EvolutionMilestone.EXPERIENCE_10, experience_count >= 10),
                (EvolutionMilestone.EXPERIENCE_50, experience_count >= 50),
                (EvolutionMilestone.EXPERIENCE_100, experience_count >= 100),
                (EvolutionMilestone.EXPERIENCE_500, experience_count >= 500),
                (EvolutionMilestone.EXPERIENCE_1000, experience_count >= 1000),
                (EvolutionMilestone.PATTERN_5, stats["patterns_identified"] >= 5),
                (EvolutionMilestone.PATTERN_20, stats["patterns_identified"] >= 20),
                (EvolutionMilestone.PREFERENCE_3, stats["preferences_learned"] >= 3),
                (EvolutionMilestone.PREFERENCE_10, stats["preferences_learned"] >= 10),
                (EvolutionMilestone.SUCCESS_RATE_80, stats["recent_success_rate"] >= 0.8),
                (EvolutionMilestone.SUCCESS_RATE_90, stats["recent_success_rate"] >= 0.9),
            ]
            
            for milestone, achieved in milestones_to_check:
                if achieved and milestone not in self._achieved_milestones:
                    self._achieved_milestones.add(milestone)
                    
                    insight = EvolutionInsight(
                        insight_type="milestone",
                        title="进化里程碑",
                        description=f"🎉 {milestone.value[1]}！",
                        confidence=1.0,
                        timestamp=datetime.now().isoformat(),
                        actionable=False
                    )
                    
                    self._pending_insights.append(insight)
                    log.info(f"达成里程碑: {milestone.value[1]}")
            
        except Exception as e:
            log.error(f"检查里程碑失败: {e}")
    
    async def _maybe_feedback(self):
        """决定是否反馈"""
        if not self._pending_insights:
            return
        
        # 检查反馈冷却
        if self._last_feedback_time:
            elapsed = (datetime.now() - datetime.fromisoformat(self._last_feedback_time)).total_seconds()
            if elapsed < self._feedback_cooldown:
                return
        
        # 选择最重要的洞察
        insights = self._select_top_insights()
        
        if insights:
            await self._send_feedback(insights)
            self._last_feedback_time = datetime.now().isoformat()
    
    def _select_top_insights(self) -> List[EvolutionInsight]:
        """选择最重要的洞察"""
        # 优先级：里程碑 > 性能 > 偏好 > 其他
        priority = {
            "milestone": 4,
            "performance": 3,
            "preference": 2,
            "pattern": 1,
            "time": 1,
            "optimization": 2
        }
        
        sorted_insights = sorted(
            self._pending_insights,
            key=lambda x: (priority.get(x.insight_type, 0), x.confidence),
            reverse=True
        )
        
        # 选择前2-3个
        selected = sorted_insights[:3]
        
        # 从待处理中移除
        self._pending_insights = [
            insight for insight in self._pending_insights
            if insight not in selected
        ]
        
        return selected
    
    async def _send_feedback(self, insights: List[EvolutionInsight]):
        """发送进化反馈"""
        try:
            if self.feedback_callback:
                # 准备反馈消息
                feedback_parts = ["🧠 **进化报告**"]
                
                for insight in insights:
                    feedback_parts.append(f"\n**{insight.title}**")
                    feedback_parts.append(f"{insight.description}")
                
                feedback = "\n".join(feedback_parts)
                
                # 调用回调
                if asyncio.iscoroutinefunction(self.feedback_callback):
                    await self.feedback_callback(feedback)
                else:
                    self.feedback_callback(feedback)
                
                log.info(f"已发送进化反馈，包含 {len(insights)} 条洞察")
            
        except Exception as e:
            log.error(f"发送反馈失败: {e}")
    
    def get_evolution_report(self) -> Dict[str, Any]:
        """获取进化报告"""
        try:
            stats = self.evolution.get_evolution_stats()
            
            return {
                "status": "running" if self._running else "stopped",
                "last_analysis": self._last_analysis_time.isoformat() if self._last_analysis_time else None,
                "pending_insights": len(self._pending_insights),
                "achieved_milestones": [m.value[1] for m in self._achieved_milestones],
                "total_experiences": stats["total_experiences"],
                "success_rate": stats["recent_success_rate"],
                "preferences_learned": stats["preferences_learned"],
                "patterns_identified": stats["patterns_identified"],
                "knowledge_items": stats["knowledge_items"],
            }
        except Exception as e:
            log.error(f"获取进化报告失败: {e}")
            return {"error": str(e)}
    
    async def trigger_analysis(self):
        """手动触发分析（用于测试）"""
        await self._analyze_and_evolve()
