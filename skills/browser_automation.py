"""
JARVIS 浏览器自动化技能
基于 Playwright 实现真正的浏览器操作

支持操作: 打开页面、点击、输入文本、截图、提取文本、执行JS、滚动、等待元素

Author: gngdingghuan
"""

import asyncio
import os
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from skills.base_skill import BaseSkill, SkillResult, PermissionLevel
from config import get_config
from utils.logger import log

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class BrowserAutomationSkill(BaseSkill):
    """
    浏览器自动化技能 - 基于 Playwright
    提供真正的浏览器操作能力：导航、点击、输入、截图、数据提取
    """
    
    name = "browser_automation"
    description = "浏览器自动化操作：打开网页、点击元素、输入文本、截图、提取数据等"
    permission_level = PermissionLevel.SAFE_WRITE
    
    def __init__(self):
        super().__init__()
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._last_activity = 0
        
        config = get_config()
        self._headless = getattr(config.browser, 'headless', True) if hasattr(config, 'browser') else True
        self._timeout = getattr(config.browser, 'timeout', 30000) if hasattr(config, 'browser') else 30000
        self._viewport_w = getattr(config.browser, 'viewport_width', 1280) if hasattr(config, 'browser') else 1280
        self._viewport_h = getattr(config.browser, 'viewport_height', 720) if hasattr(config, 'browser') else 720
        self._screenshot_dir = getattr(config.browser, 'screenshot_dir', 'generated_images') if hasattr(config, 'browser') else 'generated_images'
        self._auto_close_minutes = getattr(config.browser, 'auto_close_minutes', 10) if hasattr(config, 'browser') else 10
    
    async def _ensure_browser(self):
        """懒加载浏览器实例"""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright 未安装。请运行: pip install playwright && playwright install chromium")
        
        # 自动关闭超时检测
        if self._browser and self._last_activity > 0:
            idle_minutes = (time.time() - self._last_activity) / 60
            if idle_minutes > self._auto_close_minutes:
                log.info(f"浏览器空闲 {idle_minutes:.0f} 分钟，自动关闭")
                await self._close_browser()
        
        if self._browser is None or not self._browser.is_connected():
            log.info("正在初始化 Playwright 浏览器...")
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self._headless,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            self._context = await self._browser.new_context(
                viewport={'width': self._viewport_w, 'height': self._viewport_h},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            self._page = await self._context.new_page()
            self._page.set_default_timeout(self._timeout)
            log.info(f"浏览器已启动 (headless={self._headless})")
        
        self._last_activity = time.time()
        return self._page
    
    async def _close_browser(self):
        """关闭浏览器"""
        try:
            if self._context:
                await self._context.close()
                self._context = None
            if self._browser:
                await self._browser.close()
                self._browser = None
            if self._playwright:
                await self._playwright.stop()
                self._playwright = None
            self._page = None
            log.info("浏览器已关闭")
        except Exception as e:
            log.warning(f"关闭浏览器时出错: {e}")
    
    async def execute(self, action: str, **params) -> SkillResult:
        """执行浏览器操作"""
        actions = {
            "open_page": self._open_page,
            "click": self._click,
            "type_text": self._type_text,
            "screenshot": self._screenshot,
            "get_text": self._get_text,
            "execute_js": self._execute_js,
            "extract_data": self._extract_data,
            "scroll": self._scroll,
            "wait_for": self._wait_for,
            "get_page_info": self._get_page_info,
            "go_back": self._go_back,
            "close": self._close,
        }
        
        if action not in actions:
            return SkillResult(
                success=False,
                output=None,
                error=f"未知的操作: {action}。可用操作: {', '.join(actions.keys())}"
            )
        
        if not PLAYWRIGHT_AVAILABLE:
            return SkillResult(
                success=False,
                output=None,
                error="Playwright 未安装。请运行: pip install playwright && playwright install chromium"
            )
        
        try:
            return await actions[action](**params)
        except Exception as e:
            log.error(f"浏览器操作失败 [{action}]: {e}")
            return SkillResult(success=False, output=None, error=str(e))
    
    async def _open_page(self, url: str, wait_until: str = "domcontentloaded") -> SkillResult:
        """打开指定 URL"""
        page = await self._ensure_browser()
        
        try:
            response = await page.goto(url, wait_until=wait_until, timeout=self._timeout)
            title = await page.title()
            
            # 自动截图
            screenshot_path = await self._take_screenshot(f"page_{int(time.time())}")
            
            return SkillResult(
                success=True,
                output={
                    "url": page.url,
                    "title": title,
                    "status": response.status if response else None,
                    "screenshot": screenshot_path
                },
                attachments=[{"type": "image", "path": screenshot_path, "title": "Page Screenshot"}]
            )
        except Exception as e:
            return SkillResult(success=False, output=None, error=f"打开页面失败: {e}")
    
    async def _click(self, selector: str = None, text: str = None) -> SkillResult:
        """点击页面元素"""
        page = await self._ensure_browser()
        
        try:
            if text:
                # 文本匹配点击
                await page.get_by_text(text, exact=False).first.click(timeout=self._timeout)
                target = f"text='{text}'"
            elif selector:
                await page.click(selector, timeout=self._timeout)
                target = selector
            else:
                return SkillResult(success=False, output=None, error="必须提供 selector 或 text 参数")
            
            # 等待可能的页面变化
            await page.wait_for_load_state("domcontentloaded", timeout=20000)
            
            return SkillResult(
                success=True,
                output={"clicked": target, "current_url": page.url}
            )
        except Exception as e:
            return SkillResult(success=False, output=None, error=f"点击失败: {e}")
    
    async def _type_text(self, selector: str = None, text: str = "", placeholder: str = None, press_enter: bool = False) -> SkillResult:
        """在输入框中输入文本"""
        page = await self._ensure_browser()
        
        try:
            if placeholder:
                element = page.get_by_placeholder(placeholder)
            elif selector:
                element = page.locator(selector)
            else:
                return SkillResult(success=False, output=None, error="必须提供 selector 或 placeholder 参数")
            
            await element.fill(text, timeout=self._timeout)
            
            if press_enter:
                await element.press("Enter")
                await page.wait_for_load_state("domcontentloaded", timeout=20000)
            
            return SkillResult(
                success=True,
                output={"typed": text[:50], "selector": selector or f"placeholder='{placeholder}'"}
            )
        except Exception as e:
            return SkillResult(success=False, output=None, error=f"输入文本失败: {e}")
    
    async def _screenshot(self, filename: str = None, full_page: bool = False, selector: str = None) -> SkillResult:
        """截取页面截图"""
        page = await self._ensure_browser()
        
        try:
            name = filename or f"screenshot_{int(time.time())}"
            path = await self._take_screenshot(name, full_page=full_page, selector=selector)
            
            return SkillResult(
                success=True,
                output={"screenshot_path": path, "url": page.url},
                attachments=[{"type": "image", "path": path, "title": filename or "Screenshot"}]
            )
        except Exception as e:
            return SkillResult(success=False, output=None, error=f"截图失败: {e}")
    
    async def _take_screenshot(self, name: str, full_page: bool = False, selector: str = None) -> str:
        """内部截图方法"""
        screenshot_dir = Path(self._screenshot_dir)
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = str(screenshot_dir / f"{name}.png")
        
        if selector:
            element = self._page.locator(selector)
            await element.screenshot(path=filepath)
        else:
            await self._page.screenshot(path=filepath, full_page=full_page)
        
        return filepath
    
    async def _get_text(self, selector: str = None, all_text: bool = False) -> SkillResult:
        """获取页面元素的文本内容"""
        page = await self._ensure_browser()
        
        try:
            if all_text:
                # 获取整个页面的可见文本
                text = await page.inner_text("body")
                # 截断过长文本
                if len(text) > 5000:
                    text = text[:5000] + "\n... [文本已截断]"
                return SkillResult(success=True, output={"text": text, "selector": "body"})
            
            if selector:
                text = await page.inner_text(selector, timeout=self._timeout)
                return SkillResult(success=True, output={"text": text, "selector": selector})
            
            return SkillResult(success=False, output=None, error="必须提供 selector 或设置 all_text=True")
        except Exception as e:
            return SkillResult(success=False, output=None, error=f"获取文本失败: {e}")
    
    async def _execute_js(self, script: str) -> SkillResult:
        """执行 JavaScript 代码"""
        page = await self._ensure_browser()
        
        try:
            result = await page.evaluate(script)
            return SkillResult(
                success=True,
                output={"result": str(result) if result is not None else None}
            )
        except Exception as e:
            return SkillResult(success=False, output=None, error=f"JS 执行失败: {e}")
    
    async def _extract_data(self, selector: str, attributes: List[str] = None) -> SkillResult:
        """结构化提取页面数据 (表格/列表)"""
        page = await self._ensure_browser()
        
        try:
            elements = await page.query_selector_all(selector)
            
            data = []
            for el in elements[:50]:  # 限制数量
                item = {"text": await el.inner_text()}
                
                if attributes:
                    for attr in attributes:
                        item[attr] = await el.get_attribute(attr)
                
                data.append(item)
            
            return SkillResult(
                success=True,
                output={"count": len(data), "data": data, "selector": selector}
            )
        except Exception as e:
            return SkillResult(success=False, output=None, error=f"数据提取失败: {e}")
    
    async def _scroll(self, direction: str = "down", amount: int = 500) -> SkillResult:
        """滚动页面"""
        page = await self._ensure_browser()
        
        try:
            if direction == "down":
                await page.evaluate(f"window.scrollBy(0, {amount})")
            elif direction == "up":
                await page.evaluate(f"window.scrollBy(0, -{amount})")
            elif direction == "top":
                await page.evaluate("window.scrollTo(0, 0)")
            elif direction == "bottom":
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            
            return SkillResult(
                success=True,
                output={"scrolled": direction, "amount": amount}
            )
        except Exception as e:
            return SkillResult(success=False, output=None, error=f"滚动失败: {e}")
    
    async def _wait_for(self, selector: str, state: str = "visible", timeout: int = None) -> SkillResult:
        """等待元素出现"""
        page = await self._ensure_browser()
        
        try:
            await page.wait_for_selector(
                selector,
                state=state,
                timeout=timeout or self._timeout
            )
            return SkillResult(
                success=True,
                output={"found": selector, "state": state}
            )
        except Exception as e:
            return SkillResult(success=False, output=None, error=f"等待元素超时: {e}")
    
    async def _get_page_info(self) -> SkillResult:
        """获取当前页面信息"""
        page = await self._ensure_browser()
        
        try:
            title = await page.title()
            url = page.url
            
            # 获取页面基础信息
            info = await page.evaluate("""() => ({
                title: document.title,
                url: window.location.href,
                links_count: document.querySelectorAll('a').length,
                images_count: document.querySelectorAll('img').length,
                inputs_count: document.querySelectorAll('input, textarea').length,
                buttons_count: document.querySelectorAll('button, [type="submit"]').length,
                viewport: { width: window.innerWidth, height: window.innerHeight },
                scroll_height: document.body.scrollHeight,
            })""")
            
            return SkillResult(success=True, output=info)
        except Exception as e:
            return SkillResult(success=False, output=None, error=f"获取页面信息失败: {e}")
    
    async def _go_back(self) -> SkillResult:
        """浏览器后退"""
        page = await self._ensure_browser()
        
        try:
            await page.go_back(wait_until="domcontentloaded")
            title = await page.title()
            return SkillResult(
                success=True,
                output={"url": page.url, "title": title}
            )
        except Exception as e:
            return SkillResult(success=False, output=None, error=f"后退失败: {e}")
    
    async def _close(self) -> SkillResult:
        """关闭浏览器"""
        await self._close_browser()
        return SkillResult(success=True, output="浏览器已关闭")
    
    def get_schema(self) -> Dict[str, Any]:
        """获取 Function Calling Schema"""
        return {
            "type": "function",
            "function": {
                "name": "browser_automation",
                "description": "浏览器自动化操作：打开网页、点击元素、输入文本、截取截图、提取页面数据。可用于需要与网页进行交互的任务（如填写表单、点击按钮、提取动态内容）。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "description": "要执行的操作",
                            "enum": ["open_page", "click", "type_text", "screenshot",
                                     "get_text", "execute_js", "extract_data", "scroll",
                                     "wait_for", "get_page_info", "go_back", "close"]
                        },
                        "url": {
                            "type": "string",
                            "description": "要打开的 URL (open_page 时使用)"
                        },
                        "selector": {
                            "type": "string",
                            "description": "CSS 选择器 (click/type_text/get_text/extract_data/wait_for/screenshot 时使用)"
                        },
                        "text": {
                            "type": "string",
                            "description": "要点击的文本 (click 时) 或要输入的文本 (type_text 时)"
                        },
                        "placeholder": {
                            "type": "string",
                            "description": "输入框的 placeholder 文本 (type_text 时)"
                        },
                        "press_enter": {
                            "type": "boolean",
                            "description": "输入后是否按回车 (type_text 时)"
                        },
                        "all_text": {
                            "type": "boolean",
                            "description": "是否获取整个页面的文本 (get_text 时)"
                        },
                        "full_page": {
                            "type": "boolean",
                            "description": "是否截取整个页面 (screenshot 时)"
                        },
                        "filename": {
                            "type": "string",
                            "description": "截图文件名 (screenshot 时)"
                        },
                        "script": {
                            "type": "string",
                            "description": "要执行的 JavaScript 代码 (execute_js 时)"
                        },
                        "direction": {
                            "type": "string",
                            "description": "滚动方向 (scroll 时): up/down/top/bottom",
                            "enum": ["up", "down", "top", "bottom"]
                        },
                        "amount": {
                            "type": "integer",
                            "description": "滚动像素数 (scroll 时)"
                        },
                        "attributes": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "要提取的 HTML 属性列表 (extract_data 时)"
                        },
                        "state": {
                            "type": "string",
                            "description": "等待元素的目标状态 (wait_for 时)",
                            "enum": ["visible", "hidden", "attached", "detached"]
                        },
                        "wait_until": {
                            "type": "string",
                            "description": "页面加载等待条件 (open_page 时)",
                            "enum": ["domcontentloaded", "load", "networkidle"]
                        }
                    },
                    "required": ["action"]
                }
            }
        }
