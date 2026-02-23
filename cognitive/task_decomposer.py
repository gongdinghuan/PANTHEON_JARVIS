"""
JARVIS 任务分解器
将复杂任务分解为可执行的子步骤 DAG，支持并行执行

Author: gngdingghuan
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

from cognitive.llm_brain import LLMBrain
from utils.logger import log


class StepStatus(Enum):
    """子步骤状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TaskStep:
    """任务子步骤"""
    step_id: str
    description: str
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    depends_on: List[str] = field(default_factory=list)
    status: StepStatus = StepStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None


@dataclass
class TaskPlan:
    """任务执行计划"""
    goal: str
    steps: List[TaskStep] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    
    @property
    def total_steps(self) -> int:
        return len(self.steps)
    
    @property
    def completed_steps(self) -> int:
        return sum(1 for s in self.steps if s.status == StepStatus.COMPLETED)
    
    @property
    def is_complete(self) -> bool:
        return all(s.status in (StepStatus.COMPLETED, StepStatus.SKIPPED) for s in self.steps)
    
    @property
    def has_failure(self) -> bool:
        return any(s.status == StepStatus.FAILED for s in self.steps)
    
    def get_ready_steps(self) -> List[TaskStep]:
        """获取所有依赖已满足的待执行步骤"""
        completed_ids = {s.step_id for s in self.steps if s.status == StepStatus.COMPLETED}
        ready = []
        for step in self.steps:
            if step.status == StepStatus.PENDING:
                if all(dep in completed_ids for dep in step.depends_on):
                    ready.append(step)
        return ready
    
    def get_step(self, step_id: str) -> Optional[TaskStep]:
        """获取指定步骤"""
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None

    def summary(self) -> str:
        """生成计划摘要"""
        lines = [f"目标: {self.goal}", f"步骤数: {self.total_steps}", ""]
        for step in self.steps:
            deps = f" (依赖: {', '.join(step.depends_on)})" if step.depends_on else ""
            status_icon = {
                StepStatus.PENDING: "⏳",
                StepStatus.RUNNING: "🔄",
                StepStatus.COMPLETED: "✅",
                StepStatus.FAILED: "❌",
                StepStatus.SKIPPED: "⏭️",
            }.get(step.status, "?")
            lines.append(f"  {status_icon} [{step.step_id}] {step.description}{deps}")
        return "\n".join(lines)


