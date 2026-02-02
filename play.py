#!/usr/bin/env python3
"""
🎭 Infinite Story - 无限故事机
玩家入口 - 简洁、沉浸的游戏体验

⚠️ 已弃用警告 (Deprecated since v0.4.0):
   此文件使用旧的 OS Agent 架构，不包含 Conductor 幕管理系统。
   
   推荐使用:
   - CLI 入口: python player_entry.py
   - API 服务: python api_server.py
   
   新架构优势:
   - Conductor 幕管理系统（动态幕转换、紧迫度驱动）
   - 三模式分流优化（DIALOGUE/PLOT_ADVANCE/ACT_TRANSITION）
   - NPC 幕级指令支持
   - 更好的性能和稳定性

使用方法:
    python play.py  # 已弃用，建议使用 player_entry.py

特性:
- 极简界面，隐藏技术细节
- Screen Agent 电影质感渲染
- 智能行动建议
- 自动断点续传
"""
import warnings
warnings.warn(
    "play.py 已弃用，请使用 player_entry.py 或 api_server.py。"
    "新架构包含 Conductor 幕管理系统，功能更完整。",
    DeprecationWarning,
    stacklevel=2
)

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
    print("    [3] Build New World from Novel")
    print("    [0] Exit")
    print()


def print_help():
    """打印帮助信息"""
    print()
    print("  ┌─────────────────────────────────┐")
    print("  │  /help   - 显示帮助             │")
    print("  │  /status - 查看状态             │")
    print("  │  /save   - 保存进度             │")
    print("  │  /quit   - 退出游戏             │")
    print("  │  直接输入 - 进行行动            │")
    print("  └─────────────────────────────────┘")
    print()


def select_world(world_manager: WorldManager) -> Optional[WorldInfo]:
    """让用户选择世界"""
    worlds = world_manager.list_available_worlds()
    
    if not worlds:
        print("  暂无可用的故事世界")
        print()
        print("  请返回主菜单选择 [3] 从小说构建新世界")
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
            
            print("  (请输入有效的数字)")
            
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
            
            print("  (请输入有效的数字)")
            
        except (KeyboardInterrupt, EOFError):
            print("\n  Cancelled")
            return None


def initialize_new_game(world_name: str, player_profile: PlayerProfile) -> Optional[Path]:
    """初始化新游戏"""
    from initial_Illuminati import IlluminatiInitializer
    
    print()
    print("  ⏳ 正在构建故事世界...")
    print("     (首次加载可能需要几分钟)")
    print()
    
    try:
        initializer = IlluminatiInitializer(world_name, player_profile=player_profile.to_dict())
        runtime_dir = initializer.run()
        
        # 保存 genesis.json 兼容文件
        import json
        genesis_path = runtime_dir / "genesis.json"
        with open(genesis_path, "w", encoding="utf-8") as f:
            json.dump(initializer.genesis_data, f, ensure_ascii=False, indent=2)
        
        print("  ✓ 世界构建完成")
        
        return runtime_dir
        
    except Exception as e:
        print(f"\n  ✗ 初始化失败: {e}")
        return None


