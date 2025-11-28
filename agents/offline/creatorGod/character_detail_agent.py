"""
角色档案子客体：为单个角色生成详细档案
"""
from typing import Any, Dict, List, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from utils.llm_factory import get_llm
from utils.logger import setup_logger
from .utils import load_prompt, parse_json_response, escape_braces


class CharacterDetailAgent:
    """角色档案 Agent"""

    def __init__(
        self,
        llm=None,
        prompt_filename: str = "character_detail.txt",
        logger=None,
    ):
        self.logger = logger or setup_logger("许劭", "genesis_group.log")
        self.llm = llm or get_llm()
        self.prompt_template = load_prompt(prompt_filename)

    def _build_prompt(self, char_name: str, char_id: str) -> str:
        prompt = self.prompt_template.replace("{target_name}", char_name)
        prompt = prompt.replace("{target_id}", char_id)
        return escape_braces(prompt)

    def create_one(self, novel_text: str, char_info: Dict[str, Any]) -> Dict[str, Any]:
        """为单个角色生成档案"""
        char_id = char_info.get("id")
        char_name = char_info.get("name")
        importance = char_info.get("importance")

        prompt_text = self._build_prompt(char_name, char_id)
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", prompt_text),
                ("human", "{novel_text}"),
            ]
        )
        chain = prompt | self.llm | StrOutputParser()

        response = chain.invoke({"novel_text": novel_text}, config={"timeout": 600})
        char_data = parse_json_response(response)
        char_data["importance"] = importance
        return char_data

    def run(
        self,
        novel_text: str,
        characters_list: List[Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        """批量为角色生成档案"""
        self.logger.info("=" * 60)
        self.logger.info("📍 阶段3：创建角色详细档案")
        self.logger.info("=" * 60)

        characters_details: Dict[str, Dict[str, Any]] = {}
        total = len(characters_list)

        for idx, char_info in enumerate(characters_list, 1):
            char_id = char_info.get("id")
            char_name = char_info.get("name")
            importance = char_info.get("importance")
            self.logger.info(
                f"[{idx}/{total}] 处理角色: {char_name} (重要性 {importance})"
            )
            try:
                characters_details[char_id] = self.create_one(novel_text, char_info)
                self.logger.info(f"   ✅ {char_name} 档案创建完成")
            except Exception as e:
                self.logger.warning(f"   ⚠️  {char_name} 档案创建失败: {e}")
                characters_details[char_id] = {
                    "id": char_id,
                    "name": char_name,
                    "importance": importance,
                    "error": str(e),
                }

        self.logger.info(f"✅ 角色档案生成完成: {len(characters_details)}/{total}")
        return characters_details
