"""
游戏主入口 - CLI交互界面
运行完整的互动叙事游戏

使用新的 data/worlds/ 格式，通过 IlluminatiInitializer 初始化游戏
"""
import sys
from pathlib import Path
from typing import Optional
from config.settings import settings
from utils.logger import default_logger as logger


def print_header():
    """打印游戏标题"""
    print("\n" + "=" * 70)
    print("  🎭 Infinite Story - 无限故事机")
    print("  生成式互动叙事游戏")
    print("=" * 70)
    print()


def print_help():
    """打印帮助信息"""
    print("\n可用命令:")
    print("  /help    - 显示此帮助")
    print("  /status  - 查看游戏状态")
    print("  /save    - 保存游戏")
    print("  /quit    - 退出游戏")
    print("  其他输入 - 作为游戏中的行动\n")


def list_available_worlds() -> list:
    """列出所有可用的世界"""
    worlds_dir = settings.DATA_DIR / "worlds"
    if not worlds_dir.exists():
        return []
    
    worlds = []
    for world_dir in worlds_dir.iterdir():
        if world_dir.is_dir() and (world_dir / "world_setting.json").exists():
            worlds.append(world_dir.name)
    
    return worlds


def list_existing_runtimes(world_name: str) -> list:
    """列出指定世界的现有运行时目录"""
    runtime_dir = settings.DATA_DIR / "runtime"
    if not runtime_dir.exists():
        return []
    
    runtimes = []
    for rt_dir in runtime_dir.iterdir():
        if rt_dir.is_dir() and rt_dir.name.startswith(f"{world_name}_"):
            # 检查是否是有效的运行时目录
            if (rt_dir / "init_summary.json").exists():
                runtimes.append(rt_dir.name)
    
    return sorted(runtimes, reverse=True)  # 最新的在前面


def select_world() -> Optional[str]:
    """让用户选择世界"""
    worlds = list_available_worlds()
    
    if not worlds:
        print("❌ 未找到任何世界数据")
        print(f"\n请先运行创世组生成世界数据:")
        print(f"  python run_creator_god.py")
        return None
    
    print("📚 可用的世界:")
    for i, world in enumerate(worlds, 1):
        print(f"   {i}. {world}")
    
    print()
    
    while True:
        try:
            choice = input("请选择世界 (输入数字或名称) > ").strip()
            
            if not choice:
                continue
            
            # 尝试按数字选择
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(worlds):
                    return worlds[idx]
                print("❌ 无效的选择")
                continue
            
            # 尝试按名称选择
            if choice in worlds:
                return choice
            
            print("❌ 无效的世界名称")
            
        except KeyboardInterrupt:
            print("\n取消选择")
            return None


def select_or_create_runtime(world_name: str) -> Optional[Path]:
    """选择现有运行时或创建新的"""
    runtimes = list_existing_runtimes(world_name)
    
    print()
    print("🎮 运行选项:")
    print("   0. 开始新游戏 (初始化新的运行时)")
    
    if runtimes:
        print("   ─────────────────────────────")
        print("   继续现有游戏:")
        for i, rt in enumerate(runtimes[:5], 1):  # 只显示最近5个
            print(f"   {i}. {rt}")
    
    print()
    
    while True:
        try:
            choice = input("请选择 (输入数字) > ").strip()
            
            if not choice:
                continue
            
            if not choice.isdigit():
                print("❌ 请输入数字")
                continue
            
            idx = int(choice)
            
            if idx == 0:
                # 创建新的运行时
                return create_new_runtime(world_name)
            
            if runtimes and 1 <= idx <= len(runtimes[:5]):
                runtime_name = runtimes[idx - 1]
                return settings.DATA_DIR / "runtime" / runtime_name
            
            print("❌ 无效的选择")
            
        except KeyboardInterrupt:
            print("\n取消选择")
            return None


def create_new_runtime(world_name: str) -> Optional[Path]:
    """创建新的运行时（调用 IlluminatiInitializer）"""
    print()
    print("⏳ 正在初始化游戏世界...")
    print("   这可能需要几分钟（需要调用LLM生成初始剧情）...")
    print()
    
    try:
        from initial_Illuminati import IlluminatiInitializer
        
        initializer = IlluminatiInitializer(world_name)
        
        # 执行完整初始化流程
        print("   📍 步骤 1/3: 初始化世界状态...")
        initializer.init_world_state()
        
        print("   📍 步骤 2/3: 生成开场剧情...")
        initializer.init_plot_and_generate_opening()
        
        print("   📍 步骤 3/3: 生成环境氛围...")
        initializer.init_vibe_and_generate_atmosphere()
        
        # 保存初始化总结
        initializer._save_init_summary()
        
        # 保存 genesis.json 兼容文件（供 GameEngine 使用）
        genesis_path = initializer.runtime_dir / "genesis.json"
        import json
        with open(genesis_path, "w", encoding="utf-8") as f:
            json.dump(initializer.genesis_data, f, ensure_ascii=False, indent=2)
        
        print()
        print("✅ 游戏世界初始化完成!")
        print(f"   📁 运行时目录: {initializer.runtime_dir}")
        
        return initializer.runtime_dir
        
    except Exception as e:
        logger.error(f"❌ 初始化失败: {e}", exc_info=True)
        print(f"\n❌ 初始化失败: {e}")
        print(f"\n请查看日志: {settings.LOGS_DIR}/illuminati_init.log")
        return None


def run_game(runtime_dir: Path):
    """运行游戏"""
    from game_engine import GameEngine
    
    # 查找 genesis.json 文件
    genesis_path = runtime_dir / "genesis.json"
    
    if not genesis_path.exists():
        print("❌ 运行时目录缺少 genesis.json 文件")
        print("   请重新初始化游戏")
        return
    
    try:
        print()
        print("⏳ 正在加载游戏引擎...")
        
        game = GameEngine(genesis_path)
        
        print("✅ 游戏引擎加载完成!\n")
        
        # 开始游戏
        opening = game.start_game()
        print(opening)
        
        print_help()
        
        # 游戏主循环
        while True:
            try:
                # 获取用户输入
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
        
    except FileNotFoundError as e:
        logger.error(f"❌ 文件未找到: {e}")
        print(f"\n❌ 错误: {e}")
    except Exception as e:
        logger.error(f"❌ 游戏运行出错: {e}", exc_info=True)
        print(f"\n❌ 游戏出错: {e}")
        print("\n请查看日志文件:")
        print(f"  {settings.LOGS_DIR}/game_engine.log")


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


def main():
    """主函数"""
    print_header()
    
    # 选择世界
    world_name = select_world()
    if not world_name:
        return
    
    print(f"\n✅ 已选择世界: {world_name}")
    
    # 选择或创建运行时
    runtime_dir = select_or_create_runtime(world_name)
    if not runtime_dir:
        return
    
    # 运行游戏
    run_game(runtime_dir)


if __name__ == "__main__":
    main()
