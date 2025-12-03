"""
🎭 Infinite Story - 无限故事机
自动化完整流程入口 - 支持命令行参数控制各阶段

三阶段流程：
┌─────────────────────────────────────────────────────────────────┐
│  阶段1: 离线构建（创世组）                                        │
│  ├── 大中正: 角色普查                                            │
│  ├── Demiurge: 世界设定提取                                      │
│  └── 许劭: 角色档案制作                                          │
├─────────────────────────────────────────────────────────────────┤
│  阶段2: 在线初始化（光明会）                                      │
│  ├── WS: 世界状态初始化                                          │
│  ├── Plot: 开场剧本生成                                          │
│  └── Vibe: 初始氛围生成                                          │
├─────────────────────────────────────────────────────────────────┤
│  阶段3: 游戏运行                                                  │
│  └── GameEngine: 玩家交互循环                                    │
└─────────────────────────────────────────────────────────────────┘

使用方法：
    python run_game.py                      # 完整流程（交互模式）
    python run_game.py --skip-genesis       # 跳过创世组
    python run_game.py --world "江城市"     # 指定世界
    python run_game.py --novel my_novel.txt # 指定小说文件
    python run_game.py --auto               # 自动模式（无交互）
"""
import sys
import json
import argparse
from pathlib import Path
from typing import Optional, List, Dict, Any

from config.settings import settings
from utils.logger import setup_logger

logger = setup_logger("GameRunner", "game_runner.log")


def print_banner():
    """打印游戏横幅"""
    print()
    print("=" * 70)
    print("  🎭 Infinite Story - 无限故事机")
    print("  自动化完整流程入口")
    print("=" * 70)
    print()


def print_stage_header(stage_num: int, stage_name: str, status: str = "进行中"):
    """打印阶段标题"""
    print()
    print("─" * 70)
    print(f"  📍 阶段 {stage_num}: {stage_name}  [{status}]")
    print("─" * 70)
    print()


def print_help():
    """打印帮助信息"""
    print("\n可用命令:")
    print("  /help    - 显示此帮助")
    print("  /status  - 查看游戏状态")
    print("  /save    - 保存游戏")
    print("  /quit    - 退出游戏")
    print("  其他输入 - 作为游戏中的行动\n")


# ==========================================
# 阶段1: 创世组
# ==========================================

def get_available_worlds() -> List[str]:
    """获取所有可用的世界"""
    worlds_dir = settings.DATA_DIR / "worlds"
    if not worlds_dir.exists():
        return []
    
    worlds = []
    for world_dir in worlds_dir.iterdir():
        if world_dir.is_dir() and (world_dir / "world_setting.json").exists():
            worlds.append(world_dir.name)
    
    return sorted(worlds)


def get_available_novels() -> List[Path]:
    """获取所有可用的小说文件"""
    novels_dir = settings.DATA_DIR / "novels"
    if not novels_dir.exists():
        return []
    
    return list(novels_dir.glob("*.txt"))


def stage1_genesis(novel_filename: str = "example_novel.txt", skip: bool = False) -> Optional[Path]:
    """
    阶段1: 创世组离线构建
    
    Args:
        novel_filename: 小说文件名
        skip: 是否跳过此阶段
    
    Returns:
        世界数据目录路径
    """
    # 检查是否有现有世界数据
    worlds_dir = settings.DATA_DIR / "worlds"
    existing_worlds = get_available_worlds()
    
    if skip and existing_worlds:
        print_stage_header(1, "创世组离线构建", "⏭️ 跳过")
        # 使用最新的世界
        latest_world = existing_worlds[0]  # 已排序
        world_dir = worlds_dir / latest_world
        print(f"  📁 使用现有世界: {latest_world}")
        logger.info(f"跳过创世组，使用现有世界: {world_dir}")
        return world_dir
    
    print_stage_header(1, "创世组离线构建", "🔨 构建中")
    
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
        return None
    
    # 确保目录存在
    settings.ensure_directories()
    
    # 运行创世组
    try:
        from agents.offline.genesis_group import create_world
        
        logger.info(f"🚀 启动创世组，处理小说: {novel_filename}")
        print(f"  📖 正在处理小说: {novel_filename}")
        print()
        
        world_dir = create_world(novel_filename)
        
        print()
        print("  ✅ 世界构建成功！")
        print(f"  📁 世界数据: {world_dir}")
        print()
        print("  📖 生成的文件：")
        print(f"     - world_setting.json      # Demiurge 生成的世界观设定")
        print(f"     - characters_list.json    # 大中正 生成的角色列表")
        print(f"     - characters/             # 许劭 生成的角色详细档案")
        
        logger.info(f"✅ 阶段1完成: {world_dir}")
        return world_dir
        
    except FileNotFoundError as e:
        logger.error(f"❌ 文件未找到: {e}")
        print(f"  ❌ 运行失败：找不到小说文件")
        print(f"  请确保文件存在: {settings.NOVELS_DIR}/{novel_filename}")
        return None
        
    except Exception as e:
        logger.error(f"❌ 创世组运行失败: {e}", exc_info=True)
        print(f"  ❌ 运行失败: {e}")
        print(f"  请查看日志: {settings.LOGS_DIR}/genesis_group.log")
        return None


