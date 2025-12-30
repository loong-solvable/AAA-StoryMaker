import sys
from pathlib import Path
import shutil

# 确保项目根目录在路径中
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 导入现有的清理工具类（它自带保护逻辑）
from utils.cleanup_runtime import RuntimeCleaner
from utils.logger import setup_logger

logger = setup_logger("CleanupRuntime", "cleanup.log")

def main():
    print("=" * 50)
    print("🧹 Infinite Story - 运行时数据清理工具")
    print("=" * 50)
    print("目标: 清理运行时临时文件，【保留】所有世界设定数据。")
    print("-" * 50)

    cleaner = RuntimeCleaner()

    # 1. 清理 data/runtime (游戏过程数据)
    print("📦 正在清理运行时目录 (data/runtime/)...")
    rt_count = cleaner.cleanup_runtime_dirs()
    print(f"   ✅ 已清理 {rt_count} 个运行时实例目录")

    # 2. 清理临时生成的 NPC 脚本和提示词
    # 注意：RuntimeCleaner 内部已排除 npc_agent.py 和 __init__.py
    print("🎭 正在清理临时生成的角色脚本...")
    char_count = cleaner.cleanup_all_character_files()
    print(f"   ✅ 已清理 {char_count} 个临时角色文件 (npc_agent.py 已受保护)")

    # 3. 清理存档文件
    saves_dir = PROJECT_ROOT / "data" / "saves"
    if saves_dir.exists():
        print("💾 正在清理游戏存档 (data/saves/)...")
        deleted_saves = 0
        for item in saves_dir.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
            deleted_saves += 1
        print(f"   ✅ 已清理 {deleted_saves} 个存档文件")

    # 4. 验证世界数据完整性
    worlds_dir = PROJECT_ROOT / "data" / "worlds"
    world_list = [d for d in worlds_dir.iterdir() if d.is_dir()]
    print("-" * 50)
    print(f"📊 清理完成！")
    print(f"🛡️  受保护的世界数据: {len(world_list)} 个世界文件夹已保留")
    print(f"📍 世界路径: {worlds_dir}")
    print("=" * 50)

if __name__ == "__main__":
    main()

