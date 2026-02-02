"""
GameEngine 完整流程测试

测试新架构的完整流程：
1. GameEngine 初始化（包含 Conductor）
2. 幕目标系统（多幕配置、紧迫度驱动）
3. NPC 幕级指令传递
4. 幕转换判断（Plot + Conductor 协调）
5. 三模式分流（DIALOGUE/PLOT_ADVANCE/ACT_TRANSITION）

目标：
- 验证新架构功能完整性
- 确保 Conductor 幕管理系统正常工作
- 测试 NPC 目标推进机制
"""
import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def print_separator(title: str, char: str = "=", width: int = 70):
    """打印分隔线"""
    print()
    print(char * width)
    print(f"📌 {title}")
    print(char * width)


def find_available_worlds():
    """查找所有可用的世界目录"""
    from config.settings import settings
    worlds_dir = settings.DATA_DIR / "worlds"
    
    if not worlds_dir.exists():
        return []
    
    available_worlds = []
    for world_folder in worlds_dir.iterdir():
        if world_folder.is_dir() and (world_folder / "world_setting.json").exists():
            available_worlds.append(world_folder.name)
    
    return sorted(available_worlds)


async def test_gameengine_flow(world_name: str = None, max_turns: int = 10):
    """
    测试 GameEngine 完整流程
    
    Args:
        world_name: 世界名称，如果为 None 则自动选择
        max_turns: 最大测试回合数
    """
    from config.settings import settings
    from initial_Illuminati import IlluminatiInitializer
    from game_engine import GameEngine
    
    print("=" * 70)
    print("🎮 GameEngine 完整流程测试")
    print("=" * 70)
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. 确定世界名称
    if world_name is None:
        available_worlds = find_available_worlds()
        if not available_worlds:
            print("❌ 未找到可用的世界目录")
            return None
        world_name = available_worlds[0]
    
    print(f"📁 使用世界: {world_name}")
    
    # ==========================================
    # 阶段 1: 初始化
    # ==========================================
    print_separator("阶段 1: 光明会初始化 + GameEngine 创建")
    
    initializer = IlluminatiInitializer(world_name, skip_player=False)
    runtime_dir = initializer.run()
    
    print(f"✅ 光明会初始化完成: {runtime_dir}")
    
    # 创建 GameEngine
    genesis_path = runtime_dir / "genesis.json"
    engine = GameEngine(genesis_path, async_mode=True)
    
    print(f"✅ GameEngine 创建完成")
    
    # ==========================================
    # 阶段 2: 验证 Conductor 配置
    # ==========================================
    print_separator("阶段 2: 验证 Conductor 幕系统")
    
    conductor = engine.conductor
    
    print(f"\n📋 幕定义数量: {len(conductor.act_definitions)}")
    for i, act_def in enumerate(conductor.act_definitions, 1):
        obj = act_def.get("objective", {})
        print(f"   [{i}] {act_def.get('act_name')}")
        print(f"       目标: {obj.get('description', 'N/A')}")
        print(f"       完成条件: {len(obj.get('completion_conditions', []))} 个")
        print(f"       最大回合: {obj.get('max_turns', 'N/A')}")
    
    # 检查当前幕
    current_act = conductor.current_act
    print(f"\n📍 当前幕: {current_act.act_name if current_act else 'None'}")
    if current_act:
        print(f"   - 目标ID: {current_act.objective.objective_id}")
        print(f"   - 玩家目标: {current_act.objective.description}")
        print(f"   - 内部目标: {current_act.objective.internal_goal}")
        print(f"   - 紧迫度曲线: {current_act.objective.urgency_curve}")
    
    # ==========================================
    # 阶段 3: 开始游戏
    # ==========================================
    print_separator("阶段 3: 开始游戏")
    
    opening = engine.start_game()
    print(f"📜 开场白:\n{opening[:500]}..." if len(opening) > 500 else f"📜 开场白:\n{opening}")
    
    # 获取游戏状态
    status = engine.get_game_status()
    print(f"\n📊 游戏状态:")
    print(f"   - 回合: {status['turn']}")
    print(f"   - 位置: {status['location']}")
    print(f"   - 时间: {status['time']}")
    
    # 验证幕目标信息
    act_info = status.get('act', {})
    print(f"\n🎯 幕目标信息:")
    print(f"   - 幕编号: {act_info.get('act_number')}")
    print(f"   - 幕名称: {act_info.get('act_name')}")
    print(f"   - 目标: {act_info.get('objective')}")
    print(f"   - 进度: {act_info.get('progress', 0):.0%}")
    print(f"   - 紧迫度: {act_info.get('urgency', 0):.0%}")
    print(f"   - 剩余回合: {act_info.get('turns_remaining')}")
    
    # ==========================================
    # 阶段 4: 模拟游戏回合
    # ==========================================
    print_separator("阶段 4: 模拟游戏回合")
    
    test_inputs = [
        "你好，这里是什么地方？",
        "能告诉我更多关于这个世界的事情吗？",
        "有什么有趣的事情发生吗？",
        "我想了解一下周围的人",
        "接下来我应该做什么？"
    ]
    
    results = {
        "turns": [],
        "mode_counts": {"dialogue": 0, "plot_advance": 0, "act_transition": 0},
        "act_transitions": []
    }
    
    for i, player_input in enumerate(test_inputs[:max_turns], 1):
        print(f"\n--- 回合 {i} ---")
        print(f"🎮 玩家: {player_input}")
        
        try:
            result = await engine.process_turn_async(player_input)
            
            if result.get("success"):
                mode = result.get("mode", "unknown")
                results["mode_counts"][mode] = results["mode_counts"].get(mode, 0) + 1
                
                print(f"✅ 模式: {mode}")
                
                # 检查 NPC 反应
                npc_reactions = result.get("npc_reactions", [])
                if npc_reactions:
                    print(f"🎭 NPC 反应: {len(npc_reactions)} 个")
                    for r in npc_reactions[:2]:  # 只显示前2个
                        npc = r.get("npc")
                        reaction = r.get("reaction", {})
                        print(f"   - {npc.character_name}: {reaction.get('content', '')[:50]}...")
                
                # 检查幕转换
                text = result.get("text", "")
                if "🎬" in text and "幕" in text:
                    results["act_transitions"].append({
                        "turn": i,
                        "text": text[:200]
                    })
                    print(f"🎬 检测到幕转换!")
                
                results["turns"].append({
                    "turn": i,
                    "mode": mode,
                    "success": True
                })
            else:
                print(f"❌ 失败: {result.get('error', 'Unknown error')}")
                results["turns"].append({
                    "turn": i,
                    "success": False,
                    "error": result.get("error")
                })
                
        except Exception as e:
            print(f"❌ 异常: {e}")
            results["turns"].append({
                "turn": i,
                "success": False,
                "error": str(e)
            })
    
    # ==========================================
    # 阶段 5: 验证最终状态
    # ==========================================
    print_separator("阶段 5: 验证最终状态")
    
    final_status = engine.get_game_status()
    final_act = final_status.get('act', {})
    
    print(f"\n📊 最终游戏状态:")
    print(f"   - 回合: {final_status['turn']}")
    print(f"   - 位置: {final_status['location']}")
    
    print(f"\n🎯 最终幕目标状态:")
    print(f"   - 幕编号: {final_act.get('act_number')}")
    print(f"   - 幕名称: {final_act.get('act_name')}")
    print(f"   - 进度: {final_act.get('progress', 0):.0%}")
    print(f"   - 紧迫度: {final_act.get('urgency', 0):.0%}")
    
    # Conductor 状态
    print(f"\n📋 Conductor 状态:")
    conductor_snapshot = conductor.get_state_snapshot()
    print(f"   - 当前回合: {conductor_snapshot['current_turn']}")
    print(f"   - 对话轮数: {conductor_snapshot['dialogue_turns_since_plot']}")
    print(f"   - 对话阶段: {conductor_snapshot['dialogue_phase']}")
    print(f"   - NPC交互数: {sum(conductor_snapshot['npc_interaction_count'].values())}")
    
    # ==========================================
    # 测试总结
    # ==========================================
    print_separator("测试总结")
    
    successful_turns = sum(1 for t in results["turns"] if t.get("success"))
    total_turns = len(results["turns"])
    
    print(f"\n📊 测试统计:")
    print(f"   - 总回合数: {total_turns}")
    print(f"   - 成功回合: {successful_turns}")
    print(f"   - 成功率: {successful_turns/total_turns*100:.0f}%")
    print(f"\n📈 模式分布:")
    for mode, count in results["mode_counts"].items():
        print(f"   - {mode}: {count}")
    print(f"\n🎬 幕转换次数: {len(results['act_transitions'])}")
    
    # 验证关键功能
    print(f"\n✅ 功能验证:")
    print(f"   - Conductor 初始化: {'✓' if conductor else '✗'}")
    print(f"   - 多幕配置: {'✓' if len(conductor.act_definitions) >= 3 else '✗'}")
    print(f"   - 幕目标返回: {'✓' if act_info.get('objective') else '✗'}")
    print(f"   - 紧迫度计算: {'✓' if final_act.get('urgency', 0) > 0 else '✗'}")
    print(f"   - 进度追踪: {'✓' if final_act.get('progress', 0) > 0 else '✗'}")
    
    print(f"\n⏰ 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    return results


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="GameEngine 完整流程测试")
    parser.add_argument("--world", type=str, help="世界名称")
    parser.add_argument("--turns", type=int, default=5, help="测试回合数")
    args = parser.parse_args()
    
    try:
        result = asyncio.run(test_gameengine_flow(
            world_name=args.world,
            max_turns=args.turns
        ))
        
        if result:
            successful = sum(1 for t in result["turns"] if t.get("success"))
            total = len(result["turns"])
            if successful == total:
                print("\n✅ 所有测试通过!")
                return 0
            else:
                print(f"\n⚠️ 部分测试失败: {successful}/{total}")
                return 1
        else:
            print("\n❌ 测试未执行")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⚠️ 测试被用户中断")
        return 1
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
