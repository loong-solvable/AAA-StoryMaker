"""
玩家角色管理模块

负责：
- 收集玩家角色信息
- 创建玩家角色文件
"""

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Dict, Any

from utils.logger import setup_logger

logger = setup_logger("PlayerProfile", "player_profile.log")


@dataclass
class PlayerProfile:
    """玩家角色信息"""
    name: str = "玩家"
    gender: str = ""
    appearance: str = ""
    background: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {k: v for k, v in asdict(self).items() if v}


def prompt_player_profile(
    default_name: str = "玩家",
    interactive: bool = True
) -> PlayerProfile:
    """
    收集玩家的角色信息
    
    Args:
        default_name: 默认角色名称
        interactive: 是否交互式收集（False 时直接返回默认值）
    
    Returns:
        玩家角色信息
    """
    if not interactive:
        return PlayerProfile(name=default_name)
    
    print()
    print("[Create Your Character]")
    
    profile = PlayerProfile()
    
    try:
        name = input(f"   角色名字 (回车默认\"{default_name}\") > ").strip()
        if name:
            profile.name = name
        else:
            profile.name = default_name
        
        gender = input("   性别 (可留空) > ").strip()
        if gender:
            profile.gender = gender
        
        appearance = input("   一句话外观描述 (可留空) > ").strip()
        if appearance:
            profile.appearance = appearance
            
    except (KeyboardInterrupt, EOFError):
        print("\n使用默认玩家设定")
        profile.name = default_name
    
    return profile


def create_player_character(
    world_dir: Path,
    profile: PlayerProfile,
    runtime_dir: Optional[Path] = None
) -> Path:
    """
    在世界/运行时目录中创建玩家角色文件
    
    Args:
        world_dir: 世界数据目录
        profile: 玩家角色信息
        runtime_dir: 运行时目录（可选，用于保存玩家特定数据）
    
    Returns:
        创建的角色文件路径
    """
    # 构建玩家角色数据
    player_data = {
        "id": "user",
        "name": profile.name,
        "type": "player",
        "traits": {
            "gender": profile.gender,
            "appearance": profile.appearance,
            "background": profile.background
        },
        "is_player": True
    }
    
    # 保存到运行时目录（如果提供）
    if runtime_dir:
        player_file = runtime_dir / "player_character.json"
        player_file.parent.mkdir(parents=True, exist_ok=True)
        with open(player_file, "w", encoding="utf-8") as f:
            json.dump(player_data, f, ensure_ascii=False, indent=2)
        logger.info(f"玩家角色已保存: {player_file}")
        return player_file
    
    # 否则保存到世界目录
    characters_dir = world_dir / "characters"
    characters_dir.mkdir(parents=True, exist_ok=True)
    player_file = characters_dir / "character_user.json"
    
    with open(player_file, "w", encoding="utf-8") as f:
        json.dump(player_data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"玩家角色已保存: {player_file}")
    return player_file


def load_player_profile(runtime_dir: Path) -> Optional[PlayerProfile]:
    """
    从运行时目录加载玩家角色信息
    
    Args:
        runtime_dir: 运行时目录
    
    Returns:
        玩家角色信息，如果不存在返回 None
    """
    player_file = runtime_dir / "player_character.json"
    if not player_file.exists():
        return None
    
    try:
        with open(player_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            traits = data.get("traits", {})
            return PlayerProfile(
                name=data.get("name", "玩家"),
                gender=traits.get("gender", ""),
                appearance=traits.get("appearance", ""),
                background=traits.get("background", "")
            )
    except Exception as e:
        logger.warning(f"加载玩家角色失败: {e}")
        return None

