"""
JARVIS Code Interpreter 技能
支持安全执行 Python 代码

Author: gngdingghuan
"""

import ast
import sys
import io
import traceback
from typing import Dict, Any, Optional
from contextlib import redirect_stdout, redirect_stderr

from skills.base_skill import BaseSkill, SkillResult, PermissionLevel, create_tool_schema
from utils.logger import log


class CodeInterpreterSkill(BaseSkill):
    """代码解释器技能 - 安全执行 Python 代码"""
    
    name = "code_interpreter"
    description = "执行 Python 代码，进行数据分析、计算、生成图表等"
    permission_level = PermissionLevel.SAFE_WRITE  # 自动执行 but log
    
    # 允许的内置函数
    ALLOWED_BUILTINS = {
        'abs', 'all', 'any', 'ascii', 'bin', 'bool', 'bytearray', 'bytes',
        'callable', 'chr', 'complex', 'dict', 'dir', 'divmod', 'enumerate',
        'filter', 'float', 'format', 'frozenset', 'getattr', 'hasattr', 'hash',
        'hex', 'id', 'int', 'isinstance', 'issubclass', 'iter', 'len', 'list',
        'map', 'max', 'min', 'next', 'object', 'oct', 'ord', 'pow', 'print',
        'range', 'repr', 'reversed', 'round', 'set', 'slice', 'sorted', 'str',
        'sum', 'tuple', 'type', 'vars', 'zip',
        # 数学相关
        'True', 'False', 'None',
    }
    
    # 允许导入的模块
    ALLOWED_MODULES = {
        'math', 'statistics', 'random', 'datetime', 'json', 're',
        'collections', 'itertools', 'functools', 'operator',
        'decimal', 'fractions',
    }
    
    # 危险的 AST 节点类型
    DANGEROUS_NODES = {
        ast.Import, ast.ImportFrom,  # 将手动处理
    }
    
    def __init__(self):
        super().__init__()
        self._execution_count = 0
        self._max_output_length = 10000
        self._timeout = 30  # 秒
        
    async def execute(self, code: Optional[str] = None, **params) -> SkillResult:
        """执行 Python 代码"""
        if not code:
            return SkillResult(
                success=False, 
                output=None, 
                error="缺少必需参数: code"
            )
        
        # 安全检查
        safety_check = self._check_code_safety(code)
        if not safety_check["safe"]:
            return SkillResult(
                success=False,
                output=None,
                error=f"代码安全检查未通过: {safety_check['reason']}",
                needs_confirmation=False
            )
        
        # 直接执行
        from utils.compat import to_thread
        try:
            return await to_thread(self.execute_code_sync, code)
        except Exception as e:
            return SkillResult(success=False, output=None, error=f"执行出错: {str(e)}")
    
    def _check_code_safety(self, code: str) -> Dict[str, Any]:
        """检查代码安全性"""
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {"safe": False, "reason": f"语法错误: {e}"}
        
        # 遍历 AST 检查危险操作
        for node in ast.walk(tree):
            # 检查导入
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split('.')[0] not in self.ALLOWED_MODULES:
                        return {"safe": False, "reason": f"不允许导入模块: {alias.name}"}
                        
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split('.')[0] not in self.ALLOWED_MODULES:
                    return {"safe": False, "reason": f"不允许导入模块: {node.module}"}
            
            # 检查危险函数调用
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in {'eval', 'exec', 'compile', 'open', 'input', 
                                        '__import__', 'globals', 'locals', 'vars'}:
                        return {"safe": False, "reason": f"不允许调用函数: {node.func.id}"}
                        
                elif isinstance(node.func, ast.Attribute):
                    # 检查属性访问
                    if node.func.attr.startswith('_'):
                        return {"safe": False, "reason": f"不允许访问私有属性: {node.func.attr}"}
            
            # 检查属性访问
            elif isinstance(node, ast.Attribute):
                if node.attr.startswith('__') and node.attr.endswith('__'):
                    if node.attr not in {'__name__', '__doc__', '__class__'}:
                        return {"safe": False, "reason": f"不允许访问 dunder 属性: {node.attr}"}
        
        return {"safe": True, "reason": None}
    
    def execute_code_sync(self, code: str) -> SkillResult:
        """同步执行代码 (在确认后调用)"""
        self._execution_count += 1
        
        # 构建受限的执行环境
        import math
        import statistics
        import random
        import datetime
        import json as json_module
        import re as re_module
        import collections
        import itertools
        import functools
        import operator
        import decimal
        import fractions
        
        safe_globals = {
            '__builtins__': {name: getattr(__builtins__ if isinstance(__builtins__, dict) else __builtins__, name, None) 
                            for name in self.ALLOWED_BUILTINS if hasattr(__builtins__ if isinstance(__builtins__, dict) else __builtins__, name)},
            'math': math,
            'statistics': statistics,
            'random': random,
            'datetime': datetime,
            'json': json_module,
            're': re_module,
            'collections': collections,
            'itertools': itertools,
            'functools': functools,
            'operator': operator,
            'decimal': decimal,
            'fractions': fractions,
        }
        
        # 添加基础 builtins
        if isinstance(__builtins__, dict):
            for name in self.ALLOWED_BUILTINS:
                if name in __builtins__:
                    safe_globals['__builtins__'][name] = __builtins__[name]
        
        safe_locals = {}
        
        # 捕获输出
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                # 编译代码
                compiled = compile(code, '<code_interpreter>', 'exec')
                # 执行
                exec(compiled, safe_globals, safe_locals)
            
            stdout_output = stdout_capture.getvalue()
            stderr_output = stderr_capture.getvalue()
            
            # 限制输出长度
            if len(stdout_output) > self._max_output_length:
                stdout_output = stdout_output[:self._max_output_length] + "\n... (输出已截断)"
            
            # 获取最后一个表达式的值 (如果有)
            result_value = safe_locals.get('result', safe_locals.get('_', None))
            
            output = {
                "stdout": stdout_output,
                "stderr": stderr_output,
                "result": repr(result_value) if result_value is not None else None,
                "variables": {k: repr(v)[:200] for k, v in safe_locals.items() 
                             if not k.startswith('_') and k not in self.ALLOWED_MODULES}
            }
            
            return SkillResult(
                success=True,
                output=output
            )
            
        except Exception as e:
            error_msg = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
            return SkillResult(
                success=False,
                output=None,
                error=f"代码执行错误:\n{error_msg}"
            )
    
    def get_schema(self) -> Dict[str, Any]:
        return create_tool_schema(
            name=self.name,
            description=self.description,
            parameters={
                "code": {
                    "type": "string",
                    "description": "要执行的 Python 代码"
                }
            },
            required=["code"]
        )
