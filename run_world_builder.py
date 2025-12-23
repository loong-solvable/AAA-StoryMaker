#!/usr/bin/env python3
"""
世界构建主脚本 - 支持断点续传和阶段3并行化

功能：
1. 交互式选择：新建世界 / 继续已有世界
2. 断点续传：自动检测已完成阶段，跳过重复工作
3. 阶段3并行化：多角色同时生成，大幅缩短总耗时
4. 进度可视化：清晰显示每个阶段的状态

使用方式：
    python run_world_builder.py                    # 交互式菜单
    python run_world_builder.py --novel xxx.txt    # 指定小说文件
    python run_world_builder.py --resume 江城市    # 继续构建指定世界
    python run_world_builder.py --list             # 列出所有世界
"""
import argparse
import asyncio
import json
import os
import sys
import time
import weakref
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# 添加项目根目录
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import settings
from utils.logger import setup_logger
from utils.llm_factory import get_llm

logger = setup_logger("WorldBuilder", "world_builder.log")

# ============================================================================
# 并发控制
# ============================================================================
_LLM_CONCURRENCY = int(os.getenv("LLM_CONCURRENCY", "5"))
_LLM_SEMAPHORES: "weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Semaphore]" = (
    weakref.WeakKeyDictionary()
)


def _get_semaphore() -> asyncio.Semaphore:
    """获取与当前事件循环绑定的 Semaphore"""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop:
        sem = _LLM_SEMAPHORES.get(loop)
        if sem is None:
            sem = asyncio.Semaphore(_LLM_CONCURRENCY)
            _LLM_SEMAPHORES[loop] = sem
        return sem
    return asyncio.Semaphore(_LLM_CONCURRENCY)


# ============================================================================
# 检查点数据结构
# ============================================================================
@dataclass
class Checkpoint:
    """世界构建进度检查点"""
    stage1_done: bool = False
    stage2_done: bool = False
    stage3_done: bool = False
    stage3_completed_characters: List[str] = field(default_factory=list)
    stage3_failed_characters: List[str] = field(default_factory=list)
    last_updated: str = ""
    novel_filename: str = ""
    world_name: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage1_done": self.stage1_done,
            "stage2_done": self.stage2_done,
            "stage3_done": self.stage3_done,
            "stage3_completed_characters": self.stage3_completed_characters,
            "stage3_failed_characters": self.stage3_failed_characters,
            "last_updated": self.last_updated,
            "novel_filename": self.novel_filename,
            "world_name": self.world_name,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Checkpoint":
        return cls(
            stage1_done=data.get("stage1_done", False),
            stage2_done=data.get("stage2_done", False),
            stage3_done=data.get("stage3_done", False),
            stage3_completed_characters=data.get("stage3_completed_characters", []),
            stage3_failed_characters=data.get("stage3_failed_characters", []),
            last_updated=data.get("last_updated", ""),
            novel_filename=data.get("novel_filename", ""),
            world_name=data.get("world_name", ""),
        )


