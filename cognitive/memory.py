"""
JARVIS 记忆管理模块
使用 ChromaDB 实现向量存储和语义搜索

Author: gngdingghuan
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

from config import get_config
from utils.logger import log


@dataclass
class ConversationTurn:
    """对话轮次"""
    role: str  # user, assistant, system
    content: str
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None


class MemoryManager:
    """
    记忆管理器
    - 短期记忆：最近 N 轮对话
    - 长期记忆：向量数据库语义检索
    """
    
    def __init__(self):
        self.config = get_config().memory
        
        # 短期记忆（内存中的对话历史）
        self._short_term: List[ConversationTurn] = []
        
        # 长期记忆（ChromaDB）
        self._chroma_client = None
        self._collection = None
        
        if CHROMADB_AVAILABLE:
            self._init_chromadb()
        else:
            log.warning("ChromaDB 未安装，长期记忆功能不可用")
    
    def _init_chromadb(self):
        """初始化 ChromaDB"""
        try:
            persist_dir = Path(self.config.chroma_persist_dir)
            persist_dir.mkdir(parents=True, exist_ok=True)
            
            self._chroma_client = chromadb.PersistentClient(
                path=str(persist_dir),
                settings=Settings(anonymized_telemetry=False)
            )
            
            self._collection = self._chroma_client.get_or_create_collection(
                name="jarvis_memory",
                metadata={"description": "JARVIS conversation memory"}
            )
            
            log.info(f"ChromaDB 初始化完成，存储路径: {persist_dir}")
            
        except Exception as e:
            log.error(f"ChromaDB 初始化失败: {e}")
            self._chroma_client = None
            self._collection = None
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """
        添加一条消息到记忆
        
        Args:
            role: 角色 (user/assistant/system)
            content: 消息内容
            metadata: 额外元数据
        """
        turn = ConversationTurn(
            role=role,
            content=content,
            timestamp=datetime.now().isoformat(),
            metadata=metadata
        )
        
        # 添加到短期记忆
        self._short_term.append(turn)
        
        # 限制短期记忆大小
        max_turns = self.config.short_term_turns
        if len(self._short_term) > max_turns:
            # 移除最早的消息，但保留到长期记忆
            removed = self._short_term.pop(0)
            self._save_to_long_term(removed)
        
        log.debug(f"已添加消息到记忆: [{role}] {content[:50]}...")
    
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
                    **(turn.metadata or {})
                }],
                ids=[doc_id]
            )
            
        except Exception as e:
            log.error(f"保存到长期记忆失败: {e}")
    
    def get_recent_context(self, turns: Optional[int] = None) -> List[Dict[str, str]]:
        """
        获取最近的对话上下文
        
        Args:
            turns: 获取的轮数，默认全部短期记忆
            
        Returns:
            OpenAI 格式的消息列表
        """
        if turns is None:
            turns = len(self._short_term)
        
        recent = self._short_term[-turns:] if turns > 0 else []
        
        return [
            {"role": turn.role, "content": turn.content}
            for turn in recent
        ]
    
    def search_relevant(self, query: str, k: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        语义搜索相关记忆
        
        Args:
            query: 查询文本
            k: 返回数量
            
        Returns:
            相关记忆列表
        """
        if not self._collection:
            return []
        
        k = k or self.config.retrieval_k
        
        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=k
            )
            
            memories = []
            if results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                    memories.append({
                        "content": doc,
                        "metadata": metadata,
                        "distance": results["distances"][0][i] if results["distances"] else None
                    })
            
            return memories
            
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
