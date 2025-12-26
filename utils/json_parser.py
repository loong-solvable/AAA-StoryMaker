"""
健壮的 JSON 解析器
用于处理 LLM 返回的不规范 JSON 响应

特性：
- 去除 markdown 代码块包裹
- 去除 // 和 /* */ 注释
- 大括号匹配提取 JSON 对象
- 逐行解析作为备选
- 正则表达式作为最后手段
"""
import json
import re
from typing import Any, Optional

from utils.logger import setup_logger

logger = setup_logger("JSONParser", "json_parser.log")


def parse_json_response(response: str, raise_on_error: bool = False) -> Optional[Any]:
    """
    解析 LLM 返回的 JSON，去除 markdown 包裹与注释
    
    增强版：能够处理 JSON 后面有多余内容的情况
    
    Args:
        response: LLM 原始响应字符串
        raise_on_error: 如果为 True，解析失败时抛出异常；否则返回 None
        
    Returns:
        解析后的 Python 对象，或 None（如果解析失败且 raise_on_error=False）
    """
    if not response or not response.strip():
        if raise_on_error:
            raise ValueError("空响应")
        return None
        
    cleaned = response.strip()
    
    # 1. 去除 markdown 代码块包裹
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```JSON"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()
    
    # 2. 去除 // 与 /* */ 注释
    cleaned = re.sub(r"//.*?(?=\n|$)", "", cleaned)
    cleaned = re.sub(r"/\*.*?\*/", "", cleaned, flags=re.DOTALL)
    
    # 3. 尝试直接解析
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.debug(f"直接解析失败: {e}")
    
    # 4. 方法1: 大括号匹配提取第一个完整的 JSON 对象
    first_brace = cleaned.find('{')
    if first_brace != -1:
        result = _extract_json_by_brace_matching(cleaned, first_brace)
        if result is not None:
            logger.debug("通过大括号匹配成功提取 JSON")
            return result
    
    # 5. 方法2: 逐行解析
    result = _extract_json_line_by_line(cleaned)
    if result is not None:
        logger.debug("通过逐行解析成功提取 JSON")
        return result
    
    # 6. 方法3: 正则表达式（最后手段，简单情况）
    result = _extract_json_by_regex(cleaned)
    if result is not None:
        logger.debug("通过正则表达式成功提取 JSON")
        return result
    
    # 所有方法都失败
    logger.warning(f"JSON 解析失败，原始响应前200字: {response[:200]}...")
    
    if raise_on_error:
        raise ValueError("无法解析 JSON 响应")
    return None


def _extract_json_by_brace_matching(text: str, start_pos: int) -> Optional[Any]:
    """
    通过大括号匹配提取 JSON 对象
    
    Args:
        text: 文本内容
        start_pos: 第一个 '{' 的位置
        
    Returns:
        解析后的对象，或 None
    """
    brace_count = 0
    in_string = False
    escape_next = False
    last_brace = -1
    
    for i in range(start_pos, len(text)):
        char = text[i]
        
        # 处理转义字符
        if escape_next:
            escape_next = False
            continue
        
        if char == '\\':
            escape_next = True
            continue
        
        # 处理字符串内的引号
        if char == '"' and not escape_next:
            in_string = not in_string
            continue
        
        # 只在非字符串状态下计算大括号
        if not in_string:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    last_brace = i
                    break
    
    if last_brace != -1:
        json_str = text[start_pos:last_brace + 1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    
    return None


def _extract_json_line_by_line(text: str) -> Optional[Any]:
    """
    逐行解析提取 JSON 对象
    
    Args:
        text: 文本内容
        
    Returns:
        解析后的对象，或 None
    """
    lines = text.split('\n')
    json_lines = []
    in_json = False
    brace_count = 0
    in_string = False
    escape_next = False
    
    for line in lines:
        # 找到第一个包含 { 的行
        if '{' in line and not in_json:
            in_json = True
        
        if in_json:
            json_lines.append(line)
            
            # 计算大括号（考虑字符串内的引号）
            for char in line:
                if escape_next:
                    escape_next = False
                    continue
                if char == '\\':
                    escape_next = True
                    continue
                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue
                if not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
            
            # 当大括号匹配时，JSON 对象完整
            if brace_count == 0 and json_lines:
                json_str = '\n'.join(json_lines)
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    # 重置继续尝试
                    json_lines = []
                    in_json = False
                    brace_count = 0
    
    return None


def _extract_json_by_regex(text: str) -> Optional[Any]:
    """
    使用正则表达式提取 JSON 对象（最后手段，简单情况）
    
    注意：这个方法可能无法正确处理嵌套的复杂 JSON
    
    Args:
        text: 文本内容
        
    Returns:
        解析后的对象，或 None
    """
    # 尝试匹配简单的 JSON 对象
    json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    json_matches = re.finditer(json_pattern, text, re.DOTALL)
    
    for match in json_matches:
        json_str = match.group(0)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            continue
    
    return None


def safe_parse_npc_response(response: str, default_values: dict = None) -> dict:
    """
    安全解析 NPC 响应，失败时返回带有默认值的字典
    
    Args:
        response: LLM 原始响应
        default_values: 解析失败时使用的默认值字典
        
    Returns:
        解析后的字典，或带有默认值的字典
    """
    result = parse_json_response(response)
    
    if result is not None and isinstance(result, dict):
        # 确保必要的字段存在
        result.setdefault("thought", "")
        result.setdefault("emotion", "")
        result.setdefault("action", "")
        result.setdefault("content", result.get("dialogue", ""))
        result.setdefault("dialogue", result.get("content", ""))
        result.setdefault("addressing_target", "everyone")
        result.setdefault("is_scene_finished", False)
        return result
    
    # 解析失败，使用默认值
    defaults = {
        "thought": "（解析失败）",
        "emotion": "",
        "action": "",
        "content": response[:200] if response else "...",
        "dialogue": response[:200] if response else "...",
        "addressing_target": "everyone",
        "is_scene_finished": False
    }
    
    if default_values:
        defaults.update(default_values)
    
    return defaults
