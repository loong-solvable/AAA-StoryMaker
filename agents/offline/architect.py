"""
架构师 (The Architect)
拆分为三个子客体（角色过滤 / 世界观 / 角色档案），组合为 CreatorGod
"""
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from config.settings import settings
from utils.logger import setup_logger
from .creatorGod import CreatorGod, StageLLMConfig

logger = setup_logger("Architect", "architect.log")


class ArchitectAgent:
    """兼容旧接口的架构师，内部委托给 CreatorGod"""

    def __init__(
        self,
        stage_llm_configs: Optional[
            Dict[str, Union[StageLLMConfig, Dict[str, Any]]]
        ] = None,
    ):
        logger.info("🏗️  初始化架构师Agent（CreatorGod 组合）...")
        self.creator_god = CreatorGod(
            stage_llm_configs=stage_llm_configs,
            logger=logger,
        )
        # 兼容旧属性引用
        self.char_filter_prompt = (
            self.creator_god.character_filter_agent.prompt_text
        )
        self.world_prompt = self.creator_god.world_setting_agent.prompt_text
        self.char_detail_prompt = (
            self.creator_god.character_detail_agent.prompt_template
        )
        logger.info("✅ 架构师Agent初始化完成")

    def stage1_filter_characters(self, novel_text: str) -> List[Dict[str, Any]]:
        return self.creator_god.character_filter_agent.run(novel_text)

    def stage2_extract_world_setting(self, novel_text: str) -> Dict[str, Any]:
        return self.creator_god.world_setting_agent.run(novel_text)

    def stage3_create_character_details(
        self, novel_text: str, characters_list: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        return self.creator_god.character_detail_agent.run(
            novel_text, characters_list
        )

    def save_world_data(
        self,
        world_name: str,
        world_setting: Dict[str, Any],
        characters_list: List[Dict[str, Any]],
        characters_details: Dict[str, Dict[str, Any]],
    ) -> Path:
        return self.creator_god.save_world_data(
            world_name=world_name,
            world_setting=world_setting,
            characters_list=characters_list,
            characters_details=characters_details,
        )

    def _auto_retry_failed_characters(
        self,
        world_dir: Path,
        world_name: str,
        novel_text: str,
        characters_list: List[Dict[str, Any]],
    ):
        """兼容旧接口，转交给 CreatorGod"""
        return self.creator_god._auto_retry_failed_characters(
            world_dir=world_dir,
            world_name=world_name,
            novel_text=novel_text,
            characters_list=characters_list,
        )

    def run(self, novel_filename: str = "example_novel.txt") -> Path:
        return self.creator_god.run(novel_filename=novel_filename)


def create_world(novel_filename: str = "example_novel.txt") -> Path:
    """创建世界数据的便捷函数"""
    architect = ArchitectAgent()
    return architect.run(novel_filename)
