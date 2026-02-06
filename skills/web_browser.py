"""
JARVIS 网页浏览技能
搜索、读取网页内容

Author: gngdingghuan
"""

import re
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from urllib.parse import urlencode, urljoin

import httpx
from bs4 import BeautifulSoup

from skills.base_skill import BaseSkill, SkillResult, PermissionLevel, create_tool_schema
from config import get_config, SearchProvider
from utils.logger import log
from utils.platform_utils import open_url_in_browser

try:
    from googlesearch import search as google_search
    GOOGLE_SEARCH_AVAILABLE = True
except ImportError:
    GOOGLE_SEARCH_AVAILABLE = False


class BaseSearchEngine(ABC):
    """搜索引擎基类"""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self._client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            }
        )
    
    @abstractmethod
    async def search(self, query: str, max_results: int = 10) -> List[Dict[str, str]]:
        """
        执行搜索
        
        Args:
            query: 搜索关键词
            max_results: 最大结果数
            
        Returns:
            搜索结果列表，每个结果包含 title, url, snippet
        """
        pass
    
    async def close(self):
        """关闭客户端"""
        await self._client.aclose()


class BaiduSearcher(BaseSearchEngine):
    """百度搜索引擎"""
    
    def __init__(self, timeout: int = 30):
        super().__init__(timeout)
        self.base_url = "https://www.baidu.com/s"
    
    async def search(self, query: str, max_results: int = 10) -> List[Dict[str, str]]:
        """使用百度搜索"""
        log.info(f"使用百度搜索: {query}")
        
        params = {
            "wd": query,
            "rn": max_results,
        }
        
        try:
            url = f"{self.base_url}?{urlencode(params)}"
            response = await self._client.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # 尝试多种选择器来找到百度搜索结果
            # 百度可能使用不同的类名
            selectors = [
                '.result',
                'div[tpl]',
                'div.c-container',
                '.c-container',
            ]
            
            for selector in selectors:
                items = soup.select(selector)
                if items:
                    log.debug(f"使用选择器 '{selector}' 找到 {len(items)} 个结果")
                    
                    for item in items[:max_results]:
                        try:
                            # 尝试多种方式获取标题
                            title_elem = (
                                item.select_one('h3 a') or
                                item.select_one('.t a') or
                                item.select_one('a')
                            )
                            
                            if not title_elem:
                                continue
                            
                            title = title_elem.get_text(strip=True)
                            url = title_elem.get('href', '')
                            
                            # 跳过百度内部链接
                            if not url or 'baidu.com/link' in url:
                                if url:
                                    # 尝试从 data-tools 属性获取真实 URL
                                    data_tools = title_elem.get('data-tools', '')
                                    if data_tools:
                                        try:
                                            import json
                                            tools = json.loads(data_tools)
                                            url = tools.get('url', url)
                                        except:
                                            pass
                            
                            # 尝试多种方式获取摘要
                            snippet_elem = (
                                item.select_one('.c-abstract') or
                                item.select_one('.c-span-last') or
                                item.select_one('.c-span9') or
                                item.select_one('.c-summary')
                            )
                            
                            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                            
                            # 清理标题和摘要
                            title = re.sub(r'\s+', ' ', title)
                            snippet = re.sub(r'\s+', ' ', snippet)
                            
                            # 过滤掉纯广告或无效结果
                            if title and url and len(title) > 3:
                                results.append({
                                    "title": title,
                                    "url": url,
                                    "snippet": snippet
                                })
                                
                                if len(results) >= max_results:
                                    break
                                    
                        except Exception as e:
                            log.debug(f"解析单个搜索结果失败: {e}")
                            continue
                    
                    # 如果找到结果就跳出
                    if results:
                        break
            
            log.info(f"百度搜索返回 {len(results)} 条结果")
            return results
            
        except Exception as e:
            log.error(f"百度搜索失败: {e}")
            return []
    
    async def close(self):
        """关闭客户端"""
        await self._client.aclose()


class DuckDuckGoSearcher(BaseSearchEngine):
    """DuckDuckGo 搜索引擎（作为备选）"""
    
    def __init__(self, timeout: int = 30):
        super().__init__(timeout)
        
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
    
    async def search(self, query: str, max_results: int = 10) -> List[Dict[str, str]]:
        """使用 DuckDuckGo 搜索"""
        if not self.available:
            log.warning("DuckDuckGo 不可用，已安装 ddgs/duckduckgo-search 库才能使用")
            return []
        
        log.info(f"使用 DuckDuckGo 搜索: {query} (版本: {self.version})")
        
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
                
                results.append({
                    "title": r.get("title", ""),
                    "url": url,
                    "snippet": body
                })
            
            log.info(f"DuckDuckGo 搜索返回 {len(results)} 条结果")
            return results
            
        except Exception as e:
            log.error(f"DuckDuckGo 搜索失败: {e}")
            return []



class GoogleSearcher(BaseSearchEngine):
    """Google 搜索引擎"""
    
    def __init__(self, timeout: int = 30):
        super().__init__(timeout)
        self.available = GOOGLE_SEARCH_AVAILABLE
    
    async def search(self, query: str, max_results: int = 10) -> List[Dict[str, str]]:
        """使用 Google 搜索"""
        if not self.available:
            log.warning("googlesearch-python 未安装")
            return []
        
        log.info(f"使用 Google 搜索: {query}")
        
        try:
            # googlesearch-python 是同步库，在线程中运行
            import asyncio
            from utils.compat import to_thread
            
            def _sync_search():
                results = []
                # advanced=True 返回详细对象
                for res in google_search(query, num_results=max_results, advanced=True):
                    results.append({
                        "title": res.title,
                        "url": res.url,
                        "snippet": res.description
                    })
                return results

            results = await to_thread(_sync_search)
            log.info(f"Google 搜索返回 {len(results)} 条结果")
            return results
            
        except Exception as e:
            log.error(f"Google 搜索失败: {e}")
            return []

