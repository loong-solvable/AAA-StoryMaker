"""
🎭 Infinite Story - 无限故事机
游戏全流程运行入口

游戏流程分为三大阶段：
┌─────────────────────────────────────────────────────────────────┐
│  阶段1: 离线构建（创世组）                    [✅ 已完成]         │
│  ├── 大中正: 角色普查                                            │
│  ├── Demiurge: 世界设定提取                                      │
│  └── 许劭: 角色档案制作                                          │
├─────────────────────────────────────────────────────────────────┤
│  阶段2: 在线初始化（光明会）                  [🔜 待开发]         │
│  ├── 初始化 OS（信息中枢）                                       │
│  ├── 初始化 Logic（逻辑审查官）                                  │
│  ├── 初始化 WS（世界状态运行者）                                 │
│  ├── 初始化 Plot（命运编织者）                                   │
│  ├── 初始化 Vibe（氛围感受者）                                   │
│  └── 初始化 NPC Agents（演员组）                                 │
├─────────────────────────────────────────────────────────────────┤
│  阶段3: 游戏运行（交互循环）                  [🔜 待开发]         │
│  └── 玩家输入 → Logic审查 → Plot编剧 → OS分发 → NPC演绎 → 输出   │
└─────────────────────────────────────────────────────────────────┘

使用方法：
    python run_game.py [选项]
    
    选项：
        --skip-genesis    跳过创世组阶段（如果世界数据已存在）
        --world <名称>    指定要使用的世界名称
        --novel <文件名>  指定小说文件名（默认: example_novel.txt）
"""
import sys
import argparse
from pathlib import Path
from config.settings import settings
from utils.logger import setup_logger

logger = setup_logger("GameRunner", "game_runner.log")


def print_banner():
    """打印游戏横幅"""
    print()
    print("=" * 70)
    print("  🎭 Infinite Story - 无限故事机")
    print("  基于LangChain的生成式互动叙事游戏引擎")
    print("=" * 70)
    print()


def print_stage_header(stage_num: int, stage_name: str, status: str):
    """打印阶段标题"""
    print()
    print("─" * 70)
    print(f"  📍 阶段 {stage_num}: {stage_name}  [{status}]")
    print("─" * 70)
    print()


def stage1_genesis(novel_filename: str = "example_novel.txt", skip: bool = False) -> Path:
    """
    阶段1: 创世组离线构建
    
    创世组成员：
    - 大中正: 角色普查与重要性评估
    - Demiurge: 世界规则与背景提取
    - 许劭: 角色档案与角色卡制作
    
    Args:
        novel_filename: 小说文件名
        skip: 是否跳过此阶段
    
    Returns:
        世界数据目录路径
    """
    print_stage_header(1, "创世组离线构建", "✅ 已完成")
    
    # 检查是否有现有世界数据
    worlds_dir = settings.DATA_DIR / "worlds"
    existing_worlds = list(worlds_dir.glob("*/world_setting.json")) if worlds_dir.exists() else []
    
    if skip and existing_worlds:
        # 使用最新的世界
        latest_world = max(existing_worlds, key=lambda p: p.stat().st_mtime)
        world_dir = latest_world.parent
        print(f"  ⏭️  跳过创世组阶段")
        print(f"  📁 使用现有世界: {world_dir.name}")
        logger.info(f"跳过创世组，使用现有世界: {world_dir}")
        return world_dir
    
    print("  📌 创世组三阶段构建流程:")
    print("     1️⃣  大中正 - 角色普查，识别所有角色并评估重要性")
    print("     2️⃣  Demiurge - 提取世界观设定（物理法则、社会规则、地点）")
    print("     3️⃣  许劭 - 为每个角色创建详细档案（角色卡）")
    print()
    
    # 验证配置
    try:
        logger.info("🔍 正在验证配置...")
        settings.validate()
        logger.info("✅ 配置验证通过")
    except ValueError as e:
        logger.error(str(e))
        print("  ❌ 配置验证失败！")
        print()
        print("  请按以下步骤配置：")
        print("  1. 复制 .env.example 为 .env")
        print("  2. 编辑 .env 文件，填入你的API密钥")
        print("  3. 保存后重新运行本脚本")
        sys.exit(1)
    
    # 确保目录存在
    settings.ensure_directories()
    
    # 运行创世组
    try:
        from agents.offline.genesis_group import create_world
        
        logger.info(f"🚀 启动创世组，处理小说: {novel_filename}")
        world_dir = create_world(novel_filename)
        
        print()
        print("  ✅ 世界构建成功！")
        print(f"  📁 世界数据: {world_dir}")
        print()
        print("  📖 生成的文件：")
        print(f"     - world_setting.json      # Demiurge 生成的世界观设定")
        print(f"     - characters_list.json    # 大中正 生成的角色列表")
        print(f"     - characters/             # 许劭 生成的角色详细档案")
        print()
        
        logger.info(f"✅ 阶段1完成: {world_dir}")
        return world_dir
        
    except FileNotFoundError as e:
        logger.error(f"❌ 文件未找到: {e}")
        print(f"  ❌ 运行失败：找不到小说文件")
        print(f"  请确保文件存在: {settings.NOVELS_DIR}/{novel_filename}")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"❌ 创世组运行失败: {e}", exc_info=True)
        print(f"  ❌ 运行失败: {e}")
        print(f"  请查看日志: {settings.LOGS_DIR}/genesis_group.log")
        sys.exit(1)


