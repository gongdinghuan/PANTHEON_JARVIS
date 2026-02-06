"""
JARVIS 计算器技能
提供基本的数学计算功能

Author: gngdingghuan
"""

import ast
import math
import operator
from typing import Dict, Any, Union

from skills.base_skill import BaseSkill, SkillResult, PermissionLevel, create_tool_schema
from utils.logger import log

class CalculatorSkill(BaseSkill):
    """计算器技能"""
    
    name = "calculator"
    description = "执行数学计算，支持加减乘除、幂运算等"
    permission_level = PermissionLevel.READ_ONLY
    
    def __init__(self):
        super().__init__()
        # 支持的操作符
        self.operators = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
            ast.Mod: operator.mod,
            ast.USub: operator.neg,
            ast.UAdd: operator.pos,
        }
        
        # 支持的函数
        self.functions = {
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "sqrt": math.sqrt,
            "log": math.log,
            "abs": abs,
            "round": round,
            "ceil": math.ceil,
            "floor": math.floor,
            "pi": math.pi,
            "e": math.e,
        }
    
    async def execute(self, action: str, **params) -> SkillResult:
        """执行计算"""
        if action == "calculate":
            expression = params.get("expression")
            if not expression:
                return SkillResult(success=False, output=None, error="缺少表达式参数")
            
            return self._calculate(expression)
        else:
            return SkillResult(success=False, output=None, error=f"未知的操作: {action}")
    
    def _calculate(self, expression: str) -> SkillResult:
        """
        安全计算表达式
        使用 ast.literal_eval 的变体进行安全评估
        """
        try:
            # 移除所有空白字符
            expr = expression.replace(" ", "")
            
            # 限制长度
            if len(expr) > 100:
                return SkillResult(success=False, output=None, error="表达式过长")
            
            # 解析表达式
            node = ast.parse(expr, mode='eval')
            
            result = self._eval(node.body)
            return SkillResult(success=True, output=f"{result}")
            
        except Exception as e:
            log.warning(f"由于错误无法计算表达式 '{expression}': {e}")
            return SkillResult(success=False, output=None, error=f"计算错误: {str(e)}")
    
    def _eval(self, node):
        """递归评估 AST 节点"""
        if isinstance(node, ast.Num):  # <number>
            return node.n
        elif isinstance(node, ast.BinOp):  # <left> <operator> <right>
            return self.operators[type(node.op)](self._eval(node.left), self._eval(node.right))
        elif isinstance(node, ast.UnaryOp):  # <operator> <operand> e.g., -1
            return self.operators[type(node.op)](self._eval(node.operand))
        elif isinstance(node, ast.Call):  # func(arg)
            if isinstance(node.func, ast.Name) and node.func.id in self.functions:
                func = self.functions[node.func.id]
                args = [self._eval(arg) for arg in node.args]
                return func(*args)
            else:
                raise TypeError(f"不支持的函数: {node.func.id}")
        elif isinstance(node, ast.Name): # variable e.g. pi
             if node.id in self.functions:
                 return self.functions[node.id]
             raise TypeError(f"不支持的变量: {node.id}")
        else:
            raise TypeError(f"不支持的表达式类型: {type(node)}")
            
    def get_schema(self) -> Dict[str, Any]:
        """获取工具定义"""
        return create_tool_schema(
            name=self.name,
            description=self.description,
            parameters={
                "action": {
                    "type": "string",
                    "enum": ["calculate"],
                    "description": "要执行的操作"
                },
                "expression": {
                    "type": "string",
                    "description": "数学表达式，例如: '1 + 1', 'sqrt(16)', '2 * pi'"
                }
            },
            required=["action", "expression"]
        )
