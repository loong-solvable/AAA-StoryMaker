"""
世界观设定子客体：负责抽取世界规则与地理
"""
from typing import Any, Dict, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from utils.llm_factory import get_llm
from utils.logger import setup_logger
from .utils import load_prompt, parse_json_response, escape_braces


class WorldSettingAgent:
    """世界观设定 Agent"""

    def __init__(
        self,
        llm=None,
        prompt_filename: str = "world_setting.txt",
        logger=None,
    ):
        self.logger = logger or setup_logger("Demiurge", "genesis_group.log")
        self.llm = llm or get_llm()
        self.prompt_text = escape_braces(load_prompt(prompt_filename))

    def run(self, novel_text: str) -> Dict[str, Any]:
        """抽取世界设定"""
        self.logger.info("=" * 60)
        self.logger.info("📍 阶段2：提取世界观设定")
        self.logger.info("=" * 60)

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self.prompt_text),
                ("human", "{novel_text}"),
            ]
        )
        chain = prompt | self.llm | StrOutputParser()

        self.logger.info("🤖 正在调用世界观 LLM...")
        response = chain.invoke({"novel_text": novel_text}, config={"timeout": 600})
        world_setting = parse_json_response(response)

        return world_setting
