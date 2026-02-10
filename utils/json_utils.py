
import json
import re
from typing import Any, Dict, Union

def repair_json(json_str: str) -> Union[Dict, list, str, None]:
    """
    尝试修复并解析损坏的 JSON 字符串
    主要处理 LLM 生成时常见的格式错误：
    1. 未转义的换行符
    2. 缺少结束括号
    3. 尾部逗号
    4. Markdown 代码块包裹
    """
    if not isinstance(json_str, str):
        return json_str
        
    s = json_str.strip()
    
    # 1. 移除 Markdown 代码块标记
    if s.startswith("```"):
        # 移除第一行 (```json) 和最后一行 (```)
        lines = s.split('\n')
        if len(lines) >= 2:
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            s = '\n'.join(lines).strip()
    
    # 尝试直接解析
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
        
    # 2. 尝试修复常见错误
    try:
        # 替换未转义的换行符 (在字符串值中)
        # 这是一个简单的启发式，可能不完美
        # 更好的方法是使用 regex 匹配字符串内容
        
        # 尝试使用 strict=False (Python standard lib doesn't support strict=False for control characters fully)
        return json.loads(s, strict=False)
    except:
        pass

    # 3. 尝试手动修复控制字符 (针对 Code Interpreter)
    try:
        # 针对 code_interpreter 的 "code" 字段包含未转义换行符的情况
        # 匹配 pattern: "code": "..."
        # 注意: 这是一个简化的处理，假设 code 字段是主要问题
        
        # 策略 3.1: 针对特定的 "code"/"content" 模式尝试提取内容 (Aggressive Repair)
        # 很多时候 LLM 输出的代码/HTML 包含未转义的换行、引号，甚至被截断
        target_keys = ["code", "content"]
        for key in target_keys:
            if f'"{key}":' in s:
                # 尝试找到 value 的开始
                # 匹配 "key":\s*"
                pattern_start = re.compile(f'"{key}":\s*"', re.DOTALL)
                match_start = pattern_start.search(s)
                
                if match_start:
                    start_idx = match_start.end()
                    
                    # 尝试找到值的结束
                    # 假设 value 后面跟着 ",\n"next": 或 "}\n 结尾
                    # 我们寻找 倒数第一个 " (quote) + 结构结束符
                    # 如果被截断，可能找不到结束符
                    
                    # 简化逻辑：假设这个大字段是最后一个字段 (common case)
                    # 取出 start_idx 之后的所有内容
                    raw_content = s[start_idx:]
                    
                    # 检查是否有显式的结束标记 (", "... 或 "})
                    # 我们寻找最后一个出现在 } 或 , 之前的 "
                    # 这比较难判断，因为 content 内部可能有 "...}..."
                    
                    # Heuristic: 
                    # 1. 看是否以 "}\s*$ 结尾 (正常结束)
                    # 2. 看是否以 ..."\s*$ 结尾 (截断?)
                    
                    # 如果我们假设它是被截断的或者包含非法字符
                    # 我们直接把剩余部分当做 content，并进行清洗
                    
                    # 去掉末尾可能的 JSON 结构字符 ('}', '"')
                    # 从右往左找，如果是 } 或 空白，去掉
                    clean_content = raw_content.rstrip()
                    if clean_content.endswith('}'):
                        clean_content = clean_content[:-1].rstrip()
                    if clean_content.endswith('"'):
                         clean_content = clean_content[:-1]
                    
                    # 现在的 clean_content 应该是 "脏" 的原始内容
                    # 我们对其进行转义
                    escaped_content = clean_content.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
                    
                    # 重组 JSON
                    # 前缀 + 转义后的内容 + 后缀
                    # 假设它是最后一个字段
                    prefix = s[:start_idx]
                    fixed_json = f'{prefix}{escaped_content}"}}'
                    
                    try:
                        return json.loads(fixed_json)
                    except:
                        pass
        
        # 策略 3.3: 暴力转义所有非结构化的换行符
        # 使用正则表达式匹配所有字符串字面量，并转义其中的控制字符
        
        def replace_string_literal(match):
            s_content = match.group(1)
            # 只有当字符串内包含未转义的换行符时才处理
            if '\n' in s_content or '\r' in s_content or '\t' in s_content:
                s_content = s_content.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
            return f'"{s_content}"'
            
        # 匹配 JSON 字符串字面量 "..."
        # 核心难点是：如何区分 "是字符串结束" 还是 "字符串内部的未转义引号"
        # 标准 JSON 不允许未转义引号，但 LLM 可能会输出
        # 这里假设引号是正确转义的 (\\")，但换行符没有转义
        pattern = r'"((?:[^"\\]|\\.)*)"'
        
        # 使用 re.DOTALL 让 . 匹配换行符
        s_escaped = re.sub(pattern, replace_string_literal, s, flags=re.DOTALL)
        
        return json.loads(s_escaped)
        
    except:
        pass
        
    # 4. 尝试补全括号 (针对截断)
    try:
        open_braces = s.count('{')
        close_braces = s.count('}')
        if open_braces > close_braces:
            s += '}' * (open_braces - close_braces)
            return json.loads(s)
    except:
        pass
        
    # 5. 如果是简单的 Python 字典字符串 (单引号)，尝试 ast.literal_eval
    try:
        import ast
        return ast.literal_eval(s)
    except:
        pass
        
    return None
