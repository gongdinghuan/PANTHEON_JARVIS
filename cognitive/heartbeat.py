"""
JARVIS 心跳引擎
让 JARVIS 具有生命感和时间感知能力

Author: gngdingghuan
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass, field

from utils.logger import log


@dataclass
class SessionStats:
    """会话统计"""
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())
    total_requests: int = 0
    total_heartbeats: int = 0
    last_active: str = field(default_factory=lambda: datetime.now().isoformat())
    last_heartbeat: Optional[str] = None


@dataclass
class TimeEvent:
    """时间事件"""
    hour: int
    minute: int
    callback: Callable
    name: Optional[str] = None
    last_triggered: Optional[str] = None


class HeartbeatEngine:
    """
    心跳引擎
    
    功能：
    - 生命周期管理（启动时间、运行时长）
    - 时间感知（当前时间、日期、时段）
    - 智能问候（根据时段返回合适的问候）
    - 心跳日志（可选）
    - 时间事件（注册回调函数，支持精确到分钟的时间点）
    """
    
    def __init__(self, interval: int = 1, log_heartbeat: bool = False, timezone: str = "Asia/Shanghai"):
        """
        初始化心跳引擎并立即感知当前时间
        
        Args:
            interval: 心跳间隔（秒）
            log_heartbeat: 是否记录心跳日志
            timezone: 时区
        """
        self.interval = interval
        self.log_heartbeat = log_heartbeat
        self.timezone = timezone
        
        self._running = False
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._stats = SessionStats()
        
        # 小时级事件（保持向后兼容）
        self._hourly_events: Dict[int, List[Callable]] = {}
        
        # 精确时间点事件（新功能）
        self._time_events: List[TimeEvent] = []
        
        # 立即感知当前时间
        self._current_time_info = self.get_current_time()
        self._current_greeting = self.get_greeting()
        
        # 记录初始化时间
        init_time = datetime.now()
        self._init_time = init_time.isoformat()
        self._init_time_formatted = init_time.strftime("%Y年%m月%d日 %H:%M:%S")
        
        log.info(f"心跳引擎初始化完成 | 间隔: {interval}秒 | 当前: {self._init_time_formatted} | {self._current_time_info['period_cn']}")
    
    def start(self):
        """启动心跳"""
        if self._running:
            log.warning("心跳引擎已在运行")
            return
        
        self._running = True
        self._stats.start_time = datetime.now().isoformat()
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        log.info("心跳引擎已启动")
    
    async def stop(self):
        """停止心跳"""
        if not self._running:
            return
        
        self._running = False
        
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        
        log.info("心跳引擎已停止")
    
    async def _heartbeat_loop(self):
        """心跳循环"""
        try:
            while self._running:
                await asyncio.sleep(self.interval)
                
                if not self._running:
                    break
                
                await self._beat()
                
        except asyncio.CancelledError:
            log.debug("心跳循环被取消")
        except Exception as e:
            log.error(f"心跳循环错误: {e}")
    
    async def _beat(self):
        """单次心跳"""
        self._stats.total_heartbeats += 1
        self._stats.last_heartbeat = datetime.now().isoformat()
        
        if self.log_heartbeat:
            uptime = self.get_uptime()
            current_time = self.get_current_time()
            log.info(f"💓 心跳 - 运行时长: {uptime} | 当前时间: {current_time['time']}")
        
        # 检查时间事件
        await self._check_time_events()
    
    async def _check_time_events(self):
        """检查并触发时间事件"""
        now = datetime.now()
        current_hour = now.hour
        current_minute = now.minute
        current_date = now.date()
        
        # 检查小时级事件（向后兼容）
        if current_hour in self._hourly_events:
            for callback in self._hourly_events[current_hour]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback()
                    else:
                        callback()
                except Exception as e:
                    log.error(f"小时事件回调失败: {e}")
        
        # 检查精确时间点事件
        for event in self._time_events:
            if event.hour == current_hour and event.minute == current_minute:
                # 检查是否已经在当前日期的这个时间点触发过
                if event.last_triggered:
                    last_triggered = datetime.fromisoformat(event.last_triggered)
                    # 如果已经在今天的这个时间点触发过，跳过
                    if (last_triggered.date() == current_date and
                        last_triggered.hour == current_hour and
                        last_triggered.minute == current_minute):
                        continue
                
                # 立即标记为已触发（防止并发重复触发）
                event.last_triggered = now.isoformat()
                
                # 异步触发事件（不阻塞心跳循环）
                try:
                    event_name = event.name or f"{event.hour:02d}:{event.minute:02d}"
                    log.info(f"触发时间事件: {event_name}")
                    
                    if asyncio.iscoroutinefunction(event.callback):
                        asyncio.create_task(event.callback())
                    else:
                        event.callback()
                    
                except Exception as e:
                    log.error(f"时间点事件回调失败 ({event_name}): {e}")
    
    def get_uptime(self) -> str:
        """
        获取运行时长
        
        Returns:
            格式化的运行时长字符串
        """
        start = datetime.fromisoformat(self._stats.start_time)
        now = datetime.now()
        delta = now - start
        
        hours = int(delta.total_seconds() // 3600)
        minutes = int((delta.total_seconds() % 3600) // 60)
        seconds = int(delta.total_seconds() % 60)
        
        if hours > 0:
            return f"{hours}小时{minutes}分{seconds}秒"
        elif minutes > 0:
            return f"{minutes}分{seconds}秒"
        else:
            return f"{seconds}秒"
    
    def get_current_time(self) -> Dict[str, Any]:
        """
        获取当前时间信息
        
        Returns:
            时间信息字典
        """
        now = datetime.now()
        
        return {
            "time": now.strftime("%H:%M:%S"),
            "hour": now.hour,
            "minute": now.minute,
            "second": now.second,
            "date": now.strftime("%Y-%m-%d"),
            "weekday": now.strftime("%A"),
            "weekday_cn": self._get_weekday_cn(now.weekday()),
            "period": self._get_time_period(now.hour),
            "period_cn": self._get_time_period_cn(now.hour),
        }
    
    def _get_weekday_cn(self, weekday: int) -> str:
        """获取中文星期"""
        weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        return weekdays[weekday]
    
    def _get_time_period(self, hour: int) -> str:
        """获取时段（英文）"""
        if 0 <= hour < 5:
            return "early_morning"
        elif 5 <= hour < 9:
            return "morning"
        elif 9 <= hour < 12:
            return "forenoon"
        elif 12 <= hour < 14:
            return "noon"
        elif 14 <= hour < 18:
            return "afternoon"
        elif 18 <= hour < 22:
            return "evening"
        else:
            return "night"
    
    def _get_time_period_cn(self, hour: int) -> str:
        """获取时段（中文）"""
        if 0 <= hour < 5:
            return "凌晨"
        elif 5 <= hour < 9:
            return "早晨"
        elif 9 <= hour < 12:
            return "上午"
        elif 12 <= hour < 14:
            return "中午"
        elif 14 <= hour < 18:
            return "下午"
        elif 18 <= hour < 22:
            return "傍晚"
        else:
            return "深夜"
    
    def get_greeting(self) -> str:
        """
        获取时间相关的问候语
        
        Returns:
            问候语字符串
        """
        hour = datetime.now().hour
        period_cn = self._get_time_period_cn(hour)
        
        greetings = {
            "凌晨": "夜深了，Sir，还在工作吗？",
            "早晨": "早上好，Sir，新的一天开始了！",
            "上午": "上午好，Sir！",
            "中午": "午饭时间到了，记得休息",
            "下午": "下午好，Sir！",
            "傍晚": "晚上好，Sir，辛苦了一天",
            "深夜": "这么晚了，注意休息，Sir",
        }
        
        return greetings.get(period_cn, "你好，Sir")
    
    def record_activity(self):
        """记录活动"""
        self._stats.total_requests += 1
        self._stats.last_active = datetime.now().isoformat()
    
    def get_session_stats(self) -> Dict[str, Any]:
        """
        获取会话统计
        
        Returns:
            会话统计字典
        """
        return {
            "start_time": self._stats.start_time,
            "init_time": getattr(self, '_init_time', None),
            "uptime": self.get_uptime(),
            "total_requests": self._stats.total_requests,
            "total_heartbeats": self._stats.total_heartbeats,
            "last_active": self._stats.last_active,
            "last_heartbeat": self._stats.last_heartbeat,
            "running": self._running,
            "current_time": self.get_current_time(),
        }
    
    def get_init_time_info(self) -> Dict[str, Any]:
        """
        获取初始化时的时间信息
        
        Returns:
            初始化时间信息字典
        """
        return {
            "init_time": getattr(self, '_init_time', None),
            "init_time_formatted": getattr(self, '_init_time_formatted', None),
            "init_time_info": getattr(self, '_current_time_info', {}),
            "init_greeting": getattr(self, '_current_greeting', ''),
        }
    
    def get_init_greeting(self) -> str:
        """
        获取初始化时的问候语
        
        Returns:
            问候语字符串
        """
        return getattr(self, '_current_greeting', '你好，Sir')
    
    def get_init_time_formatted(self) -> str:
        """
        获取格式化的初始化时间
        
        Returns:
            格式化的时间字符串
        """
        return getattr(self, '_init_time_formatted', '')
    
    def get_heartbeat_status(self) -> str:
        """
        获取心跳状态（用于显示）
        
        Returns:
            心跳状态字符串
        """
        stats = self.get_session_stats()
        current = stats["current_time"]
        init_info = self.get_init_time_info()
        
        status = f"""
