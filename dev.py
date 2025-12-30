#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Infinite Story - 开发者控制台
提供完整的调试和控制能力

使用方法:
    python dev.py                    # 交互式菜单
    python dev.py --stage genesis    # 运行创世组
    python dev.py --stage game       # 运行游戏
    python dev.py --resume --runtime <dir>  # 续玩

参数:
    --stage [genesis|illuminati|game|all]  运行阶段
    --engine [osagent|gameengine]          游戏引擎
    --world <世界名>                        指定世界
    --novel <小说文件>                      指定小说
    --runtime <运行时目录>                   指定运行时目录
    --resume                                续玩模式
    --continue-build <世界名>               创世组断点续传
    --parallel / --no-parallel             并行控制
    --concurrency <数量>                    并发数
    --verbose / --quiet                    日志控制
    --auto-test                            自动测试模式
    --max-turns <回合数>                    最大回合数
    --screen-agent / --no-screen-agent     Screen Agent 开关
    --list-worlds                          列出所有世界
    --list-novels                          列出所有小说
"""

import argparse
import sys
from pathlib import Path
from typing import Optional, List

# 确保项目根目录在路径中
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import settings
from config.cli_config import DevConfig
from cli.world_manager import WorldManager
from cli.session_factory import SessionFactory
from cli.engine_resolver import resolve_engine, check_engine_conflict
from cli.player_profile import prompt_player_profile
from utils.logger import setup_logger
from utils.exception_handler import handle_exception
from utils.progress_tracker import ProgressTracker

logger = setup_logger("DevConsole", "dev_console.log")


def print_banner():
    """打印开发者控制台横幅"""
    print()
    print("=" * 80)
    print("  [DEV] Infinite Story - Developer Console")
    print("=" * 80)
    print()
    print(f"  Version: v0.10.0")
    print(f"  LLM: {settings.LLM_PROVIDER} ({settings.OPENROUTER_MODEL if settings.LLM_PROVIDER == 'openrouter' else settings.MODEL_NAME})")
    print()
    print("-" * 80)
    print()


def print_interactive_menu():
    """打印交互式菜单"""
    print("  Available Operations:")
    print()
    print("    [1] Genesis - Build world from novel")
    print("    [2] Illuminati - Initialize game world")
    print("    [3] Game - Start game flow")
    print("    [4] Full Flow - Novel to game")
    print("    [5] Status - View world/runtime status")
    print("    [0] Exit")
    print()


def list_novels():
    """列出所有小说文件"""
    novels_dir = settings.NOVELS_DIR
    if not novels_dir.exists():
        print("  [ERROR] Novel directory not found")
        return []
    
    novels = list(novels_dir.glob("*.txt"))
    if not novels:
        print("  [ERROR] No novel files found")
        print(f"     Please put novels in: {novels_dir}")
        return []
    
    print("  Available Novels:")
    print()
    for i, novel in enumerate(novels, 1):
        size = novel.stat().st_size / 1024  # KB
        print(f"    [{i}] {novel.name} ({size:.1f} KB)")
    print()
    
    return novels


def list_worlds(world_manager: WorldManager, detailed: bool = False):
    """列出所有世界"""
    worlds = world_manager.list_available_worlds()
    
    if not worlds:
        print("  [ERROR] No world data found")
        return
    
    print("  Available Worlds:")
    print()
    
    if detailed:
        print("  No.   World Name            Chars    Genre")
        print("  " + "-" * 60)
        for i, world in enumerate(worlds, 1):
            print(f"  {i:3}   {world.title or world.name:<20} {world.character_count:3}      {world.genre}")
    else:
        for i, world in enumerate(worlds, 1):
            print(f"    [{i}] {world.title or world.name}")
            if world.genre:
                print(f"        Genre: {world.genre} | Characters: {world.character_count}")
    print()


def run_genesis(novel_filename: str, world_name: Optional[str] = None, parallel: bool = True):
    """运行创世组"""
    from run_world_builder import WorldBuilder
    
    print()
    print("  [GENESIS] Starting world building...")
    print(f"     Novel: {novel_filename}")
    print(f"     Parallel mode: {'ON' if parallel else 'OFF'}")
    print()
    
    try:
        builder = WorldBuilder(
            novel_filename=novel_filename,
            world_name=world_name,
            parallel=parallel
        )
        world_dir = builder.build()
        
        print()
        print(f"  [OK] World building complete: {world_dir}")
        return world_dir
        
    except Exception as e:
        print(f"\n  {handle_exception(e, 'Genesis')}")
        return None


def run_illuminati(world_name: str, player_profile: dict = None):
    """运行光明会初始化"""
    from initial_Illuminati import IlluminatiInitializer
    
    print()
    print("  [ILLUMINATI] Starting initialization...")
    print(f"     World: {world_name}")
    print()
    
    try:
        initializer = IlluminatiInitializer(world_name, player_profile=player_profile)
        runtime_dir = initializer.run()
        
        # 保存 genesis.json
        import json
        genesis_path = runtime_dir / "genesis.json"
        with open(genesis_path, "w", encoding="utf-8") as f:
            json.dump(initializer.genesis_data, f, ensure_ascii=False, indent=2)
        
        print()
        print(f"  [OK] Illuminati initialization complete: {runtime_dir}")
        return runtime_dir
        
    except Exception as e:
        print(f"\n  {handle_exception(e, 'Illuminati')}")
        return None


def run_game(
    runtime_dir: Path,
    world_dir: Path,
    engine_type: str = "osagent",
    enable_screen_agent: bool = True,
    max_turns: int = 50,
    auto_test: bool = False
):
    """运行游戏"""
    print()
    print("  [GAME] Starting game...")
    print(f"     Engine: {engine_type}")
    print(f"     Screen Agent: {'ON' if enable_screen_agent else 'OFF'}")
    print(f"     Max turns: {max_turns}")
    print()
    
    # 检查 Screen Agent 兼容性
    if engine_type == "gameengine" and enable_screen_agent:
        print("  [WARNING] Screen Agent only supports OS Agent, ignored in GameEngine mode",
              file=sys.stderr)
        enable_screen_agent = False
    
    try:
        # 创建会话
        session = SessionFactory.create(
            runtime_dir=runtime_dir,
            world_dir=world_dir,
            engine_type=engine_type
        )
        
        # 检查是否可以续玩
        if session.can_resume():
            print(session.resume())
        else:
            print(session.start())
        
        print()
        print("  Commands: /help, /status, /save, /quit")
        print()
        
        turn_count = 0
        
        # 游戏主循环
        while turn_count < max_turns:
            try:
                if auto_test:
                    # 自动测试模式
                    user_input = f"Auto test turn {turn_count + 1}"
                    print(f"\n  [AUTO] > {user_input}")
                else:
                    user_input = input("\n  Your action > ").strip()
                
                if not user_input:
                    continue
                
                # 处理命令
                if user_input.startswith("/"):
                    command = user_input.lower()
                    if command == "/help":
                        print("\n  Commands:")
                        print("    /help    - Show help")
                        print("    /status  - View status")
                        print("    /save    - Save game")
                        print("    /quit    - Exit game")
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
                        print(f"\n  [SAVED] {save_path}")
                        continue
                    elif command == "/quit":
                        session.save("autosave", at_boundary=False)
                        print("\n  [SAVED] Game auto-saved")
                        print("  Exiting game...")
                        return
                    else:
                        print(f"  [ERROR] Unknown command: {command}")
                        continue
                
                # 处理游戏回合
                result = session.process_turn(user_input)
                turn_count += 1
                
                print(f"\n  [Turn {turn_count}] Scene {result.scene_id}")
                
                if result.text:
                    print(f"\n{result.text}")
                
                if result.error:
                    print(f"\n  [WARNING] {result.error}")
                
            except KeyboardInterrupt:
                if auto_test:
                    break
                print("\n\n  [WARNING] Exit requested")
                confirm = input("  Are you sure? (y/n) > ").lower()
                if confirm == 'y':
                    session.save("autosave", at_boundary=False)
                    print("\n  [SAVED] Game auto-saved")
                    return
        
        print(f"\n  [END] Game ended ({turn_count} turns)")
        session.save("final_save", at_boundary=True)
        
    except Exception as e:
        print(f"\n  {handle_exception(e, 'Game run')}")


def interactive_mode():
    """交互式模式"""
    world_manager = WorldManager()
    
    while True:
        print_interactive_menu()
        
        try:
            choice = input("  Select > ").strip()
            
            if choice == "0":
                print("\n  Goodbye!")
                break
            
            elif choice == "1":
                # 创世组
                novels = list_novels()
                if not novels:
                    continue
                
                novel_choice = input("  Select novel (number) > ").strip()
                if novel_choice.isdigit():
                    idx = int(novel_choice) - 1
                    if 0 <= idx < len(novels):
                        run_genesis(novels[idx].name)
                    else:
                        print("  [ERROR] Invalid choice")
                else:
                    print("  [ERROR] Please enter a number")
            
            elif choice == "2":
                # 光明会
                list_worlds(world_manager)
                worlds = world_manager.list_available_worlds()
                if not worlds:
                    continue
                
                world_choice = input("  Select world (number) > ").strip()
                if world_choice.isdigit():
                    idx = int(world_choice) - 1
                    if 0 <= idx < len(worlds):
                        profile = prompt_player_profile()
                        run_illuminati(worlds[idx].name, profile.to_dict())
                    else:
                        print("  [ERROR] Invalid choice")
                else:
                    print("  [ERROR] Please enter a number")
            
            elif choice == "3":
                # 游戏运行
                list_worlds(world_manager)
                worlds = world_manager.list_available_worlds()
                if not worlds:
                    continue
                
                world_choice = input("  Select world (number) > ").strip()
                if not world_choice.isdigit():
                    print("  [ERROR] Please enter a number")
                    continue
                
                idx = int(world_choice) - 1
                if not (0 <= idx < len(worlds)):
                    print("  [ERROR] Invalid choice")
                    continue
                
                world = worlds[idx]
                runtimes = world_manager.list_runtimes(world.name)
                
                if runtimes:
                    print()
                    print("  Available runtime directories:")
                    print("    [0] Create new runtime")
                    for i, rt in enumerate(runtimes[:5], 1):
                        print(f"    [{i}] {rt.name}")
                    
                    rt_choice = input("  Select > ").strip()
                    if rt_choice == "0" or not runtimes:
                        profile = prompt_player_profile()
                        runtime_dir = run_illuminati(world.name, profile.to_dict())
                    elif rt_choice.isdigit():
                        rt_idx = int(rt_choice) - 1
                        if 0 <= rt_idx < len(runtimes[:5]):
                            runtime_dir = runtimes[rt_idx].path
                        else:
                            print("  [ERROR] Invalid choice")
                            continue
                    else:
                        continue
                else:
                    profile = prompt_player_profile()
                    runtime_dir = run_illuminati(world.name, profile.to_dict())
                
                if runtime_dir:
                    run_game(runtime_dir, world.world_dir)
            
            elif choice == "4":
                # 完整流程
                novels = list_novels()
                if not novels:
                    continue
                
                novel_choice = input("  Select novel (number) > ").strip()
                if not novel_choice.isdigit():
                    print("  [ERROR] Please enter a number")
                    continue
                
                idx = int(novel_choice) - 1
                if not (0 <= idx < len(novels)):
                    print("  [ERROR] Invalid choice")
                    continue
                
                # 运行创世组
                world_dir = run_genesis(novels[idx].name)
                if world_dir is None:
                    continue
                
                # 运行光明会
                world_name = world_dir.name
                profile = prompt_player_profile()
                runtime_dir = run_illuminati(world_name, profile.to_dict())
                if runtime_dir is None:
                    continue
                
                # 运行游戏
                run_game(runtime_dir, world_dir)
            
            elif choice == "5":
                # 状态查看
                list_worlds(world_manager, detailed=True)
            
            else:
                print("  [ERROR] Invalid choice")
                
        except (KeyboardInterrupt, EOFError):
            print("\n\n  Goodbye!")
            break
        except Exception as e:
            print(f"\n  {handle_exception(e, 'Interactive menu')}")


def parse_args(argv: List[str] = None):
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="Infinite Story 开发者控制台",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # 运行控制
    parser.add_argument("--stage", choices=["genesis", "illuminati", "game", "all"],
                        help="运行阶段")
    parser.add_argument("--engine", choices=["osagent", "gameengine"],
                        help="游戏引擎类型")
    parser.add_argument("--world", help="世界名称")
    parser.add_argument("--novel", help="小说文件名")
    parser.add_argument("--runtime", type=Path, help="运行时目录路径")
    
    # 断点续传
    parser.add_argument("--resume", action="store_true", help="续玩模式")
    parser.add_argument("--continue-build", metavar="WORLD", help="创世组断点续传")
    
    # 并行化控制
    parser.add_argument("--parallel", action="store_true", default=True, help="启用并行模式")
    parser.add_argument("--no-parallel", action="store_false", dest="parallel", help="禁用并行模式")
    parser.add_argument("--concurrency", type=int, default=5, help="并发数")
    
    # 日志控制
    parser.add_argument("--verbose", action="store_true", help="详细日志")
    parser.add_argument("--quiet", action="store_true", help="静默模式")
    
    # 游戏运行控制
    parser.add_argument("--auto-test", action="store_true", help="自动测试模式")
    parser.add_argument("--max-turns", type=int, default=50, help="最大回合数")
    
    # 功能开关
    parser.add_argument("--screen-agent", action="store_true", default=True, help="启用 Screen Agent")
    parser.add_argument("--no-screen-agent", action="store_false", dest="screen_agent", help="禁用 Screen Agent")
    
    # 信息查询
    parser.add_argument("--list-worlds", action="store_true", help="列出所有世界")
    parser.add_argument("--list-novels", action="store_true", help="列出所有小说")
    
    return parser.parse_args(argv)


def main(argv: List[str] = None):
    """主函数"""
    if argv is None:
        argv = sys.argv[1:]
    
    args = parse_args(argv)
    
    # 参数验证
    if args.resume and args.continue_build:
        print("[ERROR] --resume and --continue-build are mutually exclusive", file=sys.stderr)
        sys.exit(1)
    
    if args.resume and not args.runtime:
        print("[ERROR] --resume requires --runtime to specify runtime directory", file=sys.stderr)
        sys.exit(1)
    
    if args.continue_build and args.stage != "genesis":
        print("[ERROR] --continue-build is only for --stage genesis", file=sys.stderr)
        sys.exit(1)
    
    print_banner()
    
    world_manager = WorldManager()
    
    # 信息查询
    if args.list_worlds:
        list_worlds(world_manager, detailed=True)
        return
    
    if args.list_novels:
        list_novels()
        return
    
    # 无参数时进入交互模式
    if not args.stage and not args.resume:
        interactive_mode()
        return
    
    # 处理具体阶段
    if args.stage == "genesis":
        if not args.novel and not args.continue_build:
            print("[ERROR] Genesis requires --novel or --continue-build", file=sys.stderr)
            sys.exit(1)
        
        if args.continue_build:
            run_genesis(f"{args.continue_build}.txt", args.continue_build, args.parallel)
        else:
            run_genesis(args.novel, args.world, args.parallel)
    
    elif args.stage == "illuminati":
        if not args.world:
            print("[ERROR] Illuminati requires --world", file=sys.stderr)
            sys.exit(1)
        
        profile = prompt_player_profile(interactive=not args.auto_test)
        run_illuminati(args.world, profile.to_dict())
    
    elif args.stage == "game":
        if not args.runtime:
            print("[ERROR] Game requires --runtime", file=sys.stderr)
            sys.exit(1)
        
        if not args.runtime.exists():
            print(f"[ERROR] Runtime directory not found: {args.runtime}", file=sys.stderr)
            sys.exit(1)
        
        # 解析引擎类型
        engine_type = resolve_engine(
            cli_engine=args.engine,
            is_resume=args.resume,
            runtime_dir=args.runtime
        )
        
        # 检查引擎冲突
        if args.engine:
            check_engine_conflict(args.engine, args.runtime)
        
        # 获取世界目录
        rt_name = args.runtime.name
        world_name = rt_name.split("_")[0] if "_" in rt_name else rt_name
        world_dir = settings.DATA_DIR / "worlds" / world_name
        
        run_game(
            runtime_dir=args.runtime,
            world_dir=world_dir,
            engine_type=engine_type,
            enable_screen_agent=args.screen_agent,
            max_turns=args.max_turns,
            auto_test=args.auto_test
        )
    
    elif args.resume:
        # 续玩模式
        if not args.runtime.exists():
            print(f"[ERROR] Runtime directory not found: {args.runtime}", file=sys.stderr)
            sys.exit(1)
        
        # 解析引擎类型
        engine_type = resolve_engine(
            cli_engine=args.engine,
            is_resume=True,
            runtime_dir=args.runtime
        )
        
        # 检查引擎冲突
        if args.engine:
            check_engine_conflict(args.engine, args.runtime)
        
        # 获取世界目录
        rt_name = args.runtime.name
        world_name = rt_name.split("_")[0] if "_" in rt_name else rt_name
        world_dir = settings.DATA_DIR / "worlds" / world_name
        
        run_game(
            runtime_dir=args.runtime,
            world_dir=world_dir,
            engine_type=engine_type,
            enable_screen_agent=args.screen_agent,
            max_turns=args.max_turns,
            auto_test=args.auto_test
        )


if __name__ == "__main__":
    main()

