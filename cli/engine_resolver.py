"""
引擎解析模块

负责：
- 解析最终使用的引擎类型
- 处理引擎切换逻辑
- 发出引擎冲突警告
"""

import sys
from pathlib import Path
from typing import Optional, Tuple

from utils.progress_tracker import ProgressTracker
from utils.logger import setup_logger

logger = setup_logger("EngineResolver", "engine_resolver.log")


def resolve_engine(
    cli_engine: Optional[str],
    is_resume: bool,
    runtime_dir: Optional[Path],
    default: str = "osagent"
) -> str:
    """
    解析最终使用的引擎类型（统一入口）
    
    Args:
        cli_engine: CLI --engine 参数值（可能为 None）
        is_resume: 是否为续玩模式
        runtime_dir: 运行时目录（续玩时必需）
        default: 默认引擎类型
    
    Returns:
        最终引擎类型: "osagent" 或 "gameengine"
    
    优先级：CLI > progress.json(仅续玩时且未损坏) > default
    """
    # 1. CLI 显式指定优先
    if cli_engine is not None:
        return cli_engine
    
    # 2. 续玩时尝试从 progress.json 读取
    if is_resume and runtime_dir is not None:
        progress_file = runtime_dir / "plot" / "progress.json"
        if progress_file.exists():
            progress = ProgressTracker().load_progress(runtime_dir)
            # 仅从未损坏的进度中继承 engine_type
            if not progress.is_corrupted and progress.engine_type:
                return progress.engine_type
    
    # 3. 新开局或无进度或进度损坏时使用默认值
    return default


def check_engine_conflict(
    cli_engine: Optional[str],
    runtime_dir: Optional[Path]
) -> None:
    """
    检查引擎冲突并发出警告
    
    Args:
        cli_engine: CLI --engine 参数值
        runtime_dir: 运行时目录
    """
    if cli_engine is None or runtime_dir is None:
        return
    
    progress_file = runtime_dir / "plot" / "progress.json"
    if not progress_file.exists():
        return
    
    progress = ProgressTracker().load_progress(runtime_dir)
    
    # 仅在进度未损坏时检查冲突
    if (
        not progress.is_corrupted 
        and progress.engine_type 
        and cli_engine != progress.engine_type
    ):
        print(
            f"⚠️  警告：CLI 指定引擎 ({cli_engine}) 与存档引擎 ({progress.engine_type}) 不同\n"
            f"   继续将使用 {cli_engine}，可能导致状态不一致",
            file=sys.stderr
        )
        
        if not progress.can_switch_engine:
            print("   ❌ 当前进度不支持引擎切换，操作已中止", file=sys.stderr)
            sys.exit(1)


def can_switch_engine(runtime_dir: Path) -> Tuple[bool, str]:
    """
    检查是否可以切换引擎
    
    Args:
        runtime_dir: 运行时目录
    
    Returns:
        (可以切换, 原因说明)
    """
    # 先检查进度文件是否存在
    progress_file = runtime_dir / "plot" / "progress.json"
    if not progress_file.exists():
        return False, "progress.json 不存在，无法切换引擎"
    
    progress = ProgressTracker().load_progress(runtime_dir)
    
    # 检查进度是否损坏
    if progress.is_corrupted:
        return False, "progress.json 已损坏，无法切换引擎"
    
    if not progress.can_switch_engine:
        return False, "当前进度处于场景/回合中途，不支持切换"
    
    return True, "可以安全切换"


def switch_engine(runtime_dir: Path, target_engine: str) -> None:
    """
    切换引擎（仅更新 progress.json，不迁移数据）
    
    Args:
        runtime_dir: 运行时目录
        target_engine: 目标引擎类型
    
    Raises:
        RuntimeError: 如果当前进度不支持切换
    """
    can_switch, reason = can_switch_engine(runtime_dir)
    if not can_switch:
        raise RuntimeError(f"无法切换引擎：{reason}")
    
    # 更新 progress.json 的 engine_type（显式传入所有参数，不依赖默认值）
    progress = ProgressTracker().load_progress(runtime_dir)
    ProgressTracker().save_progress(
        runtime_dir=runtime_dir,
        current_scene_id=progress.current_scene_id,
        next_scene_id=progress.next_scene_id,
        turn_count=progress.turn_count,
        engine_type=target_engine,
        can_switch_engine=True  # 切换完成后允许再次切换
    )
    
    logger.info(f"引擎已切换为 {target_engine}")
    print(f"✅ 引擎已切换为 {target_engine}")
    print(f"   注意：切换后将从场景 {progress.current_scene_id}、回合 {progress.turn_count} 继续")