# ==========================================
# 阶段2: 光明会初始化
# ==========================================

def stage2_illuminati(world_name: str, player_profile: Optional[Dict[str, Any]] = None) -> Optional[Path]:
    """
    阶段2: 光明会初始化
    
    Args:
        world_name: 世界名称
        player_profile: 玩家设定
    
    Returns:
        运行时目录路径
    """
    from initial_Illuminati import IlluminatiInitializer
    
    print_stage_header(2, "光明会初始化", "🔨 初始化中")
    
    print("  📌 光明会三大 Agent:")
    print("     • WS (世界状态运行者) - 初始化世界状态")
    print("     • Plot (命运编织者) - 生成开场剧本")
    print("     • Vibe (氛围感受者) - 生成初始氛围")
    print()
    
    try:
        initializer = IlluminatiInitializer(world_name, player_profile=player_profile)
        runtime_dir = initializer.run()
        
        # 保存 genesis.json（供 GameEngine 使用）
        genesis_path = runtime_dir / "genesis.json"
        with open(genesis_path, "w", encoding="utf-8") as f:
            json.dump(initializer.genesis_data, f, ensure_ascii=False, indent=2)
        
        print()
        print("  ✅ 光明会初始化完成！")
        print(f"  📁 运行时目录: {runtime_dir}")
        
        logger.info(f"✅ 阶段2完成: {runtime_dir}")
        return runtime_dir
        
    except Exception as e:
        logger.error(f"❌ 光明会初始化失败: {e}", exc_info=True)
        print(f"  ❌ 初始化失败: {e}")
        print(f"  请查看日志: {settings.LOGS_DIR}/illuminati_init.log")
        return None


# ==========================================
# 阶段3: 游戏运行
# ==========================================

def stage3_game_run(runtime_dir: Path, auto_mode: bool = False):
    """
    阶段3: 游戏运行
    
    Args:
        runtime_dir: 运行时目录
        auto_mode: 是否自动模式（用于测试）
    """
    from game_engine import GameEngine
    
    print_stage_header(3, "游戏运行", "🎮 游戏中")
    
    genesis_path = runtime_dir / "genesis.json"
    
    if not genesis_path.exists():
        print("  ❌ 运行时目录缺少 genesis.json 文件")
        return
    
    try:
        print("  ⏳ 正在加载游戏引擎...")
        
        game = GameEngine(genesis_path)
        
        print("  ✅ 游戏引擎加载完成!")
        print()
        
        # 开始游戏
        opening = game.start_game()
        print(opening)
        
        if auto_mode:
            print()
            print("  ℹ️  自动模式：游戏初始化成功，跳过交互循环")
            print("  📊 游戏状态已就绪，可通过 GameEngine 实例进行操作")
            game.save_game("auto_init")
            return
        
        print_help()
        
        # 游戏主循环
        game_loop(game)
        
    except Exception as e:
        logger.error(f"❌ 游戏运行出错: {e}", exc_info=True)
        print(f"  ❌ 游戏出错: {e}")
        print(f"  请查看日志: {settings.LOGS_DIR}/game_engine.log")


def game_loop(game):
    """游戏主循环"""
    while True:
        try:
            user_input = input("\n👤 你的行动 > ").strip()
            
            if not user_input:
                continue
            
            # 处理命令
            if user_input.startswith("/"):
                command = user_input.lower()
                
                if command == "/help":
                    print_help()
                elif command == "/status":
                    print_game_status(game)
                elif command == "/save":
                    game.save_game("manual_save")
                    print("✅ 游戏已保存")
                elif command == "/quit":
                    print("\n👋 感谢游玩！游戏已自动保存。")
                    game.save_game("autosave")
                    break
                else:
                    print(f"❌ 未知命令: {command}")
                    print("   输入 /help 查看可用命令")
                
                continue
            
            # 处理游戏回合
            print("\n⏳ 处理中...")
            result = game.process_turn(user_input)
            
            if result["success"]:
                print(result["text"])
            else:
                print(f"\n❌ {result.get('error', '未知错误')}")
                print("请重新输入\n")
            
        except KeyboardInterrupt:
            print("\n\n⚠️  检测到Ctrl+C")
            confirm = input("确定要退出吗? (y/n) > ").lower()
            if confirm == 'y':
                print("\n👋 游戏已自动保存，再见!")
                game.save_game("autosave")
                break
        except EOFError:
            print("\n\n👋 游戏已自动保存，再见!")
            game.save_game("autosave")
            break


