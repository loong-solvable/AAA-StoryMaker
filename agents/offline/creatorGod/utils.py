"""
CreatorGod 公共工具：提示词加载与 JSON 解析
"""
import json
import re
from pathlib import Path
from typing import Any

from config.settings import settings
from utils.logger import setup_logger

logger = setup_logger("CreatorGod", "architect.log")


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
    """
    cleaned = response.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    # 去除 // 与 /* */ 注释
    cleaned = re.sub(r"//.*?(?=\n|$)", "", cleaned)
    cleaned = re.sub(r"/\*.*?\*/", "", cleaned, flags=re.DOTALL)
    cleaned = "\n".join(line for line in cleaned.split("\n") if line.strip())

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON 解析失败: {e}")
        logger.error(f"原始响应前500字: {response[:500]}...")
        logger.error(f"清理后前500字: {cleaned[:500]}...")
        raise ValueError("LLM 返回的 JSON 格式不正确") from e


def escape_braces(text: str) -> str:
    """将 { 和 } 转义为 {{ 和 }}，用于关闭 PromptTemplate 的变量识别"""
    return text.replace("{", "{{").replace("}", "}}")
