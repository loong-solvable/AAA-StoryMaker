"""
🎭 Infinite Story - 无限故事机
游戏主入口 - 运行此文件即可开始游戏

流程:
1. 检测世界数据 (data/worlds/) → 无则引导创建
2. 检测运行时数据 (data/runtime/) → 无则自动初始化
3. 启动游戏引擎进入交互循环

使用方法:
    python main.py
"""
import sys
from pathlib import Path
from typing import Optional, List

from config.settings import settings
from utils.logger import default_logger as logger


def print_banner():
    """打印游戏横幅"""
    print()
    print("=" * 70)
    print("  🎭 Infinite Story - 无限故事机")
    print("  基于LangChain的生成式互动叙事游戏")
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


def get_existing_runtimes(world_name: str) -> List[Path]:
    """获取指定世界的现有运行时目录"""
    runtime_dir = settings.DATA_DIR / "runtime"
    if not runtime_dir.exists():
        return []
    
    runtimes = []
    for rt_dir in runtime_dir.iterdir():
        if rt_dir.is_dir() and rt_dir.name.startswith(f"{world_name}_"):
            # 检查是否是有效的运行时目录
            if (rt_dir / "init_summary.json").exists():
                runtimes.append(rt_dir)
    
    return sorted(runtimes, key=lambda p: p.stat().st_mtime, reverse=True)


def select_world(available_worlds: List[str]) -> Optional[str]:
    """让用户选择世界"""
    if len(available_worlds) == 1:
        world = available_worlds[0]
        print(f"📁 检测到唯一世界: {world}")
        return world
    
    print("📚 可用的世界:")
    for i, world in enumerate(available_worlds, 1):
        print(f"   {i}. {world}")
    print()
    
    while True:
        try:
            choice = input("请选择世界 (输入数字) > ").strip()
            if not choice:
                continue
            
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(available_worlds):
                    return available_worlds[idx]
            
            print("❌ 无效的选择，请重新输入")
            
        except (KeyboardInterrupt, EOFError):
            print("\n取消选择")
            return None


def select_or_create_runtime(world_name: str) -> Optional[Path]:
    """选择现有运行时或创建新的"""
    runtimes = get_existing_runtimes(world_name)
    
    print()
    print("🎮 运行选项:")
    print("   0. 开始新游戏")
    
    if runtimes:
        print("   ─────────────────────────────")
        print("   继续现有游戏:")
        for i, rt in enumerate(runtimes[:5], 1):  # 只显示最近5个
            print(f"   {i}. {rt.name}")
    
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
                return initialize_new_game(world_name)
            
            if runtimes and 1 <= idx <= len(runtimes[:5]):
                return runtimes[idx - 1]
            
            print("❌ 无效的选择")
            
        except (KeyboardInterrupt, EOFError):
            print("\n取消选择")
            return None


def prompt_player_profile() -> dict:
    """收集玩家的最小角色信息"""
    print()
    print("📝 创建你的角色:")
    
    profile = {}
    try:
        name = input("   角色名字 (回车默认"玩家") > ").strip()
        if name:
            profile["name"] = name
        
        gender = input("   性别 (可留空) > ").strip()
        if gender:
            profile["gender"] = gender
        
        appearance = input("   一句话外观描述 (可留空) > ").strip()
        if appearance:
            profile["appearance"] = appearance
            
    except (KeyboardInterrupt, EOFError):
        print("\n使用默认玩家设定")
    
    return profile


def initialize_new_game(world_name: str) -> Optional[Path]:
    """创建新的运行时（调用 IlluminatiInitializer）"""
    from initial_Illuminati import IlluminatiInitializer
    
    print()
    print("⏳ 正在初始化游戏世界...")
    print("   这可能需要几分钟（需要调用LLM生成初始剧情）...")
    print()
    
    # 收集玩家信息
    player_profile = prompt_player_profile()
    
    try:
        initializer = IlluminatiInitializer(world_name, player_profile=player_profile)
        runtime_dir = initializer.run()
        
        # 保存 genesis.json 兼容文件（供 GameEngine 使用）
        import json
        genesis_path = runtime_dir / "genesis.json"
        with open(genesis_path, "w", encoding="utf-8") as f:
            json.dump(initializer.genesis_data, f, ensure_ascii=False, indent=2)
        
        print()
        print("✅ 游戏世界初始化完成!")
        print(f"   📁 运行时目录: {runtime_dir}")
        
        return runtime_dir
        
    except Exception as e:
        logger.error(f"❌ 初始化失败: {e}", exc_info=True)
        print(f"\n❌ 初始化失败: {e}")
        print(f"\n请查看日志: {settings.LOGS_DIR}/illuminati_init.log")
        return None


