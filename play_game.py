"""
游戏主入口 - CLI交互界面
运行完整的互动叙事游戏
"""
import sys
from pathlib import Path
from config.settings import settings
from utils.logger import default_logger as logger
from game_engine import GameEngine


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


def print_status(game: GameEngine):
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
    """主游戏循环"""
    print_header()
    
    # 检查Genesis文件
    genesis_path = settings.GENESIS_DIR / "genesis.json"
    
    if not genesis_path.exists():
        print("❌ 未找到Genesis.json文件")
        print(f"\n请先运行以下命令生成世界数据:")
        print(f"  python run_architect.py")
        print()
        return
    
    try:
        # 初始化游戏引擎
        print("⏳ 正在初始化游戏引擎...")
        print("   这可能需要几秒钟...\n")
        
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
                        print_status(game)
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


if __name__ == "__main__":
    main()

