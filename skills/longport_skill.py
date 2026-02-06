
"""
LongPort 股票数据技能
使用 LongPort Open API 获取实时股票行情和历史数据
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

from longport.openapi import QuoteContext, Config
from longport.openapi import Period, AdjustType

from skills.base_skill import BaseSkill, create_tool_schema, SkillResult
from config import get_config
from utils.logger import log

class LongPortSkill(BaseSkill):
    name = "longport_skill"
    description = "提供股票查询功能，支持获取实时行情、K线数据、公司概况等"
    
    def __init__(self):
        super().__init__()
        self.config = get_config().longport
        self._ctx: Optional[QuoteContext] = None
        
    async def initialize(self) -> bool:
        """初始化连接"""
        if not self.config.enabled:
            log.warning("LongPort 配置未启用 (缺少 APP KEY)")
            return False
            
        try:
            # 验证配置
            if not all([self.config.app_key, self.config.app_secret, self.config.access_token]):
                log.warning("LongPort 配置不完整")
                return False
                
            # 初始化配置
            lp_config = Config(
                app_key=self.config.app_key,
                app_secret=self.config.app_secret,
                access_token=self.config.access_token
            )
            
            # 创建 QuoteContext (行情上下文)
            # 注意：LongPort SDK 是同步/异步混合的，但 QuoteContext.create 是异步的吗？
            # 查阅文档，Config 是同步的，QuoteContext 通常可以异步 await QuoteContext.create(config)
            # 或者直接初始化 QuoteContext(config)
            # 直接初始化
            self._ctx = QuoteContext(lp_config)
            
            log.info("LongPort QuoteContext 初始化成功")
            return True
            
        except Exception as e:
            log.error(f"LongPort 初始化失败: {e}")
            return False

    async def execute(self, task: str, **kwargs) -> SkillResult:
        """
        执行任务
        
        Args:
            task: 任务类型 (quote, candlestick, static_info)
            kwargs: 参数 (symbol, period, count 等)
        """
        if not self._ctx:
            # 尝试延迟初始化
            success = await self.initialize()
            if not success:
                return SkillResult(False, None, error="LongPort service not available")
        
        try:
            if task == "quote":
                return await self._get_quote(kwargs.get("symbol"))
            elif task == "candlestick":
                return await self._get_candlestick(
                    symbol=kwargs.get("symbol"),
                    period=kwargs.get("period", "day"),
                    count=kwargs.get("count", 100)
                )
            elif task == "static_info":
                return await self._get_static_info(kwargs.get("symbol"))
            else:
                return SkillResult(False, None, error=f"Unknown task: {task}")
                
        except Exception as e:
            log.error(f"执行 LongPort 任务失败: {e}")
            return SkillResult(False, None, error=str(e))

    async def _get_quote(self, symbol: str) -> SkillResult:
        """获取实时行情"""
        if not symbol:
            return SkillResult(False, None, error="Missing symbol")
            
        # 确保 symbol 大写
        symbol = symbol.upper()
        
        # 调用 SDK
        quotes = self._ctx.quote([symbol])
        
        if not quotes:
            return SkillResult(False, None, error="No quote data found")
            
        q = quotes[0]
        
        return SkillResult(
            success=True,
            output=f"{symbol} 当前价格: {q.last_done} ({q.timestamp})",
            visualization={
                "type": "card",
                "data": {
                    "title": symbol,
                    "value": q.last_done,
                    "sub_value": str(q.timestamp),
                    "details": [
                        {"label": "开盘", "value": q.open},
                        {"label": "最高", "value": q.high},
                        {"label": "最低", "value": q.low},
                        {"label": "成交量", "value": q.volume}
                    ]
                }
            }
        )

    async def _get_candlestick(self, symbol: str, period: str, count: int) -> SkillResult:
        """获取K线数据"""
        if not symbol:
            return SkillResult(False, None, error="Missing symbol")
            
        symbol = symbol.upper()
        
        # 映射周期
        period_map = {
            "day": Period.Day,
            "week": Period.Week,
            "month": Period.Month,
            "year": Period.Year,
            "1min": Period.Min_1,
            "5min": Period.Min_5,
            "30min": Period.Min_30,
            "60min": Period.Min_60,
        }
        
        lp_period = period_map.get(period, Period.Day)
        
        # 调用 SDK
        candlesticks = self._ctx.candlesticks(symbol, lp_period, count, AdjustType.NoAdjust)
        
        data = []
        for k in candlesticks:
            data.append({
                "time": str(k.timestamp),
                "open": float(k.open),
                "high": float(k.high),
                "low": float(k.low),
                "close": float(k.close),
                "volume": int(k.volume)
            })
            
        return SkillResult(
            success=True,
            output=f"已获取 {symbol} 最近 {count} 条 {period} K线数据",
            visualization={
                "type": "echarts",
                "option": {
                    "title": {"text": f"{symbol} K线图"},
                    "tooltip": {"trigger": "axis", "axisPointer": {"type": "cross"}},
                    "xAxis": {"data": [d["time"] for d in data]},
                    "yAxis": {"scale": True},
                    "series": [{
                        "type": "candlestick",
                        "data": [[d["open"], d["close"], d["low"], d["high"]] for d in data]
                    }]
                }
            }
        )
        
    async def _get_static_info(self, symbol: str) -> SkillResult:
        """获取基础信息"""
        if not symbol:
            return SkillResult(False, None, error="Missing symbol")
            
        symbol = symbol.upper()
        
        infos = self._ctx.static_info([symbol])
        
        if not infos:
            return SkillResult(False, None, error="No static info found")
            
        info = infos[0]
        
        return SkillResult(
            success=True,
            output=f"{info.name_cn} ({info.symbol}) - {info.exchange}\n币种: {info.currency}, 每手: {info.lot_size}"
        )


    async def close(self):
        """关闭连接"""
        # QuoteContext 在当前 SDK 版本中可能没有显式的 close 方法，
        # 或者它是通过 __exit__ 管理的。
        # 如果有 close/exit 可以在这里调用
        pass

    def get_schema(self) -> Dict[str, Any]:
        return create_tool_schema(
            name=self.name,
            description=self.description,
            parameters={
                "task": {
                    "type": "string",
                    "description": "任务类型",
                    "enum": ["quote", "candlestick", "static_info"]
                },
                "symbol": {
                    "type": "string",
                    "description": "股票代码 (如 700.HK, AAPL.US)"
                },
                "period": {
                    "type": "string",
                    "description": "K线周期 (仅 task=candlestick 时有效)",
                    "enum": ["day", "week", "month", "year", "1min", "5min", "30min", "60min"],
                    "default": "day"
                },
                "count": {
                    "type": "integer",
                    "description": "K线数量 (仅 task=candlestick 时有效)",
                    "default": 100
                }
            },
            required=["task", "symbol"]
        )