## 心跳状态

- **状态**: {'🟢 正常' if self._running else '🔴 已停止'}
- **启动时间**: {init_info.get('init_time_formatted', 'N/A')}
- **当前时间**: {current['date']} {current['weekday_cn']} {current['time']}
- **当前时段**: {current['period_cn']}
- **运行时长**: {stats['uptime']}
- **会话请求**: {stats['total_requests']} 次
- **心跳次数**: {stats['total_heartbeats']} 次
- **最后活跃**: {stats['last_active'].split('T')[1][:8] if stats['last_active'] else 'N/A'}
"""
        
        if stats['last_heartbeat']:
            status += f"- **最后心跳**: {stats['last_heartbeat'].split('T')[1][:8]}\n"
        
        return status.strip()
    
    def register_time_event(self, hour: int, callback: Callable):
        """
        注册小时级时间事件（向后兼容）
        
        Args:
            hour: 小时（0-23）
            callback: 回调函数
        """
        if hour not in self._hourly_events:
            self._hourly_events[hour] = []
        
        self._hourly_events[hour].append(callback)
        log.info(f"已注册小时级时间事件: {hour}:00")
    
    def register_timepoint_event(self, hour: int, minute: int, callback: Callable, name: Optional[str] = None):
        """
        注册精确时间点事件（新功能）
        
        Args:
            hour: 小时（0-23）
            minute: 分钟（0-59）
            callback: 回调函数
            name: 事件名称（可选）
        """
        event = TimeEvent(
            hour=hour,
            minute=minute,
            callback=callback,
            name=name
        )
        self._time_events.append(event)
        event_name = name or f"{hour:02d}:{minute:02d}"
        log.info(f"已注册时间点事件: {event_name}")
        
        return event
    
    def unregister_time_event(self, hour: int, callback: Callable):
        """
        取消注册小时级时间事件
        
        Args:
            hour: 小时（0-23）
            callback: 回调函数
        """
        if hour in self._hourly_events:
            if callback in self._hourly_events[hour]:
                self._hourly_events[hour].remove(callback)
                log.info(f"已取消小时级时间事件: {hour}:00")
    
    def unregister_timepoint_event(self, event: TimeEvent):
        """
        取消注册时间点事件
        
        Args:
            event: 时间事件对象
        """
        if event in self._time_events:
            self._time_events.remove(event)
            event_name = event.name or f"{event.hour:02d}:{event.minute:02d}"
            log.info(f"已取消时间点事件: {event_name}")
    
    def get_registered_events(self) -> Dict[str, Any]:
        """
        获取所有已注册的事件
        
        Returns:
            事件字典
        """
        return {
            "hourly_events": {
                hour: len(callbacks)
                for hour, callbacks in self._hourly_events.items()
            },
            "timepoint_events": [
                {
                    "name": event.name or f"{event.hour:02d}:{event.minute:02d}",
                    "time": f"{event.hour:02d}:{event.minute:02d}",
                    "last_triggered": event.last_triggered
                }
                for event in self._time_events
            ]
        }
    
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._running
