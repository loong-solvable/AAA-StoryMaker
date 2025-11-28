"""
创世组 (Genesis Group)
由三位专职Agent组成：大中正（角色普查）、Demiurge（世界设定）、许劭（角色档案）
组合为 CreatorGod 协同完成世界数据的提取与构建
"""
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from config.settings import settings
from utils.logger import setup_logger
from .creatorGod import CreatorGod, StageLLMConfig

logger = setup_logger("GenesisGroup", "genesis_group.log")


class GenesisGroup:
    """
    创世组 - 离线世界构建的核心组件
    
    成员：
    - 大中正 (The Censor): 角色普查与重要性评估
    - Demiurge (造物主): 世界规则与背景提取
    - 许劭 (角色雕刻师): 角色档案与角色卡制作
    """

    def __init__(
        self,
        stage_llm_configs: Optional[
            Dict[str, Union[StageLLMConfig, Dict[str, Any]]]
        ] = None,
    ):
        logger.info("🏗️  初始化创世组...")
        self.creator_god = CreatorGod(
            stage_llm_configs=stage_llm_configs,
            logger=logger,
        )
        # 成员引用
        self.censor = self.creator_god.character_filter_agent  # 大中正
        self.demiurge = self.creator_god.world_setting_agent   # Demiurge
        self.xu_shao = self.creator_god.character_detail_agent  # 许劭
        logger.info("✅ 创世组初始化完成（大中正 + Demiurge + 许劭）")

    def stage1_character_census(self, novel_text: str) -> List[Dict[str, Any]]:
        """阶段1：大中正 - 角色普查"""
        logger.info("📍 阶段1：大中正执行角色普查...")
        return self.censor.run(novel_text)

    def stage2_world_setting(self, novel_text: str) -> Dict[str, Any]:
        """阶段2：Demiurge - 世界设定提取"""
        logger.info("📍 阶段2：Demiurge提取世界设定...")
        return self.demiurge.run(novel_text)

    def stage3_character_profiles(
        self, novel_text: str, characters_list: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """阶段3：许劭 - 角色档案制作"""
        logger.info("📍 阶段3：许劭制作角色档案...")
        return self.xu_shao.run(novel_text, characters_list)

    def save_world_data(
        self,
        world_name: str,
        world_setting: Dict[str, Any],
        characters_list: List[Dict[str, Any]],
        characters_details: Dict[str, Dict[str, Any]],
    ) -> Path:
        """保存世界数据"""
        return self.creator_god.save_world_data(
            world_name=world_name,
            world_setting=world_setting,
            characters_list=characters_list,
            characters_details=characters_details,
        )

    def run(self, novel_filename: str = "example_novel.txt") -> Path:
        """运行完整的三阶段世界构建流程"""
        return self.creator_god.run(novel_filename=novel_filename)


# 兼容旧接口
ArchitectAgent = GenesisGroup


def create_world(novel_filename: str = "example_novel.txt") -> Path:
    """创建世界数据的便捷函数"""
    genesis = GenesisGroup()
    return genesis.run(novel_filename)

