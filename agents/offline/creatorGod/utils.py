"""
CreatorGod 公共工具：提示词加载与 JSON 解析
"""
import json
import re
from pathlib import Path
from typing import Any

from config.settings import settings
from utils.logger import setup_logger

logger = setup_logger("CreatorGod", "genesis_group.log")


def load_prompt(filename: str) -> str:
    """
    加载 CreatorGod 阶段提示词
    优先从 prompts/offline/creatorGod/ 读取
    """
    prompt_file = settings.PROMPTS_DIR / "offline" / "creatorGod" / filename
    if not prompt_file.exists():
        logger.error(f"❌ 未找到提示词文件: {prompt_file}")
        raise FileNotFoundError(f"提示词文件不存在: {prompt_file}")

    return prompt_file.read_text(encoding="utf-8")


def parse_json_response(response: str) -> Any:
    """
    解析 LLM 返回的 JSON，去除 markdown 包裹与注释
    增强版：能够处理JSON后面有多余内容的情况（Extra data错误）
    """
    cleaned = response.strip()
    
    # 1. 去除 markdown 代码块包裹
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
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
        # 4. 如果失败，尝试提取第一个完整的JSON对象
        logger.warning(f"⚠️  直接解析失败，尝试提取JSON对象: {e}")
        
        # 方法1: 找到第一个 { 和匹配的最后一个 }
        first_brace = cleaned.find('{')
        if first_brace != -1:
            brace_count = 0
            last_brace = -1
            in_string = False
            escape_next = False
            
            for i in range(first_brace, len(cleaned)):
                char = cleaned[i]
                
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
                json_str = cleaned[first_brace:last_brace + 1]
                try:
                    result = json.loads(json_str)
                    logger.info("✅ 成功提取JSON对象（方法1：大括号匹配）")
                    return result
                except json.JSONDecodeError as e2:
                    logger.warning(f"⚠️  方法1失败: {e2}")
        
        # 方法2: 逐行解析，找到完整的JSON对象
        lines = cleaned.split('\n')
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
                
                # 当大括号匹配时，JSON对象完整
                if brace_count == 0:
                    json_str = '\n'.join(json_lines)
                    try:
                        result = json.loads(json_str)
                        logger.info("✅ 成功提取JSON对象（方法2：逐行解析）")
                        return result
                    except json.JSONDecodeError as e2:
                        logger.warning(f"⚠️  方法2失败: {e2}")
        
        # 方法3: 使用正则表达式提取JSON对象（最后手段，简单情况）
        # 注意：这个方法可能无法正确处理嵌套的复杂JSON
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        json_matches = re.finditer(json_pattern, cleaned, re.DOTALL)
        for match in json_matches:
            json_str = match.group(0)
            try:
                result = json.loads(json_str)
                logger.info("✅ 成功提取JSON对象（方法3：正则表达式）")
                return result
            except json.JSONDecodeError:
                continue
        
        # 所有方法都失败，记录详细错误信息
        logger.error(f"❌ JSON 解析失败: {e}")
        logger.error(f"原始响应前500字: {response[:500]}...")
        logger.error(f"清理后前500字: {cleaned[:500]}...")
        
        # 尝试找到可能的JSON起始位置
        json_start = cleaned.find('{')
        if json_start != -1:
            logger.error(f"检测到JSON起始位置: {json_start}")
            logger.error(f"JSON起始位置后的内容: {cleaned[json_start:json_start+300]}...")
        
        raise ValueError("LLM 返回的 JSON 格式不正确") from e


def escape_braces(text: str) -> str:
    """将 { 和 } 转义为 {{ 和 }}，用于关闭 PromptTemplate 的变量识别"""
    return text.replace("{", "{{").replace("}", "}}")
