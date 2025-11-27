"""
世界数据加载模块（新格式）
负责加载拆分后的世界数据（world_setting.json + characters_list.json + characters/*.json）
"""
import json
from pathlib import Path
from typing import Dict, Any, List
from utils.logger import setup_logger

logger = setup_logger("InitWorld")


def load_world_data(world_dir: Path) -> Dict[str, Any]:
    """
    加载完整的世界数据（从拆分的三份文件中）
    
    Args:
        world_dir: 世界文件夹路径（如 data/worlds/修仙世界/）
    
    Returns:
        完整的世界数据字典，包含：
        {
            "world_setting": {...},
            "characters_list": [...],
            "characters": {char_id: char_data, ...}
        }
    
    Raises:
        FileNotFoundError: 必要文件不存在
        json.JSONDecodeError: JSON格式错误
    """
    logger.info(f"📖 开始加载世界数据: {world_dir}")
    
    if not world_dir.exists():
        logger.error(f"❌ 世界文件夹不存在: {world_dir}")
        raise FileNotFoundError(f"世界文件夹不存在: {world_dir}")
    
    world_data = {}
    
    # 1. 加载世界设定
    world_setting_path = world_dir / "world_setting.json"
    world_data["world_setting"] = _load_json_file(world_setting_path)
    logger.info("✅ 已加载 world_setting.json")
    
    # 2. 加载角色列表
    characters_list_path = world_dir / "characters_list.json"
    world_data["characters_list"] = _load_json_file(characters_list_path)
    logger.info(f"✅ 已加载 characters_list.json ({len(world_data['characters_list'])}个角色)")
    
    # 3. 加载所有角色档案
    characters_dir = world_dir / "characters"
    world_data["characters"] = _load_all_character_files(characters_dir)
    logger.info(f"✅ 已加载 {len(world_data['characters'])}个角色档案")
    
    logger.info("✅ 世界数据加载完成")
    logger.info(f"   - 世界: {world_data['world_setting'].get('meta', {}).get('title', '未知')}")
    logger.info(f"   - 角色: {len(world_data['characters'])}个")
    logger.info(f"   - 地点: {len(world_data['world_setting'].get('locations', []))}个")
    
    return world_data


def load_world_setting(world_dir: Path) -> Dict[str, Any]:
    """
    仅加载世界设定
    
    Args:
        world_dir: 世界文件夹路径
    
    Returns:
        world_setting.json 数据
    """
    logger.info(f"📖 加载世界设定: {world_dir}")
    
    world_setting_path = world_dir / "world_setting.json"
    world_setting = _load_json_file(world_setting_path)
    
    logger.info("✅ 世界设定加载完成")
    return world_setting


def load_characters_list(world_dir: Path) -> List[Dict[str, Any]]:
    """
    仅加载角色列表
    
    Args:
        world_dir: 世界文件夹路径
    
    Returns:
        characters_list.json 数据
    """
    logger.info(f"📖 加载角色列表: {world_dir}")
    
    characters_list_path = world_dir / "characters_list.json"
    characters_list = _load_json_file(characters_list_path)
    
    logger.info(f"✅ 角色列表加载完成 ({len(characters_list)}个)")
    return characters_list


def load_character_details(world_dir: Path, character_id: str) -> Dict[str, Any]:
    """
    加载单个角色的详细档案
    
    Args:
        world_dir: 世界文件夹路径
        character_id: 角色ID
    
    Returns:
        角色档案数据
    """
    logger.info(f"📖 加载角色档案: {character_id}")
    
    char_file = world_dir / "characters" / f"character_{character_id}.json"
    char_data = _load_json_file(char_file)
    
    logger.info(f"✅ 角色档案加载完成: {char_data.get('name', '未知')}")
    return char_data


def load_all_characters(world_dir: Path) -> Dict[str, Dict[str, Any]]:
    """
    加载所有角色的详细档案
    
    Args:
        world_dir: 世界文件夹路径
    
    Returns:
        {character_id: character_data, ...}
    """
    logger.info(f"📖 加载所有角色档案: {world_dir}")
    
    characters_dir = world_dir / "characters"
    characters = _load_all_character_files(characters_dir)
    
    logger.info(f"✅ 所有角色档案加载完成 ({len(characters)}个)")
    return characters


def _load_json_file(file_path: Path) -> Any:
    """
    加载JSON文件的内部辅助函数
    
    Args:
        file_path: JSON文件路径
    
    Returns:
        解析后的数据
    
    Raises:
        FileNotFoundError: 文件不存在
        json.JSONDecodeError: JSON格式错误
    """
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON解析失败: {file_path}")
        raise


def _load_all_character_files(characters_dir: Path) -> Dict[str, Dict[str, Any]]:
    """
    加载characters目录下的所有角色文件
    
    Args:
        characters_dir: characters文件夹路径
    
    Returns:
        {character_id: character_data, ...}
    """
    if not characters_dir.exists():
        logger.warning(f"⚠️  角色文件夹不存在: {characters_dir}")
        return {}
    
    characters = {}
    
    for char_file in characters_dir.glob("character_*.json"):
        try:
            with open(char_file, "r", encoding="utf-8") as f:
                char_data = json.load(f)
            
            char_id = char_data.get("id")
            if char_id:
                characters[char_id] = char_data
            else:
                logger.warning(f"⚠️  角色文件缺少ID字段: {char_file.name}")
        
        except Exception as e:
            logger.warning(f"⚠️  加载角色文件失败 {char_file.name}: {e}")
            continue
    
    return characters


def list_available_worlds() -> List[str]:
    """
    列出data/worlds/目录下所有可用的世界
    
    Returns:
        世界名称列表
    """
    from config.settings import settings
    
    worlds_dir = settings.DATA_DIR / "worlds"
    
    if not worlds_dir.exists():
        logger.warning("⚠️  worlds目录不存在")
        return []
    
    worlds = []
    for world_dir in worlds_dir.iterdir():
        if world_dir.is_dir():
            # 检查是否包含必要文件
            if (world_dir / "world_setting.json").exists():
                worlds.append(world_dir.name)
    
    logger.info(f"📚 发现 {len(worlds)} 个世界: {worlds}")
    return worlds