def stage2_initialize(world_dir: Path):
    """
    阶段2: 在线初始化（光明会）
    
    初始化内容：
    - OS（信息中枢）: 剧本拆分与分发
    - Logic（逻辑审查官）: 输入输出审核
    - WS（世界状态运行者）: 世界仿真
    - Plot（命运编织者）: 剧情编织
    - Vibe（氛围感受者）: 环境渲染
    - NPC Agents（演员组）: 角色扮演
    
    Args:
        world_dir: 世界数据目录
    """
    print_stage_header(2, "在线初始化（光明会）", "🔜 待开发")
    
    print("  📋 待初始化的组件：")
    print()
    print("  第一层 - 安检与中枢")
    print("     • OS（信息中枢）: 剧本拆分、消息分发、状态管理")
    print("     • Logic（逻辑审查官）: 输入验证、输出审查、幻觉检测")
    print()
    print("  第二层 - 光明会（逻辑大脑）")
    print("     • WS（世界状态运行者）: 时间流逝、NPC状态、离屏事件")
    print("     • Plot（命运编织者）: 剧情走向、高潮控制、情绪指导")
    print("     • Vibe（氛围感受者）: 环境描写、感官细节、氛围渲染")
    print()
    print("  第三层 - 演员组（表现层）")
    print("     • NPC Agents: 根据角色卡扮演各个角色")
    print()
    print("  ⏳ 此阶段尚未实现，请运行 run_initial.py（待开发）")
    print()
    
    logger.info("阶段2尚未实现")


def stage3_game_loop(world_dir: Path):
    """
    阶段3: 游戏运行（交互循环）
    
    游戏回合流程：
    1. 接收用户输入
    2. Logic 审查输入合法性
    3. Plot 编织新剧本
    4. OS 拆分剧本并分发
    5. NPC Agents 演绎角色
    6. 整合输出展示给玩家
    
    Args:
        world_dir: 世界数据目录
    """
    print_stage_header(3, "游戏运行（交互循环）", "🔜 待开发")
    
    print("  🎮 游戏回合流程：")
    print()
    print("     用户输入")
    print("        │")
    print("        ▼")
    print("     Logic 审查 ─────→ 拒绝非法输入")
    print("        │")
    print("        ▼")
    print("     Plot 编剧 ←───── WS + Vibe 提供上下文")
    print("        │")
    print("        ▼")
    print("     OS 拆分剧本")
    print("        │")
    print("        ├─→ NPC-A 演绎")
    print("        ├─→ NPC-B 演绎")
    print("        └─→ ...")
    print("              │")
    print("              ▼")
    print("     OS 整合输出 → 展示给玩家")
    print()
    print("  ⏳ 此阶段尚未实现，请运行 play_game.py（待开发）")
    print()
    
    logger.info("阶段3尚未实现")


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description="🎭 Infinite Story - 无限故事机 游戏全流程运行入口",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run_game.py                          # 完整流程（从创世组开始）
  python run_game.py --skip-genesis           # 跳过创世组（使用现有世界）
  python run_game.py --novel my_novel.txt     # 使用指定小说文件
        """
    )
    parser.add_argument(
        "--skip-genesis", 
        action="store_true",
        help="跳过创世组阶段（如果世界数据已存在）"
    )
    parser.add_argument(
        "--world",
        type=str,
        default=None,
        help="指定要使用的世界名称"
    )
    parser.add_argument(
        "--novel",
        type=str,
        default="example_novel.txt",
        help="指定小说文件名（默认: example_novel.txt）"
    )
    
    args = parser.parse_args()
    
    # 打印横幅
    print_banner()
    
    logger.info("=" * 60)
    logger.info("🎮 启动 Infinite Story 游戏流程")
    logger.info("=" * 60)
    
    # ========================================
    # 阶段1: 创世组离线构建 [✅ 已完成]
    # ========================================
    if args.world:
        # 使用指定的世界
        world_dir = settings.DATA_DIR / "worlds" / args.world
        if not world_dir.exists():
            print(f"  ❌ 指定的世界不存在: {args.world}")
            print(f"  可用的世界:")
            worlds_dir = settings.DATA_DIR / "worlds"
            if worlds_dir.exists():
                for w in worlds_dir.iterdir():
                    if w.is_dir() and (w / "world_setting.json").exists():
                        print(f"     - {w.name}")
            sys.exit(1)
        print_stage_header(1, "创世组离线构建", "⏭️ 跳过")
        print(f"  📁 使用指定世界: {args.world}")
    else:
        world_dir = stage1_genesis(
            novel_filename=args.novel,
            skip=args.skip_genesis
        )
    
    # ========================================
    # 阶段2: 在线初始化 [🔜 待开发]
    # ========================================
    stage2_initialize(world_dir)
    
    # ========================================
    # 阶段3: 游戏运行 [🔜 待开发]
    # ========================================
    stage3_game_loop(world_dir)
    
    # 总结
    print("=" * 70)
    print("  📊 流程总结")
    print("=" * 70)
    print()
    print("  ✅ 阶段1 - 创世组离线构建: 完成")
    print("  🔜 阶段2 - 在线初始化: 待开发 (run_initial.py)")
    print("  🔜 阶段3 - 游戏运行: 待开发 (play_game.py)")
    print()
    print(f"  📁 世界数据位置: {world_dir}")
    print(f"  📋 运行日志: {settings.LOGS_DIR}/game_runner.log")
    print()
    print("=" * 70)
    print("  🎉 感谢使用 Infinite Story!")
    print("=" * 70)
    print()
    
    logger.info("游戏流程结束")


if __name__ == "__main__":
    main()

