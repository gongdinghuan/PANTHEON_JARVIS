"""
JARVIS Embedding 路由器
统一 embedding 接口，支持多种后端

后端选项:
- local: sentence-transformers (免费, 离线, 需 GPU/CPU)
- chromadb: ChromaDB 内置 (onnxruntime, 默认)
- openai: text-embedding-3-small (API, 收费)
- zhipu: Embedding-3 (API, 收费)

Author: gngdingghuan
"""

import os
import json
import hashlib
from typing import List, Optional, Dict, Any
from pathlib import Path

from config import get_config
from utils.logger import log


class EmbeddingRouter:
    """
    统一 Embedding 接口
    
    根据配置选择 embedding 后端，提供统一的 encode() 接口。
    支持结果缓存以减少重复计算。
    """
    
    def __init__(self, provider: Optional[str] = None):
        """
        Args:
            provider: embedding 提供商 ("chromadb", "local", "openai", "zhipu")
                      默认从配置读取
        """
        config = get_config()
        self.provider = provider or getattr(config.memory, 'embedding_provider', 'chromadb')
        self._model = None
        self._client = None
        self._cache: Dict[str, List[float]] = {}
        self._cache_max_size = 1000
        
        self._init_backend()
        log.info(f"Embedding Router 初始化: provider={self.provider}")
    
    def _init_backend(self):
        """初始化 embedding 后端"""
        if self.provider == "local":
            self._init_local()
        elif self.provider == "openai":
            self._init_openai()
        elif self.provider == "zhipu":
            self._init_zhipu()
        else:
            # 默认 chromadb 内置，不需要额外初始化
            self.provider = "chromadb"
            log.info("使用 ChromaDB 内置 embedding")
    
    def _init_local(self):
        """初始化本地 sentence-transformers"""
        try:
            from sentence_transformers import SentenceTransformer
            model_name = os.getenv("LOCAL_EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
            self._model = SentenceTransformer(model_name)
            log.info(f"本地 embedding 模型加载成功: {model_name}")
        except ImportError:
            log.warning("sentence-transformers 未安装，回退到 chromadb 内置")
            self.provider = "chromadb"
        except Exception as e:
            log.warning(f"本地 embedding 加载失败: {e}，回退到 chromadb")
            self.provider = "chromadb"
    
    def _init_openai(self):
        """初始化 OpenAI embedding"""
        try:
            from openai import OpenAI
            config = get_config().llm
            api_key = config.openai_api_key
            base_url = config.openai_base_url
            
            if not api_key:
                log.warning("OpenAI API Key 未配置，回退到 chromadb")
                self.provider = "chromadb"
                return
            
            self._client = OpenAI(api_key=api_key, base_url=base_url)
            self._model = getattr(config, 'embedding_model', 'text-embedding-3-small')
            log.info(f"OpenAI embedding 初始化: model={self._model}")
        except Exception as e:
            log.warning(f"OpenAI embedding 初始化失败: {e}，回退到 chromadb")
            self.provider = "chromadb"
    
    def _init_zhipu(self):
        """初始化 ZhipuAI embedding"""
        try:
            from openai import OpenAI
            config = get_config().llm
            api_key = config.zhipu_api_key
            base_url = config.zhipu_base_url
            
            if not api_key:
                log.warning("Zhipu API Key 未配置，回退到 chromadb")
                self.provider = "chromadb"
                return
            
            self._client = OpenAI(api_key=api_key, base_url=base_url)
            self._model = "embedding-3"
            log.info(f"Zhipu embedding 初始化: model={self._model}")
        except Exception as e:
            log.warning(f"Zhipu embedding 初始化失败: {e}，回退到 chromadb")
            self.provider = "chromadb"
    
    def encode(self, texts: List[str]) -> List[List[float]]:
        """
        编码文本为向量
        
        Args:
            texts: 文本列表
            
        Returns:
            向量列表，每个向量是 float 列表
        """
        if not texts:
            return []
        
        if self.provider == "chromadb":
            # ChromaDB 内置 embedding，返回 None 让 ChromaDB 自行处理
            return None
        
        # 检查缓存
        results = [None] * len(texts)
        uncached_indices = []
        uncached_texts = []
        
        for i, text in enumerate(texts):
            cache_key = self._cache_key(text)
            if cache_key in self._cache:
                results[i] = self._cache[cache_key]
            else:
                uncached_indices.append(i)
                uncached_texts.append(text)
        
        # 编码未缓存的文本
        if uncached_texts:
            if self.provider == "local":
                embeddings = self._encode_local(uncached_texts)
            elif self.provider in ("openai", "zhipu"):
                embeddings = self._encode_api(uncached_texts)
            else:
                return None
            
            # 填入结果并缓存
            for idx, embedding in zip(uncached_indices, embeddings):
                results[idx] = embedding
                cache_key = self._cache_key(texts[idx])
                self._cache[cache_key] = embedding
            
            # 清理过大的缓存
            if len(self._cache) > self._cache_max_size:
                keys = list(self._cache.keys())
                for k in keys[:len(keys) // 2]:
                    del self._cache[k]
        
        return results
    
    def encode_single(self, text: str) -> Optional[List[float]]:
        """编码单个文本"""
        result = self.encode([text])
        return result[0] if result else None
    
    def _encode_local(self, texts: List[str]) -> List[List[float]]:
        """使用本地模型编码"""
        try:
            embeddings = self._model.encode(texts, convert_to_numpy=True)
            return [emb.tolist() for emb in embeddings]
        except Exception as e:
            log.error(f"本地 embedding 编码失败: {e}")
            return [[0.0] * 384] * len(texts)  # 返回零向量作为回退
    
    def _encode_api(self, texts: List[str]) -> List[List[float]]:
        """使用 API 编码"""
        try:
            response = self._client.embeddings.create(
                model=self._model,
                input=texts,
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            log.error(f"API embedding 编码失败: {e}")
            return [[0.0] * 1536] * len(texts)
    
    def _cache_key(self, text: str) -> str:
        """生成缓存键"""
        return hashlib.md5(f"{self.provider}:{text}".encode()).hexdigest()
    
    @property
    def dimension(self) -> int:
        """返回 embedding 向量维度"""
        dims = {
            "chromadb": 384,  # onnxruntime default
            "local": 384,    # MiniLM-L12
            "openai": 1536,  # text-embedding-3-small
            "zhipu": 2048,   # embedding-3
        }
        return dims.get(self.provider, 384)
    
    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()


class SimpleReranker:
    """
    简单的 Reranker
    
    使用 LLM 对粗检索结果进行二次精排。
    适用于无独立 Reranker 模型的场景。
    """
    
    def __init__(self, llm_brain=None):
        """
        Args:
            llm_brain: LLM Brain 实例 (用于 LLM-based reranking)
        """
        self.brain = llm_brain
    
    async def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        对文档列表重排
        
        Args:
            query: 查询文本
            documents: 文档列表 [{"content": "...", "score": 0.x, ...}]
            top_k: 返回前 k 个
            
        Returns:
            重排后的文档列表
        """
        if not documents or len(documents) <= top_k:
            return documents
        
        if self.brain:
            return await self._rerank_with_llm(query, documents, top_k)
        else:
            return self._rerank_keyword(query, documents, top_k)
    
    async def _rerank_with_llm(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """使用 LLM 进行 reranking"""
        try:
            # 构建文档列表文本
            doc_texts = []
            for i, doc in enumerate(documents[:20]):  # 最多发送 20 个
                content = doc.get("content", "")[:200]
                doc_texts.append(f"[{i}] {content}")
            
            docs_str = "\n".join(doc_texts)
            
            prompt = f"""给定查询和一组文档，请选出与查询最相关的 {top_k} 个文档。
只输出文档编号（从 0 开始），用逗号分隔，按相关性从高到低排列。

查询: {query}

文档:
{docs_str}

输出格式: 0,3,1,7,2"""
            
            response = await self.brain.simple_chat(prompt, system_prompt="你是一个文档相关性评估专家。只输出文档编号。")
            
            # 解析返回的编号
            indices = []
            for part in response.strip().split(","):
                part = part.strip()
                try:
                    idx = int(part)
                    if 0 <= idx < len(documents):
                        indices.append(idx)
                except ValueError:
                    continue
            
            # 按 LLM 排序返回
            if indices:
                reranked = [documents[i] for i in indices[:top_k]]
                return reranked
            
        except Exception as e:
            log.warning(f"LLM reranking 失败: {e}，回退到关键词排序")
        
        return self._rerank_keyword(query, documents, top_k)
    
    def _rerank_keyword(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """使用关键词匹配进行简单排序"""
        query_tokens = set(query.lower().split())
        
        scored = []
        for doc in documents:
            content = doc.get("content", "").lower()
            # 原始分 + 关键词匹配加分
            original_score = doc.get("score", 0)
            keyword_score = sum(1 for token in query_tokens if token in content)
            # 综合得分
            combined = original_score * 0.7 + (keyword_score / max(len(query_tokens), 1)) * 0.3
            scored.append((combined, doc))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored[:top_k]]
