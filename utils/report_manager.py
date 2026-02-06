"""
JARVIS 报告管理器
统一管理生成的报告文件

Author: gngdingghuan
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict

from utils.logger import log
from config import get_config
import pytz


# 报告存储目录
REPORTS_DIR = Path(__file__).parent.parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


@dataclass
class ReportMeta:
    """报告元数据"""
    id: str
    title: str
    file_name: str
    file_path: str
    file_type: str  # pdf, html, txt, md, json
    file_size: int
    created_at: str
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class ReportManager:
    """报告管理器"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.reports_dir = REPORTS_DIR
        self.meta_file = REPORTS_DIR / "reports_index.json"
        self.reports: Dict[str, ReportMeta] = {}
        self._load_index()
        self._initialized = True
        log.info(f"ReportManager 初始化完成，报告目录: {self.reports_dir}")
    
    def _load_index(self):
        """加载报告索引"""
        if self.meta_file.exists():
            try:
                with open(self.meta_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for item in data:
                        meta = ReportMeta(**item)
                        self.reports[meta.id] = meta
                log.debug(f"加载了 {len(self.reports)} 个报告索引")
            except Exception as e:
                log.warning(f"加载报告索引失败: {e}")
    
    def _save_index(self):
        """保存报告索引"""
        try:
            data = [asdict(meta) for meta in self.reports.values()]
            with open(self.meta_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log.error(f"保存报告索引失败: {e}")
    
    def save_report(
        self,
        content: str,
        title: str,
        file_type: str = "txt",
        description: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> ReportMeta:
        """
        保存报告
        
        Args:
            content: 报告内容
            title: 报告标题
            file_type: 文件类型 (txt, md, html, json)
            description: 报告描述
            tags: 标签列表
            
        Returns:
            报告元数据
        """
        # 生成唯一 ID
        try:
            timezone_str = get_config().heartbeat.timezone
            tz = pytz.timezone(timezone_str)
            now = datetime.now(tz)
        except:
            now = datetime.now()
            
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        report_id = f"report_{timestamp}"
        
        # 生成文件名 (清理特殊字符)
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_', '中文')).strip()
        safe_title = safe_title[:50] if len(safe_title) > 50 else safe_title
        file_name = f"{safe_title}_{timestamp}.{file_type}"
        file_path = self.reports_dir / file_name
        
        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # 创建元数据
        meta = ReportMeta(
            id=report_id,
            title=title,
            file_name=file_name,
            file_path=str(file_path),
            file_type=file_type,
            file_size=len(content.encode('utf-8')),
            created_at=now.isoformat(),
            description=description,
            tags=tags
        )
        
        # 保存索引
        self.reports[report_id] = meta
        self._save_index()
        
        log.info(f"报告已保存: {title} -> {file_name}")
        return meta
    
    def save_binary_report(
        self,
        content: bytes,
        title: str,
        file_type: str = "pdf",
        description: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> ReportMeta:
        """保存二进制报告 (如 PDF)"""
        try:
            timezone_str = get_config().heartbeat.timezone
            tz = pytz.timezone(timezone_str)
            now = datetime.now(tz)
        except:
            now = datetime.now()
            
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        report_id = f"report_{timestamp}"
        
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()[:50]
        file_name = f"{safe_title}_{timestamp}.{file_type}"
        file_path = self.reports_dir / file_name
        
        with open(file_path, 'wb') as f:
            f.write(content)
        
        meta = ReportMeta(
            id=report_id,
            title=title,
            file_name=file_name,
            file_path=str(file_path),
            file_type=file_type,
            file_size=len(content),
            created_at=now.isoformat(),
            description=description,
            tags=tags
        )
        
        self.reports[report_id] = meta
        self._save_index()
        
        log.info(f"二进制报告已保存: {title} -> {file_name}")
        return meta
    
    def get_report(self, report_id: str) -> Optional[ReportMeta]:
        """获取报告元数据"""
        return self.reports.get(report_id)
    
    def get_report_content(self, report_id: str) -> Optional[str]:
        """获取报告内容"""
        meta = self.reports.get(report_id)
        if not meta:
            return None
        
        file_path = Path(meta.file_path)
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except:
            return None
    
    def list_reports(self, limit: int = 20, tags: Optional[List[str]] = None) -> List[ReportMeta]:
        """列出报告"""
        reports = list(self.reports.values())
        
        # 按标签过滤
        if tags:
            reports = [r for r in reports if r.tags and any(t in r.tags for t in tags)]
        
        # 按时间排序 (最新的在前)
        reports.sort(key=lambda r: r.created_at, reverse=True)
        
        return reports[:limit]
    
    def delete_report(self, report_id: str) -> bool:
        """删除报告"""
        meta = self.reports.get(report_id)
        if not meta:
            return False
        
        # 删除文件
        file_path = Path(meta.file_path)
        if file_path.exists():
            file_path.unlink()
        
        # 从索引删除
        del self.reports[report_id]
        self._save_index()
        
        log.info(f"报告已删除: {report_id}")
        return True
    
    def create_attachment_info(self, meta: ReportMeta) -> Dict[str, Any]:
        """
        创建附件信息 (用于前端显示)
        
        Returns:
            可用于 SkillResult.attachments 的字典
        """
        # 图标映射
        icons = {
            "pdf": "📄",
            "txt": "📝",
            "md": "📋",
            "html": "🌐",
            "json": "📊",
        }
        
        return {
            "id": meta.id,
            "title": meta.title,
            "file_name": meta.file_name,
            "file_type": meta.file_type,
            "file_size": meta.file_size,
            "file_size_text": self._format_file_size(meta.file_size),
            "created_at": meta.created_at,
            "description": meta.description,
            "icon": icons.get(meta.file_type, "📁"),
            "download_url": f"/api/reports/{meta.id}/download",
            "preview_url": f"/api/reports/{meta.id}/preview"
        }
    
    def _format_file_size(self, size: int) -> str:
        """格式化文件大小"""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"


# 全局实例
_report_manager: Optional[ReportManager] = None


def get_report_manager() -> ReportManager:
    """获取全局报告管理器实例"""
    global _report_manager
    if _report_manager is None:
        _report_manager = ReportManager()
    return _report_manager
