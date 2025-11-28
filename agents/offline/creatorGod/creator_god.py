"""
CreatorGod：组合三个离线 LLM 子客体（角色过滤 / 世界设定 / 角色档案）
"""
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Union

from config.settings import settings
from utils.llm_factory import get_llm
from utils.logger import setup_logger
from .character_detail_agent import CharacterDetailAgent
from .character_filter_agent import CharacterFilterAgent
from .world_setting_agent import WorldSettingAgent


@dataclass
class StageLLMConfig:
    """每个阶段的 LLM 配置"""

    provider: Optional[str] = None
    model_name: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


class CreatorGod:
    """创世神：组合三个子 Agent 完成离线世界构建"""

    def __init__(
        self,
        stage_llm_configs: Optional[
            Dict[str, Union[StageLLMConfig, Dict[str, Any]]]
        ] = None,
        logger=None,
    ):
        self.logger = logger or setup_logger("CreatorGod", "genesis_group.log")
        self.stage_llm_configs = {
            key: self._normalize_config(cfg)
            for key, cfg in (stage_llm_configs or {}).items()
        }

        self.character_filter_agent = CharacterFilterAgent(
            llm=self._build_stage_llm("filter"),
            logger=self.logger,
        )
        self.world_setting_agent = WorldSettingAgent(
            llm=self._build_stage_llm("world"),
            logger=self.logger,
        )
        self.character_detail_agent = CharacterDetailAgent(
            llm=self._build_stage_llm("detail"),
            logger=self.logger,
        )

    def _normalize_config(
        self, cfg: Union[StageLLMConfig, Dict[str, Any]]
    ) -> StageLLMConfig:
        if isinstance(cfg, StageLLMConfig):
            return cfg
        return StageLLMConfig(
            provider=cfg.get("provider"),
            model_name=cfg.get("model_name"),
            temperature=cfg.get("temperature"),
            max_tokens=cfg.get("max_tokens"),
        )

    def _build_stage_llm(self, stage: str):
        """为每个阶段单独创建 LLM，可使用不同模型"""
        cfg = self.stage_llm_configs.get(stage)
        if not cfg:
            return get_llm()

        kwargs: Dict[str, Any] = {}
        if cfg.provider is not None:
            kwargs["provider"] = cfg.provider
        if cfg.model_name is not None:
            kwargs["model_name"] = cfg.model_name
        if cfg.temperature is not None:
            kwargs["temperature"] = cfg.temperature
        if cfg.max_tokens is not None:
            kwargs["max_tokens"] = cfg.max_tokens

        return get_llm(**kwargs)

    def _read_novel(self, novel_path: Path) -> str:
        """读取小说文本"""
        if not novel_path.exists():
            self.logger.error(f"❌ 小说文件不存在: {novel_path}")
            raise FileNotFoundError(f"小说文件不存在: {novel_path}")

        text = novel_path.read_text(encoding="utf-8")
        self.logger.info(f"✅ 成功读取小说: {novel_path.name} ({len(text)}字)")
        return text

    def run_pipeline(self, novel_text: str, world_dir: Optional[Path] = None):
        """
        执行三阶段流水线（每阶段完成后立即保存）
        
        Args:
            novel_text: 小说文本
            world_dir: 可选的世界目录，若提供则每阶段完成后立即保存
        """
        # 阶段1：角色过滤
        characters_list = self.character_filter_agent.run(novel_text)
        if world_dir:
            self._save_characters_list(world_dir, characters_list)
        
        # 阶段2：世界观提取
        world_setting = self.world_setting_agent.run(novel_text)
        if world_dir:
            self._save_world_setting(world_dir, world_setting)
        
        # 阶段3：角色档案（传入characters_list以保持ID一致）
        characters_details = self.character_detail_agent.run(
            novel_text, characters_list, world_dir
        )
        
        return world_setting, characters_list, characters_details

    def _save_characters_list(self, world_dir: Path, characters_list: Any) -> None:
        """保存角色列表（阶段1产物）"""
        world_dir.mkdir(parents=True, exist_ok=True)
        characters_list_file = world_dir / "characters_list.json"
        with characters_list_file.open("w", encoding="utf-8") as f:
            json.dump(characters_list, f, ensure_ascii=False, indent=2)
        self.logger.info(f"💾 阶段1完成 - 已保存角色列表: {characters_list_file}")

    def _save_world_setting(self, world_dir: Path, world_setting: Dict[str, Any]) -> None:
        """保存世界设定（阶段2产物）"""
        world_dir.mkdir(parents=True, exist_ok=True)
        world_setting_file = world_dir / "world_setting.json"
        with world_setting_file.open("w", encoding="utf-8") as f:
            json.dump(world_setting, f, ensure_ascii=False, indent=2)
        self.logger.info(f"💾 阶段2完成 - 已保存世界设定: {world_setting_file}")

    def save_world_data(
        self,
        world_name: str,
        world_setting: Dict[str, Any],
        characters_list: Any,
        characters_details: Dict[str, Dict[str, Any]],
    ) -> Path:
        """
        保存三份产物到 data/worlds/<world_name>/
        （兼容旧版调用，当未使用分阶段保存时可用此方法一次性保存）
        """
        self.logger.info("=" * 60)
        self.logger.info("💾 保存世界数据")
        self.logger.info("=" * 60)

        world_dir = settings.DATA_DIR / "worlds" / world_name
        world_dir.mkdir(parents=True, exist_ok=True)
        characters_dir = world_dir / "characters"
        characters_dir.mkdir(exist_ok=True)

        with (world_dir / "world_setting.json").open("w", encoding="utf-8") as f:
            json.dump(world_setting, f, ensure_ascii=False, indent=2)
        with (world_dir / "characters_list.json").open("w", encoding="utf-8") as f:
            json.dump(characters_list, f, ensure_ascii=False, indent=2)
        for char_id, char_data in characters_details.items():
            char_file = characters_dir / f"character_{char_id}.json"
            with char_file.open("w", encoding="utf-8") as f:
                json.dump(char_data, f, ensure_ascii=False, indent=2)

        self.logger.info(f"✅ 已保存 {len(characters_details)} 个角色档案")
        self.logger.info(f"📁 世界数据路径: {world_dir}")
        return world_dir

    def _auto_retry_failed_characters(
        self,
        world_dir: Path,
        world_name: str,
        novel_text: str,
        characters_list: Any,
        retry_delay: int = 10,
        max_retries: int = 3,
    ):
        """自动检测并重试失败角色"""
        self.logger.info("=" * 80)
        self.logger.info("🔍 检查角色创建状态...")
        self.logger.info("=" * 80)

        characters_dir = world_dir / "characters"
        failed = []

        for char_info in characters_list:
            char_id = char_info["id"]
            char_name = char_info["name"]
            importance = char_info["importance"]
            char_file = characters_dir / f"character_{char_id}.json"

            if not char_file.exists():
                self.logger.warning(f"⚠️  {char_name} (ID: {char_id}): 文件不存在")
                failed.append((char_id, char_name, importance))
                continue

            try:
                with char_file.open("r", encoding="utf-8") as f:
                    char_data = json.load(f)
                if "error" in char_data:
                    self.logger.warning(f"⚠️  {char_name} (ID: {char_id}): 创建失败")
                    failed.append((char_id, char_name, importance))
            except json.JSONDecodeError:
                self.logger.warning(f"⚠️  {char_name} (ID: {char_id}): JSON 解析失败")
                failed.append((char_id, char_name, importance))

        if not failed:
            self.logger.info("✅ 所有角色创建成功，无需重试")
            return

        self.logger.info(
            f"⚠️  发现 {len(failed)} 个角色创建失败，开始自动重试..."
        )

        success_count = 0
        still_failed = []
        for char_id, char_name, importance in failed:
            retry_count = 0
            success = False
            while retry_count < max_retries and not success:
                retry_count += 1
                self.logger.info(
                    f"🔄 [{retry_count}/{max_retries}] 重试: {char_name} (ID: {char_id})"
                )
                if retry_count > 1:
                    self.logger.info(
                        f"⏳ 等待 {retry_delay} 秒以避免限流..."
                    )
                    time.sleep(retry_delay)
                try:
                    char_info = {
                        "id": char_id,
                        "name": char_name,
                        "importance": importance,
                    }
                    # 传入characters_list以保持ID一致性
                    char_data = self.character_detail_agent.create_one(
                        novel_text, char_info, characters_list
                    )
                    char_file = characters_dir / f"character_{char_id}.json"
                    with char_file.open("w", encoding="utf-8") as f:
                        json.dump(char_data, f, ensure_ascii=False, indent=2)
                    success = True
                    success_count += 1
                    self.logger.info(f"✅ {char_name} 重试成功")
                except Exception as e:
                    self.logger.warning(
                        f"❌ {char_name} 第 {retry_count} 次重试失败: {e}"
                    )
                    if retry_count < max_retries:
                        time.sleep(retry_delay * 2)
            if not success:
                still_failed.append((char_id, char_name, importance))

        self.logger.info("=" * 80)
        self.logger.info("📊 自动重试完成")
        self.logger.info(f"   ✅ 成功修复: {success_count}")
        self.logger.info(f"   ❌ 仍然失败: {len(still_failed)}")
        if still_failed:
            for cid, cname, importance in still_failed:
                self.logger.warning(f"   - {cname} (ID: {cid}, 重要性 {importance})")
        self.logger.info("=" * 80)

    def run(self, novel_filename: str = "example_novel.txt", world_name: Optional[str] = None) -> Path:
        """
        完整流程：读取小说 -> 三阶段（每阶段完成后保存） -> 自动重试
        
        Args:
            novel_filename: 小说文件名
            world_name: 可选的世界名称，若不提供则从阶段2的世界设定中提取
        """
        self.logger.info("=" * 80)
        self.logger.info("🚀 启动 CreatorGod - 三阶段世界构建")
        self.logger.info("=" * 80)

        novel_path = settings.NOVELS_DIR / novel_filename
        novel_text = self._read_novel(novel_path)

        # 如果提前指定了世界名称，可以在阶段1完成后就开始保存
        # 否则需要等阶段2完成获取世界名称后再保存
        if world_name:
            world_dir = settings.DATA_DIR / "worlds" / world_name
            world_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"📁 使用指定世界名称: {world_name}")
        else:
            world_dir = None
        
        # 阶段1：角色过滤
        characters_list = self.character_filter_agent.run(novel_text)
        
        # 阶段2：世界观提取
        world_setting = self.world_setting_agent.run(novel_text)
        
        # 如果没有预先指定世界名称，从世界设定中获取
        if not world_name:
            world_name = world_setting.get("meta", {}).get("world_name", "未知世界")
            world_dir = settings.DATA_DIR / "worlds" / world_name
            world_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"📁 从世界设定中获取世界名称: {world_name}")
        
        # 阶段1和阶段2数据现在可以保存了
        self._save_characters_list(world_dir, characters_list)
        self._save_world_setting(world_dir, world_setting)
        
        # 阶段3：角色档案（每个角色创建后即时保存）
        characters_dir = world_dir / "characters"
        characters_dir.mkdir(exist_ok=True)
        characters_details = self.character_detail_agent.run(
            novel_text, characters_list, world_dir
        )

        self._auto_retry_failed_characters(
            world_dir=world_dir,
            world_name=world_name,
            novel_text=novel_text,
            characters_list=characters_list,
        )
        return world_dir
