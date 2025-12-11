"""
🎭 Infinite Story - 无限故事机
交互式CLI入口 - 提供完整的游戏管理功能

功能:
- 选择/创建世界
- 管理多个存档（运行时目录）
- 新建/继续游戏
- 玩家角色自定义

使用方法:
    python play_game.py
"""
import sys
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from config.settings import settings
from utils.logger import default_logger as logger


def print_banner():
    """打印游戏横幅"""
    print()
    print("=" * 70)
    print("  🎭 Infinite Story - 无限故事机")
    print("  交互式CLI游戏界面")
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


# ==========================================
# 世界管理
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


def get_world_info(world_name: str) -> Dict[str, Any]:
    """获取世界的详细信息"""
    world_dir = settings.DATA_DIR / "worlds" / world_name
    
    info = {"name": world_name}
    
    # 读取世界设定
    setting_file = world_dir / "world_setting.json"
    if setting_file.exists():
        with open(setting_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            meta = data.get("meta", {})
            info["title"] = meta.get("world_name", world_name)
            info["genre"] = meta.get("genre_type", "未知")
            info["description"] = meta.get("description", "")[:100]
    
    # 读取角色列表
    chars_file = world_dir / "characters_list.json"
    if chars_file.exists():
        with open(chars_file, "r", encoding="utf-8") as f:
            chars = json.load(f)
            info["character_count"] = len(chars)
    
    return info


def select_world() -> Optional[str]:
    """让用户选择世界"""
    worlds = get_available_worlds()
    
    if not worlds:
        print("❌ 未找到任何世界数据")
        print()
        print("请先运行创世组生成世界数据:")
        print("  python run_creator_god.py")
        return None
    
    print("📚 可用的世界:")
    print()
    
    for i, world in enumerate(worlds, 1):
        info = get_world_info(world)
        print(f"   {i}. {info.get('title', world)}")
        if info.get("genre"):
            print(f"      类型: {info['genre']}")
        if info.get("character_count"):
            print(f"      角色: {info['character_count']} 人")
        if info.get("description"):
            print(f"      简介: {info['description']}...")
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
            
        except (KeyboardInterrupt, EOFError):
            print("\n取消选择")
            return None


# ==========================================
# 运行时（存档）管理
# ==========================================

def get_existing_runtimes(world_name: str) -> List[Dict[str, Any]]:
    """获取指定世界的现有运行时目录"""
    runtime_dir = settings.DATA_DIR / "runtime"
    if not runtime_dir.exists():
        return []
    
    runtimes = []
    for rt_dir in runtime_dir.iterdir():
        if rt_dir.is_dir() and rt_dir.name.startswith(f"{world_name}_"):
            # 检查是否是有效的运行时目录
            summary_file = rt_dir / "init_summary.json"
            if summary_file.exists():
                try:
                    with open(summary_file, "r", encoding="utf-8") as f:
                        summary = json.load(f)
                    
                    runtimes.append({
                        "path": rt_dir,
                        "name": rt_dir.name,
                        "initialized_at": summary.get("initialized_at", "未知"),
                        "llm_model": summary.get("llm_config", {}).get("model", "未知")
                    })
                except:
                    runtimes.append({
                        "path": rt_dir,
                        "name": rt_dir.name,
                        "initialized_at": "未知",
                        "llm_model": "未知"
                    })
    
    return sorted(runtimes, key=lambda x: x["initialized_at"], reverse=True)


def select_or_create_runtime(world_name: str) -> Optional[Path]:
    """选择现有运行时或创建新的"""
    runtimes = get_existing_runtimes(world_name)
    
    print()
    print("🎮 运行选项:")
    print("   0. 🆕 开始新游戏 (初始化新的存档)")
    
    if runtimes:
        print()
        print("   继续现有游戏:")
        for i, rt in enumerate(runtimes[:5], 1):  # 只显示最近5个
            time_str = rt["initialized_at"][:16].replace("T", " ") if "T" in rt["initialized_at"] else rt["initialized_at"]
            print(f"   {i}. {rt['name']}")
            print(f"      创建时间: {time_str}")
    
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
                return runtimes[idx - 1]["path"]
            
            print("❌ 无效的选择")
            
        except (KeyboardInterrupt, EOFError):
            print("\n取消选择")
            return None


def prompt_player_profile() -> Dict[str, Any]:
    """收集玩家的角色信息"""
    print()
    print("📝 创建你的角色 (所有项均可回车跳过使用默认值)")
    print()
    
    profile = {}
    
    try:
        name = input("   角色名字 [默认: 玩家] > ").strip()
        if name:
            profile["name"] = name
        
        gender = input("   性别 [可选] > ").strip()
        if gender:
            profile["gender"] = gender
        
        appearance = input("   一句话外观/风格描述 [可选] > ").strip()
        if appearance:
            profile["appearance"] = appearance
            
    except (KeyboardInterrupt, EOFError):
        print("\n使用默认玩家设定")
    
    return profile


def create_new_runtime(world_name: str) -> Optional[Path]:
    """创建新的运行时"""
    from initial_Illuminati import IlluminatiInitializer
    
    print()
    print("⏳ 准备初始化游戏世界...")
    print("   这需要调用LLM生成初始剧情，可能需要几分钟")
    print()
    
    # 收集玩家信息
    player_profile = prompt_player_profile()
    
    print()
    print("⏳ 开始初始化...")
    print("   📍 步骤 1/3: WS - 初始化世界状态")
    print("   📍 步骤 2/3: Plot - 生成开场剧本")
    print("   📍 步骤 3/3: Vibe - 生成初始氛围")
    print()
    
    try:
        initializer = IlluminatiInitializer(world_name, player_profile=player_profile)
        runtime_dir = initializer.run()
        
        # 保存 genesis.json（供 GameEngine 使用）
        genesis_path = runtime_dir / "genesis.json"
        with open(genesis_path, "w", encoding="utf-8") as f:
            json.dump(initializer.genesis_data, f, ensure_ascii=False, indent=2)
        
        print()
        print("✅ 游戏世界初始化完成!")
        print(f"   📁 存档目录: {runtime_dir}")
        
        return runtime_dir
        
    except Exception as e:
        logger.error(f"❌ 初始化失败: {e}", exc_info=True)
        print(f"\n❌ 初始化失败: {e}")
        print(f"\n请查看日志: {settings.LOGS_DIR}/illuminati_init.log")
        return None


# ==========================================
# 游戏运行
# ==========================================

def run_game(runtime_dir: Path):
    """运行游戏"""
    from game_engine import GameEngine
    
    genesis_path = runtime_dir / "genesis.json"
    
    if not genesis_path.exists():
        print("❌ 存档目录缺少 genesis.json 文件")
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
        game_loop(game)
        
    except FileNotFoundError as e:
        logger.error(f"❌ 文件未找到: {e}")
        print(f"\n❌ 错误: {e}")
    except Exception as e:
        logger.error(f"❌ 游戏运行出错: {e}", exc_info=True)
        print(f"\n❌ 游戏出错: {e}")
        print(f"\n请查看日志: {settings.LOGS_DIR}/game_engine.log")


def game_loop(game):
    """游戏主循环"""
    while True:
        try:
            # 生成行动建议
            print("\n💡 行动建议:")
            suggestions = game.generate_action_suggestions()
            for i, suggestion in enumerate(suggestions, 1):
                print(f"   [{i}] {suggestion}")
            print("   [自定义] 直接输入你的行动")

            user_input = input("\n👤 你的行动 > ").strip()

            if not user_input:
                continue

            # 检查是否选择了建议选项
            if user_input in ("1", "2"):
                idx = int(user_input) - 1
                if 0 <= idx < len(suggestions):
                    user_input = suggestions[idx]
                    print(f"   → 选择: {user_input}")

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
