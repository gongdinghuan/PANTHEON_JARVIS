"""
JARVIS 自我进化和学习模块
通过经验学习和模式识别，持续优化系统性能和用户体验

Author: gngdingghuan
"""

import json
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import Counter, defaultdict
import statistics

from cognitive.memory import MemoryManager
from utils.logger import log


@dataclass
class Experience:
    """经验记录"""
    timestamp: str
    task_type: str
    user_input: str
    response: str
    tools_used: List[str]
    success: bool
    user_feedback: Optional[str] = None
    execution_time: float = 0.0
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserPreference:
    """用户偏好"""
    preference_type: str
    key: str
    value: Any
    confidence: float
    last_updated: str
    usage_count: int = 0


@dataclass
class Pattern:
    """使用模式"""
    pattern_type: str
    pattern_data: Dict[str, Any]
    frequency: int
    last_seen: str
    prediction_accuracy: float = 0.0


class SelfEvolutionEngine:
    """
    自我进化引擎
    - 经验学习
    - 用户偏好识别
    - 模式预测
    - 知识积累
    - 性能优化
    """
    
    def __init__(self, memory: MemoryManager):
        self.memory = memory
        self._experiences: List[Experience] = []
        self._user_preferences: Dict[str, List[UserPreference]] = defaultdict(list)
        self._patterns: Dict[str, List[Pattern]] = defaultdict(list)
        self._knowledge_base: Dict[str, List[Dict]] = defaultdict(list)
        
        self._load_state()
        log.info("自我进化引擎初始化完成")
    
    def record_experience(
        self,
        task_type: str,
        user_input: str,
        response: str,
        tools_used: List[str],
        success: bool,
        execution_time: float = 0.0,
        user_feedback: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """
        记录经验
        
        Args:
            task_type: 任务类型
            user_input: 用户输入
            response: 系统响应
            tools_used: 使用的工具列表
            success: 是否成功
            execution_time: 执行时间（秒）
            user_feedback: 用户反馈
            context: 上下文信息
        """
        experience = Experience(
            timestamp=datetime.now().isoformat(),
            task_type=task_type,
            user_input=user_input,
            response=response,
            tools_used=tools_used,
            success=success,
            execution_time=execution_time,
            user_feedback=user_feedback,
            context=context or {}
        )
        
        self._experiences.append(experience)
        
        # 保存到长期记忆
        self._save_experience(experience)
        
        # 分析并学习
        self._learn_from_experience(experience)
        
        # 限制内存中的经验数量
        if len(self._experiences) > 1000:
            self._experiences = self._experiences[-1000:]
    
    def _save_experience(self, experience: Experience):
        """保存经验到长期记忆"""
        # 检查 ChromaDB collection 是否可用
        if not self.memory._collection:
            return
        
        try:
            record = {
                "timestamp": experience.timestamp,
                "task_type": experience.task_type,
                "user_input": experience.user_input,
                "response": experience.response,
                "tools_used": experience.tools_used,
                "success": experience.success,
                "execution_time": experience.execution_time,
                "user_feedback": experience.user_feedback,
            }
            
            self.memory._collection.add(
                documents=[json.dumps(record, ensure_ascii=False)],
                metadatas=[{
                    "type": "experience",
                    "task_type": experience.task_type,
                    "timestamp": experience.timestamp,
                    "success": str(experience.success)
                }],
                ids=[f"exp_{datetime.now().timestamp()}"]
            )
        except Exception as e:
            log.warning(f"保存经验到记忆失败: {e}")
    
    def _learn_from_experience(self, experience: Experience):
        """从经验中学习"""
        # 学习用户偏好
        self._learn_preferences(experience)
        
        # 识别模式
        self._identify_patterns(experience)
        
        # 提取知识
        self._extract_knowledge(experience)
    
    def _learn_preferences(self, experience: Experience):
        """学习用户偏好"""
        # 学习偏好的工具
        for tool in experience.tools_used:
            self._update_preference(
                preference_type="tool",
                key=tool,
                value=tool,
                confidence=0.1 if experience.success else -0.05
            )
        
        # 学习任务偏好
        self._update_preference(
            preference_type="task",
            key=experience.task_type,
            value=experience.task_type,
            confidence=0.1 if experience.success else -0.05
        )
        
        # 学习时间偏好
        hour = datetime.fromisoformat(experience.timestamp).hour
        time_period = self._get_time_period(hour)
        self._update_preference(
            preference_type="time",
            key=time_period,
            value=time_period,
            confidence=0.05
        )
        
        # 从用户反馈学习
        if experience.user_feedback:
            feedback_lower = experience.user_feedback.lower()
            
            if "好" in feedback_lower or "优秀" in feedback_lower or "thanks" in feedback_lower:
                self._update_preference(
                    preference_type="positive_response",
                    key="quality",
                    value="high",
                    confidence=0.2
                )
            elif "慢" in feedback_lower or "太慢" in feedback_lower:
                self._update_preference(
                    preference_type="performance",
                    key="speed",
                    value="fast",
                    confidence=0.15
                )
    
    def _update_preference(
        self,
        preference_type: str,
        key: str,
        value: Any,
        confidence: float
    ):
        """更新偏好"""
        # 查找现有偏好
        existing = None
        for pref in self._user_preferences[preference_type]:
            if pref.key == key:
                existing = pref
                break
        
        if existing:
            # 更新置信度
            existing.confidence += confidence
            existing.confidence = max(0.0, min(1.0, existing.confidence))
            existing.usage_count += 1
            existing.last_updated = datetime.now().isoformat()
        else:
            # 创建新偏好
            self._user_preferences[preference_type].append(
                UserPreference(
                    preference_type=preference_type,
                    key=key,
                    value=value,
                    confidence=abs(confidence),
                    last_updated=datetime.now().isoformat(),
                    usage_count=1
                )
            )
        
        # 清理低置信度的偏好
        self._user_preferences[preference_type] = [
            p for p in self._user_preferences[preference_type]
            if p.confidence > 0.1 or p.usage_count > 3
        ]
    
    def _identify_patterns(self, experience: Experience):
        """识别使用模式"""
        # 时间模式
        hour = datetime.fromisoformat(experience.timestamp).hour
        time_period = self._get_time_period(hour)
        
        self._update_pattern(
            pattern_type="time",
            pattern_data={
                "period": time_period,
                "task_type": experience.task_type
            }
        )
        
        # 工具组合模式
        if len(experience.tools_used) > 1:
            tools_key = "+".join(sorted(experience.tools_used))
            
            self._update_pattern(
                pattern_type="tool_combination",
                pattern_data={
                    "combination": tools_key,
                    "task_type": experience.task_type
                }
            )
        
        # 输入模式
        words = self._extract_keywords(experience.user_input)
        
        for word in words:
            self._update_pattern(
                pattern_type="keyword",
                pattern_data={
                    "keyword": word,
                    "task_type": experience.task_type
                }
            )
    
    def _update_pattern(self, pattern_type: str, pattern_data: Dict[str, Any]):
        """更新模式"""
        # 生成唯一键
        pattern_key = json.dumps(pattern_data, sort_keys=True)
        
        # 查找现有模式
        existing = None
        for pattern in self._patterns[pattern_type]:
            if json.dumps(pattern.pattern_data, sort_keys=True) == pattern_key:
                existing = pattern
                break
        
        if existing:
            existing.frequency += 1
            existing.last_seen = datetime.now().isoformat()
        else:
            self._patterns[pattern_type].append(
                Pattern(
                    pattern_type=pattern_type,
                    pattern_data=pattern_data,
                    frequency=1,
                    last_seen=datetime.now().isoformat()
                )
            )
        
        # 限制模式数量
        if len(self._patterns[pattern_type]) > 100:
            self._patterns[pattern_type] = sorted(
                self._patterns[pattern_type],
                key=lambda p: p.frequency,
                reverse=True
            )[:100]
    
    def _extract_knowledge(self, experience: Experience):
        """从经验中提取知识"""
        # 提取成功的工作流程
        if experience.success and experience.tools_used:
            workflow = {
                "task_type": experience.task_type,
                "tools": experience.tools_used,
                "success_rate": 1.0,
                "timestamp": experience.timestamp
            }
            
            self._knowledge_base["workflows"].append(workflow)
            
            # 限制知识库大小
            if len(self._knowledge_base["workflows"]) > 50:
                # 保留最成功的
                self._knowledge_base["workflows"] = sorted(
                    self._knowledge_base["workflows"],
                    key=lambda x: x.get("success_rate", 0),
                    reverse=True
                )[:50]
        
        # 提取 FAQ 知识
        if experience.success:
            faq = {
                "question": experience.user_input,
                "answer": experience.response,
                "confidence": 0.5,
                "timestamp": experience.timestamp
            }
            
            self._knowledge_base["faq"].append(faq)
            
            if len(self._knowledge_base["faq"]) > 100:
                self._knowledge_base["faq"] = self._knowledge_base["faq"][-100:]
    
    def predict_next_action(self, user_input: str) -> Optional[Dict[str, Any]]:
        """
        预测下一个可能的操作
        
        Args:
            user_input: 用户输入
            
        Returns:
            预测结果，包含 task_type, confidence, suggested_tools
        """
        words = self._extract_keywords(user_input)
        
        # 基于关键词预测任务类型
        task_scores = defaultdict(float)
        
        for word in words:
            for pattern in self._patterns["keyword"]:
                if pattern.pattern_data.get("keyword") == word:
                    task_type = pattern.pattern_data.get("task_type")
                    task_scores[task_type] += pattern.frequency * 0.3
        
        # 基于时间预测
        hour = datetime.now().hour
        time_period = self._get_time_period(hour)
        
        for pattern in self._patterns["time"]:
            if pattern.pattern_data.get("period") == time_period:
                task_type = pattern.pattern_data.get("task_type")
                task_scores[task_type] += pattern.frequency * 0.2
        
        # 基于用户偏好
        for pref in self._user_preferences["task"]:
            task_scores[pref.key] += pref.confidence * 10
        
        # 找出最可能的任务
        if task_scores:
            best_task = max(task_scores.items(), key=lambda x: x[1])
            
            # 查找该任务的推荐工具
            suggested_tools = []
            for exp in self._experiences[-50:]:
                if exp.task_type == best_task[0] and exp.success:
                    for tool in exp.tools_used:
                        if tool not in suggested_tools:
                            suggested_tools.append(tool)
            
            return {
                "task_type": best_task[0],
                "confidence": min(0.95, best_task[1] / 10),
                "suggested_tools": suggested_tools[:3]
            }
        
        return None
    
    def get_optimization_suggestions(self) -> List[str]:
        """获取优化建议"""
        suggestions = []
        
        # 分析最近的经验
        recent_experiences = self._experiences[-100:]
        
        if not recent_experiences:
            return ["暂无足够数据进行优化"]
        
        # 1. 分析成功率
        success_rate = sum(1 for e in recent_experiences if e.success) / len(recent_experiences)
        
        if success_rate < 0.7:
            suggestions.append(
                f"成功率较低 ({success_rate:.1%})，建议检查工具配置和 API 密钥"
            )
        
        # 2. 分析执行时间
        avg_time = statistics.mean(e.execution_time for e in recent_experiences if e.execution_time > 0)
        
        if avg_time > 5.0:
            suggestions.append(
                f"平均响应时间较长 ({avg_time:.1f}秒)，建议优化工作流程或使用更快的 LLM 模型"
            )
        
        # 3. 分析工具使用
        tool_usage = Counter()
        for exp in recent_experiences:
            for tool in exp.tools_used:
                tool_usage[tool] += 1
        
        if tool_usage:
            most_used = tool_usage.most_common(3)
            suggestions.append(
                f"最常用的工具: {', '.join(t[0] for t in most_used)}"
            )
            
            # 检查是否有工具组合模式
            for i, (tool, count) in enumerate(most_used):
                if i < len(most_used) - 1:
                    next_tool = most_used[i + 1][0]
                    combination = f"{tool}+{next_tool}"
                    suggestions.append(
                        f"工具组合 '{combination}' 使用频繁，考虑创建快捷技能"
                    )
        
        # 4. 分析时间模式
        hourly_activity = defaultdict(int)
        for exp in recent_experiences:
            hour = datetime.fromisoformat(exp.timestamp).hour
            hourly_activity[hour] += 1
        
        peak_hours = sorted(hourly_activity.items(), key=lambda x: x[1], reverse=True)[:3]
        if peak_hours:
            suggestions.append(
                f"最活跃时段: {', '.join(f'{h}:00' for h, _ in peak_hours)}"
            )
        
        # 5. 分析用户偏好
        if self._user_preferences["tool"]:
            top_tools = sorted(
                self._user_preferences["tool"],
                key=lambda p: p.confidence,
                reverse=True
            )[:3]
            suggestions.append(
                f"用户偏好工具: {', '.join(t.key for t in top_tools)}"
            )
        
        return suggestions[:10]
    
    def get_learned_knowledge(self, topic: str, limit: int = 5) -> List[Dict]:
        """
        获取已学习的知识
        
        Args:
            topic: 主题关键词
            limit: 返回数量限制
            
        Returns:
            相关知识列表
        """
        # 检查 ChromaDB collection 是否可用
        if not self.memory._collection:
            return []
        
        try:
            results = self.memory._collection.query(
                query_texts=[topic],
                n_results=limit,
                where={"type": "experience"}
            )
            
            if not results.get("metadatas"):
                return []
            
            knowledge = []
            for i, metadata in enumerate(results["metadatas"][0]):
                knowledge.append({
                    "task_type": metadata.get("task_type"),
                    "success": metadata.get("success") == "True",
                    "timestamp": metadata.get("timestamp")
                })
            
            return knowledge
            
        except Exception as e:
            log.warning(f"获取学习知识失败: {e}")
            return []
    
    def get_evolution_stats(self) -> Dict[str, Any]:
        """获取进化统计"""
        total_experiences = len(self._experiences)
        
        if total_experiences == 0:
            return {
                "total_experiences": 0,
                "success_rate": 0.0,
                "preferences_learned": 0,
                "patterns_identified": 0,
                "knowledge_items": 0
            }
        
        recent_experiences = self._experiences[-100:]
        success_count = sum(1 for e in recent_experiences if e.success)
        success_rate = success_count / len(recent_experiences)
        
        avg_time = 0.0
        timed_experiences = [e for e in recent_experiences if e.execution_time > 0]
        if timed_experiences:
            avg_time = statistics.mean(e.execution_time for e in timed_experiences)
        
        total_preferences = sum(len(prefs) for prefs in self._user_preferences.values())
        total_patterns = sum(len(patterns) for patterns in self._patterns.values())
        total_knowledge = sum(len(items) for items in self._knowledge_base.values())
        
        return {
            "total_experiences": total_experiences,
            "recent_success_rate": success_rate,
            "avg_execution_time": avg_time,
            "preferences_learned": total_preferences,
            "patterns_identified": total_patterns,
            "knowledge_items": total_knowledge,
            "top_preferences": {
                pref_type: sorted(prefs, key=lambda p: p.confidence, reverse=True)[:3]
                for pref_type, prefs in self._user_preferences.items()
            }
        }
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 移除标点和特殊字符
        cleaned = re.sub(r'[^\w\s\u4e00-\u9fff]', '', text.lower())
        
        # 分词（支持中英文）
        words = cleaned.split()
        
        # 过滤停用词
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 
                    'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 
                    'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                    '的', '是', '在', '有', '我', '你', '他', '她', '它', '我们', '你们'}
        
        keywords = [w for w in words if w not in stop_words and len(w) > 1]
        
        return keywords
    
    def _get_time_period(self, hour: int) -> str:
        """获取时间段"""
        if 5 <= hour < 9:
            return "早晨"
        elif 9 <= hour < 12:
            return "上午"
        elif 12 <= hour < 14:
            return "中午"
        elif 14 <= hour < 18:
            return "下午"
        elif 18 <= hour < 22:
            return "晚上"
        else:
            return "深夜"
    
    def _load_state(self):
        """从长期记忆加载状态"""
        # 检查 ChromaDB collection 是否可用
        if not self.memory._collection:
            return
        
        try:
            results = self.memory._collection.get(
                include=["metadatas", "documents"]
            )
            
            if not results.get("metadatas"):
                return
            
            for metadata, document in zip(results["metadatas"], results.get("documents", [])):
                if metadata.get("type") == "experience":
                    try:
                        exp_data = json.loads(document)
                        self._experiences.append(Experience(**exp_data))
                    except Exception as e:
                        log.warning(f"加载经验失败: {e}")
            
            log.info(f"从记忆加载了 {len(self._experiences)} 条经验")
            
        except Exception as e:
            log.warning(f"加载状态失败: {e}")

    def search_similar_experience(self, task_description: str, task_type: Optional[str] = None, limit: int = 3) -> List[Dict]:
        """
        搜索相似的成功经验
        
        Args:
            task_description: 任务描述
            task_type: 任务类型（可选，用于过滤）
            limit: 限制数量
            
        Returns:
            相似经验列表
        """
        if not self.memory._collection:
            return []
            
        try:
            # 构建过滤条件 (使用 $and 显式组合)
            # ChromaDB 要求: 多条件必须用 $and 或 $or 包裹，或者每个条件是单独的 dict
            base_conditions = [
                {"type": "experience"},
                {"success": "True"}
            ]
            
            if task_type:
                base_conditions.append({"task_type": task_type})
            
            if len(base_conditions) > 1:
                where_clause = {"$and": base_conditions}
            else:
                where_clause = base_conditions[0]
            
            results = self.memory._collection.query(
                query_texts=[task_description],
                n_results=limit * 2, #以此获取更多候选
                where=where_clause
            )
            
            experiences = []
            if results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    metadata = results["metadatas"][0][i]
                    # 再次过滤: 确保是成功的经验
                    if metadata.get("success") == "True":
                       try:
                           exp_data = json.loads(doc)
                           experiences.append({
                               "task_type": exp_data.get("task_type"),
                               "user_input": exp_data.get("user_input"),
                               "tools_used": exp_data.get("tools_used"),
                               "response": exp_data.get("response"),
                               "execution_time": exp_data.get("execution_time"),
                               "score": results["distances"][0][i] if results["distances"] else 0
                           })
                       except:
                           pass
            
            # 按相关性排序
            experiences.sort(key=lambda x: x["score"])
            return experiences[:limit]
            
        except Exception as e:
            log.warning(f"搜索相似经验失败: {e}")
            return []

    def analyze_failure(self, error: str, task_context: str) -> Optional[str]:
        """
        分析失败并寻找历史解决方案 (Reflexion)
        
        Args:
            error: 错误信息
            task_context: 任务上下文
            
        Returns:
            建议的解决方案
        """
        # TODO: 暂时简单实现，未来可以检索 error 数据库
        error_lower = error.lower()
        if "timeout" in error_lower or "timed out" in error_lower:
            return "建议增加超时时间或减少请求的数据量。"
        if "rate limit" in error_lower or "429" in error_lower:
            return "检测到速率限制，建议等待一段时间后重试，或切换 API Key。"
        if "not found" in error_lower or "404" in error_lower:
            return "目标资源不存在，请检查 URL 或文件名是否正确。"
            
        return None

    def analyze_failure(self, error: str, task_context: str) -> Optional[str]:
        """
        分析失败并寻找历史解决方案 (Reflexion)
        
        Args:
            error: 错误信息
            task_context: 任务上下文
            
        Returns:
            建议的解决方案
        """
        # TODO: 暂时简单实现，未来可以检索 error 数据库
        error_lower = error.lower()
        if "timeout" in error_lower or "timed out" in error_lower:
            return "建议增加超时时间或减少请求的数据量。"
        if "rate limit" in error_lower or "429" in error_lower:
            return "检测到速率限制，建议等待一段时间后重试，或切换 API Key。"
        if "not found" in error_lower or "404" in error_lower:
            return "目标资源不存在，请检查 URL 或文件名是否正确。"
            
        return None
        
    def export_knowledge(self) -> Dict[str, Any]:
        """导出学习到的知识"""
        return {
            "preferences": {
                pref_type: [
                    {
                        "key": p.key,
                        "value": p.value,
                        "confidence": p.confidence,
                        "usage_count": p.usage_count
                    }
                    for p in prefs
                ]
                for pref_type, prefs in self._user_preferences.items()
            },
            "patterns": {
                pattern_type: [
                    {
                        "pattern_data": p.pattern_data,
                        "frequency": p.frequency,
                        "last_seen": p.last_seen
                    }
                    for p in patterns
                ]
                for pattern_type, patterns in self._patterns.items()
            },
            "knowledge_base": self._knowledge_base,
            "export_time": datetime.now().isoformat()
        }
    
    def import_knowledge(self, knowledge: Dict[str, Any]):
        """导入知识"""
        try:
            # 导入偏好
            for pref_type, pref_list in knowledge.get("preferences", {}).items():
                for pref_data in pref_list:
                    self._user_preferences[pref_type].append(
                        UserPreference(
                            preference_type=pref_type,
                            key=pref_data["key"],
                            value=pref_data["value"],
                            confidence=pref_data["confidence"],
                            last_updated=datetime.now().isoformat(),
                            usage_count=pref_data["usage_count"]
                        )
                    )
            
            # 导入模式
            for pattern_type, pattern_list in knowledge.get("patterns", {}).items():
                for pattern_data in pattern_list:
                    self._patterns[pattern_type].append(
                        Pattern(
                            pattern_type=pattern_type,
                            pattern_data=pattern_data["pattern_data"],
                            frequency=pattern_data["frequency"],
                            last_seen=pattern_data["last_seen"]
                        )
                    )
            
            # 导入知识库
            self._knowledge_base.update(knowledge.get("knowledge_base", {}))
            
            log.info("知识导入成功")
            
        except Exception as e:
            log.error(f"知识导入失败: {e}")
            raise
