import os
import requests
import json
try:
    from tavily import TavilyClient
except ImportError:
    TavilyClient = None
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Union

from config import get_config
from utils.logger import log

class SearchInterface(ABC):
    """搜索基类，定义统一接口"""
    @abstractmethod
    def search(self, query: str, **kwargs) -> str:
        pass

class TavilySearcher(SearchInterface):
    """
    Tavily 专门用于 AI Agent，能直接返回页面内容（Context），
    非常适合深入学习和回答复杂问题。
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or get_config().web.tavily_api_key
        if not self.api_key:
            log.warning("Missing TAVILY_API_KEY")
        
        try:
            if self.api_key and TavilyClient:
                self.client = TavilyClient(api_key=self.api_key)
            else:
                self.client = None
                if not TavilyClient:
                    log.warning("TavilyClient lib not installed")
        except Exception as e:
            log.error(f"Failed to initialize TavilyClient: {e}")
            self.client = None

    def search(self, query: str, max_results: int = 3, **kwargs) -> str:
        if not self.client:
            return "Tavily client not initialized (missing API key)."
            
        try:
            # search_depth="advanced" 会进行爬取和清洗，耗时稍长但质量高
            response = self.client.search(
                query=query,
                search_depth="advanced",
                max_results=max_results,
                include_answer=True # 让 Tavily 先尝试生成一个直接答案
            )
            
            # 格式化输出给 LLM
            results = []
            if response.get("answer"):
                results.append(f"★ 直接答案 summary: {response['answer']}")
                
            for res in response.get("results", []):
                content = res.get("content", "")[:800] # 截断防止 Token 爆炸
                results.append(f"Source: {res['url']}\nTitle: {res['title']}\nContent: {content}\n")
                
            return "\n---\n".join(results)
            
        except Exception as e:
            log.error(f"Tavily Search Error: {e}")
            return f"Tavily Search Error: {str(e)}"

class BraveSearcher(SearchInterface):
    """
    Brave Search 提供纯粹的搜索结果列表，响应速度极快，
    适合快速获取最新资讯、链接列表或验证事实。
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or get_config().web.brave_api_key
        if not self.api_key:
            log.warning("Missing BRAVE_API_KEY")
        self.base_url = "https://api.search.brave.com/res/v1/web/search"

    def search(self, query: str, count: int = 5, **kwargs) -> str:
        if not self.api_key:
            return "Brave API key not found."
            
        headers = {
            "X-Subscription-Token": self.api_key,
            "Accept": "application/json",
        }
        params = {
            "q": query,
            "count": count,
            "text_decorations": 0, # 不需要 HTML 标签
            "search_lang": "en",   # 或者 "zh"
            "country": "US"        # 设定搜索地区
        }
        
        try:
            response = requests.get(self.base_url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = []
            # Brave 返回的是 web -> results 结构
            web_results = data.get("web", {}).get("results", [])
            
            if not web_results:
                return "Brave Search returned no results."

            for item in web_results:
                title = item.get("title", "No Title")
                url = item.get("url", "")
                description = item.get("description", "")
                # 还可以获取 published_time
                age = item.get("age", "") 
                
                entry = f"Title: {title}\nURL: {url}\nSnippet: {description}"
                if age:
                    entry += f"\nDate: {age}"
                results.append(entry)
                
            return "\n---\n".join(results)

        except Exception as e:
            log.error(f"Brave Search Error: {e}")
            return f"Brave Search Error: {str(e)}"

class DuckDuckGoSearcher(SearchInterface):
    """DuckDuckGo 搜索引擎（作为备选）"""
    
    def __init__(self, timeout: int = 30):
        # 尝试导入 ddgs 包
        try:
            from ddgs import DDGS
            self.DDGS = DDGS
            self.version = "new"
            self.available = True
        except ImportError:
            try:
                from duckduckgo_search import DDGS
                self.DDGS = DDGS
                self.version = "old"
                self.available = True
            except ImportError:
                self.available = False
                self.version = None
    
    def search(self, query: str, max_results: int = 5, **kwargs) -> str:
        if not self.available:
            return "DuckDuckGo not available (library not installed)."
            
        try:
            if self.version == "new":
                ddgs = self.DDGS()
                raw_results = []
                for result in ddgs.text(query, max_results=max_results):
                    raw_results.append(result)
            else:
                with self.DDGS() as ddgs:
                    raw_results = list(ddgs.text(query, max_results=max_results))
            
            results = []
            for r in raw_results:
                url = r.get("link") or r.get("href", "")
                body = r.get("body") or r.get("snippet", "")
                title = r.get("title", "")
                
                results.append(f"Title: {title}\nURL: {url}\nSnippet: {body}")
            
            if not results:
                return "DuckDuckGo returned no results."
                
            return "\n---\n".join(results)
            
        except Exception as e:
            log.error(f"DuckDuckGo Search Error: {e}")
            return f"DuckDuckGo Search Error: {str(e)}"

class InformationRetrieval:
    """
    Agent 的统一搜索接口。
    智能策略：优先用 Tavily 获取深度内容，如果需要广度或为了省钱则用 Brave。
    """
    def __init__(self):
        # 懒加载，防止初始化时因为缺 Key 报错
        self.tavily = None 
        self.brave = None
        self.ddg = None

    def _get_tavily(self):
        if not self.tavily:
            self.tavily = TavilySearcher()
        return self.tavily

    def _get_brave(self):
        if not self.brave:
            self.brave = BraveSearcher()
        return self.brave
        
    def _get_ddg(self):
        if not self.ddg:
            self.ddg = DuckDuckGoSearcher()
        return self.ddg

    def run(self, query: str, engine: str = "auto") -> str:
        """
        :param query: 搜索关键词
        :param engine: 'auto', 'tavily', 'brave', 'duckduckgo'
        :return: 搜索结果字符串
        """
        log.info(f"[*] Search Tool invoked: [{engine}] '{query}'")
        
        # 智能路由策略
        if engine == "auto":
            # 优先检查 Key 是否存在
            has_tavily = bool(get_config().web.tavily_api_key)
            has_brave = bool(get_config().web.brave_api_key)
            
            if not has_tavily and not has_brave:
                log.info("No API keys found, falling back to DuckDuckGo")
                engine = "duckduckgo"
            elif any(k in query.lower() for k in ["how", "code", "教程", "原理", "analysis", "implement"]) and has_tavily:
                engine = "tavily"
            elif has_brave:
                engine = "brave"
            elif has_tavily:
                engine = "tavily"
            else:
                engine = "duckduckgo"
        
        try:
            if engine == "tavily":
                return self._get_tavily().search(query)
            elif engine == "brave":
                return self._get_brave().search(query)
            elif engine == "duckduckgo":
                return self._get_ddg().search(query)
            else:
                return "Unknown search engine specified."
        except Exception as e:
            log.error(f"Search System Critical Failure: {e}")
            return f"Search System Critical Failure: {str(e)}"
