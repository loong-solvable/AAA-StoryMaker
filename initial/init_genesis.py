"""
Genesis数据加载模块
负责加载和验证世界数据包
"""
import json
from pathlib import Path
from typing import Dict, Any
from utils.logger import setup_logger

logger = setup_logger("InitGenesis")


def load_genesis_data(genesis_path: Path) -> Dict[str, Any]:
    """
    加载Genesis世界数据
    
    Args:
        genesis_path: Genesis.json文件路径
    
    Returns:
        Genesis数据字典
    
    Raises:
        FileNotFoundError: 文件不存在
        json.JSONDecodeError: JSON格式错误
    """
    logger.info(f"📖 开始加载Genesis数据: {genesis_path}")
    
    if not genesis_path.exists():
        logger.error(f"❌ Genesis文件不存在: {genesis_path}")
        raise FileNotFoundError(f"Genesis文件不存在: {genesis_path}")
    
    try:
        with open(genesis_path, "r", encoding="utf-8") as f:
            genesis_data = json.load(f)
        
        # 验证必要字段
        _validate_genesis_data(genesis_data)
        
        logger.info("✅ Genesis数据加载成功")
        logger.info(f"   - 世界: {genesis_data.get('world', {}).get('title', '未知')}")
        logger.info(f"   - 角色数: {len(genesis_data.get('characters', []))}")
        logger.info(f"   - 地点数: {len(genesis_data.get('locations', []))}")
        logger.info(f"   - 剧情线索: {len(genesis_data.get('plot_hints', []))}")
        
        return genesis_data
    
    except json.JSONDecodeError as e:
        logger.error(f"❌ Genesis JSON解析失败: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ 加载Genesis数据失败: {e}")
        raise


def _validate_genesis_data(genesis_data: Dict[str, Any]) -> None:
    """
    验证Genesis数据结构
    
    Args:
        genesis_data: Genesis数据
    
    Raises:
        ValueError: 数据结构不完整
    """
    required_keys = ["world", "characters", "locations"]
    missing_keys = [key for key in required_keys if key not in genesis_data]
    
    if missing_keys:
        raise ValueError(f"Genesis数据缺少必要字段: {', '.join(missing_keys)}")
    
    if not genesis_data.get("characters"):
        logger.warning("⚠️  Genesis中没有角色数据")
    
    if not genesis_data.get("locations"):
        logger.warning("⚠️  Genesis中没有地点数据")