def run_game(runtime_dir: Path, world_dir: Path):
    """
    运行游戏主循环
    
    重要：使用 run_scene_loop 的原生回调机制，而不是分离的 process_turn
    这样 NPC 会先建立场景，然后等待玩家输入
    """
    import importlib.util
    from pathlib import Path
    from utils.scene_memory import create_scene_memory
    from agents.online.layer3.screen_agent import ScreenAgent
    from utils.progress_tracker import ProgressTracker
    
    print()
    print("  ⏳ 载入存档...")
    
    try:
        # 初始化 OS Agent
        os_file = Path(__file__).parent / "agents" / "online" / "layer1" / "os_agent.py"
        spec = importlib.util.spec_from_file_location("os_agent", os_file)
        os_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(os_module)
        
        genesis_path = runtime_dir / "genesis.json"
        if genesis_path.exists():
            os_agent = os_module.OperatingSystem(genesis_path)
        else:
            os_agent = os_module.OperatingSystem()
        
        # 初始化 Screen Agent
        world_name = world_dir.name if world_dir else ""
        screen_agent = ScreenAgent(runtime_dir=runtime_dir, world_name=world_name)
        
        # 初始化进度追踪
        progress_tracker = ProgressTracker()
        progress = progress_tracker.load_progress(runtime_dir)
        current_scene_id = progress.current_scene_id
        
        # Screen 回调
        def screen_callback(event: str, data: dict):
            if event == "scene_start":
                screen_agent.render_scene_header(
                    scene_id=data.get("scene_id", current_scene_id),
                    location_name=data.get("location", ""),
                    description=data.get("description", "")
                )
            elif event in {"dialogue", "player_input"}:
                screen_agent.render_single_dialogue(
                    speaker=data.get("speaker", ""),
                    content=data.get("content", ""),
                    action=data.get("action", ""),
                    emotion=data.get("emotion", ""),
                    is_player=(event == "player_input"),
                )
        
        # 玩家输入回调（关键！处理命令 + 返回输入）
        def get_user_input(prompt: str) -> str:
            """获取玩家输入，处理命令"""
            while True:
                try:
                    user_input = input(f"\n  Your action > ").strip()
                    
                    if not user_input:
                        return "look around"  # 默认动作
                    
                    # 处理命令
                    if user_input.startswith("/"):
                        command = user_input.lower()
                        if command == "/help":
                            print_help()
                            continue  # 重新获取输入
                        elif command == "/status":
                            print(f"\n  📍 第 {current_scene_id} 幕 · {world_name}")
                            continue
                        elif command == "/save":
                            progress_tracker.save_progress(
                                runtime_dir=runtime_dir,
                                current_scene_id=current_scene_id,
                                next_scene_id=current_scene_id + 1,
                                turn_count=0,
                                engine_type="osagent",
                                can_switch_engine=False
                            )
                            print(f"\n  💾 进度已保存")
                            continue
                        elif command == "/quit":
                            raise KeyboardInterrupt("用户退出")
                        elif command == "/skip":
                            return "__SKIP_SCENE__"  # 跳过当前幕
                        else:
                            print(f"  (未知命令，输入 /help 查看帮助)")
                            continue
                    
                    return user_input
                    
                except EOFError:
                    raise KeyboardInterrupt("EOF")
        
        print("  ✓ 载入完成\n")
        print_help()
        
        # === 主游戏循环（按幕循环） ===
        loop_count = 0
        max_loops = 10  # 最多 10 幕
        
        while loop_count < max_loops:
            # 1. 初始化 NPC（静默）
            os_agent.ensure_scene_characters_initialized(
                runtime_dir=runtime_dir,
                world_dir=world_dir
            )
            
            # 2. 分发剧本给 NPC（静默）
            try:
                os_agent.dispatch_script_to_actors(runtime_dir)
            except Exception:
                pass  # 静默处理，不打扰玩家
            
            # 3. 运行场景循环（NPC 先说，然后玩家）
            try:
                loop_result = os_agent.run_scene_loop(
                    runtime_dir=runtime_dir,
                    world_dir=world_dir,
                    max_turns=15,
                    user_input_callback=get_user_input,
                    screen_callback=screen_callback
                )
                
                # 场景完成时不显示技术信息
                
            except KeyboardInterrupt:
                print("\n")
                confirm = input("  退出游戏？(y/n) > ").lower()
                if confirm == 'y':
                    progress_tracker.save_progress(
                        runtime_dir=runtime_dir,
                        current_scene_id=current_scene_id,
                        next_scene_id=current_scene_id + 1,
                        turn_count=0,
                        engine_type="osagent",
                        can_switch_engine=False
                    )
                    print("\n  💾 进度已自动保存")
                    print("  再见！")
                    return
                continue
            
            # 4. 幕间处理
            if loop_result.get("scene_finished", False):
                print()
                print("  " + "═" * 50)
                print(f"         ✨ 第 {current_scene_id} 幕 结束 ✨")
                print("  " + "═" * 50)
                
                scene_memory = create_scene_memory(runtime_dir, scene_id=current_scene_id)
                
                try:
                    transition_result = os_agent.process_scene_transition(
                        runtime_dir=runtime_dir,
                        world_dir=world_dir,
                        scene_memory=scene_memory,
                        scene_summary=f"Scene {current_scene_id} completed."
                    )
                    
                    next_scene_id = transition_result.get("next_scene_id") or (current_scene_id + 1)
                    progress_tracker.save_progress(
                        runtime_dir=runtime_dir,
                        current_scene_id=current_scene_id,
                        next_scene_id=next_scene_id,
                        turn_count=0,
                        engine_type="osagent",
                        can_switch_engine=True
                    )
                    current_scene_id = next_scene_id
                    
                except Exception:
                    current_scene_id += 1  # 静默处理错误
                
                # 询问是否继续
                print()
                choice = input("  继续下一幕？(回车继续 / n退出) > ").strip().lower()
                if choice == 'n':
                    print("\n  再见！")
                    return
            
            loop_count += 1
        
        print()
        print("  " + "═" * 50)
        print("         🎭 故事结束 🎭")
        print("  " + "═" * 50)
        
    except Exception as e:
        print(f"\n  ✗ 发生错误: {e}")


