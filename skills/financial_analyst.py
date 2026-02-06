"""
JARVIS 金融分析技能
利用 LongPort 和 Google 搜索提供专业的金融数据分析

Author: gngdingghuan
"""

from googlesearch import search
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import asyncio

from longport.openapi import QuoteContext, Config, Period, AdjustType
from skills.base_skill import BaseSkill, SkillResult, PermissionLevel, create_tool_schema
from config import get_config
from utils.logger import log
from utils.compat import to_thread

class FinancialAnalystSkill(BaseSkill):
    """金融分析技能"""
    
    name = "financial_analyst"
    description = "金融市场分析：股票行情、财务数据、市场新闻、投资报告"
    permission_level = PermissionLevel.READ_ONLY
    
    def __init__(self):
        super().__init__()
        self.lp_config = get_config().longport
        self._ctx: Optional[QuoteContext] = None
        
    async def _ensure_context(self) -> bool:
        """确保 LongPort Context 已初始化"""
        if self._ctx:
            return True
            
        try:
            if not (self.lp_config.app_key and self.lp_config.app_secret and self.lp_config.access_token):
                log.error("LongPort 配置缺失")
                return False
                
            config = Config(
                app_key=self.lp_config.app_key,
                app_secret=self.lp_config.app_secret,
                access_token=self.lp_config.access_token
            )
            # 在线程中初始化以避免阻塞
            self._ctx = await to_thread(QuoteContext, config)
            return True
        except Exception as e:
            log.error(f"LongPort 初始化失败: {e}")
            return False
    
    async def execute(self, action: Optional[str] = None, **params) -> SkillResult:
        """执行金融分析任务"""
        actions = {
            "get_stock_info": self._get_stock_info,
            "search_news": self._search_news,
            "get_market_summary": self._get_market_summary,
            "get_report_data": self._get_report_data,
            "generate_analysis_report": self._generate_analysis_report
        }
        
        if not action:
            return SkillResult(success=False, output=None, error="缺少必需参数: action")

        if action not in actions:
            return SkillResult(success=False, output=None, error=f"未知的操作: {action}")
        
        # 确保连接
        if action in ["get_stock_info", "get_market_summary", "get_report_data", "generate_analysis_report"]:
            if not await self._ensure_context():
                return SkillResult(False, None, error="LongPort 服务不可用，请检查配置")
        
        try:
            return await actions[action](**params)
        except Exception as e:
            log.error(f"金融分析操作失败: {action}, 错误: {e}")
            return SkillResult(success=False, output=None, error=str(e))
            
    async def _get_stock_info(self, symbol: str) -> SkillResult:
        """获取股票详细信息 (Using LongPort)"""
        try:
            return await to_thread(self._sync_get_stock_info, symbol)
        except Exception as e:
            return SkillResult(success=False, output=None, error=f"获取股票信息失败: {e}")

    def _sync_get_stock_info(self, symbol: str) -> SkillResult:
        if not self._ctx:
            return SkillResult(False, None, error="Context not initialized")
            
        symbol = symbol.upper()
        
        # 1. 获取实时行情
        quotes = self._ctx.quote([symbol])
        if not quotes:
            return SkillResult(False, None, error=f"未找到股票行情: {symbol}")
        q = quotes[0]
        
        # 2. 获取静态信息
        infos = self._ctx.static_info([symbol])
        info = infos[0] if infos else None
        
        # 组装数据
        data = {
            "symbol": q.symbol,
            "name": info.name_cn if info else q.symbol,
            "name_en": info.name_en if info else "",
            "price": float(q.last_done),
            "currency": info.currency if info else "",
            "open": float(q.open),
            "high": float(q.high),
            "low": float(q.low),
            "volume": int(q.volume),
            "turnover": float(q.turnover),
            "market_cap": float(q.total_market_value) if hasattr(q, 'total_market_value') else None,
            "pe_ratio": float(q.pe_ttm) if hasattr(q, 'pe_ttm') else None,
            "dividend_yield": float(q.dividend_yield) if hasattr(q, 'dividend_yield') else None,
            "exchange": info.exchange if info else "",
            "lot_size": info.lot_size if info else 0,
            "timestamp": str(q.timestamp)
        }
        
        # 添加可视化卡片
        viz = {
            "type": "card",
            "data": {
                "title": f"{data['name']} ({data['symbol']})",
                "value": str(data['price']),
                "sub_value": f"{data['currency']} | {data['timestamp']}",
                "details": [
                    {"label": "今开", "value": data["open"]},
                    {"label": "最高", "value": data["high"]},
                    {"label": "最低", "value": data["low"]},
                    {"label": "成交额", "value": f"{data['turnover']/10000:.2f}万"}
                ]
            }
        }
        
        return SkillResult(success=True, output=data, visualization=viz)

    async def _search_news(self, query: str, num_results: int = 5) -> SkillResult:
        """搜索金融新闻 (Google)"""
        try:
            return await to_thread(self._sync_search_news, query, num_results)
        except Exception as e:
            return SkillResult(success=False, output=None, error=f"搜索新闻失败: {e}")

    def _sync_search_news(self, query: str, num_results: int) -> SkillResult:
        # 添加 "financial news" 或 "stock analysis" 后缀优化搜索
        search_query = f"{query} financial news analysis"
        results = []
        
        try:
            for url in search(search_query, num_results=num_results, advanced=True):
                results.append({
                    "title": url.title,
                    "url": url.url,
                    "description": url.description
                })
        except Exception as e:
            log.warning(f"Google 搜索失败 (可能触发验证码): {e}")
            return SkillResult(success=False, output=None, error=f"Google 搜索暂时不可用: {e}")

        return SkillResult(success=True, output=results)

    async def _get_market_summary(self) -> SkillResult:
        """获取市场摘要 (主要指数)"""
        # LongPort 指数代码可能不同，这里列出常见的
        indices_map = {
            "SPX.US": "标普500",
            "DJI.US": "道琼斯",
            "IXIC.US": "纳斯达克",
            "HSI.HK": "恒生指数",
            "000001.SH": "上证指数" # 注意: LongPort A股代码可能是 SH/SZ 后缀
        }
        
        symbols = list(indices_map.keys())
        
        try:
            return await to_thread(self._sync_get_market_summary, symbols, indices_map)
        except Exception as e:
            return SkillResult(success=False, output=None, error=f"获取市场摘要失败: {e}")

    def _sync_get_market_summary(self, symbols: List[str], indices_map: Dict[str, str]) -> SkillResult:
        if not self._ctx:
            return SkillResult(False, None, error="Context not initialized")
            
        quotes = self._ctx.quote(symbols)
        results = {}
        
        for q in quotes:
            name = indices_map.get(q.symbol, q.symbol)
            
            # 计算涨跌幅
            prev_close = float(q.prev_close_price)
            current = float(q.last_done)
            change_percent = ((current - prev_close) / prev_close) * 100 if prev_close else 0
            
            results[name] = {
                "price": current,
                "change_percent": round(change_percent, 2),
                "symbol": q.symbol
            }
            
        return SkillResult(success=True, output=results)

    async def _get_report_data(self, symbol: str) -> SkillResult:
        """获取生成报告所需的所有数据 (组合操作)"""
        # 并行获取数据
        stock_task = self._get_stock_info(symbol)
        news_task = self._search_news(f"{symbol} stock news", num_results=3)
        
        stock_res, news_res = await asyncio.gather(stock_task, news_task, return_exceptions=True)
        
        output = {
            "symbol": symbol,
            "generated_at": datetime.now().isoformat(),
            "stock_data": stock_res.output if isinstance(stock_res, SkillResult) and stock_res.success else None,
            "news_data": news_res.output if isinstance(news_res, SkillResult) and news_res.success else [],
            "error": []
        }
        
        if isinstance(stock_res, SkillResult) and not stock_res.success:
            output["error"].append(f"行情获取失败: {stock_res.error}")
        if isinstance(news_res, SkillResult) and not news_res.success:
            output["error"].append(f"新闻获取失败: {news_res.error}")
            
        return SkillResult(success=True, output=output)

    async def _generate_analysis_report(self, symbol: str) -> SkillResult:
        """生成并保存 HTML 分析报告"""
        from utils.report_manager import get_report_manager
        
        # 获取数据
        data_res = await self._get_report_data(symbol)
        if not data_res.success:
            return data_res
            
        data = data_res.output
        stock = data.get("stock_data", {})
        news = data.get("news_data", [])
        
        if not stock:
            return SkillResult(False, None, error="无法获取股票数据，无法生成报告")
            
        # 生成 HTML 内容
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{symbol} 深度分析报告</title>
            <style>
                body {{ font-family: 'Segoe UI', sans-serif; padding: 40px; background: #f5f7fa; color: #333; }}
                .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.05); }}
                h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 15px; }}
                h2 {{ color: #34495e; margin-top: 30px; }}
                .price-card {{ background: linear-gradient(135deg, #3498db, #2980b9); color: white; padding: 20px; border-radius: 10px; margin: 20px 0; display: flex; justify-content: space-between; align-items: center; }}
                .price {{ font-size: 2.5em; font-weight: bold; }}
                .change {{ font-size: 1.2em; }}
                .change.up {{ color: #2ecc71; }}
                .change.down {{ color: #e74c3c; }}
                .info-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin: 20px 0; }}
                .info-item {{ background: #f8f9fa; padding: 15px; border-radius: 8px; }}
                .label {{ color: #7f8c8d; font-size: 0.9em; }}
                .value {{ font-size: 1.2em; font-weight: 600; color: #2c3e50; }}
                .news-item {{ border-left: 4px solid #3498db; padding: 15px; margin-bottom: 15px; background: #f8f9fa; }}
                .news-title {{ font-weight: bold; margin-bottom: 5px; }}
                .news-link {{ color: #3498db; text-decoration: none; font-size: 0.9em; }}
                .footer {{ margin-top: 40px; font-size: 0.8em; color: #95a5a6; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📈 {stock.get('name', symbol)} ({symbol}) 深度分析报告</h1>
                
                <div class="price-card">
                    <div>
                        <div style="font-size: 0.9em; opacity: 0.8;">当前价格</div>
                        <div class="price">{stock.get('currency', '')} {stock.get('price', '--')}</div>
                    </div>
                    <div style="text-align: right;">
                        <div class="change" style="color: white;">
                            {stock.get('change_percent', 0)}%
                        </div>
                        <div style="font-size: 0.9em; opacity: 0.8;">{stock.get('change_amount', 0)}</div>
                    </div>
                </div>
                
                <div class="info-grid">
                    <div class="info-item">
                        <div class="label">开盘价</div>
                        <div class="value">{stock.get('open', '--')}</div>
                    </div>
                    <div class="info-item">
                        <div class="label">最高价</div>
                        <div class="value">{stock.get('high', '--')}</div>
                    </div>
                    <div class="info-item">
                        <div class="label">最低价</div>
                        <div class="value">{stock.get('low', '--')}</div>
                    </div>
                    <div class="info-item">
                        <div class="label">成交量</div>
                        <div class="value">{stock.get('volume', '--')}</div>
                    </div>
                </div>
                
                <h2>📰 相关新闻</h2>
                {''.join([f'''
                <div class="news-item">
                    <div class="news-title">{item['title']}</div>
                    <a href="{item['url']}" class="news-link" target="_blank">阅读原文</a>
                </div>
                ''' for item in news]) if news else '<p>暂无相关新闻</p>'}
                
                <div class="footer">
                    生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Generated by JARVIS Financial Analyst
                </div>
            </div>
        </body>
        </html>
        """
        
        # 保存报告
        manager = get_report_manager()
        meta = manager.save_report(
            content=html_content,
            title=f"{symbol} 分析报告",
            file_type="html",
            description=f"{symbol} 的详细市场数据与新闻分析",
            tags=["financial", "report", symbol]
        )
        
        return SkillResult(
            success=True,
            output=f"已生成 {symbol} 的深度分析报告。",
            attachments=[manager.create_attachment_info(meta)]
        )

    def get_schema(self) -> Dict[str, Any]:
        return create_tool_schema(
            name=self.name,
            description=self.description,
            parameters={
                "action": {
                    "type": "string",
                    "enum": ["get_stock_info", "search_news", "get_market_summary", "get_report_data", "generate_analysis_report"],
                    "description": "操作类型"
                },
                "symbol": {
                    "type": "string",
                    "description": "股票代码 (如 700.HK, AAPL.US)"
                },
                "query": {
                    "type": "string",
                    "description": "搜索关键词"
                },
                "num_results": {
                    "type": "integer",
                    "description": "搜索结果数量",
                    "default": 5
                }
            },
            required=["action"]
        )