class TaskDecomposer:
    """
    任务分解器
    
    将复杂请求分解为可执行的子步骤计划：
    1. 使用 LLM 分析任务，生成结构化计划
    2. 按依赖关系构建 DAG
    3. 并行执行无依赖的步骤
    """
    
    DECOMPOSE_PROMPT = """你是一个任务规划专家。请将用户的请求分解为具体的执行步骤。

### 可用工具
{tools_description}

### 规则
1. 每个步骤应该对应一个具体的工具调用或简单操作
2. 步骤之间的依赖关系要明确
3. 如果多个步骤互不依赖，可以标记为并行执行
4. 如果请求简单（1-2 步即可完成），不要过度分解

### 输出格式 (严格 JSON)
{{
  "goal": "简短描述最终目标",
  "complexity": "simple|moderate|complex",
  "steps": [
    {{
      "step_id": "step_1",
      "description": "做什么",
      "tool_name": "工具名称 (如果需要)",
      "tool_args": {{}},
      "depends_on": []
    }}
  ]
}}

### 用户请求
{user_input}"""
    
    def __init__(self, brain: LLMBrain, available_tools: Optional[Dict[str, str]] = None):
        """
        Args:
            brain: LLM 大脑
            available_tools: 可用工具字典 {tool_name: description}
        """
        self.brain = brain
        self.available_tools = available_tools or {}
    
    def update_tools(self, tools: Dict[str, str]):
        """更新可用工具列表"""
        self.available_tools = tools
    
    async def decompose(self, user_input: str) -> TaskPlan:
        """
        使用 LLM 将用户输入分解为执行计划
        
        Args:
            user_input: 用户输入
            
        Returns:
            TaskPlan 对象
        """
        # 构建工具描述
        tools_desc = "\n".join(
            f"- {name}: {desc}" for name, desc in self.available_tools.items()
        ) if self.available_tools else "暂无可用工具"
        
        prompt = self.DECOMPOSE_PROMPT.format(
            tools_description=tools_desc,
            user_input=user_input,
        )
        
        try:
            # 尝试使用结构化输出
            response = await self.brain.chat(
                messages=[
                    {"role": "system", "content": "你是一个精确的任务规划器。只输出 JSON，不要包含任何其他文本。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )
            
            content = response.get("content", "").strip()
            
            # 清理 markdown 标记
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            plan_data = json.loads(content)
            return self._build_plan(plan_data)
            
        except json.JSONDecodeError as e:
            log.warning(f"任务分解 JSON 解析失败: {e}")
            # 回退：创建一个单步骤计划
            return TaskPlan(
                goal=user_input,
                steps=[TaskStep(
                    step_id="step_1",
                    description=user_input,
                )]
            )
        except Exception as e:
            log.error(f"任务分解失败: {e}")
            return TaskPlan(
                goal=user_input,
                steps=[TaskStep(
                    step_id="step_1",
                    description=user_input,
                )]
            )
    
    def _build_plan(self, plan_data: Dict) -> TaskPlan:
        """从 LLM 输出构建 TaskPlan"""
        steps = []
        for step_data in plan_data.get("steps", []):
            steps.append(TaskStep(
                step_id=step_data.get("step_id", f"step_{len(steps)+1}"),
                description=step_data.get("description", ""),
                tool_name=step_data.get("tool_name"),
                tool_args=step_data.get("tool_args"),
                depends_on=step_data.get("depends_on", []),
            ))
        
        return TaskPlan(
            goal=plan_data.get("goal", ""),
            steps=steps,
        )
    
    def estimate_complexity(self, user_input: str) -> str:
        """
        快速估算任务复杂度 (不调用 LLM)
        
        Returns:
            "simple" | "moderate" | "complex"
        """
        # 简单启发式规则
        input_len = len(user_input)
        
        # 复杂指标关键词
        complex_keywords = ["并且", "然后", "同时", "之后", "首先", "最后", "接着",
                           "步骤", "流程", "报告", "分析", "对比", "综合"]
        complex_count = sum(1 for kw in complex_keywords if kw in user_input)
        
        if complex_count >= 3 or input_len > 200:
            return "complex"
        elif complex_count >= 1 or input_len > 80:
            return "moderate"
        else:
            return "simple"


class PlanExecutor:
    """
    计划执行器
    
    按照 DAG 依赖关系执行 TaskPlan，支持并行。
    """
    
    def __init__(
        self,
        execute_tool: Callable,
        on_step_start: Optional[Callable] = None,
        on_step_complete: Optional[Callable] = None,
    ):
        """
        Args:
            execute_tool: 工具执行函数 async (tool_name, tool_args) -> result
            on_step_start: 步骤开始回调 (step)
            on_step_complete: 步骤完成回调 (step)
        """
        self.execute_tool = execute_tool
        self.on_step_start = on_step_start
        self.on_step_complete = on_step_complete
    
    async def execute_plan(self, plan: TaskPlan) -> TaskPlan:
        """
        执行计划，按依赖关系并行执行
        
        Args:
            plan: 要执行的计划
            
        Returns:
            更新后的计划 (包含执行结果)
        """
        max_rounds = len(plan.steps) + 1  # 防止无限循环
        
        for _ in range(max_rounds):
            if plan.is_complete or plan.has_failure:
                break
            
            ready_steps = plan.get_ready_steps()
            if not ready_steps:
                break
            
            # 并行执行所有就绪的步骤
            if len(ready_steps) == 1:
                await self._execute_step(ready_steps[0])
            else:
                log.info(f"并行执行 {len(ready_steps)} 个步骤: {[s.step_id for s in ready_steps]}")
                tasks = [self._execute_step(step) for step in ready_steps]
                await asyncio.gather(*tasks, return_exceptions=True)
        
        return plan
    
    async def _execute_step(self, step: TaskStep):
        """执行单个步骤"""
        step.status = StepStatus.RUNNING
        step.started_at = time.time()
        
        if self.on_step_start:
            try:
                if asyncio.iscoroutinefunction(self.on_step_start):
                    await self.on_step_start(step)
                else:
                    self.on_step_start(step)
            except Exception:
                pass
        
        try:
            if step.tool_name and self.execute_tool:
                result = await self.execute_tool(step.tool_name, step.tool_args or {})
                step.result = result
                
                # 判断是否成功
                if isinstance(result, dict):
                    step.status = StepStatus.COMPLETED if result.get("success", True) else StepStatus.FAILED
                    step.error = result.get("error")
                else:
                    step.status = StepStatus.COMPLETED
            else:
                # 无工具调用的步骤（如纯描述）标记为完成
                step.status = StepStatus.COMPLETED
                step.result = {"output": step.description}
        
        except Exception as e:
            step.status = StepStatus.FAILED
            step.error = str(e)
            log.error(f"步骤 {step.step_id} 执行失败: {e}")
        
        finally:
            step.completed_at = time.time()
            if self.on_step_complete:
                try:
                    if asyncio.iscoroutinefunction(self.on_step_complete):
                        await self.on_step_complete(step)
                    else:
                        self.on_step_complete(step)
                except Exception:
                    pass
