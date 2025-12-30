#!/usr/bin/env python3
"""
🎭 Infinite Story - 无限故事机
玩家入口 - 简洁、沉浸的游戏体验

使用方法:
    python play.py

特性:
- 极简界面，隐藏技术细节
- Screen Agent 电影质感渲染
- 智能行动建议
- 自动断点续传
"""

import sys
from pathlib import Path
from typing import Optional, List

# 确保项目根目录在路径中
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import settings
from cli.world_manager import WorldManager, WorldInfo, RuntimeInfo
from cli.session_factory import SessionFactory
from cli.player_profile import prompt_player_profile, PlayerProfile
from utils.player_log_filter import setup_player_logging
from utils.exception_handler import handle_exception
from utils.progress_tracker import ProgressTracker


def print_banner():
    """打印游戏横幅"""
    print()
    print("=" * 64)
    print()
    print("              I N F I N I T E   S T O R Y")
    print("                    [Infinite Story]")
    print()
    print("              ---------------------------------")
    print("              AI-Powered Interactive Narrative")
    print()
    print("=" * 64)
    print()


def print_main_menu():
    """打印主菜单"""
    print("  Menu:")
    print()
    print("    [1] New Story")
    print("    [2] Continue Story")
    print("    [0] Exit")
    print()


def print_help():
    """打印帮助信息"""
    print("\n可用命令:")
    print("  /help    - 显示此帮助")
    print("  /status  - 查看游戏状态")
    print("  /save    - 保存游戏")
    print("  /quit    - 退出游戏")
    print("  其他输入 - 作为游戏中的行动\n")


def select_world(world_manager: WorldManager) -> Optional[WorldInfo]:
    """让用户选择世界"""
    worlds = world_manager.list_available_worlds()
    
    if not worlds:
        print("[ERROR] No world data found")
        print()
        print("Please run Genesis Group first:")
        print("  python dev.py --stage genesis --novel <novel_file>")
        return None
    
    print("-" * 64)
    print("  Available Story Worlds")
    print("-" * 64)
    print()
    
    for i, world in enumerate(worlds, 1):
        print(f"  [{i}] {world.title or world.name}")
        if world.genre:
            print(f"      Genre: {world.genre} | Characters: {world.character_count}")
        if world.description:
            print(f"      \"{world.description[:50]}...\"")
        print()
    
    print("  [0] <- Back to main menu")
    print()
    
    while True:
        try:
            choice = input("  Select world > ").strip()
            
            if choice == "0":
                return None
            
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(worlds):
                    return worlds[idx]
            
            print("  [ERROR] Invalid choice, please try again")
            
        except (KeyboardInterrupt, EOFError):
            print("\n  Cancelled")
            return None


def select_runtime(world_manager: WorldManager, world_name: str) -> Optional[RuntimeInfo]:
    """让用户选择存档"""
    runtimes = world_manager.list_runtimes(world_name)
    
    print()
    print("-" * 64)
    print(f"  {world_name} - Save Files")
    print("-" * 64)
    print()
    print("  [0] * New Game")
    
    if runtimes:
        print()
        print("  " + "-" * 60)
        print("  Continue from save:")
        print()
        
        for i, rt in enumerate(runtimes[:5], 1):  # 只显示最近5个
            time_str = rt.initialized_at[:16].replace("T", " ") if "T" in rt.initialized_at else rt.initialized_at
            print(f"  [{i}] {rt.name}")
            print(f"      Scene: {rt.current_scene_id} | Time: {time_str}")
            print()
    
    while True:
        try:
            choice = input("  Select > ").strip()
            
            if choice == "0":
                return None  # 新游戏
            
            if choice.isdigit() and runtimes:
                idx = int(choice) - 1
                if 0 <= idx < len(runtimes[:5]):
                    return runtimes[idx]
            
            print("  [ERROR] Invalid choice")
            
        except (KeyboardInterrupt, EOFError):
            print("\n  Cancelled")
            return None


def initialize_new_game(world_name: str, player_profile: PlayerProfile) -> Optional[Path]:
    """初始化新游戏"""
    from initial_Illuminati import IlluminatiInitializer
    
    print()
    print("  [LOADING] Initializing game world...")
    print("     This may take a few minutes (LLM generating initial plot)...")
    print()
    
    try:
        initializer = IlluminatiInitializer(world_name, player_profile=player_profile.to_dict())
        runtime_dir = initializer.run()
        
        # 保存 genesis.json 兼容文件
        import json
        genesis_path = runtime_dir / "genesis.json"
        with open(genesis_path, "w", encoding="utf-8") as f:
            json.dump(initializer.genesis_data, f, ensure_ascii=False, indent=2)
        
        print()
        print("  [OK] Game world initialized!")
        print(f"     Runtime directory: {runtime_dir}")
        
        return runtime_dir
        
    except Exception as e:
        print(f"\n  {handle_exception(e, 'Initialize game')}")
        return None


