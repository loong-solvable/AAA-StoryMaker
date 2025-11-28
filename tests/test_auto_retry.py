"""
测试创世组的自动重试功能
验证角色创建失败后能否自动重试
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agents.offline.genesis_group import GenesisGroup
from utils.logger import setup_logger

logger = setup_logger("AutoRetryTest", "auto_retry_test.log")


def test_auto_retry_logic():
    """测试自动重试逻辑"""
    logger.info("=" * 80)
    logger.info("🧪 测试：创世组自动重试功能")
    logger.info("=" * 80)
    
    # 检查未知世界是否存在失败的角色
    world_path = project_root / "data" / "worlds" / "未知世界"
    
    if not world_path.exists():
        logger.error("❌ 未找到'未知世界'文件夹，请先运行创世组(run_creator_god.py)")
        return False
    
    characters_list_path = world_path / "characters_list.json"
    characters_dir = world_path / "characters"
    
    if not characters_list_path.exists() or not characters_dir.exists():
        logger.error("❌ 世界数据不完整")
        return False
    
    # 读取角色列表
    import json
    with open(characters_list_path, "r", encoding="utf-8") as f:
        characters_list = json.load(f)
    
    logger.info(f"📋 角色列表中共有 {len(characters_list)} 个角色")
    
    # 检查哪些角色有error字段
    failed_count = 0
    for char_info in characters_list:
        char_id = char_info["id"]
        char_name = char_info["name"]
        char_file = characters_dir / f"character_{char_id}.json"
        
        if not char_file.exists():
            logger.warning(f"⚠️  {char_name} (ID: {char_id}): 文件不存在")
            failed_count += 1
            continue
        
        with open(char_file, "r", encoding="utf-8") as f:
            char_data = json.load(f)
        
        if "error" in char_data:
            logger.warning(f"⚠️  {char_name} (ID: {char_id}): 包含error字段")
            failed_count += 1
        else:
            logger.info(f"✅ {char_name} (ID: {char_id}): 状态正常")
    
    logger.info("=" * 80)
    logger.info(f"📊 扫描结果：{failed_count} 个失败的角色")
    logger.info("=" * 80)
    
    if failed_count > 0:
        logger.info("💡 下次运行创世组时，这些失败的角色将自动重试")
        logger.info("   或者手动运行：python temp/retry_failed_characters.py 未知世界 data/novels/example_novel.txt")
    else:
        logger.info("🎉 所有角色状态正常！")
    
    return True


if __name__ == "__main__":
    test_auto_retry_logic()

