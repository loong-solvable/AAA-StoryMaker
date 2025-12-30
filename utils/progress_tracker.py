"""
断点续传模块 - 统一的进度跟踪器

负责：
- 加载/保存 progress.json
- 兼容 v1/v2 格式
- 处理损坏的进度文件
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from utils.logger import setup_logger

logger = setup_logger("ProgressTracker", "progress_tracker.log")

# 默认值常量（确保所有分支一致）
DEFAULT_ENGINE_TYPE = "osagent"
# v1 兼容：默认 False（保守策略，防止旧存档在非安全点切换）
# 只有明确到达边界点（幕间/存档点）时才设为 True
DEFAULT_CAN_SWITCH = False


@dataclass
class ProgressData:
    """进度数据（v2格式，向后兼容）"""
    format_version: int = 2
    current_scene_id: int = 1
    next_scene_id: int = 2
    turn_count: int = 0
    engine_type: str = DEFAULT_ENGINE_TYPE  # "osagent"
    updated_at: str = ""
    can_switch_engine: bool = DEFAULT_CAN_SWITCH  # v3.5+: False（保守策略）
    is_corrupted: bool = False  # 标记 progress.json 是否损坏


class ProgressTracker:
    """进度跟踪器"""
    
    def load_resume_scene_id(self, runtime_dir: Path) -> int:
        """
        获取恢复场景ID（便捷方法）
        
        注意：
        - 内部调用 load_progress() 以复用 v2 默认值补齐逻辑
        - 如果 is_corrupted=True，抛出异常而非返回默认值
        
        Raises:
            RuntimeError: 如果 progress.json 损坏
        """
        progress = self.load_progress(runtime_dir)
        if progress.is_corrupted:
            raise RuntimeError("progress.json 已损坏，无法获取恢复场景ID")
        return progress.current_scene_id
    
    def load_progress(self, runtime_dir: Path) -> ProgressData:
        """
        加载进度，兼容新旧格式，处理损坏场景。
        
        无论哪种格式，都返回完整的 ProgressData，缺失字段使用默认值。
        """
        progress_file = runtime_dir / "plot" / "progress.json"
        
        if not progress_file.exists():
            # 文件不存在：返回默认进度（使用 DEFAULT_* 常量，can_switch_engine=False）
            return ProgressData()  # 内部使用 DEFAULT_CAN_SWITCH=False
        
        try:
            # 使用 with 语句确保文件句柄关闭（Windows 上 rename 需要）
            with open(progress_file, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            # JSON 损坏处理
            import sys
            
            # 使用时间戳避免覆盖之前的备份
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = progress_file.with_suffix(f".corrupted_{timestamp}.json")
            
            try:
                progress_file.rename(backup_path)
            except Exception as rename_error:
                logger.error(f"⚠️ 重命名损坏文件失败: {rename_error}")
            
            # ⚠️ 跨进程限制：重命名后，下一进程只会看到"文件不存在"
            # 这是预期行为：损坏文件已被安全移走，新进程从默认状态开始
            # 若需要区分"不存在"和"已损坏"，需检查 .corrupted_*.json 备份
            
            # 记录到日志文件
            logger.error(f"progress.json 损坏并已备份到 {backup_path}: {e}")
            
            print(
                f"\n⚠️  警告：progress.json 损坏 ({e})\n"
                f"   已备份到：{backup_path}\n",
                file=sys.stderr
            )
            
            # 返回带损坏标记的默认进度，让调用方决定是否 fail-fast
            return ProgressData(is_corrupted=True)
        except Exception as e:
            logger.error(f"读取 progress.json 失败: {e}")
            return ProgressData(is_corrupted=True)
        
        # 正常解析流程
        version = data.get("format_version", 1)
        
        # 统一提取字段，缺失时使用默认值
        return ProgressData(
            format_version=version,
            current_scene_id=data.get("current_scene_id", 1),
            next_scene_id=data.get("next_scene_id", 2),
            turn_count=data.get("turn_count", 0),  # v1 无此字段，默认 0
            engine_type=data.get("engine_type", DEFAULT_ENGINE_TYPE),  # v1 无此字段
            updated_at=data.get("updated_at", ""),
            can_switch_engine=data.get("can_switch_engine", DEFAULT_CAN_SWITCH)  # v1 无此字段
        )
    
    def save_progress(
        self,
        runtime_dir: Path,
        current_scene_id: int,
        next_scene_id: int,
        turn_count: int = 0,
        engine_type: str = DEFAULT_ENGINE_TYPE,
        can_switch_engine: bool = DEFAULT_CAN_SWITCH  # v3.6+: 默认 False（保守策略）
    ) -> None:
        """
        保存进度（v2格式）
        
        Args:
            runtime_dir: 运行时目录
            current_scene_id: 当前场景 ID
            next_scene_id: 下一场景 ID
            turn_count: 累计回合数
            engine_type: 引擎类型 ("osagent" | "gameengine")
            can_switch_engine: 是否允许切换引擎（场景中途应为 False）
        
        以下字段由函数内部自动补齐：
        - format_version: 固定为 2
        - updated_at: 自动填充当前时间戳
        """
        progress_file = runtime_dir / "plot" / "progress.json"
        progress_file.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "format_version": 2,
            "current_scene_id": current_scene_id,
            "next_scene_id": next_scene_id,
            "turn_count": turn_count,
            "engine_type": engine_type,
            "updated_at": datetime.now().isoformat(),
            "can_switch_engine": can_switch_engine
        }
        
        try:
            with open(progress_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug(f"进度已保存: scene={current_scene_id}, turn={turn_count}, can_switch={can_switch_engine}")
        except Exception as e:
            logger.error(f"保存 progress.json 失败: {e}")
            raise


# 全局单例（便捷使用）
progress_tracker = ProgressTracker()