def run_game(runtime_dir: Path, world_dir: Path):
    """运行游戏主循环"""
    from cli.osagent_session import OSAgentSession
    
    print()
    print("  [LOADING] Loading game...")
    
    try:
        # play.py 固定使用 OS Agent
        session = OSAgentSession(runtime_dir, world_dir)
        
        # 检查是否可以续玩
        if session.can_resume():
            print(session.resume())
        else:
            print(session.start())
        
        print_help()
        
        # 游戏主循环
        while True:
            try:
                user_input = input("\n  Your action > ").strip()
                
                if not user_input:
                    continue
                
                # 处理命令
                if user_input.startswith("/"):
                    command = user_input.lower()
                    if command == "/help":
                        print_help()
                        continue
                    elif command == "/status":
                        status = session.get_status()
                        print(f"\n  [STATUS]")
                        print(f"     Scene: {status.scene_id}")
                        print(f"     Turn: {status.turn_id}")
                        print(f"     Location: {status.location}")
                        continue
                    elif command == "/save":
                        save_path = session.save("manual_save", at_boundary=False)
                        print(f"\n  [SAVED] Game saved to: {save_path}")
                        continue
                    elif command == "/quit":
                        session.save("autosave", at_boundary=False)
                        print("\n  [SAVED] Game auto-saved")
                        print("  Goodbye!")
                        return
                    else:
                        print(f"  [ERROR] Unknown command: {command}")
                        continue
                
                # 处理游戏回合
                result = session.process_turn(user_input)
                
                if result.text:
                    print(f"\n{result.text}")
                
                if result.error:
                    print(f"\n  [WARNING] {result.error}")
                
                # 显示行动建议
                suggestions = session.get_action_suggestions()
                if suggestions:
                    print("\n  [SUGGESTIONS]:")
                    for i, suggestion in enumerate(suggestions, 1):
                        print(f"     [{i}] {suggestion}")
                
            except KeyboardInterrupt:
                print("\n\n  [WARNING] Exit requested")
                confirm = input("  Are you sure? (y/n) > ").lower()
                if confirm == 'y':
                    session.save("autosave", at_boundary=False)
                    print("\n  [SAVED] Game auto-saved")
                    print("  Goodbye!")
                    return
                continue
                
    except Exception as e:
        print(f"\n  {handle_exception(e, 'Game run')}")


def main(argv: List[str] = None):
    """主函数"""
    # 设置玩家模式日志
    log_filter = setup_player_logging()
    
    print_banner()
    
    world_manager = WorldManager()
    
    while True:
        print_main_menu()
        
        try:
            choice = input("  > ").strip()
            
            if choice == "0":
                print("\n  Goodbye!")
                break
            
            elif choice == "1":
                # 开始新故事
                world = select_world(world_manager)
                if world is None:
                    continue
                
                # 选择存档
                runtime = select_runtime(world_manager, world.name)
                
                if runtime is None:
                    # 新游戏
                    profile = prompt_player_profile()
                    runtime_dir = initialize_new_game(world.name, profile)
                    if runtime_dir is None:
                        continue
                else:
                    runtime_dir = runtime.path
                
                # 运行游戏
                run_game(runtime_dir, world.world_dir)
            
            elif choice == "2":
                # 继续已有故事
                world = select_world(world_manager)
                if world is None:
                    continue
                
                runtimes = world_manager.list_runtimes(world.name)
                if not runtimes:
                    print("\n  [ERROR] No save files found for this world")
                    print("     Please start a new game first")
                    continue
                
                runtime = select_runtime(world_manager, world.name)
                if runtime is None:
                    # 用户选择了新游戏
                    profile = prompt_player_profile()
                    runtime_dir = initialize_new_game(world.name, profile)
                    if runtime_dir is None:
                        continue
                else:
                    runtime_dir = runtime.path
                
                # 运行游戏
                run_game(runtime_dir, world.world_dir)
            
            else:
                print("\n  [ERROR] Invalid choice")
                
        except (KeyboardInterrupt, EOFError):
            print("\n\n  Goodbye!")
            break
        except Exception as e:
            print(f"\n  {handle_exception(e, '主菜单')}")


if __name__ == "__main__":
    main()