def run_game_engine(runtime_dir: Path):
    """运行游戏引擎"""
    from game_engine import GameEngine
    
    genesis_path = runtime_dir / "genesis.json"
    
    if not genesis_path.exists():
        print("❌ 运行时目录缺少 genesis.json 文件")
        print("   请重新初始化游戏")
        return
    
    try:
        print()
        print("⏳ 正在加载游戏引擎...")
        
        game = GameEngine(genesis_path)
        
        print("✅ 游戏引擎加载完成!")
        print()
        
        # 开始游戏
        opening = game.start_game()
        print(opening)
        
        print_help()
        
        # 游戏主循环
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
        
    except FileNotFoundError as e:
        logger.error(f"❌ 文件未找到: {e}")
        print(f"\n❌ 错误: {e}")
    except Exception as e:
        logger.error(f"❌ 游戏运行出错: {e}", exc_info=True)
        print(f"\n❌ 游戏出错: {e}")
        print(f"\n请查看日志: {settings.LOGS_DIR}/game_engine.log")


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


def run_genesis_if_needed() -> bool:
    """如果没有世界数据，引导用户运行创世组"""
    from agents.offline.genesis_group import create_world
    
    print("📌 检测到没有可用的世界数据")
    print()
    print("需要先运行创世组（Genesis Group）从小说中提取世界数据。")
    print()
    
    # 检查是否有小说文件
    novels_dir = settings.DATA_DIR / "novels"
    if not novels_dir.exists():
        novels_dir.mkdir(parents=True, exist_ok=True)
    
    novels = list(novels_dir.glob("*.txt"))
    
    if not novels:
        print("❌ 未找到小说文件")
        print(f"\n请将小说文件(.txt)放入: {novels_dir}")
        return False
    
    print("📚 可用的小说文件:")
    for i, novel in enumerate(novels, 1):
        print(f"   {i}. {novel.name}")
    print()
    
    try:
        choice = input("选择小说文件 (输入数字) > ").strip()
        if not choice.isdigit():
            print("❌ 无效的选择")
            return False
        
        idx = int(choice) - 1
        if not (0 <= idx < len(novels)):
            print("❌ 无效的选择")
            return False
        
        novel_file = novels[idx]
        
        print()
        print("⏳ 正在运行创世组，这可能需要几分钟...")
        print("   📍 阶段1: 大中正 - 角色普查")
        print("   📍 阶段2: Demiurge - 世界设定提取")
        print("   📍 阶段3: 许劭 - 角色档案制作")
        print()
        
        # 验证配置
        settings.validate()
        settings.ensure_directories()
        
        # 运行创世组
        world_dir = create_world(novel_file.name)
        
        print()
        print("✅ 世界构建成功!")
        print(f"   📁 世界数据: {world_dir}")
        print()
        
        return True
        
    except KeyboardInterrupt:
        print("\n取消操作")
        return False
    except Exception as e:
        logger.error(f"❌ 创世组运行失败: {e}", exc_info=True)
        print(f"\n❌ 创世组运行失败: {e}")
        print(f"\n请查看日志: {settings.LOGS_DIR}/genesis_group.log")
        return False


def main():
    """主函数"""
    print_banner()
    
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
    
    # 确保目录存在
    settings.ensure_directories()
    
    # 检测可用的世界
    available_worlds = get_available_worlds()
    
    if not available_worlds:
        # 没有世界数据，引导创建
        if not run_genesis_if_needed():
            return
        
        # 重新检测
        available_worlds = get_available_worlds()
        if not available_worlds:
            print("❌ 创世组运行后仍未检测到世界数据")
            return
    
    # 选择世界
    world_name = select_world(available_worlds)
    if not world_name:
        return
    
    print(f"\n✅ 已选择世界: {world_name}")
    
    # 选择或创建运行时
    runtime_dir = select_or_create_runtime(world_name)
    if not runtime_dir:
        return
    
    # 运行游戏引擎
    run_game_engine(runtime_dir)


if __name__ == "__main__":
    main()
