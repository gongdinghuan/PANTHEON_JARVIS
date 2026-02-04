"""
JARVIS 文件管理技能
文件读写、目录操作

Author: gngdingghuan
"""

import asyncio
import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from skills.base_skill import BaseSkill, SkillResult, PermissionLevel, create_tool_schema
from config import get_config
from utils.logger import log
from utils.compat import to_thread


class FileManagerSkill(BaseSkill):
    """文件管理技能"""
    
    name = "file_manager"
    description = "文件管理：读取、创建、移动、删除文件和目录"
    permission_level = PermissionLevel.SAFE_WRITE
    
    def __init__(self):
        super().__init__()
        self.security_config = get_config().security
    
    def _is_path_safe(self, path: str) -> bool:
        """检查路径是否安全"""
        path_obj = Path(path).resolve()
        path_str = str(path_obj)
        
        # 检查黑名单
        for forbidden in self.security_config.forbidden_directories:
            if path_str.startswith(forbidden):
                return False
        
        return True
    
    def needs_confirmation(self, params: Dict[str, Any]) -> bool:
        """危险操作需要确认"""
        action = params.get("action", "")
        return action in ["delete_file", "delete_directory", "move_file"]
    
    async def execute(self, action: str, **params) -> SkillResult:
        """执行文件管理操作"""
        actions = {
            "read_file": self._read_file,
            "write_file": self._write_file,
            "create_file": self._create_file,
            "delete_file": self._delete_file,
            "list_directory": self._list_directory,
            "create_directory": self._create_directory,
            "delete_directory": self._delete_directory,
            "move_file": self._move_file,
            "copy_file": self._copy_file,
            "file_info": self._file_info,
            "search_files": self._search_files,
        }
        
        if action not in actions:
            return SkillResult(success=False, output=None, error=f"未知的操作: {action}")
        
        try:
            result = await actions[action](**params)
            return result
        except Exception as e:
            log.error(f"文件操作失败: {action}, 错误: {e}")
            return SkillResult(success=False, output=None, error=str(e))
    
    async def _read_file(self, path: str, encoding: str = "utf-8") -> SkillResult:
        """读取文件内容"""
        if not self._is_path_safe(path):
            return SkillResult(success=False, output=None, error="访问被拒绝：路径不在安全范围内")
        
        path_obj = Path(path).expanduser()
        
        if not path_obj.exists():
            return SkillResult(success=False, output=None, error=f"文件不存在: {path}")
        
        if not path_obj.is_file():
            return SkillResult(success=False, output=None, error=f"不是文件: {path}")
        
        # 限制文件大小
        if path_obj.stat().st_size > 1024 * 1024:  # 1MB
            return SkillResult(success=False, output=None, error="文件过大（超过 1MB）")
        
        try:
            content = path_obj.read_text(encoding=encoding)
            log.info(f"读取文件: {path}, 大小: {len(content)} 字符")
            return SkillResult(success=True, output=content)
        except UnicodeDecodeError:
            return SkillResult(success=False, output=None, error="无法解码文件，可能是二进制文件")
    
    async def _write_file(self, path: str, content: str, encoding: str = "utf-8") -> SkillResult:
        """写入文件"""
        if not self._is_path_safe(path):
            return SkillResult(success=False, output=None, error="访问被拒绝：路径不在安全范围内")
        
        path_obj = Path(path).expanduser()
        
        try:
            path_obj.parent.mkdir(parents=True, exist_ok=True)
            path_obj.write_text(content, encoding=encoding)
            log.info(f"写入文件: {path}, 大小: {len(content)} 字符")
            return SkillResult(success=True, output=f"已写入文件: {path}")
        except Exception as e:
            return SkillResult(success=False, output=None, error=str(e))
    
    async def _create_file(self, path: str, content: str = "") -> SkillResult:
        """创建文件"""
        return await self._write_file(path, content)
    
    async def _delete_file(self, path: str) -> SkillResult:
        """删除文件"""
        if not self._is_path_safe(path):
            return SkillResult(success=False, output=None, error="访问被拒绝：路径不在安全范围内")
        
        path_obj = Path(path).expanduser()
        
        if not path_obj.exists():
            return SkillResult(success=False, output=None, error=f"文件不存在: {path}")
        
        if not path_obj.is_file():
            return SkillResult(success=False, output=None, error=f"不是文件: {path}")
        
        try:
            path_obj.unlink()
            log.warning(f"删除文件: {path}")
            return SkillResult(success=True, output=f"已删除文件: {path}")
        except Exception as e:
            return SkillResult(success=False, output=None, error=str(e))
    
    async def _list_directory(self, path: str, pattern: str = "*", detail: bool = False) -> SkillResult:
        """列出目录内容"""
        if not self._is_path_safe(path):
            return SkillResult(success=False, output=None, error="访问被拒绝：路径不在安全范围内")
        
        path_obj = Path(path).expanduser()
        
        if not path_obj.exists():
            return SkillResult(success=False, output=None, error=f"目录不存在: {path}")
        
        if not path_obj.is_dir():
            return SkillResult(success=False, output=None, error=f"不是目录: {path}")
        
        try:
            log.info(f"开始列出目录: {path}, 模式: {pattern}")
            items = []
            
            # 使用 asyncio.to_thread 来避免阻塞事件循环
            def list_items():
                result = []
                try:
                    for item in path_obj.glob(pattern):
                        item_info = {
                            "name": item.name,
                            "type": "directory" if item.is_dir() else "file",
                        }
                        if detail and item.is_file():
                            try:
                                item_info["size"] = item.stat().st_size
                            except:
                                item_info["size"] = 0
                        result.append(item_info)
                        
                        # 安全限制：最多处理 1000 个项目
                        if len(result) >= 1000:
                            log.warning(f"目录 {path} 文件过多，已限制到 1000 个")
                            break
                except Exception as e:
                    log.error(f"遍历目录时出错: {e}")
                    raise
                return result
            
            # 在线程池中执行，设置超时
            items = await asyncio.wait_for(
                to_thread(list_items),
                timeout=10.0  # 10 秒超时
            )
            
            # 按类型和名称排序
            items.sort(key=lambda x: (x["type"] != "directory", x["name"].lower()))
            
            log.info(f"目录 {path} 列出完成，共 {len(items)} 项")
            return SkillResult(success=True, output=items[:100])  # 返回最多 100 个
            
        except asyncio.TimeoutError:
            log.error(f"列出目录超时: {path}")
            return SkillResult(success=False, output=None, error=f"操作超时：目录 {path} 响应时间过长")
        except Exception as e:
            log.error(f"列出目录失败: {path}, 错误: {e}")
            return SkillResult(success=False, output=None, error=str(e))
    
    async def _create_directory(self, path: str) -> SkillResult:
        """创建目录"""
        if not self._is_path_safe(path):
            return SkillResult(success=False, output=None, error="访问被拒绝：路径不在安全范围内")
        
        path_obj = Path(path).expanduser()
        
        try:
            path_obj.mkdir(parents=True, exist_ok=True)
            log.info(f"创建目录: {path}")
            return SkillResult(success=True, output=f"已创建目录: {path}")
        except Exception as e:
            return SkillResult(success=False, output=None, error=str(e))
    
    async def _delete_directory(self, path: str) -> SkillResult:
        """删除目录"""
        if not self._is_path_safe(path):
            return SkillResult(success=False, output=None, error="访问被拒绝：路径不在安全范围内")
        
        path_obj = Path(path).expanduser()
        
        if not path_obj.exists():
            return SkillResult(success=False, output=None, error=f"目录不存在: {path}")
        
        if not path_obj.is_dir():
            return SkillResult(success=False, output=None, error=f"不是目录: {path}")
        
        try:
            shutil.rmtree(path_obj)
            log.warning(f"删除目录: {path}")
            return SkillResult(success=True, output=f"已删除目录: {path}")
        except Exception as e:
            return SkillResult(success=False, output=None, error=str(e))
    
    async def _move_file(self, source: str, destination: str) -> SkillResult:
        """移动文件"""
        if not self._is_path_safe(source) or not self._is_path_safe(destination):
            return SkillResult(success=False, output=None, error="访问被拒绝：路径不在安全范围内")
        
        src = Path(source).expanduser()
        dst = Path(destination).expanduser()
        
        if not src.exists():
            return SkillResult(success=False, output=None, error=f"源文件不存在: {source}")
        
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            log.info(f"移动文件: {source} -> {destination}")
            return SkillResult(success=True, output=f"已移动: {source} -> {destination}")
        except Exception as e:
            return SkillResult(success=False, output=None, error=str(e))
    
    async def _copy_file(self, source: str, destination: str) -> SkillResult:
        """复制文件"""
        if not self._is_path_safe(source) or not self._is_path_safe(destination):
            return SkillResult(success=False, output=None, error="访问被拒绝：路径不在安全范围内")
        
        src = Path(source).expanduser()
        dst = Path(destination).expanduser()
        
        if not src.exists():
            return SkillResult(success=False, output=None, error=f"源文件不存在: {source}")
        
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.is_dir():
                shutil.copytree(str(src), str(dst))
            else:
                shutil.copy2(str(src), str(dst))
            log.info(f"复制文件: {source} -> {destination}")
            return SkillResult(success=True, output=f"已复制: {source} -> {destination}")
        except Exception as e:
            return SkillResult(success=False, output=None, error=str(e))
    
    async def _file_info(self, path: str) -> SkillResult:
        """获取文件信息"""
        if not self._is_path_safe(path):
            return SkillResult(success=False, output=None, error="访问被拒绝：路径不在安全范围内")
        
        path_obj = Path(path).expanduser()
        
        if not path_obj.exists():
            return SkillResult(success=False, output=None, error=f"文件不存在: {path}")
        
        stat = path_obj.stat()
        
        info = {
            "name": path_obj.name,
            "path": str(path_obj.absolute()),
            "type": "directory" if path_obj.is_dir() else "file",
            "size": stat.st_size,
            "size_human": self._format_size(stat.st_size),
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "extension": path_obj.suffix if path_obj.is_file() else None,
        }
        
        return SkillResult(success=True, output=info)
    
    async def _search_files(self, pattern: str, directory: str = None, path: str = None, recursive: bool = True) -> SkillResult:
        """搜索文件
        
        Args:
            pattern: 搜索模式 (glob pattern)
            directory: 搜索目录 (也可用 path 参数)
            path: 搜索目录 (directory 的别名)
            recursive: 是否递归搜索
        """
        # 支持 path 作为 directory 的别名
        search_dir = directory or path or str(Path.home())
        if not self._is_path_safe(search_dir):
            return SkillResult(success=False, output=None, error="访问被拒绝：路径不在安全范围内")
        
        dir_obj = Path(search_dir).expanduser()
        
        if not dir_obj.exists() or not dir_obj.is_dir():
            return SkillResult(success=False, output=None, error=f"目录不存在: {search_dir}")
        
        try:
            if recursive:
                matches = list(dir_obj.rglob(pattern))
            else:
                matches = list(dir_obj.glob(pattern))
            
            results = [str(m) for m in matches[:50]]  # 限制数量
            
            return SkillResult(
                success=True,
                output={
                    "count": len(matches),
                    "files": results,
                    "truncated": len(matches) > 50
                }
            )
        except Exception as e:
            return SkillResult(success=False, output=None, error=str(e))
    
    def _format_size(self, size: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    def get_schema(self) -> Dict[str, Any]:
        """获取 Function Calling Schema"""
        return create_tool_schema(
            name="file_manager",
            description="文件管理操作：读取、写入、创建、删除、移动、复制文件和目录",
            parameters={
                "action": {
                    "type": "string",
                    "enum": [
                        "read_file",
                        "write_file",
                        "create_file",
                        "delete_file",
                        "list_directory",
                        "create_directory",
                        "delete_directory",
                        "move_file",
                        "copy_file",
                        "file_info",
                        "search_files"
                    ],
                    "description": "要执行的操作类型"
                },
                "path": {
                    "type": "string",
                    "description": "文件或目录路径"
                },
                "content": {
                    "type": "string",
                    "description": "文件内容（用于 write_file, create_file）"
                },
                "source": {
                    "type": "string",
                    "description": "源路径（用于 move_file, copy_file）"
                },
                "destination": {
                    "type": "string",
                    "description": "目标路径（用于 move_file, copy_file）"
                },
                "pattern": {
                    "type": "string",
                    "description": "匹配模式，如 *.txt（用于 list_directory, search_files）"
                },
                "recursive": {
                    "type": "boolean",
                    "description": "是否递归搜索（用于 search_files）"
                }
            },
            required=["action"]
        )