def print_game_status(game):
    """打印游戏状态"""
    status = game.get_game_status()
    
    print("\n" + "=" * 70)
    print("  📊 游戏状态")
    print("=" * 70)
    print(f"  回合数: {status['turn']}")
    print(f"  时间: {status['time']}")
    print(f"  位置: {status['location']}")
    print(f"\n  剧情进度: {status['plot_progress']['current_stage']}")
    print(f"  场景数: {status['plot_progress']['scene_count']}")
    print(f"  已完成节点: {len(status['plot_progress']['completed_nodes'])}/{status['plot_progress']['total_nodes']}")
    
    print(f"\n  在场角色:")
    present_chars = game.os.world_context.present_characters
    for char_id in present_chars:
        if char_id in status['npcs']:
            npc_state = status['npcs'][char_id]
            print(f"    - {npc_state['name']} (心情: {npc_state['mood']})")
    
    print("=" * 70 + "\n")


# ==========================================
# 主函数
# ==========================================

def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description="🎭 Infinite Story - 无限故事机 自动化完整流程入口",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run_game.py                          # 完整流程（交互模式）
  python run_game.py --skip-genesis           # 跳过创世组（使用现有世界）
  python run_game.py --world "江城市"         # 指定世界名称
  python run_game.py --novel my_novel.txt     # 使用指定小说文件
  python run_game.py --auto                   # 自动模式（无交互，用于测试）
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
    parser.add_argument(
        "--auto",
        action="store_true",
        help="自动模式（无交互，仅初始化并验证）"
    )
    parser.add_argument(
        "--player-name",
        type=str,
        default=None,
        help="玩家角色名称"
    )
    
    args = parser.parse_args()
    
    # 打印横幅
    print_banner()
    
    logger.info("=" * 60)
    logger.info("🎮 启动 Infinite Story 完整流程")
    logger.info("=" * 60)
    
    # 验证配置
    try:
        settings.validate()
    except ValueError as e:
        print(f"❌ 配置验证失败: {e}")
        print()
        print("请按以下步骤配置：")
        print("1. 复制 .env.example 为 .env")
        print("2. 编辑 .env 文件，填入你的API密钥")
        print("3. 保存后重新运行本脚本")
        return
    
    settings.ensure_directories()
    
    # ========================================
    # 阶段1: 创世组离线构建
    # ========================================
    world_dir = None
    
    if args.world:
        # 使用指定的世界
        world_dir = settings.DATA_DIR / "worlds" / args.world
        if not world_dir.exists():
            print(f"  ❌ 指定的世界不存在: {args.world}")
            print()
            print("  可用的世界:")
            for w in get_available_worlds():
                print(f"     - {w}")
            return
        print_stage_header(1, "创世组离线构建", "⏭️ 跳过")
        print(f"  📁 使用指定世界: {args.world}")
    else:
        world_dir = stage1_genesis(
            novel_filename=args.novel,
            skip=args.skip_genesis
        )
        
        if not world_dir:
            print()
            print("❌ 阶段1失败，流程终止")
            return
    
    world_name = world_dir.name
    
    # ========================================
    # 阶段2: 光明会初始化
    # ========================================
    player_profile = {}
    if args.player_name:
        player_profile["name"] = args.player_name
    
    runtime_dir = stage2_illuminati(world_name, player_profile=player_profile if player_profile else None)
    
    if not runtime_dir:
        print()
        print("❌ 阶段2失败，流程终止")
        return
    
    # ========================================
    # 阶段3: 游戏运行
    # ========================================
    stage3_game_run(runtime_dir, auto_mode=args.auto)
    
    # 总结
    print()
    print("=" * 70)
    print("  📊 流程总结")
    print("=" * 70)
    print()
    print("  ✅ 阶段1 - 创世组离线构建: 完成")
    print("  ✅ 阶段2 - 光明会初始化: 完成")
    print("  ✅ 阶段3 - 游戏运行: 完成")
    print()
    print(f"  📁 世界数据: {world_dir}")
    print(f"  📁 运行时数据: {runtime_dir}")
    print(f"  📋 运行日志: {settings.LOGS_DIR}/game_runner.log")
    print()
    print("=" * 70)
    print("  🎉 感谢使用 Infinite Story!")
    print("=" * 70)
    print()
    
    logger.info("游戏流程结束")


if __name__ == "__main__":
    main()