class WebBrowserSkill(BaseSkill):
    """网页浏览技能"""
    
    name = "web_browser"
    description = "网页浏览：搜索信息、读取网页内容、打开URL"
    permission_level = PermissionLevel.READ_ONLY
    
    def __init__(self):
        super().__init__()
        
        # 获取配置
        self.config = get_config().web
        
        # 创建搜索引擎实例
        self._search_engine = self._create_search_engine()
        
        # HTTP 客户端（用于其他操作）
        self._client = httpx.AsyncClient(
            timeout=self.config.search_timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )
    
    def _create_search_engine(self) -> BaseSearchEngine:
        """根据配置创建搜索引擎实例"""
        provider = self.config.search_provider
        
        if provider == SearchProvider.BAIDU:
            return BaiduSearcher(timeout=self.config.search_timeout)
        elif provider == SearchProvider.DUCKDUCKGO:
            return DuckDuckGoSearcher(timeout=self.config.search_timeout)
        elif provider == SearchProvider.GOOGLE:
            return GoogleSearcher(timeout=self.config.search_timeout)
        else:
            log.warning(f"未知的搜索引擎提供商: {provider}，使用百度搜索")
            return BaiduSearcher(timeout=self.config.search_timeout)
    
    async def execute(self, action: str, **params) -> SkillResult:
        """执行网页操作"""
        actions = {
            "search": self._search,
            "read_webpage": self._read_webpage,
            "open_url": self._open_url,
            "get_weather": self._get_weather,
        }
        
        if action not in actions:
            return SkillResult(success=False, output=None, error=f"未知的操作: {action}")
        
        try:
            result = await actions[action](**params)
            return result
        except Exception as e:
            log.error(f"网页操作失败: {action}, 错误: {e}")
            return SkillResult(success=False, output=None, error=str(e))
    
    async def _search(self, query: str, max_results: int = 5) -> SkillResult:
        """搜索信息"""
        log.info(f"执行搜索: {query}")
        
        try:
            results = await self._search_engine.search(query, max_results=max_results)
            
            if not results:
                return SkillResult(
                    success=True,
                    output={"message": "未找到相关结果", "results": []}
                )
            
            return SkillResult(
                success=True,
                output={
                    "query": query,
                    "count": len(results),
                    "results": results,
                    "engine": self.config.search_provider.value
                }
            )
            
        except Exception as e:
            log.error(f"搜索异常: {e}")
            return SkillResult(success=False, output=None, error=f"搜索失败: {e}")
    
    async def _read_webpage(self, url: str) -> SkillResult:
        """读取网页内容（提取文本）"""
        log.info(f"读取网页: {url}")
        
        try:
            response = await self._client.get(url)
            response.raise_for_status()
            
            html = response.text
            
            # 使用 BeautifulSoup 提取文本
            soup = BeautifulSoup(html, 'html.parser')
            
            # 移除不需要的标签
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            text = soup.get_text()
            
            # 清理文本
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            # 限制长度
            if len(text) > 5000:
                text = text[:5000] + "...(内容已截断)"
            
            return SkillResult(
                success=True,
                output={
                    "url": url,
                    "status_code": response.status_code,
                    "content": text
                }
            )
            
        except httpx.HTTPError as e:
            return SkillResult(success=False, output=None, error=f"HTTP 错误: {e}")
        except Exception as e:
            return SkillResult(success=False, output=None, error=str(e))
    
    async def _open_url(self, url: str) -> SkillResult:
        """在浏览器中打开 URL"""
        log.info(f"打开 URL: {url}")
        
        success = open_url_in_browser(url)
        if success:
            return SkillResult(success=True, output=f"已在浏览器中打开: {url}")
        else:
            return SkillResult(success=False, output=None, error="无法打开浏览器")
    
    async def _get_weather(self, city: str = "北京") -> SkillResult:
        """获取天气信息（通过搜索）"""
        query = f"{city}天气"
        return await self._search(query, max_results=3)
    
    async def close(self):
        """关闭资源"""
        await self._search_engine.close()
        await self._client.aclose()
    
    def get_schema(self) -> Dict[str, Any]:
        """获取 Function Calling Schema"""
        return create_tool_schema(
            name="web_browser",
            description="网页浏览操作：搜索信息、读取网页内容、打开URL、查询天气",
            parameters={
                "action": {
                    "type": "string",
                    "enum": ["search", "read_webpage", "open_url", "get_weather"],
                    "description": "要执行的操作类型"
                },
                "query": {
                    "type": "string",
                    "description": "搜索关键词（用于 search）"
                },
                "url": {
                    "type": "string",
                    "description": "网页 URL（用于 read_webpage, open_url）"
                },
                "city": {
                    "type": "string",
                    "description": "城市名称（用于 get_weather）"
                },
                "max_results": {
                    "type": "integer",
                    "description": "最大结果数量（用于 search）"
                }
            },
            required=["action"]
        )
