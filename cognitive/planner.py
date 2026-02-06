"""
JARVIS ReAct 任务规划器
实现 Reasoning + Acting 循环

Author: gngdingghuan
"""

import json
import re
from typing import Dict, List, Any, Optional, Callable

from cognitive.llm_brain import LLMBrain
from cognitive.memory import MemoryManager
from cognitive.context_manager import ContextManager
from cognitive.self_evolution import SelfEvolutionEngine
from cognitive.task_manager import TaskManager, TaskStatus
from utils.logger import log
from skills.base_skill import SkillResult
from utils.error_handler import (
    ErrorHandler,
    RetryConfig,
    CircuitBreaker,
)
import time
import uuid


class ReActPlanner:
    """
    ReAct 任务规划器
    实现 感知 -> 思考 -> 行动 -> 观察 -> 反思 循环
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
        
        # 工具使用跟踪（用于进化学习）
        self._last_used_tools: List[str] = []
        
        log.info(f"ReAct 规划器初始化完成，已注册 {len(self.skills)} 个技能")
    
    def register_skill(self, name: str, skill: Any):
        """注册技能"""
        self.skills[name] = skill
        log.debug(f"已注册技能: {name}")
    
    def set_confirmation_callback(self, callback: Callable):
        """设置确认回调函数"""
        self._confirmation_callback = callback
    
    def get_task_manager(self) -> TaskManager:
        """获取任务管理器"""
        return self.task_manager
    
    def _get_tools_schema(self) -> List[Dict]:
        """获取所有技能的 Function Calling Schema"""
        tools = []
        for name, skill in self.skills.items():
            if hasattr(skill, 'get_schema'):
                schema = skill.get_schema()
                if schema:
                    tools.append(schema)
        return tools
    
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
3. 对于危险操作，系统会自动请求用户确认
4. 如果无法完成任务，请如实告知原因"""
        
        return full_prompt
    
    async def plan_and_execute(self, user_input: str, user_id: str = "default") -> str:
        """
        规划并执行任务（带自我进化）
        
        Args:
            user_input: 用户输入
            user_id: 用户标识
            
        Returns:
            最终回复
        """
        start_time = time.time()
        task_type = self._classify_task(user_input)
        
        log.info(f"收到用户请求: {user_input[:50]}... (User: {user_id})")
        log.debug(f"任务类型: {task_type}")
        
        if self.evolution_engine:
            prediction = self.evolution_engine.predict_next_action(user_input)
            if prediction:
                log.info(f"预测任务: {prediction['task_type']} (置信度: {prediction['confidence']:.1%})")
                log.debug(f"建议工具: {prediction['suggested_tools']}")
            
            # [新增] 检索相似的成功经验 (使用任务类型过滤，提高准确性)
            similar_experiences = self.evolution_engine.search_similar_experience(
                user_input, 
                task_type=task_type,
                limit=10
            )
        else:
            similar_experiences = []
        
        # 保存到短期记忆
        self.memory.add_message("user", user_input)
        
        # 获取上下文和历史
        messages = []
        
        # [新增] Holo-Mem 混合语境检索 (Graph + Vector)
        holo_context = await self.memory.retrieve_context_hybrid(user_input)
        holo_context_text = ""
        if holo_context:
            holo_context_text = "\n\n## 动态语境 (Holo-Mem)\n" + "\n".join(holo_context)

        # 系统提示词
        base_system_prompt = self._build_system_prompt()
        
        # [新增] 注入经验到系统提示词 (优化版)
        experience_text = ""
        if similar_experiences:
            exp_lines = ["\n\n【相关成功经验参考】"]
            for i, exp in enumerate(similar_experiences):
                tools_str = ", ".join(exp.get('tools_used', []))
                time_cost = exp.get('execution_time', 0)
                exp_lines.append(f"经验 #{i+1}:")
                exp_lines.append(f"  - 用户请求: '{exp.get('user_input')}'")
                exp_lines.append(f"  - 成功路径: 使用工具 [{tools_str}]")
                exp_lines.append(f"  - 耗时: {time_cost:.2f}s")
                exp_lines.append(f"  - 建议: 请参考此工具组合路径来解决当前问题。")
            experience_text = "\n".join(exp_lines)
            
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
        attachments = []  # 收集文件附件
        success = True
        
        while iteration < self.MAX_ITERATIONS:
            iteration += 1
            log.debug(f"ReAct 循环第 {iteration} 次")
            
            try:
                # 调用 LLM
                response = await self.brain.chat(messages, tools=tools if tools else None)
                
                # 检查是否有工具调用
                if response.get("tool_calls"):
                    # 记录使用的工具
                    for tc in response["tool_calls"]:
                        if tc["name"] not in tools_used:
                            tools_used.append(tc["name"])
                    
                    # 执行工具调用
                    tool_results = await self._execute_tool_calls(response["tool_calls"])
                    
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
                            for tc in response["tool_calls"]
                        ]
                    })
                    
                    for tc, result in zip(response["tool_calls"], tool_results):
                        # [新增] 如果失败，尝试分析原因并注入到上下文中
                        extra_info = ""
                        if not result.get("success", True) and self.evolution_engine:
                            error_msg = result.get("error", "Unknown error")
                            suggestion = self.evolution_engine.analyze_failure(error_msg, str(tc))
                            if suggestion:
                                extra_info = f"\n[JARVIS Evolution Suggestion]: 检测到错误，建议尝试: {suggestion}"
                                log.info(f"应用进化建议: {suggestion}")
                        
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": json.dumps(result, ensure_ascii=False) + extra_info
                        })
                        
                        # 收集可视化数据
                        if isinstance(result, dict) and "visualization" in result and result["visualization"]:
                            visualizations.append(result["visualization"])
                        
                        # 收集文件附件
                        if isinstance(result, dict) and "attachments" in result and result["attachments"]:
                            attachments.extend(result["attachments"])
                    
                    # 继续循环，让 LLM 处理结果
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
        
        # 保存回复到记忆
        self.memory.add_message("assistant", final_response)
        
        # 记录经验到自我进化引擎
        execution_time = time.time() - start_time
        if self.evolution_engine:
            self.evolution_engine.record_experience(
                task_type=task_type,
                user_input=user_input,
                response=final_response,
                tools_used=tools_used,
                success=success,
                execution_time=execution_time,
                context=self.context.get_system_state()
            )
        
        log.info(f"请求处理完成，共 {iteration} 次循环，耗时 {execution_time:.2f}秒")
        
        # 返回结果和可视化数据
        if visualizations or attachments:
            return {
                "content": final_response,
                "visualizations": visualizations,
                "attachments": attachments
            }
        else:
            return final_response
    
    def _classify_task(self, user_input: str) -> str:
        """
        分类任务类型
        
        Args:
            user_input: 用户输入
            
        Returns:
            任务类型
        """
        # 简单关键词匹配分类
        keywords_map = {
            "文件管理": ["文件", "文件夹", "创建", "删除", "移动", "复制", "读取", "写入"],
            "系统控制": ["打开", "关闭", "启动", "音量", "屏幕", "窗口"],
            "网络浏览": ["搜索", "查找", "网页", "网站", "信息"],
            "终端命令": ["执行", "运行", "命令", "终端"],
            "信息查询": ["查询", "状态", "信息", "统计"],
        }
        
        for task_type, keywords in keywords_map.items():
            for keyword in keywords:
                if keyword in user_input:
                    return task_type
        
        return "其他"
    
    async def _execute_tool_calls(self, tool_calls: List[Dict], user_id: str = "default") -> List[Dict]:
        """执行工具调用（带自动重试和错误处理，支持后台任务）"""
        results = []
        
        for tool_call in tool_calls:
            # LLMBrain 返回的是简化结构: {"id":..., "name":..., "arguments":...}
            # 且 arguments 已经是 dict
            name = tool_call["name"]
            arguments = tool_call["arguments"]
            tool_call_id = tool_call["id"]
            
            # double check: 如果 arguments 是字符串 (兼容性)
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except:
                    pass
            
            # 检查技能是否存在
            if name not in self.skills:
                results.append({
                    "tool_call_id": tool_call_id,
                    "name": name,
                    "success": False,
                    "error": f"Tool '{name}' not found"
                })
                continue
            
            skill = self.skills[name]
            
            # 检测是否请求后台执行
            run_in_background = False
            if "run_in_background" in arguments:
                run_in_background = arguments.pop("run_in_background")
            elif "background" in arguments:
                run_in_background = arguments.pop("background")
            
            # 手动指定的后台技能强制后台运行
            if name == "background_task":
                run_in_background = True
            
            log.info(f"执行工具: {name}, 参数: {arguments}, 后台: {run_in_background}")
            
            if run_in_background:
                # 后台执行
                task_id = str(uuid.uuid4())
                result = await self._execute_background_task(name, skill, arguments, task_id, user_id)
                result["tool_call_id"] = tool_call_id
                results.append(result)
            else:
                # 前台执行
                result = await self._execute_foreground_task(name, skill, arguments)
                result["tool_call_id"] = tool_call_id
                results.append(result)
        
        return results

    async def _execute_foreground_task(self, name: str, skill: Any, arguments: Dict) -> Dict:
        """前台执行任务"""
        # 获取或创建该技能的熔断器
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
                    # 在线程池中执行同步技能
                    output = await asyncio.to_thread(skill.execute, **arguments)
                
                return SkillResult(
                    success=True,
                    output=output
                )
            
            # 通过熔断器执行
            result = await circuit_breaker.call(_execute)
            
            return self._process_skill_result(result)
                
        except Exception as e:
            # 检查历史错误模式，获取恢复策略
            recovery_strategy = self._error_handler.get_recovery_strategy(e)
            
            if recovery_strategy:
                log.info(f"应用恢复策略: {recovery_strategy}")
            
            # 尝试使用错误处理器重试
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
        
        # 设置技能的 task_id
        if hasattr(skill, 'set_task_id'):
            skill.set_task_id(task_id)
        
        # 创建进度回调
        async def progress_callback(progress: float):
            log.debug(f"任务 {task_id} 进度: {progress * 100:.1f}%")
        
        # 设置进度回调
        if hasattr(skill, 'set_progress_callback'):
            skill.set_progress_callback(lambda p: asyncio.create_task(progress_callback(p)))
        
        # 使用 partial 绑定参数，避免参数名与 submit_task 的参数（如 name）冲突
        import functools
        func_to_run = functools.partial(skill.execute, **arguments)
        
        # 提交任务到任务管理器
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
    
    def _process_skill_result(self, result: Any) -> Dict:
        """处理技能执行结果，确保可序列化"""
        if isinstance(result, SkillResult):
            result_dict = {
                "success": result.success,
                "output": result.output,
                "error": result.error,
                "visualization": result.visualization
            }
            # 检查 output 是否可序列化
            try:
                json.dumps(result_dict, ensure_ascii=False)
                return result_dict
            except (TypeError, ValueError):
                # 如果 output 不可序列化，转换为字符串
                return {
                    "success": result.success,
                    "output": str(result.output) if result.output is not None else None,
                    "error": result.error
                }
        else:
            # 处理非 SkillResult 结果
            try:
                json.dumps(result, ensure_ascii=False)
                return {
                    "success": True,
                    "output": result
                }
            except (TypeError, ValueError):
                # 如果结果不可序列化，转换为字符串
                return {
                    "success": True,
                    "output": str(result) if result is not None else None
                }
    
    async def simple_respond(self, user_input: str) -> str:
        """
        简单回复模式（不使用工具）
        
        Args:
            user_input: 用户输入
            
        Returns:
            AI 回复
        """
        self.memory.add_message("user", user_input)
        
        messages = self.memory.get_context_with_memory(user_input)
        messages.insert(0, {
            "role": "system",
            "content": self._build_system_prompt()  # 使用包含时间的系统提示词
        })
        
        response = await self.brain.chat(messages)
        reply = response.get("content", "")
        
        self.memory.add_message("assistant", reply)
        
        return reply
