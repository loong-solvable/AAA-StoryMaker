"""
角色过滤子客体：负责角色普查
"""
from typing import Any, Dict, List, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from utils.llm_factory import get_llm
from utils.logger import setup_logger
from .utils import load_prompt, parse_json_response, escape_braces


class CharacterFilterAgent:
    """角色过滤 Agent：扫描小说并输出角色列表"""

    def __init__(
        self,
        llm=None,
        prompt_filename: str = "character_filter.txt",
        logger=None,
    ):
        self.logger = logger or setup_logger("大中正", "genesis_group.log")
        self.llm = llm or get_llm()
        self.prompt_text = escape_braces(load_prompt(prompt_filename))

    def run(self, novel_text: str) -> List[Dict[str, Any]]:
        """执行角色普查"""
        self.logger.info("=" * 60)
        self.logger.info("📍 阶段1：角色过滤（角色普查）")
        self.logger.info("=" * 60)

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self.prompt_text),
                ("human", "{novel_text}"),
            ]
        )
        chain = prompt | self.llm | StrOutputParser()

        self.logger.info("🤖 正在调用角色过滤 LLM...")
        response = chain.invoke({"novel_text": novel_text}, config={"timeout": 600})
        characters_list = parse_json_response(response)

        self.logger.info(f"✅ 角色普查完成，发现 {len(characters_list)} 个角色")
        return characters_list