# ============================================================================
# 世界构建器
# ============================================================================
class WorldBuilder:
    """支持断点续传的世界构建器"""

    def __init__(
        self,
        novel_filename: str,
        world_name: Optional[str] = None,
        parallel: bool = True,
    ):
        self.novel_filename = novel_filename
        self.world_name = world_name
        self.parallel = parallel
        self.world_dir: Optional[Path] = None
        self.checkpoint: Optional[Checkpoint] = None

        # 延迟导入 Agent
        from agents.offline.creatorGod.character_filter_agent import CharacterFilterAgent
        from agents.offline.creatorGod.world_setting_agent import WorldSettingAgent
        from agents.offline.creatorGod.character_detail_agent import CharacterDetailAgent

        self.character_filter_agent = CharacterFilterAgent(logger=logger)
        self.world_setting_agent = WorldSettingAgent(logger=logger)
        self.character_detail_agent = CharacterDetailAgent(logger=logger)

    def _get_checkpoint_path(self) -> Path:
        """获取检查点文件路径"""
        return self.world_dir / ".checkpoint.json"

    def _load_checkpoint(self) -> Checkpoint:
        """加载检查点"""
        checkpoint_file = self._get_checkpoint_path()
        if checkpoint_file.exists():
            try:
                data = json.loads(checkpoint_file.read_text(encoding="utf-8"))
                return Checkpoint.from_dict(data)
            except Exception as e:
                logger.warning(f"⚠️ 检查点文件损坏，将重新开始: {e}")
        return Checkpoint(novel_filename=self.novel_filename)

    def _save_checkpoint(self):
        """保存检查点"""
        self.checkpoint.last_updated = datetime.now().isoformat()
        self.checkpoint.world_name = self.world_name or ""
        checkpoint_file = self._get_checkpoint_path()
        checkpoint_file.write_text(
            json.dumps(self.checkpoint.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        logger.info(f"💾 检查点已保存: {checkpoint_file}")

    def _read_novel(self) -> str:
        """读取小说文本"""
        novel_path = settings.NOVELS_DIR / self.novel_filename
        if not novel_path.exists():
            raise FileNotFoundError(f"小说文件不存在: {novel_path}")
        text = novel_path.read_text(encoding="utf-8")
        logger.info(f"📖 成功读取小说: {self.novel_filename} ({len(text):,} 字)")
        return text

    def _load_characters_list(self) -> List[Dict[str, Any]]:
        """加载已保存的角色列表"""
        file_path = self.world_dir / "characters_list.json"
        return json.loads(file_path.read_text(encoding="utf-8"))

    def _load_world_setting(self) -> Dict[str, Any]:
        """加载已保存的世界设定"""
        file_path = self.world_dir / "world_setting.json"
        return json.loads(file_path.read_text(encoding="utf-8"))

    def _save_characters_list(self, characters_list: List[Dict[str, Any]]):
        """保存角色列表"""
        file_path = self.world_dir / "characters_list.json"
        file_path.write_text(
            json.dumps(characters_list, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        logger.info(f"💾 角色列表已保存: {file_path}")

    def _save_world_setting(self, world_setting: Dict[str, Any]):
        """保存世界设定"""
        file_path = self.world_dir / "world_setting.json"
        file_path.write_text(
            json.dumps(world_setting, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        logger.info(f"💾 世界设定已保存: {file_path}")

    def _save_character(self, char_id: str, char_data: Dict[str, Any]):
        """保存单个角色档案"""
        characters_dir = self.world_dir / "characters"
        characters_dir.mkdir(exist_ok=True)
        file_path = characters_dir / f"character_{char_id}.json"
        file_path.write_text(
            json.dumps(char_data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def _check_character_done(self, char_id: str) -> bool:
        """检查角色档案是否已完成"""
        file_path = self.world_dir / "characters" / f"character_{char_id}.json"
        if not file_path.exists():
            return False
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            return "error" not in data
        except Exception:
            return False

    # ========================================================================
    # 阶段执行
    # ========================================================================

    def run_stage1(self, novel_text: str) -> List[Dict[str, Any]]:
        """阶段1：角色普查"""
        logger.info("=" * 60)
        logger.info("📍 阶段1：角色普查 (大中正)")
        logger.info("=" * 60)

        characters_list = self.character_filter_agent.run(novel_text)
        self._save_characters_list(characters_list)

        self.checkpoint.stage1_done = True
        self._save_checkpoint()

        logger.info(f"✅ 阶段1完成，识别到 {len(characters_list)} 个角色")
        return characters_list

    def run_stage2(self, novel_text: str) -> Dict[str, Any]:
        """阶段2：世界观提取"""
        logger.info("=" * 60)
        logger.info("📍 阶段2：世界观提取 (Demiurge)")
        logger.info("=" * 60)

        world_setting = self.world_setting_agent.run(novel_text)

        # 如果没有预设世界名称，从世界设定中获取
        if not self.world_name:
            self.world_name = world_setting.get("meta", {}).get("world_name", "未知世界")
            # 更新世界目录
            new_world_dir = settings.DATA_DIR / "worlds" / self.world_name
            if self.world_dir != new_world_dir:
                # 迁移数据（如果有的话）
                if self.world_dir and self.world_dir.exists():
                    import shutil
                    if new_world_dir.exists():
                        shutil.rmtree(new_world_dir)
                    shutil.move(str(self.world_dir), str(new_world_dir))
                self.world_dir = new_world_dir
                self.world_dir.mkdir(parents=True, exist_ok=True)

        self._save_world_setting(world_setting)

        self.checkpoint.stage2_done = True
        self._save_checkpoint()

        logger.info(f"✅ 阶段2完成，世界名称: {self.world_name}")
        return world_setting

    async def run_stage1_and_2_parallel(
        self, novel_text: str
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """并行执行阶段1和阶段2"""
        logger.info("=" * 60)
        logger.info("📍 阶段1+2：并行执行角色普查与世界观提取")
        logger.info("=" * 60)

        start_time = time.time()

        async def _run_stage1():
            """异步包装阶段1"""
            logger.info("🎭 [并行] 启动阶段1：角色普查 (大中正)")
            sem = _get_semaphore()
            async with sem:
                result = await asyncio.to_thread(
                    self.character_filter_agent.run, novel_text
                )
            self._save_characters_list(result)
            self.checkpoint.stage1_done = True
            self._save_checkpoint()
            logger.info(f"✅ [并行] 阶段1完成，识别到 {len(result)} 个角色")
            return result

        async def _run_stage2():
            """异步包装阶段2"""
            logger.info("🌍 [并行] 启动阶段2：世界观提取 (Demiurge)")
            sem = _get_semaphore()
            async with sem:
                result = await asyncio.to_thread(
                    self.world_setting_agent.run, novel_text
                )
            # 注意：世界目录重命名在主流程中处理，避免并发冲突
            logger.info("✅ [并行] 阶段2完成")
            return result

        # 并行执行
        characters_list, world_setting = await asyncio.gather(
            _run_stage1(), _run_stage2()
        )

        # 处理世界目录重命名（阶段2的后处理）
        if not self.world_name:
            self.world_name = world_setting.get("meta", {}).get("world_name", "未知世界")
            new_world_dir = settings.DATA_DIR / "worlds" / self.world_name
            if self.world_dir != new_world_dir:
                if self.world_dir and self.world_dir.exists():
                    import shutil
                    if new_world_dir.exists():
                        shutil.rmtree(new_world_dir)
                    shutil.move(str(self.world_dir), str(new_world_dir))
                self.world_dir = new_world_dir
                self.world_dir.mkdir(parents=True, exist_ok=True)

        self._save_world_setting(world_setting)
        self.checkpoint.stage2_done = True
        self._save_checkpoint()

        elapsed = time.time() - start_time
        logger.info("=" * 60)
        logger.info(f"📊 阶段1+2并行完成，总耗时: {elapsed:.1f}s")
        logger.info(f"   - 角色数: {len(characters_list)}")
        logger.info(f"   - 世界名: {self.world_name}")
        logger.info("=" * 60)

        return characters_list, world_setting

    async def run_all_stages_parallel(self, novel_text: str) -> Dict[str, Dict[str, Any]]:
        """
        流水线并行：Stage1完成后立即启动Stage3，不等Stage2

        执行流程:
        ┌─────────────────────────────────────────────────┐
        │  Stage1 (角色普查) ──完成──→ Stage3 (角色档案)   │
        │       ↑                         ↓               │
        │       └── 并行 ──→ Stage2 (世界设定)            │
        └─────────────────────────────────────────────────┘
        """
        logger.info("=" * 60)
        logger.info("📍 流水线并行模式：Stage1→Stage3 与 Stage2 并发")
        logger.info("=" * 60)

        start_time = time.time()

        # 用于Stage1→Stage3的数据传递
        characters_list_future: asyncio.Future[List[Dict[str, Any]]] = asyncio.Future()

        async def _run_stage1_then_3():
            """Stage1完成后立即启动Stage3"""
            # Stage1
            logger.info("🎭 [流水线] 启动阶段1：角色普查 (大中正)")
            sem = _get_semaphore()
            async with sem:
                characters_list = await asyncio.to_thread(
                    self.character_filter_agent.run, novel_text
                )
            self._save_characters_list(characters_list)
            self.checkpoint.stage1_done = True
            self._save_checkpoint()
            logger.info(f"✅ [流水线] 阶段1完成，识别到 {len(characters_list)} 个角色")

            # 通知其他任务Stage1已完成
            characters_list_future.set_result(characters_list)

            # 立即启动Stage3（不等Stage2）
            logger.info("🚀 [流水线] 立即启动阶段3：角色档案生成")
            characters_details = await self.run_stage3_parallel(novel_text, characters_list)
            return characters_list, characters_details

        async def _run_stage2():
            """Stage2独立运行"""
            logger.info("🌍 [流水线] 启动阶段2：世界观提取 (Demiurge)")
            sem = _get_semaphore()
            async with sem:
                world_setting = await asyncio.to_thread(
                    self.world_setting_agent.run, novel_text
                )
            logger.info("✅ [流水线] 阶段2完成")
            return world_setting

        # 并行执行
        (characters_list, characters_details), world_setting = await asyncio.gather(
            _run_stage1_then_3(), _run_stage2()
        )

        # 处理世界目录重命名
        if not self.world_name:
            self.world_name = world_setting.get("meta", {}).get("world_name", "未知世界")
            new_world_dir = settings.DATA_DIR / "worlds" / self.world_name
            if self.world_dir != new_world_dir:
                if self.world_dir and self.world_dir.exists():
                    import shutil
                    if new_world_dir.exists():
                        shutil.rmtree(new_world_dir)
                    shutil.move(str(self.world_dir), str(new_world_dir))
                self.world_dir = new_world_dir
                self.world_dir.mkdir(parents=True, exist_ok=True)

        self._save_world_setting(world_setting)
        self.checkpoint.stage2_done = True
        self._save_checkpoint()

        elapsed = time.time() - start_time
        logger.info("=" * 60)
        logger.info(f"📊 流水线并行完成，总耗时: {elapsed:.1f}s")
        logger.info(f"   - 角色数: {len(characters_list)}")
        logger.info(f"   - 角色档案: {len(characters_details)}")
        logger.info(f"   - 世界名: {self.world_name}")
        logger.info("=" * 60)

        return characters_details

    def run_stage3_serial(
        self,
        novel_text: str,
        characters_list: List[Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        """阶段3：角色档案（串行版本）"""
        logger.info("=" * 60)
        logger.info("📍 阶段3：角色档案生成 (许劭) - 串行模式")
        logger.info("=" * 60)

        characters_details: Dict[str, Dict[str, Any]] = {}
        total = len(characters_list)

        for idx, char_info in enumerate(characters_list, 1):
            char_id = char_info.get("id")
            char_name = char_info.get("name")

            # 检查是否已完成
            if self._check_character_done(char_id):
                logger.info(f"[{idx}/{total}] ⏭️ 跳过已完成: {char_name}")
                continue

            logger.info(f"[{idx}/{total}] 🎭 处理角色: {char_name}")

            try:
                char_data = self.character_detail_agent.create_one(
                    novel_text, char_info, characters_list
                )
                characters_details[char_id] = char_data
                self._save_character(char_id, char_data)

                self.checkpoint.stage3_completed_characters.append(char_id)
                self._save_checkpoint()

                logger.info(f"   ✅ {char_name} 档案创建完成")

            except Exception as e:
                logger.error(f"   ❌ {char_name} 档案创建失败: {e}")
                self.checkpoint.stage3_failed_characters.append(char_id)
                self._save_checkpoint()

        self.checkpoint.stage3_done = True
        self._save_checkpoint()

        return characters_details

    async def run_stage3_parallel(
        self,
        novel_text: str,
        characters_list: List[Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        """阶段3：角色档案（并行版本）"""
        logger.info("=" * 60)
        logger.info(f"📍 阶段3：角色档案生成 (许劭) - 并行模式 (并发数: {_LLM_CONCURRENCY})")
        logger.info("=" * 60)

        # 筛选需要处理的角色
        pending_chars = []
        for char_info in characters_list:
            char_id = char_info.get("id")
            if not self._check_character_done(char_id):
                pending_chars.append(char_info)
            else:
                logger.info(f"⏭️ 跳过已完成: {char_info.get('name')}")

        if not pending_chars:
            logger.info("✅ 所有角色档案已完成")
            self.checkpoint.stage3_done = True
            self._save_checkpoint()
            return {}

        logger.info(f"📋 待处理角色: {len(pending_chars)} 个")

        async def create_character(char_info: Dict[str, Any]) -> tuple:
            """异步创建单个角色"""
            char_id = char_info.get("id")
            char_name = char_info.get("name")

            sem = _get_semaphore()
            async with sem:
                logger.info(f"🎭 开始处理: {char_name}")
                try:
                    # 使用线程池执行同步的 LLM 调用
                    char_data = await asyncio.to_thread(
                        self.character_detail_agent.create_one,
                        novel_text,
                        char_info,
                        characters_list
                    )
                    # 立即保存
                    self._save_character(char_id, char_data)
                    logger.info(f"✅ {char_name} 档案创建完成")
                    return char_id, char_data, None
                except Exception as e:
                    logger.error(f"❌ {char_name} 档案创建失败: {e}")
                    return char_id, None, str(e)

        # 并行执行
        start_time = time.time()
        tasks = [create_character(char_info) for char_info in pending_chars]
        results = await asyncio.gather(*tasks)
        elapsed = time.time() - start_time

        # 处理结果
        characters_details: Dict[str, Dict[str, Any]] = {}
        success_count = 0
        fail_count = 0

        for char_id, char_data, error in results:
            if error:
                self.checkpoint.stage3_failed_characters.append(char_id)
                fail_count += 1
            else:
                characters_details[char_id] = char_data
                self.checkpoint.stage3_completed_characters.append(char_id)
                success_count += 1

        self.checkpoint.stage3_done = True
        self._save_checkpoint()

        logger.info("=" * 60)
        logger.info(f"📊 阶段3完成统计")
        logger.info(f"   ✅ 成功: {success_count}")
        logger.info(f"   ❌ 失败: {fail_count}")
        logger.info(f"   ⏱️ 总耗时: {elapsed:.1f}s")
        logger.info(f"   ⚡ 平均: {elapsed / len(pending_chars):.1f}s/角色")
        logger.info("=" * 60)

        return characters_details

    # ========================================================================
    # 主入口
    # ========================================================================

    def run(self) -> Path:
        """执行完整的世界构建流程"""
        logger.info("=" * 70)
        logger.info("🚀 世界构建器启动")
        logger.info("=" * 70)

        # 读取小说
        novel_text = self._read_novel()

        # 初始化世界目录
        if self.world_name:
            self.world_dir = settings.DATA_DIR / "worlds" / self.world_name
        else:
            # 临时目录，阶段2完成后会重命名
            self.world_dir = settings.DATA_DIR / "worlds" / f"_temp_{int(time.time())}"
        self.world_dir.mkdir(parents=True, exist_ok=True)

        # 加载检查点
        self.checkpoint = self._load_checkpoint()
        self.checkpoint.novel_filename = self.novel_filename

        # 显示当前状态
        self._print_status()

        # 检查各阶段完成状态
        stage1_done = self.checkpoint.stage1_done
        stage2_done = self.checkpoint.stage2_done
        stage3_done = self.checkpoint.stage3_done and not self.checkpoint.stage3_failed_characters

        if stage1_done and stage2_done and stage3_done:
            # 全部完成
            logger.info("⏭️ 所有阶段已完成，无需重新构建")
            return self.world_dir

        # 全新构建 + 并行模式：使用流水线并行（Stage1→Stage3 与 Stage2 并发）
        if not stage1_done and not stage2_done and not stage3_done and self.parallel:
            logger.info("🚀 启用流水线并行模式")
            asyncio.run(self.run_all_stages_parallel(novel_text))
        else:
            # 部分完成或串行模式，按顺序处理
            # 阶段1 + 阶段2
            if stage1_done and stage2_done:
                logger.info("⏭️ 阶段1+2已完成，加载缓存...")
                characters_list = self._load_characters_list()
                world_setting = self._load_world_setting()
                if not self.world_name:
                    self.world_name = world_setting.get("meta", {}).get("world_name", "未知世界")
            elif not stage1_done and not stage2_done and self.parallel:
                # 两个阶段都未完成且开启并行模式，并行执行
                characters_list, world_setting = asyncio.run(
                    self.run_stage1_and_2_parallel(novel_text)
                )
            else:
                # 部分完成或串行模式，按顺序执行
                if stage1_done:
                    logger.info("⏭️ 阶段1已完成，加载缓存...")
                    characters_list = self._load_characters_list()
                else:
                    characters_list = self.run_stage1(novel_text)

                if stage2_done:
                    logger.info("⏭️ 阶段2已完成，加载缓存...")
                    world_setting = self._load_world_setting()
                    if not self.world_name:
                        self.world_name = world_setting.get("meta", {}).get("world_name", "未知世界")
                else:
                    world_setting = self.run_stage2(novel_text)

            # 阶段3
            if stage3_done:
                logger.info("⏭️ 阶段3已完成，无需重新生成")
            else:
                if self.parallel:
                    asyncio.run(self.run_stage3_parallel(novel_text, characters_list))
                else:
                    self.run_stage3_serial(novel_text, characters_list)

        # 完成
        logger.info("=" * 70)
        logger.info("🎉 世界构建完成！")
        logger.info(f"📁 世界目录: {self.world_dir}")
        logger.info("=" * 70)

        return self.world_dir

    def _print_status(self):
        """打印当前状态"""
        logger.info("-" * 40)
        logger.info("📋 当前进度:")
        logger.info(f"   阶段1 (角色普查): {'✅ 完成' if self.checkpoint.stage1_done else '⏳ 待执行'}")
        logger.info(f"   阶段2 (世界设定): {'✅ 完成' if self.checkpoint.stage2_done else '⏳ 待执行'}")
        if self.checkpoint.stage3_done:
            status = "✅ 完成"
            if self.checkpoint.stage3_failed_characters:
                status += f" (有 {len(self.checkpoint.stage3_failed_characters)} 个失败)"
        else:
            completed = len(self.checkpoint.stage3_completed_characters)
            status = f"⏳ 进行中 ({completed} 个已完成)"
        logger.info(f"   阶段3 (角色档案): {status}")
        logger.info("-" * 40)


# ============================================================================
# 工具函数
# ============================================================================

def list_novels() -> List[str]:
    """列出所有可用的小说文件"""
    novels_dir = settings.NOVELS_DIR
    if not novels_dir.exists():
        return []
    return [f.name for f in novels_dir.glob("*.txt")]


def list_worlds() -> List[Dict[str, Any]]:
    """列出所有已创建的世界"""
    worlds_dir = settings.DATA_DIR / "worlds"
    if not worlds_dir.exists():
        return []

    worlds = []
    for world_path in worlds_dir.iterdir():
        if not world_path.is_dir() or world_path.name.startswith("_"):
            continue

        info = {"name": world_path.name, "path": str(world_path)}

        # 检查各阶段完成情况
        characters_list_file = world_path / "characters_list.json"
        info["has_characters_list"] = characters_list_file.exists()
        info["has_world_setting"] = (world_path / "world_setting.json").exists()

        characters_dir = world_path / "characters"
        if characters_dir.exists():
            # 只统计 character_npc_*.json，排除 user.json 等
            info["character_count"] = len(list(characters_dir.glob("character_npc_*.json")))
        else:
            info["character_count"] = 0

        # 读取检查点
        checkpoint_file = world_path / ".checkpoint.json"
        if checkpoint_file.exists():
            try:
                checkpoint = json.loads(checkpoint_file.read_text(encoding="utf-8"))
                info["checkpoint"] = checkpoint
            except Exception:
                pass
        else:
            # 没有检查点文件时，根据实际文件推断状态
            info["checkpoint"] = _infer_checkpoint(world_path, characters_list_file, info["character_count"])

        worlds.append(info)

    return worlds


def _infer_checkpoint(world_path: Path, characters_list_file: Path, char_file_count: int) -> Dict[str, Any]:
    """从现有文件推断检查点状态"""
    checkpoint = {
        "stage1_done": characters_list_file.exists(),
        "stage2_done": (world_path / "world_setting.json").exists(),
        "stage3_done": False,
        "stage3_completed_characters": [],
        "stage3_failed_characters": [],
    }

    if characters_list_file.exists():
        try:
            characters_list = json.loads(characters_list_file.read_text(encoding="utf-8"))
            expected_count = len(characters_list)

            # 检查每个角色是否有档案
            characters_dir = world_path / "characters"
            completed = []
            failed = []

            for char_info in characters_list:
                char_id = char_info.get("id")
                char_file = characters_dir / f"character_{char_id}.json"

                if char_file.exists():
                    try:
                        data = json.loads(char_file.read_text(encoding="utf-8"))
                        if "error" in data:
                            failed.append(char_id)
                        else:
                            completed.append(char_id)
                    except Exception:
                        failed.append(char_id)
                else:
                    failed.append(char_id)

            checkpoint["stage3_completed_characters"] = completed
            checkpoint["stage3_failed_characters"] = failed
            checkpoint["stage3_done"] = len(failed) == 0 and len(completed) == expected_count

        except Exception:
            pass

    return checkpoint


def print_worlds_table(worlds: List[Dict[str, Any]]):
    """打印世界列表表格"""
    if not worlds:
        print("📭 还没有创建任何世界")
        return

    print("\n" + "=" * 70)
    print("🌍 已创建的世界列表")
    print("=" * 70)
    print(f"{'序号':<4} {'世界名称':<20} {'阶段1':<8} {'阶段2':<8} {'角色数':<8} {'状态':<10}")
    print("-" * 70)

    for idx, world in enumerate(worlds, 1):
        stage1 = "✅" if world.get("has_characters_list") else "❌"
        stage2 = "✅" if world.get("has_world_setting") else "❌"
        char_count = world.get("character_count", 0)

        checkpoint = world.get("checkpoint", {})
        if checkpoint.get("stage3_done"):
            failed = len(checkpoint.get("stage3_failed_characters", []))
            status = "✅ 完成" if failed == 0 else f"⚠️ {failed}个失败"
        elif checkpoint.get("stage3_completed_characters"):
            status = "🔄 进行中"
        else:
            status = "⏳ 未开始"

        print(f"{idx:<4} {world['name']:<20} {stage1:<8} {stage2:<8} {char_count:<8} {status:<10}")

    print("=" * 70 + "\n")


def interactive_menu():
    """交互式菜单 - 自动探测并展示所有选项"""
    novels = list_novels()
    worlds = list_worlds()
    complete_worlds = [w for w in worlds if w.get("checkpoint", {}).get("stage3_done")]
    incomplete_worlds = [w for w in worlds if not w.get("checkpoint", {}).get("stage3_done")]

    print("\n" + "=" * 60)
    print("🏗️  世界构建器")
    print("=" * 60)

    options = []

    # 选项1: 已完成的世界（可进入游戏）
    if complete_worlds:
        print(f"\n🌍 已完成的世界 (可启动游戏):")
        for world in complete_worlds:
            options.append(("play", world))
            char_count = world.get("character_count", 0)
            print(f"   [{len(options)}] ▶️  {world['name']} ({char_count} 个角色)")

    # 选项2: 未完成的世界（可继续构建）
    if incomplete_worlds:
        print(f"\n🔄 未完成的世界 (可继续构建):")
        for world in incomplete_worlds:
            options.append(("resume", world))
            checkpoint = world.get("checkpoint", {})
            completed = len(checkpoint.get("stage3_completed_characters", []))
            failed = len(checkpoint.get("stage3_failed_characters", []))
            stage = "阶段1" if not checkpoint.get("stage1_done") else \
                    "阶段2" if not checkpoint.get("stage2_done") else \
                    f"阶段3 ({completed}个完成)"
            print(f"   [{len(options)}] 🔧 {world['name']} - {stage}")

    # 选项3: 可用的小说（可新建）
    if novels:
        print(f"\n📚 从小说新建世界:")
        for novel in novels:
            options.append(("new", novel))
            print(f"   [{len(options)}] ➕ {novel}")
    else:
        print("\n📭 没有小说文件，请将 .txt 放入 data/novels/")

    # 退出选项
    print(f"\n   [0] 退出")
    print("-" * 60)

    if not options:
        print("没有可用操作")
        return

    # 获取用户选择
    choice = input("请选择 [0-" + str(len(options)) + "]: ").strip()

    if choice == "0":
        print("👋 再见！")
        sys.exit(0)

    try:
        choice_idx = int(choice) - 1
        if choice_idx < 0 or choice_idx >= len(options):
            print("❌ 无效选择")
            return
    except ValueError:
        print("❌ 请输入数字")
        return

    action, data = options[choice_idx]

    if action == "play":
        # 启动游戏
        world = data
        world_name = world['name']
        print(f"\n🎮 启动世界: {world_name}")

        # 查找已有的 runtime 目录
        runtime_dir = settings.DATA_DIR / "runtime"
        runtime_dirs = list(runtime_dir.glob(f"{world_name}_*")) if runtime_dir.exists() else []

        genesis_file = None
        if runtime_dirs:
            # 找最新的 runtime
            latest_runtime = max(runtime_dirs, key=lambda p: p.stat().st_mtime)
            # 尝试两种命名方式
            for name in ["genesis.json", "Genesis.json"]:
                candidate = latest_runtime / name
                if candidate.exists():
                    genesis_file = candidate
                    print(f"📁 使用已有存档: {latest_runtime.name}")
                    break

        if genesis_file:
            # 直接启动游戏
            print(f"🚀 启动游戏引擎...")
            import subprocess
            subprocess.run([sys.executable, "run_game.py", "--genesis", str(genesis_file)])
        else:
            # 需要初始化
            print(f"🔧 首次启动，正在初始化世界...")

            try:
                from initial_Illuminati import IlluminatiInitializer

                # 初始化光明会
                initializer = IlluminatiInitializer(world_name=world_name)
                runtime_path = initializer.run()

                genesis_file = runtime_path / "Genesis.json"

                if genesis_file.exists():
                    print(f"\n✅ 初始化完成！")
                    print(f"🚀 启动游戏引擎...")
                    import subprocess
                    subprocess.run([sys.executable, "run_game.py", "--genesis", str(genesis_file)])
                else:
                    print(f"❌ 初始化失败: Genesis.json 未生成")

            except Exception as e:
                logger.error(f"初始化失败: {e}", exc_info=True)
                print(f"❌ 初始化失败: {e}")

    elif action == "resume":
        # 继续构建
        world = data
        checkpoint = world.get("checkpoint", {})
        novel_filename = checkpoint.get("novel_filename", "")

        if not novel_filename:
            # 尝试从小说列表中匹配
            if len(novels) == 1:
                novel_filename = novels[0]
                print(f"📖 自动选择小说: {novel_filename}")
            else:
                print("无法确定原始小说文件")
                for idx, novel in enumerate(novels, 1):
                    print(f"  {idx}. {novel}")
                novel_choice = input("请选择 [输入序号]: ").strip()
                try:
                    novel_filename = novels[int(novel_choice) - 1]
                except (ValueError, IndexError):
                    print("❌ 无效选择")
                    return

        print(f"\n🚀 继续构建世界: {world['name']}")
        builder = WorldBuilder(novel_filename, world["name"], parallel=True)
        builder.run()

    elif action == "new":
        # 新建世界
        novel_filename = data
        print(f"\n🚀 从小说创建新世界: {novel_filename}")
        print("   (世界名称将从小说内容自动提取)")
        builder = WorldBuilder(novel_filename, world_name=None, parallel=True)
        builder.run()


# ============================================================================
# 主入口
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="世界构建器 - 支持断点续传和并行化",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run_world_builder.py                    # 交互式菜单
  python run_world_builder.py --novel xxx.txt    # 从小说创建新世界
  python run_world_builder.py --resume 江城市    # 继续构建指定世界
  python run_world_builder.py --list             # 列出所有世界
  python run_world_builder.py --novel xxx.txt --no-parallel  # 禁用并行
        """
    )
    parser.add_argument("--novel", "-n", help="小说文件名")
    parser.add_argument("--world", "-w", help="世界名称（可选）")
    parser.add_argument("--resume", "-r", help="继续构建指定世界")
    parser.add_argument("--list", "-l", action="store_true", help="列出所有世界")
    parser.add_argument("--no-parallel", action="store_true", help="禁用并行模式")
    parser.add_argument("--concurrency", "-c", type=int, default=5, help="并发数 (默认: 5)")

    args = parser.parse_args()

    # 设置并发数
    if args.concurrency:
        os.environ["LLM_CONCURRENCY"] = str(args.concurrency)
        global _LLM_CONCURRENCY
        _LLM_CONCURRENCY = args.concurrency

    if args.list:
        worlds = list_worlds()
        print_worlds_table(worlds)

    elif args.resume:
        # 继续构建
        worlds = list_worlds()
        world = next((w for w in worlds if w["name"] == args.resume), None)
        if not world:
            print(f"❌ 世界 '{args.resume}' 不存在")
            sys.exit(1)

        checkpoint = world.get("checkpoint", {})
        novel_filename = checkpoint.get("novel_filename", "")
        if not novel_filename:
            print("❌ 无法确定原始小说文件，请使用 --novel 参数指定")
            sys.exit(1)

        builder = WorldBuilder(novel_filename, args.resume, parallel=not args.no_parallel)
        builder.run()

    elif args.novel:
        # 新建世界
        builder = WorldBuilder(args.novel, args.world, parallel=not args.no_parallel)
        builder.run()

    else:
        # 交互式菜单
        while True:
            try:
                interactive_menu()
            except KeyboardInterrupt:
                print("\n👋 再见！")
                break


if __name__ == "__main__":
    main()
