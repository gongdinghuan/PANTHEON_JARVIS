"""
JARVIS 记忆管理模块
使用 ChromaDB 实现向量存储和语义搜索

Author: gngdingghuan
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, asdict

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

from config import get_config
from utils.logger import log
from .graph_storage import GraphStorage
import uuid
import asyncio


@dataclass
class ConversationTurn:
    """对话轮次"""
    role: str  # user, assistant, system
    content: str
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None
    importance: float = 1.0  # 重要性评分 (1-10)


class MemoryManager:
    """
    记忆管理器
    - 短期记忆：最近 N 轮对话
    - 长期记忆：向量数据库语义检索
    - 核心记忆：用户画像和关键事实 (Persistent)
    """
    
    def __init__(self):
        self.config = get_config().memory
        
        # 短期记忆（内存中的对话历史）
        self._short_term: List[ConversationTurn] = []
        
        # 核心记忆 (Key-Value)
        self._core_memory: Dict[str, str] = {}
        self._core_memory_file = Path(self.config.chroma_persist_dir) / "core_memory.json"
        self._load_core_memory()
        
        # Holo-Mem L3: 知识图谱
        self.graph_storage = GraphStorage(self.config.graph_storage_path)
        
        # 长期记忆（ChromaDB）
        self._chroma_client = None
        self._collection = None
        
        if CHROMADB_AVAILABLE:
            self._init_chromadb()
        else:
            log.warning("ChromaDB 未安装，长期记忆功能不可用")
            
    def _load_core_memory(self):
        """加载核心记忆"""
        if self._core_memory_file.exists():
            try:
                with open(self._core_memory_file, 'r', encoding='utf-8') as f:
                    self._core_memory = json.load(f)
            except Exception as e:
                log.error(f"加载核心记忆失败: {e}")
                
    def _save_core_memory(self):
        """保存核心记忆"""
        try:
            self._core_memory_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._core_memory_file, 'w', encoding='utf-8') as f:
                json.dump(self._core_memory, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log.error(f"保存核心记忆失败: {e}")
            
    def update_core_memory(self, key: str, value: str):
        """更新核心记忆 (如: name, preferences)"""
        self._core_memory[key] = value
        self._save_core_memory()
        log.info(f"核心记忆已更新: {key}={value}")
        
    def get_core_memory_text(self) -> str:
        """获取格式化的核心记忆文本"""
        if not self._core_memory:
            return ""
        
        lines = ["核心记忆 (User Profile):"]
        for k, v in self._core_memory.items():
            lines.append(f"- {k}: {v}")
        return "\n".join(lines)
    
    def _init_chromadb(self):
        """初始化 ChromaDB"""
        try:
            persist_dir = Path(self.config.chroma_persist_dir)
            persist_dir.mkdir(parents=True, exist_ok=True)
            
            self._chroma_client = chromadb.PersistentClient(
                path=str(persist_dir),
                settings=Settings(anonymized_telemetry=False)
            )
            
            # 使用 OpenAI Embedding Function
            from chromadb.utils import embedding_functions
            openai_ef = embedding_functions.OpenAIEmbeddingFunction(
                api_key=get_config().llm.api_key,
                model_name=self.config.embedding_model
            )

            self._collection = self._chroma_client.get_or_create_collection(
                name="jarvis_memory",
                embedding_function=openai_ef,
                metadata={"description": "JARVIS conversation memory"}
            )
            
            log.info(f"ChromaDB 初始化完成，存储路径: {persist_dir}")
            
        except Exception as e:
            log.error(f"ChromaDB 初始化失败: {e}")
            self._chroma_client = None
            self._collection = None

    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None, importance: float = 1.0):
        """
        添加一条消息到记忆
        
        Args:
            role: 角色 (user/assistant/system)
            content: 消息内容
            metadata: 额外元数据
            importance: 重要性评分 (1-10)
        """
        # 安全截断，防止 Context Overflow
        safe_content = content
        if len(safe_content) > 20000:
             log.warning(f"新消息过长 ({len(safe_content)} 字符)，正在截断...")
             safe_content = safe_content[:20000] + f"\n... [Content Truncated due to length {len(safe_content)} > 20000]"

        turn = ConversationTurn(
            role=role,
            content=safe_content,
            timestamp=datetime.now().isoformat(),
            metadata=metadata,
            importance=importance
        )
        
        # 添加到短期记忆
        self._short_term.append(turn)
        
        # 限制短期记忆大小
        max_turns = self.config.short_term_turns
        if len(self._short_term) > max_turns:
            # 移除最早的消息，但保留到长期记忆
            removed = self._short_term.pop(0)
            self._save_to_long_term(removed)
        
        log.debug(f"已添加消息到记忆: [{role}] {content[:50]}... (重要性: {importance})")

    async def nightly_consolidate(self, summarizer_func: Callable[[str], Any], extractor_func: Optional[Callable[[str], List[Dict]]] = None):
        """
        夜间固化 (Consolidation):
        1. L1 -> L2: 将近期 raw logs 摘要为 Daily Timeline (Markdown)
        2. L2 -> L3: 从摘要中提取实体关系，存入 Graph
        """
        if not self._short_term:
            return
            
        log.info("开始执行记忆固化 (Consolidation)...")
        
        # 1. 准备数据
        buffer_text = "\n".join([f"[{t.timestamp}] {t.role}: {t.content}" for t in self._short_term])
        date_str = datetime.now().strftime("%Y-%m-%d")
        
        # 2. 生成每日摘要 (L2)
        try:
            summary = await summarizer_func(f"请将以下今日对话日志总结为一份精炼的事实性摘要 (Daily Summary)，忽略闲聊，保留重要决策、偏好和操作结果：\n\n{buffer_text}")
            
            # 存储为 Markdown 文件
            timeline_dir = Path(self.config.timeline_storage_dir)
            timeline_dir.mkdir(parents=True, exist_ok=True)
            timeline_file = timeline_dir / f"{date_str}.md"
            
            with open(timeline_file, "w", encoding='utf-8') as f:
                f.write(f"# {date_str} Memory Consolidation\n\n")
                f.write(summary)
            
            # 将摘要存入向量库 (Type=episodic)
            if self._collection:
                 self._collection.add(
                    documents=[summary],
                    metadatas=[{"type": "episodic", "date": date_str}],
                    ids=[f"summary_{date_str}_{uuid.uuid4().hex[:6]}"]
                 )
                 
            log.info(f"L2 记忆固化完成: {timeline_file}")
            
            # 3. 提取知识图谱 (L3)
            if extractor_func:
                log.info("正在提取知识图谱三元组...")
                try:
                    triplets = await extractor_func(summary) 
                    count = 0
                    for item in triplets:
                        head = item.get('head')
                        relation = item.get('relation')
                        tail = item.get('tail')
                        if head and relation and tail:
                            self.graph_storage.add_relation(head, relation, tail)
                            count += 1
                            
                    self.graph_storage.save_graph()
                    log.info(f"L3 图谱更新完成，新增 {count} 条关系")
                except Exception as e:
                    log.warning(f"L3 图谱提取失败: {e}")

        except Exception as e:
            log.error(f"记忆固化失败: {e}")

    async def retrieve_context_hybrid(self, query: str, limit: Optional[int] = None) -> List[str]:
        """
        混合检索 (Hybrid Retrieval): Vector + Graph
        """
        limit = limit or self.config.retrieval_k  # 使用全局配置
        context_results = []
        
        # 1. 向量检索
        if self._collection:
            try:
                log.info(f"正在执行向量检索: query='{query[:50]}...', limit={limit}")
                results = self._collection.query(
                    query_texts=[query],
                    n_results=limit,
                    where=None # 不限类型，同时检索原始日志和摘要
                )
                
                if results['documents'] and results['documents'][0]:
                    count = len(results['documents'][0])
                    log.info(f"向量检索命中 {count} 条记录")
                    
                    current_chars = 0
                    MAX_CHARS = 20000  # 限制最大检索内容长度 (约 5k tokens)
                    
                    for i, doc in enumerate(results['documents'][0]):
                        if current_chars + len(doc) > MAX_CHARS:
                            log.warning(f"检索内容达到安全限制 ({MAX_CHARS} 字符)，截断剩余 {count - i} 条记录")
                            break
                            
                        context_results.append(f"[History] {doc}")
                        current_chars += len(doc)
                else:
                    log.info("向量检索未找到匹配项")
                    
            except Exception as e:
                log.error(f"向量检索失败: {e}")
                
        # 2. 图谱检索 (关联挖掘)
        # 简单提取查询中的名词作为实体锚点
        potential_entities = self.graph_storage.simple_search(query)
        
        # 限制实体数量，防止上下文爆炸
        for entity in potential_entities[:3]: 
            neighbors = self.graph_storage.get_neighbors(entity, depth=1)
            for n in neighbors:
                rel_str = f"{n['source']} --[{n['relation']}]--> {n['target']}"
                context_results.append(f"[Graph] {rel_str}")
                
        # 去重
        return list(set(context_results))

    def get_interest_areas(self, limit: int = 5) -> List[str]:
        """
        获取用户当前的兴趣领域（基于知识图谱的核心概念）
        """
        return self.graph_storage.get_central_concepts(limit)
 
    async def restore_with_summary(self, summarizer_func: Callable[[str], Any], recent_count: int = 20):
        """
        从长期记忆恢复，支持全量历史摘要
        
        Args:
            summarizer_func: 异步摘要函数 (text -> summary)
            recent_count: 保留的近期原始对话轮数
        """
        if not self._collection:
            return
            
        try:
            # 1. 获取所有记录
            # Chroma get() 默认获取所有（如果未指定 limit）
            result = self._collection.get()
            if not result["ids"]:
                return
                
            history = []
            for i, _ in enumerate(result["ids"]):
                meta = result["metadatas"][i]
                content = result["documents"][i]
                
                # 兼容旧数据
                timestamp = meta.get("timestamp", "")
                role = meta.get("role", "user")
                if role not in ["system", "user", "assistant", "tool", "function"]:
                    role = "user"
                    
                importance = meta.get("importance", 1.0)
                
                history.append(ConversationTurn(
                    role=role,
                    content=content,
                    timestamp=timestamp,
                    metadata=meta,
                    importance=importance
                ))
            
            # 2. 按时间排序
            history.sort(key=lambda x: x.timestamp)
            
            # 3. 仿生分层记忆策略：仅加载近期活跃记忆 (Short-Term)
            # 长期记忆 (Long-Term) 已存在于 VectorDB 中，按需检索，无需启动时全量摘要
            
            total_count = len(history)
            
            if total_count <= recent_count:
                # 数量较少，直接全部加载
                self._short_term = self._truncate_history(history)
                log.info(f"已恢复全量短期记忆 ({total_count} 条)")
            else:
                # 仅保留最近 N 条，旧的丢弃（但在长期记忆/图谱中仍可被检索）
                recent_history = history[-recent_count:]
                self._short_term = self._truncate_history(recent_history)
                
                log.info(f"仿生记忆加载: 仅恢复最近 {len(recent_history)} 条活跃记忆 (总历史 {total_count} 条)")
                log.info("更早的记忆将通过 RAG (Vector + Graph) 按需检索，不再进行启动时全量摘要，提高效率。")

        except Exception as e:
            log.error(f"恢复记忆失败: {e}")

    def _truncate_history(self, history: List[ConversationTurn], max_chars: int = 20000) -> List[ConversationTurn]:
        """截断过长的历史消息，防止 Context Overflow"""
        truncated_history = []
        for turn in history:
            if len(turn.content) > max_chars:
                log.warning(f"检测到超长历史消息 ({len(turn.content)} 字符)，正在截断...")
                truncated_content = turn.content[:max_chars] + f"\n... [Content Truncated due to length {len(turn.content)} > {max_chars}]"
                new_turn = ConversationTurn(
                    role=turn.role,
                    content=truncated_content,
                    timestamp=turn.timestamp,
                    metadata=turn.metadata,
                    importance=turn.importance
                )
                truncated_history.append(new_turn)
            else:
                truncated_history.append(turn)
        return truncated_history

    def restore_short_term_from_long_term(self):
        """从长期记忆恢复短期对话历史 (Deprecated: see restore_with_summary)"""
        if not self._collection:
            return
            
        try:
            # 获取所有记录并按时间排序 (简单实现，适用于数据量不大)
            result = self._collection.get()
            if not result["ids"]:
                return
                
            history = []
            for i, _ in enumerate(result["ids"]):
                meta = result["metadatas"][i]
                content = result["documents"][i]
                # 兼容旧数据，防止 role unknown
                timestamp = meta.get("timestamp", "")
                role = meta.get("role", "user") # 默认为 user 而不是 unknown
                if role not in ["system", "user", "assistant", "tool", "function"]:
                    role = "user"
                    
                importance = meta.get("importance", 1.0)
                
                history.append(ConversationTurn(
                    role=role,
                    content=content,
                    timestamp=timestamp,
                    metadata=meta,
                    importance=importance
                ))
            
            # 按时间排序
            history.sort(key=lambda x: x.timestamp)
            
            # 取最近 N 条
            recent = history[-self.config.short_term_turns:]
            self._short_term = recent
            
            log.info(f"已从长期记忆恢复 {len(self._short_term)} 条短期记忆")
            
        except Exception as e:
            log.error(f"恢复短期记忆失败: {e}")

    def _save_to_long_term(self, turn: ConversationTurn):
        """保存到长期记忆（ChromaDB）"""
        if not self._collection:
            return
        
        try:
            doc_id = f"{turn.role}_{turn.timestamp}"
            
            self._collection.add(
                documents=[turn.content],
                metadatas=[{
                    "role": turn.role,
                    "timestamp": turn.timestamp,
                    "importance": turn.importance,
                    **(turn.metadata or {})
                }],
                ids=[doc_id]
            )
            
        except Exception as e:
            log.error(f"保存到长期记忆失败: {e}")

    def get_recent_context(self) -> List[Dict[str, str]]:
        """获取近期对话上下文"""
        return [
            {"role": turn.role, "content": turn.content}
            for turn in self._short_term
        ]

    def search_relevant(self, query: str, k: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        语义搜索相关记忆（综合考虑 相似度、重要性、时效性）
        
        Score = (Similarity * 0.6) + (Importance_Norm * 0.3) + (Recency_Norm * 0.1)
        
        Args:
            query: 查询文本
            k: 返回数量
            
        Returns:
            相关记忆列表 (早已按权重排序)
        """
        if not self._collection:
            return []
        
        k = k or self.config.retrieval_k
        # 获取更多候选用于重排序
        candidate_k = k * 3
        
        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=candidate_k
            )
            
            candidates = []
            if results["documents"] and results["documents"][0]:
                now = datetime.now()
                for i, doc in enumerate(results["documents"][0]):
                    meta = results["metadatas"][0][i] if results["metadatas"] else {}
                    distance = results["distances"][0][i] if results["distances"] else 1.0
                    
                    # 1. 计算相似度 (distance 越小相似度越高，假设 distance 是欧几里得距离或余弦距离的变体)
                    # Chroma 默认 L2，范围不固定。这里简单归一化: 1 / (1 + distance)
                    similarity = 1 / (1 + distance)
                    
                    # 2. 计算重要性 (归一化到 0-1)
                    importance = float(meta.get("importance", 1.0)) / 10.0
                    
                    # 3. 计算时效性 (简单衰减: 30天内线性衰减，或者对数衰减)
                    timestamp_str = meta.get("timestamp", now.isoformat())
                    try:
                        record_time = datetime.fromisoformat(timestamp_str)
                        # 简单的天数差
                        days_diff = (now - record_time).days
                        recency = 1.0 / (1.0 + max(0, days_diff)) # 越近越大
                    except:
                        recency = 0.5
                    
                    # 综合评分权重
                    # 这里假设我们更看重语义相关性，其次是重要性，最后是时间
                    final_score = (similarity * 0.6) + (importance * 0.3) + (recency * 0.1)
                    
                    candidates.append({
                        "content": doc,
                        "metadata": meta,
                        "score": final_score,
                        "raw_distance": distance
                    })
            
            # 按最终得分排序
            candidates.sort(key=lambda x: x["score"], reverse=True)
            
            return candidates[:k]
            
        except Exception as e:
            log.error(f"语义搜索失败: {e}")
            return []
    
    def get_context_with_memory(self, query: str) -> List[Dict[str, str]]:
        """
        获取包含相关长期记忆的完整上下文
        
        Args:
            query: 当前查询
            
        Returns:
            增强的消息列表
        """
        messages = []
        
        # 检索相关长期记忆
        relevant_memories = self.search_relevant(query)
        
        if relevant_memories:
            memory_text = "\n".join([
                f"[{m['metadata'].get('role', 'unknown')}] {m['content']}"
                for m in relevant_memories
            ])
            
            messages.append({
                "role": "system",
                "content": f"以下是与当前话题相关的历史记忆：\n{memory_text}"
            })
        
        # 添加短期记忆
        messages.extend(self.get_recent_context())
        
        return messages
    
    def clear_short_term(self):
        """清空短期记忆"""
        # 先保存到长期记忆
        for turn in self._short_term:
            self._save_to_long_term(turn)
        
        self._short_term.clear()
        log.info("短期记忆已清空")
    
    def clear_all(self):
        """清空所有记忆"""
        self._short_term.clear()
        
        if self._collection:
            try:
                # 删除并重建 collection
                self._chroma_client.delete_collection("jarvis_memory")
                self._collection = self._chroma_client.create_collection(
                    name="jarvis_memory",
                    metadata={"description": "JARVIS conversation memory"}
                )
            except Exception as e:
                log.error(f"清空长期记忆失败: {e}")
        
        log.info("所有记忆已清空")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取记忆统计信息"""
        stats = {
            "short_term_count": len(self._short_term),
            "long_term_count": 0,
            "chromadb_available": CHROMADB_AVAILABLE,
        }
        
        if self._collection:
            try:
                stats["long_term_count"] = self._collection.count()
            except:
                pass
        
        return stats
