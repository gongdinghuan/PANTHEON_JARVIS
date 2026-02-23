"""
JARVIS ReAct 任务规划器 v3.0
实现 Reasoning + Acting 循环，支持动态路由和并行工具调用

升级特性:
- 动态路由: 简单/中等/复杂任务自动选择执行策略
- 并行工具调用: 互不依赖的工具并行执行
- Plan-and-Execute: 复杂任务先分解再执行
- 事件发射: 实时向前端推送思考/工具调用/结果

Author: gngdingghuan
"""

import json
import re
import asyncio
import functools
import time
import uuid
from typing import Dict, List, Any, Optional, Callable

from cognitive.llm_brain import LLMBrain, VisionAnalyzer
from utils.json_utils import repair_json
from cognitive.memory import MemoryManager
from cognitive.context_manager import ContextManager
from cognitive.self_evolution import SelfEvolutionEngine
from cognitive.task_manager import TaskManager, TaskStatus
from cognitive.task_decomposer import TaskDecomposer, PlanExecutor, TaskPlan, StepStatus
from utils.logger import log
from skills.base_skill import SkillResult
from utils.error_handler import (
    ErrorHandler,
    RetryConfig,
    CircuitBreaker,
)


class ReActPlanner:
    """
    ReAct 任务规划器 v3.0
    
    执行策略:
    - 简单任务 → simple_respond (无工具)
    - 中等任务 → ReAct 循环 (感知→思考→行动→观察→反思)
    - 复杂任务 → Plan-and-Execute (分解→并行执行→汇总)
    """
    
    MAX_ITERATIONS = 100  # 最大循环次数，防止无限循环
    
    def __init__(
        self,
        brain: LLMBrain,
        memory: MemoryManager,
        context: ContextManager,
        skills: Optional[Dict[str, Any]] = None,
        evolution_engine: Optional[SelfEvolutionEngine] = None,
    ):
        """
        初始化规划器
        
        Args:
            brain: LLM 大脑实例
            memory: 记忆管理器
            context: 上下文管理器
            skills: 技能字典 {skill_name: skill_instance}
            evolution_engine: 自我进化引擎
        """
        self.brain = brain
        self.memory = memory
        self.context = context
        self.skills = skills or {}
        self.evolution_engine = evolution_engine
        
        # 错误处理器和熔断器
        self._error_handler = ErrorHandler()
        self._skill_circuit_breakers: Dict[str, CircuitBreaker] = {}
        
        # 任务管理器（支持后台任务）
        self.task_manager = TaskManager(max_workers=5)
        
        # 确认回调函数
        self._confirmation_callback: Optional[Callable] = None
        
        # 事件回调 (用于 Streaming 可视化)
        self._event_callback: Optional[Callable] = None
        
        # 工具使用跟踪（用于进化学习）
        self._last_used_tools: List[str] = []
        
        # Tool schema 缓存
        self._tools_schema_cache: Optional[List[Dict]] = None
        self._tools_schema_dirty: bool = True
        
        # 任务分解器 (延迟初始化)
        self._task_decomposer: Optional[TaskDecomposer] = None
        
        # [新增] 视觉分析器 (延迟初始化)
        self._vision_analyzer: Optional[VisionAnalyzer] = None
        
        log.info(f"ReAct 规划器 v3.0 初始化完成，已注册 {len(self.skills)} 个技能")
    
    def register_skill(self, name: str, skill: Any):
        """注册技能"""
        self.skills[name] = skill
        self._tools_schema_dirty = True
        # 更新 TaskDecomposer 的工具列表
        if self._task_decomposer:
            self._update_decomposer_tools()
        log.debug(f"已注册技能: {name}")
    
    def set_confirmation_callback(self, callback: Callable):
        """设置确认回调函数"""
        self._confirmation_callback = callback
    
    def set_event_callback(self, callback: Callable):
        """设置事件回调 (用于前端实时推送)"""
        self._event_callback = callback
    
    def get_task_manager(self) -> TaskManager:
        """获取任务管理器"""
        return self.task_manager
    
    async def _emit_event(self, event_type: str, data: Dict[str, Any]):
        """发射事件到前端"""
        if self._event_callback:
            try:
                if asyncio.iscoroutinefunction(self._event_callback):
                    await self._event_callback(event_type, data)
                else:
                    self._event_callback(event_type, data)
            except Exception as e:
                log.debug(f"事件回调失败: {e}")
    
    def _get_task_decomposer(self) -> TaskDecomposer:
        """获取或创建任务分解器"""
        if not self._task_decomposer:
            self._task_decomposer = TaskDecomposer(self.brain)
            self._update_decomposer_tools()
        return self._task_decomposer
    
    def _update_decomposer_tools(self):
        """更新任务分解器的工具列表"""
        tools = {}
        for name, skill in self.skills.items():
            if hasattr(skill, 'description'):
                tools[name] = skill.description
        if self._task_decomposer:
            self._task_decomposer.update_tools(tools)
    
    def _get_vision_analyzer(self) -> VisionAnalyzer:
        """获取或创建视觉分析器"""
        if not self._vision_analyzer:
            self._vision_analyzer = VisionAnalyzer(main_brain=self.brain)
        return self._vision_analyzer
    
    def _get_tools_schema(self) -> List[Dict]:
        """获取所有技能的 Function Calling Schema（带缓存）"""
        if self._tools_schema_dirty or self._tools_schema_cache is None:
            tools = []
            for name, skill in self.skills.items():
                if hasattr(skill, 'get_schema'):
                    schema = skill.get_schema()
                    if schema:
                        tools.append(schema)
            self._tools_schema_cache = tools
            self._tools_schema_dirty = False
        return self._tools_schema_cache
    
    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        base_prompt = self.brain.get_system_prompt()
        
        # 核心记忆 (User Profile)
        core_memory_text = ""
        if hasattr(self.memory, 'get_core_memory_text'):
            core_memory_text = self.memory.get_core_memory_text()
            if core_memory_text:
                core_memory_text = f"\n\n{core_memory_text}"
        
        # 添加上下文信息
        context_summary = self.context.get_context_summary()
        
        # 添加可用技能列表
        skill_list = []
        for name, skill in self.skills.items():
            if hasattr(skill, 'description'):
                skill_list.append(f"- {name}: {skill.description}")
        
        skills_text = "\n".join(skill_list) if skill_list else "暂无可用技能"
        
        full_prompt = f"""{base_prompt}{core_memory_text}

当前上下文信息：
{context_summary}

可用技能列表：
{skills_text}

重要提示：
1. 如果需要执行操作，请调用相应的工具函数
2. 如果任务需要多个步骤，请逐步执行并观察结果
3. 如果多个工具调用互不依赖，可以同时调用多个工具来提高效率
4. 对于危险操作，系统会自动请求用户确认
5. 如果无法完成任务，请如实告知原因"""
        
        return full_prompt
    
    # ----------------------------------------------------------------
    #  主入口: 智能路由
    # ----------------------------------------------------------------
    
    async def plan_and_execute(self, user_input: str, user_id: str = "default", images: list = None) -> str:
        """
        规划并执行任务（带智能路由和自我进化）
        
        路由策略:
        - simple → 直接 ReAct 循环
        - complex → Plan-and-Execute (先分解再执行)
        
        Args:
            user_input: 用户输入
            user_id: 用户标识
            images: 图片路径列表 (用于多模态理解)
            
        Returns:
            最终回复
        """
        start_time = time.time()
        task_type = self._classify_task(user_input)
        
        # 多模态检测
        if images:
            log.info(f"多模态请求: {len(images)} 张图片")
            task_type = "图片分析"
        
        log.info(f"收到用户请求: {user_input[:50]}... (User: {user_id})")
        log.debug(f"任务类型: {task_type}")
        
        # 经验检索与预测
        similar_experiences = []
        if self.evolution_engine:
            prediction = self.evolution_engine.predict_next_action(user_input)
            if prediction:
                log.info(f"预测任务: {prediction['task_type']} (置信度: {prediction['confidence']:.1%})")
            
            similar_experiences = self.evolution_engine.search_similar_experience(
                user_input, 
                task_type=task_type,
                limit=3
            )
        
        # 判断复杂度 → 选择执行策略
        decomposer = self._get_task_decomposer()
        complexity = decomposer.estimate_complexity(user_input)
        log.info(f"任务复杂度: {complexity}")
        
        await self._emit_event("planning", {"complexity": complexity, "task_type": task_type})
        
        if complexity == "complex":
            # 复杂任务 → Plan-and-Execute
            result = await self._plan_and_execute_complex(
                user_input, user_id, task_type, similar_experiences, start_time,
                images=images,
            )
        else:
            # 简单/中等任务 → ReAct 循环
            result = await self._react_loop(
                user_input, user_id, task_type, similar_experiences, start_time,
                images=images,
            )
        
        return result
    
    # ----------------------------------------------------------------
    #  ReAct 循环 (兼容原有逻辑，支持并行工具调用)
    # ----------------------------------------------------------------
    
    async def _react_loop(
        self,
        user_input: str,
        user_id: str,
        task_type: str,
        similar_experiences: List,
        start_time: float,
        images: list = None,
    ) -> str:
        """ReAct 循环执行"""
        # 保存到短期记忆
        self.memory.add_message("user", user_input)
        
        # 获取上下文和历史
        messages = []
        
        # Holo-Mem 混合语境检索
        holo_context = await self.memory.retrieve_context_hybrid(user_input)
        holo_context_text = ""
        if holo_context:
            holo_context_text = "\n\n## 动态语境 (Holo-Mem)\n" + "\n".join(holo_context)

        # 系统提示词
        base_system_prompt = self._build_system_prompt()
        
        # [NEW] 多模态提示
        if images:
            base_system_prompt += "\n\n注意: 用户已上传图片，请仔细观察和理解图片内容，结合用户的文字描述给出回答。"
        
        # 注入经验
        experience_text = self._format_experience(similar_experiences)
            
        messages.append({
            "role": "system",
            "content": f"{base_system_prompt}{holo_context_text}{experience_text}"
        })
        
        # 历史对话
        messages.extend(self.memory.get_recent_context())
        
        # 获取工具定义
        tools = self._get_tools_schema()
        
        # ReAct 循环
        iteration = 0
        final_response = ""
        tools_used = []
        visualizations = []
        attachments = []
        success = True
        
        while iteration < self.MAX_ITERATIONS:
            iteration += 1
            log.debug(f"ReAct 循环第 {iteration} 次")
            
            try:
                # [升级] 多模态两阶段处理:
                # Stage 1: 使用视觉模型分析图片 → 文本描述
                # Stage 2: 将描述注入主模型 Prompt → 结合用户问题回答
                if images and iteration == 1:
                    log.info(f"多模态请求: 使用两阶段视觉管线分析 {len(images)} 张图片")
                    await self._emit_event("thinking", {"content": f"正在使用视觉模型分析 {len(images)} 张图片..."})
                    
                    # Stage 1: 视觉分析
                    vision_analyzer = self._get_vision_analyzer()
                    image_description = await vision_analyzer.analyze_images(
                        images=images,
                        user_query=user_input,
                    )
                    
                    # Stage 2: 将图片描述注入最后一条 user 消息
                    if image_description:
                        vision_context = (
                            f"\n\n【图片分析结果】(由视觉模型生成)\n{image_description}"
                        )
                        # 修改最后一条 user 消息，追加图片分析
                        for i in range(len(messages) - 1, -1, -1):
                            if messages[i]["role"] == "user":
                                messages[i]["content"] += vision_context
                                break
                        
                        log.info(f"图片分析结果已注入 Prompt ({len(image_description)} 字)")
                        mode_label = "专用视觉模型" if vision_analyzer.is_dedicated else "主LLM回退"
                        await self._emit_event("thinking", {"content": f"图片分析完成 ({mode_label})，正在结合分析结果回答..."})
                
                # 调用主 LLM
                response = await self.brain.chat(messages, tools=tools if tools else None)
                
                # [NEW] 发射 thinking 事件
                if response.get("thinking"):
                    await self._emit_event("thinking", {"content": response["thinking"]})
                
                # 检查是否有工具调用
                if response.get("tool_calls"):
                    tool_calls = response["tool_calls"]
                    
                    # 记录使用的工具
                    for tc in tool_calls:
                        if tc["name"] not in tools_used:
                            tools_used.append(tc["name"])
                    
                    # [NEW] 发射 tool_start 事件
                    for tc in tool_calls:
                        await self._emit_event("tool_start", {
                            "name": tc["name"],
                            "arguments": tc["arguments"],
                        })
                    
                    # [UPGRADED] 并行执行互不依赖的工具
                    tool_results = await self._execute_tool_calls_parallel(tool_calls, user_id)
                    
                    # [NEW] 发射 tool_result 事件
                    for tc, result in zip(tool_calls, tool_results):
                        await self._emit_event("tool_result", {
                            "name": tc["name"],
                            "success": result.get("success", True),
                            "output_preview": str(result.get("output", ""))[:200],
                        })
                    
                    # 检查是否有失败
                    if not all(r.get("success", True) for r in tool_results):
                        success = False
                    
                    # 将工具调用和结果添加到消息
                    messages.append({
                        "role": "assistant",
                        "content": response.get("content", ""),
                        "tool_calls": [
                            {
                                "id": tc["id"],
                                "type": "function",
                                "function": {
                                    "name": tc["name"],
                                    "arguments": json.dumps(tc["arguments"], ensure_ascii=False)
                                }
                            }
                            for tc in tool_calls
                        ]
                    })
                    
                    for tc, result in zip(tool_calls, tool_results):
                        extra_info = ""
                        if not result.get("success", True) and self.evolution_engine:
                            error_msg = result.get("error", "Unknown error")
                            suggestion = self.evolution_engine.analyze_failure(error_msg, str(tc))
                            if suggestion:
                                extra_info = f"\n[JARVIS Evolution Suggestion]: {suggestion}"
                                log.info(f"应用进化建议: {suggestion}")
                        
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": json.dumps(result, ensure_ascii=False) + extra_info
                        })
                        
                        # 收集可视化和附件
                        if isinstance(result, dict):
                            if result.get("visualization"):
                                visualizations.append(result["visualization"])
                            if result.get("attachments"):
                                attachments.extend(result["attachments"])
                    
                    continue
                
                else:
                    # 没有工具调用，直接返回回复
                    final_response = response.get("content", "")
                    break
                    
            except Exception as e:
                log.error(f"ReAct 循环出错: {e}")
                final_response = f"抱歉，处理请求时出现错误: {str(e)}"
                success = False
                break
        
        if iteration >= self.MAX_ITERATIONS:
            log.warning("达到最大循环次数")
            final_response = "抱歉，任务过于复杂，无法在限定步骤内完成。"
            success = False
        
        # 保存回复和经验
        self.memory.add_message("assistant", final_response)
        self._record_experience(task_type, user_input, final_response, tools_used, success, start_time)
        
        log.info(f"请求处理完成，共 {iteration} 次循环，耗时 {time.time()-start_time:.2f}秒")
        
        if visualizations or attachments:
            return {
                "content": final_response,
                "visualizations": visualizations,
                "attachments": attachments
            }
        return final_response
    
    # ----------------------------------------------------------------
    #  [NEW] Plan-and-Execute 模式 (复杂任务)
    # ----------------------------------------------------------------
    
    async def _plan_and_execute_complex(
        self,
        user_input: str,
        user_id: str,
        task_type: str,
        similar_experiences: List,
        start_time: float,
        images: list = None,
    ) -> str:
        """复杂任务: 先分解 → 再执行 → 最后汇总"""
        self.memory.add_message("user", user_input)
        
        decomposer = self._get_task_decomposer()
        
        # 1. 分解任务
        await self._emit_event("decomposing", {"input": user_input[:100]})
        plan = await decomposer.decompose(user_input)
        log.info(f"任务已分解为 {plan.total_steps} 个步骤:\n{plan.summary()}")
        
        await self._emit_event("plan_created", {
            "goal": plan.goal,
            "steps": [{"id": s.step_id, "desc": s.description, "tool": s.tool_name} for s in plan.steps]
        })
        
        # 2. 执行计划
        tools_used = []
        
        async def execute_tool(tool_name: str, tool_args: Dict) -> Dict:
            """工具执行回调"""
            if tool_name not in self.skills:
                return {"success": False, "error": f"Tool '{tool_name}' not found"}
            
            skill = self.skills[tool_name]
            tools_used.append(tool_name)
            
            await self._emit_event("tool_start", {"name": tool_name, "arguments": tool_args})
            result = await self._execute_foreground_task(tool_name, skill, tool_args)
            await self._emit_event("tool_result", {
                "name": tool_name,
                "success": result.get("success", True),
            })
            return result
        
        async def on_step_start(step):
            await self._emit_event("step_start", {"id": step.step_id, "desc": step.description})
        
        async def on_step_complete(step):
            duration = (step.completed_at or 0) - (step.started_at or 0)
            await self._emit_event("step_complete", {
                "id": step.step_id,
                "status": step.status.value,
                "duration": round(duration, 2),
            })
        
        executor = PlanExecutor(
            execute_tool=execute_tool,
            on_step_start=on_step_start,
            on_step_complete=on_step_complete,
        )
        
        plan = await executor.execute_plan(plan)
        
        # 3. 汇总结果
        success = not plan.has_failure
        
        # 收集所有步骤的结果
        step_results = []
        for step in plan.steps:
            status_icon = "✅" if step.status == StepStatus.COMPLETED else "❌"
            result_text = ""
            if isinstance(step.result, dict):
                result_text = str(step.result.get("output", ""))[:200]
            elif step.result:
                result_text = str(step.result)[:200]
            if step.error:
                result_text = f"错误: {step.error}"
            step_results.append(f"{status_icon} {step.description}: {result_text}")
        
        results_text = "\n".join(step_results)
        
        # 让 LLM 生成最终汇总
        summary_messages = [
            {"role": "system", "content": self.brain.get_system_prompt()},
            {"role": "user", "content": user_input},
            {"role": "assistant", "content": f"我已按计划执行了以下步骤:\n{results_text}\n\n请让我为你总结结果。"},
        ]
        
        summary_response = await self.brain.chat(summary_messages)
        final_response = summary_response.get("content", results_text)
        
        # 保存和记录
        self.memory.add_message("assistant", final_response)
        self._record_experience(task_type, user_input, final_response, tools_used, success, start_time)
        
        log.info(f"复杂任务完成，{plan.completed_steps}/{plan.total_steps} 步成功，耗时 {time.time()-start_time:.2f}秒")
        
        return final_response
    
    # ----------------------------------------------------------------
    #  [UPGRADED] 并行工具执行
    # ----------------------------------------------------------------
    
    async def _execute_tool_calls_parallel(self, tool_calls: List[Dict], user_id: str = "default") -> List[Dict]:
        """
        并行执行工具调用
        
        所有工具调用同时执行（除了有 background 标记的）。
        """
        if len(tool_calls) == 1:
            # 单个工具调用，直接执行
            return await self._execute_tool_calls(tool_calls, user_id)
        
        # 多个工具调用，并行执行
        tasks = []
        for tool_call in tool_calls:
            tasks.append(self._execute_single_tool_call(tool_call, user_id))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        processed = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed.append({
                    "tool_call_id": tool_calls[i]["id"],
                    "name": tool_calls[i]["name"],
                    "success": False,
                    "error": str(result),
                })
            else:
                processed.append(result)
        
        return processed
    
    async def _execute_single_tool_call(self, tool_call: Dict, user_id: str) -> Dict:
        """执行单个工具调用"""
        name = tool_call["name"]
        arguments = tool_call["arguments"]
        tool_call_id = tool_call["id"]
        
        # 参数修复
        if isinstance(arguments, str):
            repaired = repair_json(arguments)
            if repaired is not None and isinstance(repaired, dict):
                arguments = repaired
            else:
                return {
                    "tool_call_id": tool_call_id,
                    "name": name,
                    "success": False,
                    "error": f"Invalid arguments format: {arguments[:200]}..."
                }
        
        if not isinstance(arguments, dict):
            return {
                "tool_call_id": tool_call_id,
                "name": name,
                "success": False,
                "error": f"Arguments must be a dictionary, got {type(arguments)}"
            }
        
        if name not in self.skills:
            return {
                "tool_call_id": tool_call_id,
                "name": name,
                "success": False,
                "error": f"Tool '{name}' not found"
            }
        
        skill = self.skills[name]
        
        # 后台检测
        run_in_background = False
        if "run_in_background" in arguments:
            run_in_background = arguments.pop("run_in_background")
        elif "background" in arguments:
            run_in_background = arguments.pop("background")
        if name == "background_task":
            run_in_background = True
        
        log.info(f"执行工具: {name}, 参数: {arguments}, 后台: {run_in_background}")
        
        if run_in_background:
            task_id = str(uuid.uuid4())
            result = await self._execute_background_task(name, skill, arguments, task_id, user_id)
        else:
            result = await self._execute_foreground_task(name, skill, arguments)
        
        result["tool_call_id"] = tool_call_id
        return result
    
    async def _execute_tool_calls(self, tool_calls: List[Dict], user_id: str = "default") -> List[Dict]:
        """执行工具调用 (兼容旧接口，顺序执行)"""
        results = []
        for tool_call in tool_calls:
            result = await self._execute_single_tool_call(tool_call, user_id)
            results.append(result)
        return results

    async def _execute_foreground_task(self, name: str, skill: Any, arguments: Dict) -> Dict:
        """前台执行任务"""
        if name not in self._skill_circuit_breakers:
            self._skill_circuit_breakers[name] = CircuitBreaker(
                failure_threshold=3,
                recovery_timeout=30.0
            )
        
        circuit_breaker = self._skill_circuit_breakers[name]
        
        try:
            async def _execute():
                # 检查是否需要确认
                if hasattr(skill, 'needs_confirmation') and skill.needs_confirmation(arguments):
                    if self._confirmation_callback:
                        confirmed = await self._confirmation_callback(
                            f"是否允许执行 '{name}' 操作？\n参数: {arguments}"
                        )
                        if not confirmed:
                            return SkillResult(
                                success=False,
                                output=None,
                                error="用户拒绝执行此操作"
                            )
                
                # 执行技能
                if asyncio.iscoroutinefunction(skill.execute):
                    output = await skill.execute(**arguments)
                else:
                    output = await asyncio.to_thread(skill.execute, **arguments)
                
                return SkillResult(
                    success=True,
                    output=output
                )
            
            result = await circuit_breaker.call(_execute)
            return self._process_skill_result(result)
                
        except Exception as e:
            recovery_strategy = self._error_handler.get_recovery_strategy(e)
            if recovery_strategy:
                log.info(f"应用恢复策略: {recovery_strategy}")
            
            retry_config = RetryConfig(
                max_attempts=2,
                base_delay=0.5,
                max_delay=5.0,
                exponential_base=2.0,
            )
            
            try:
                async def _retry():
                    return await skill.execute(**arguments)
                
                result = await self._error_handler.retry_with_backoff(
                    _retry,
                    config=retry_config,
                    context={"skill": name, "arguments": arguments}
                )
                return self._process_skill_result(result)
                
            except Exception as retry_error:
                log.error(f"技能执行失败（重试后）: {name}, 错误: {retry_error}")
                return {
                    "success": False,
                    "error": f"执行失败（已重试）: {str(retry_error)}"
                }
    
    async def _execute_background_task(self, name: str, skill: Any, arguments: Dict, task_id: str, user_id: str) -> Dict:
        """后台执行任务"""
        log.info(f"提交后台任务: {name}, 任务ID: {task_id}, 用户: {user_id}")
        
        if hasattr(skill, 'set_task_id'):
            skill.set_task_id(task_id)
        
        async def progress_callback(progress: float):
            log.debug(f"任务 {task_id} 进度: {progress * 100:.1f}%")
        
        if hasattr(skill, 'set_progress_callback'):
            skill.set_progress_callback(lambda p: asyncio.create_task(progress_callback(p)))
        
        func_to_run = functools.partial(skill.execute, **arguments)
        
        submitted_task_id = await self.task_manager.submit_task(
            name=f"{name}_task",
            func=func_to_run,
            is_background=True,
            user_id=user_id
        )
        
        log.info(f"后台任务已提交: {submitted_task_id}")
        
        return {
            "name": name,
            "success": True,
            "output": f"任务已提交到后台执行，任务ID: {submitted_task_id} (稍后会自动汇报结果)",
            "is_background": True,
            "task_id": submitted_task_id
        }
    
    # ----------------------------------------------------------------
    #  辅助方法
    # ----------------------------------------------------------------
    
    def _classify_task(self, user_input: str) -> str:
        """分类任务类型"""
        keywords_map = {
            "文件管理": ["文件", "文件夹", "创建", "删除", "移动", "复制", "读取", "写入"],
            "系统控制": ["打开", "关闭", "启动", "音量", "屏幕", "窗口"],
            "网络浏览": ["搜索", "查找", "网页", "网站", "信息"],
            "终端命令": ["执行", "运行", "命令", "终端"],
            "信息查询": ["查询", "状态", "信息", "统计"],
            "金融分析": ["股票", "行情", "K线", "涨跌", "市场"],
            "图片分析": ["图片", "截图", "看看", "识别", "照片"],
        }
        
        for task_type, keywords in keywords_map.items():
            for keyword in keywords:
                if keyword in user_input:
                    return task_type
        
        return "其他"
    
    def _format_experience(self, similar_experiences: List) -> str:
        """格式化经验注入文本"""
        if not similar_experiences:
            return ""
        
        log.info(f"注入 {len(similar_experiences)} 条成功经验到 Prompt")
        exp_lines = ["\n\n【相关成功经验参考】"]
        for i, exp in enumerate(similar_experiences):
            tools_str = ", ".join(exp.get('tools_used', []))
            time_cost = exp.get('execution_time', 0)
            exp_lines.append(f"经验 #{i+1}:")
            exp_lines.append(f"  - 用户请求: '{exp.get('user_input')}'")
            exp_lines.append(f"  - 成功路径: 使用工具 [{tools_str}]")
            exp_lines.append(f"  - 耗时: {time_cost:.2f}s")
            exp_lines.append(f"  - 建议: 请参考此工具组合路径来解决当前问题。")
        return "\n".join(exp_lines)
    
    def _record_experience(
        self, task_type: str, user_input: str, response: str,
        tools_used: List[str], success: bool, start_time: float
    ):
        """记录经验到进化引擎"""
        execution_time = time.time() - start_time
        if self.evolution_engine:
            self.evolution_engine.record_experience(
                task_type=task_type,
                user_input=user_input,
                response=response if isinstance(response, str) else str(response),
                tools_used=tools_used,
                success=success,
                execution_time=execution_time,
                context=self.context.get_system_state()
            )
    
    def _process_skill_result(self, result: Any) -> Dict:
        """处理技能执行结果，确保可序列化"""
        if isinstance(result, SkillResult):
            result_dict = {
                "success": result.success,
                "output": result.output,
                "error": result.error,
                "visualization": result.visualization,
                "attachments": result.attachments
            }
        else:
            result_dict = {
                "success": True,
                "output": result
            }
        
        try:
            json.dumps(result_dict, ensure_ascii=False)
            return result_dict
        except (TypeError, ValueError):
            clean_dict = {
                "success": result_dict.get("success", True),
                "output": str(result_dict.get("output")) if result_dict.get("output") is not None else None,
                "error": result_dict.get("error")
            }
            if result_dict.get("visualization"):
                clean_dict["visualization"] = result_dict.get("visualization")
            if result_dict.get("attachments"):
                clean_dict["attachments"] = result_dict.get("attachments")
            return clean_dict
    
    async def simple_respond(self, user_input: str) -> str:
        """简单回复模式（不使用工具）"""
        self.memory.add_message("user", user_input)
        
        messages = self.memory.get_context_with_memory(user_input)
        messages.insert(0, {
            "role": "system",
            "content": self._build_system_prompt()
        })
        
        response = await self.brain.chat(messages)
        reply = response.get("content", "")
        
        self.memory.add_message("assistant", reply)
        
        return reply