def list_novels() -> list:
    """列出所有小说文件"""
    novels_dir = settings.DATA_DIR / "novels"
    if not novels_dir.exists():
        novels_dir.mkdir(parents=True, exist_ok=True)
        print(f"  [提示] 已创建小说目录: {novels_dir}")
        print(f"  请将 .txt 小说文件放入此目录")
        return []
    
    novels = list(novels_dir.glob("*.txt"))
    if not novels:
        print("  暂无小说文件")
        print(f"  请将 .txt 小说文件放入: {novels_dir}")
        return []
    
    print("-" * 64)
    print("  Available Novels")
    print("-" * 64)
    print()
    for i, novel in enumerate(novels, 1):
        size = novel.stat().st_size / 1024  # KB
        print(f"    [{i}] {novel.name} ({size:.1f} KB)")
    print()
    print("  [0] <- Back to main menu")
    print()
    
    return novels


def build_world_from_novel() -> bool:
    """从小说构建新世界"""
    novels = list_novels()
    if not novels:
        return False
    
    while True:
        try:
            choice = input("  Select novel > ").strip()
            
            if choice == "0":
                return False
            
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(novels):
                    selected_novel = novels[idx]
                    break
            
            print("  (请输入有效的数字)")
            
        except (KeyboardInterrupt, EOFError):
            print("\n  Cancelled")
            return False
    
    print()
    print(f"  已选择: {selected_novel.name}")
    print()
    print("  ⏳ 正在构建世界...")
    print("     (这可能需要几分钟，请耐心等待)")
    print()
    
    try:
        # Import WorldBuilder from run_world_builder_old
        from run_world_builder_old import WorldBuilder
        
        builder = WorldBuilder(
            novel_filename=selected_novel.name,
            world_name=None,  # Auto-generate from novel name
            parallel=True
        )
        world_dir = builder.run()
        
        print()
        print(f"  ✓ 世界构建完成！")
        print(f"     路径: {world_dir}")
        print()
        print("  现在可以返回主菜单选择 [1] New Story 开始游戏")
        return True
        
    except Exception as e:
        print(f"\n  ✗ 构建失败: {e}")
        return False


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
                print("\n  再见！")
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
                    print("\n  该世界暂无存档，请先开始新游戏")
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
            
            elif choice == "3":
                # 从小说构建新世界
                build_world_from_novel()
            
            else:
                print("\n  (请输入有效的选项)")
                
        except (KeyboardInterrupt, EOFError):
            print("\n\n  再见！")
            break
        except Exception as e:
            print(f"\n  ✗ 发生错误: {e}")


if __name__ == "__main__":
    main()

