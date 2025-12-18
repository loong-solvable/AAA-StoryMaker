"""
统一文件命名工具模块

提供统一的文件命名规则，确保整个项目中文件命名的一致性。
"""
from typing import Optional


def format_scene_id(scene_num: int) -> str:
    """
    格式化场景ID为3位数字字符串
    
    Args:
        scene_num: 场景编号（从1开始）
    
    Returns:
        格式化后的场景ID，如 "001", "002", "010"
    
    Examples:
        >>> format_scene_id(1)
        '001'
        >>> format_scene_id(12)
        '012'
        >>> format_scene_id(123)
        '123'
    """
    return f"{scene_num:03d}"


def format_plot_archive_name(file_type: str, scene_num: int) -> str:
    """
    格式化主剧本归档文件名
    
    Args:
        file_type: 文件类型，如 "script", "scene"
        scene_num: 场景编号
    
    Returns:
        归档文件名，如 "script_001.json", "scene_001.json"
    
    Examples:
        >>> format_plot_archive_name("script", 1)
        'script_001.json'
        >>> format_plot_archive_name("scene", 12)
        'scene_012.json'
    """
    scene_id = format_scene_id(scene_num)
    return f"{file_type}_{scene_id}.json"


def format_actor_script_archive_name(npc_id: str, scene_num: int) -> str:
    """
    格式化角色小剧本归档文件名
    
    Args:
        npc_id: 角色ID，如 "npc_003"
        scene_num: 场景编号
    
    Returns:
        归档文件名，如 "npc_003_scene_001.json"
    
    Examples:
        >>> format_actor_script_archive_name("npc_003", 1)
        'npc_003_scene_001.json'
        >>> format_actor_script_archive_name("npc_001", 12)
        'npc_001_scene_012.json'
    """
    scene_id = format_scene_id(scene_num)
    return f"{npc_id}_scene_{scene_id}.json"


def format_actor_current_script_name(npc_id: str) -> str:
    """
    格式化角色当前小剧本文件名
    
    Args:
        npc_id: 角色ID
    
    Returns:
        文件名，如 "npc_003.json"
    
    Examples:
        >>> format_actor_current_script_name("npc_003")
        'npc_003.json'
    """
    return f"{npc_id}.json"


def format_actor_history_name(npc_id: str) -> str:
    """
    格式化角色演绎历史文件名
    
    Args:
        npc_id: 角色ID
    
    Returns:
        文件名，如 "npc_003.json"
    
    Examples:
        >>> format_actor_history_name("npc_003")
        'npc_003.json'
    """
    return f"{npc_id}.json"


def format_scene_memory_archive_name(scene_num: int) -> str:
    """
    格式化场景记忆归档文件名
    
    Args:
        scene_num: 场景编号
    
    Returns:
        归档文件名，如 "scene_001.json"
    
    Examples:
        >>> format_scene_memory_archive_name(1)
        'scene_001.json'
        >>> format_scene_memory_archive_name(12)
        'scene_012.json'
    """
    scene_id = format_scene_id(scene_num)
    return f"scene_{scene_id}.json"


def parse_scene_id_from_filename(filename: str) -> Optional[int]:
    """
    从文件名中解析场景ID
    
    Args:
        filename: 文件名，如 "script_001.json", "npc_003_scene_002.json"
    
    Returns:
        场景编号，如果解析失败返回 None
    
    Examples:
        >>> parse_scene_id_from_filename("script_001.json")
        1
        >>> parse_scene_id_from_filename("npc_003_scene_002.json")
        2
        >>> parse_scene_id_from_filename("invalid.json")
        None
    """
    try:
        # 尝试匹配 scene_XXX 格式
        if "_scene_" in filename:
            parts = filename.split("_scene_")
            if len(parts) == 2:
                scene_part = parts[1].replace(".json", "")
                return int(scene_part)
        
        # 尝试匹配 filetype_XXX 格式
        if "_" in filename:
            parts = filename.split("_")
            if len(parts) >= 2:
                last_part = parts[-1].replace(".json", "")
                if last_part.isdigit():
                    return int(last_part)
        
        return None
    except (ValueError, IndexError):
        return None






