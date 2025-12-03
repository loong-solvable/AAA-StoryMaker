"""
三幕完整流程测试

测试完整的三幕流程：
1. 光明会初始化（生成第1幕剧本）
2. 第1幕演绎 → 幕间处理（归档 + 生成第2幕）
3. 第2幕演绎 → 幕间处理（归档 + 生成第3幕）
4. 第3幕演绎 → 结束

目标：
- 验证剧本分发、角色演绎、幕间处理的完整流程
- 验证旧剧本归档到 history 文件夹
- 观察流程与设想的差距
"""
import sys
import json
import time
import argparse
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


def print_dialogue(dialogue_log: list):
    """格式化打印对话记录"""
    for entry in dialogue_log:
        order_id = entry.get("order_id")
        speaker = entry.get("speaker_name")
        content = entry.get("content", "")[:100]
        action = entry.get("action", "")[:50]
        emotion = entry.get("emotion", "")
        target = entry.get("addressing_target", "everyone")
        
        target_str = f" → {target}" if target != "everyone" else ""
        
        print(f"\n  [{order_id}] 【{speaker}】{target_str}")
        if action:
            print(f"      动作: {action}...")
        if emotion:
            print(f"      情绪: {emotion}")
        print(f"      台词: {content}...")


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


def select_world_interactive(available_worlds):
    """交互式选择世界"""
    if len(available_worlds) == 1:
        return available_worlds[0]
    
    print("\n📋 可用的世界:")
    for i, w in enumerate(available_worlds, 1):
        print(f"   {i}. {w}")
    
    try:
        choice = input(f"\n请选择世界 (1-{len(available_worlds)}): ").strip()
        idx = int(choice) - 1
        if 0 <= idx < len(available_worlds):
            return available_worlds[idx]
        else:
            print("❌ 无效选择")
            return None
    except (ValueError, KeyboardInterrupt):
        print("\n❌ 取消选择")
        return None


def create_mock_user_input_callback(scene_num: int):
    """创建模拟玩家输入的回调函数
    
    Args:
        scene_num: 当前场景编号（1-3）
    
    Returns:
        玩家输入回调函数
    """
    turn_count = [0]  # 使用列表以便在闭包中修改
    
    def mock_user_input(prompt: str) -> str:
        """模拟玩家输入"""
        turn_count[0] += 1
        current_turn = turn_count[0]
        
        # 根据场景和轮次提供不同的输入
        if scene_num == 1:
            # 第1幕：玩家初次参与，比较好奇和谨慎
            if current_turn == 1:
                return "发生了什么事？"
            elif current_turn == 2:
                return "原来如此，那我们应该一起合作解决这个问题。"
            else:
                return "我明白了，让我们继续吧。"
        
        elif scene_num == 2:
            # 第2幕：玩家已经熟悉情况，更加主动
            if current_turn == 1:
                return "好"
            elif current_turn == 2:
                return "好的，让我们开始行动吧。"
            else:
                return "继续，我在听。"
        
        else:  # scene_num == 3
            # 第3幕：玩家已经深入剧情，更加投入
            if current_turn == 1:
                return "没问题"
            elif current_turn == 2:
                return "我完全理解"
            else:
                return "好的，我准备好了。"
    
    return mock_user_input


def run_three_scenes_test(world_name: str = None):
    """运行三幕完整测试
    
    Args:
        world_name: 世界名称，如果为None则自动检测或提示选择
    """
    
    print("=" * 70)
    print("🎬 三幕完整流程测试")
    print("=" * 70)
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    from config.settings import settings
    from initial_Illuminati import IlluminatiInitializer
    from utils.scene_memory import create_scene_memory, create_all_scene_memory
    import importlib.util
    
    # 1. 确定世界名称
    if world_name is None:
        available_worlds = find_available_worlds()
        if not available_worlds:
            print("❌ 未找到可用的世界目录")
            print(f"   请确保 {settings.DATA_DIR / 'worlds'} 目录下有世界数据")
            print(f"   或者先运行: python run_creator_god.py")
            return None
        
        if len(available_worlds) == 1:
            world_name = available_worlds[0]
            print(f"📁 自动选择世界: {world_name}")
        else:
            world_name = select_world_interactive(available_worlds)
            if world_name is None:
                return None
    
    world_dir = settings.DATA_DIR / "worlds" / world_name
    if not world_dir.exists():
        print(f"❌ 世界目录不存在: {world_dir}")
        print(f"   请先运行: python run_creator_god.py 创建世界数据")
        return None
    
    print(f"📁 使用世界: {world_name}")
    print(f"📁 世界目录: {world_dir}")
    print()
    
    # ==========================================
    # 阶段 0: 光明会初始化
    # ==========================================
    print_separator("阶段 0: 光明会初始化")
    
    initializer = IlluminatiInitializer(world_name, skip_player=True)  # 不添加玩家
    runtime_dir = initializer.run()
    
    print(f"✅ 光明会初始化完成")
    print(f"📁 运行时目录: {runtime_dir}")
    
    # 初始化全剧记事板
    all_memory = create_all_scene_memory(runtime_dir)
    print(f"📚 全剧记事板初始化完成")
    
    # ==========================================
    # 阶段 1: 初始化 OS Agent
    # ==========================================
    print_separator("阶段 1: 初始化 OS Agent")
    
    os_file = PROJECT_ROOT / "agents" / "online" / "layer1" / "os_agent.py"
    spec = importlib.util.spec_from_file_location("os_agent", os_file)
    os_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(os_module)
    
    os_agent = os_module.OperatingSystem()
    print("✅ OS Agent 初始化完成")
    
    # 用于存储测试结果
    test_results = {
        "scenes": [],
        "history_files": [],
        "issues": []
    }
    
    # 注意：虽然初始化时 skip_player=True，但路由系统可能会将玩家加入对话
    # 因此我们提供模拟的玩家输入回调函数
    
    # ==========================================
    # 运行三幕
    # ==========================================
    for scene_num in range(1, 4):
        print_separator(f"第 {scene_num} 幕", char="*")
        
        scene_result = {
            "scene_id": scene_num,
            "success": False,
            "total_turns": 0,
            "dialogue_count": 0,
            "transition_result": None
        }
        
        # === 2.1 剧本拆分 ===
        print(f"\n🎬 拆分第 {scene_num} 幕剧本...")
        dispatch_result = os_agent.dispatch_script_to_actors(runtime_dir)
        
        if dispatch_result.get("success"):
            actor_scripts = dispatch_result.get("actor_scripts", {})
            print(f"   ✅ 剧本拆分完成: {len(actor_scripts)} 个任务卡")
            for npc_id in actor_scripts:
                print(f"      - {npc_id}")
        else:
            issue = f"第{scene_num}幕剧本拆分失败: {dispatch_result.get('error')}"
            print(f"   ❌ {issue}")
            test_results["issues"].append(issue)
            continue
        
        # === 2.2 初始化首次出场角色 ===
        print(f"\n🎭 初始化首次出场角色...")
        init_result = os_agent.initialize_first_appearance_characters(
            runtime_dir=runtime_dir,
            world_dir=world_dir
        )
        
        initialized = init_result.get("initialized", [])
        if initialized:
            print(f"   ✅ 初始化了 {len(initialized)} 个角色:")
            for char in initialized:
                print(f"      - {char['name']} ({char['id']})")
        else:
            print(f"   ℹ️ 无新角色需要初始化")
        
        # === 2.3 场景演绎 ===
        print(f"\n🎬 开始第 {scene_num} 幕对话循环（最多 12 轮）...")
        print("-" * 50)
        
        # 创建模拟玩家输入回调函数（根据场景提供不同的输入）
        mock_user_input = create_mock_user_input_callback(scene_num)
        
        loop_result = os_agent.run_scene_loop(
            runtime_dir=runtime_dir,
            world_dir=world_dir,
            max_turns=12,  # 每幕最多12轮对话
            user_input_callback=mock_user_input  # 使用模拟玩家输入
        )
        
        scene_result["success"] = loop_result.get("success", False)
        scene_result["total_turns"] = loop_result.get("total_turns", 0)
        scene_result["dialogue_count"] = loop_result.get("dialogue_count", 0)
        
        print(f"\n📊 第 {scene_num} 幕演绎结果:")
        print(f"   - 成功: {scene_result['success']}")
        print(f"   - 总轮数: {scene_result['total_turns']}")
        print(f"   - 对话数: {scene_result['dialogue_count']}")
        
        # 显示本幕对话概要
        scene_memory = create_scene_memory(runtime_dir, scene_id=scene_num)
        dialogue_log = scene_memory.get_dialogue_log()
        if dialogue_log:
            print(f"\n📝 本幕对话概要:")
            print_dialogue(dialogue_log[-3:])  # 只显示最后3条
        
        # === 2.4 幕间处理（前两幕之后）===
        if scene_num < 3:
            print_separator(f"幕间处理: 第{scene_num}幕 → 第{scene_num+1}幕", char="-")
            
            # 检查归档前的 archive 目录
            archive_dir = runtime_dir / "plot" / "archive"
            files_before = list(archive_dir.glob("*.json")) if archive_dir.exists() else []
            print(f"\n📂 归档前 archive 文件数: {len(files_before)}")
            
            transition_result = os_agent.process_scene_transition(
                runtime_dir=runtime_dir,
                world_dir=world_dir,
                scene_memory=scene_memory,
                scene_summary=f"第{scene_num}幕剧情演绎完成。"
            )
            
            scene_result["transition_result"] = {
                "scene_archived": transition_result.get("scene_archived"),
                "world_state_updated": transition_result.get("world_state_updated"),
                "next_script_generated": transition_result.get("next_script_generated"),
                "next_scene_id": transition_result.get("next_scene_id")
            }
            
            print(f"\n📊 幕间处理结果:")
            print(f"   - 场景归档: {transition_result.get('scene_archived')}")
            print(f"   - WS更新: {transition_result.get('world_state_updated')}")
            print(f"   - 剧本生成: {transition_result.get('next_script_generated')}")
            print(f"   - 下一幕ID: {transition_result.get('next_scene_id')}")
            
            # 检查归档后的 archive 目录
            files_after = list(archive_dir.glob("*.json")) if archive_dir.exists() else []
            new_files = set(f.name for f in files_after) - set(f.name for f in files_before)
            
            print(f"\n📂 归档后 archive 文件数: {len(files_after)}")
            if new_files:
                print(f"   ✅ 新归档文件:")
                for f in new_files:
                    print(f"      - {f}")
                    test_results["history_files"].append(f)
            else:
                issue = f"第{scene_num}幕后未产生新归档文件"
                print(f"   ⚠️ {issue}")
                test_results["issues"].append(issue)
            
            # 小延迟避免API限流
            time.sleep(1)
        
        test_results["scenes"].append(scene_result)
    
    # ==========================================
    # 最终检查
    # ==========================================
    print_separator("最终检查")
    
    # 检查全剧记事板
    all_memory_final = create_all_scene_memory(runtime_dir)
    all_data = all_memory_final.to_dict()
    scenes_archived = len(all_data.get("scenes", []))
    
    print(f"\n📚 全剧记事板状态:")
    print(f"   - 已归档幕数: {scenes_archived}")
    print(f"   - 当前幕ID: {all_data.get('meta', {}).get('current_scene_id')}")
    
    # 检查 archive 目录最终状态
    archive_dir = runtime_dir / "plot" / "archive"
    all_archive_files = list(archive_dir.glob("*.json")) if archive_dir.exists() else []
    
    print(f"\n📂 Archive 目录最终状态:")
    print(f"   - 文件总数: {len(all_archive_files)}")
    for f in all_archive_files:
        print(f"      - {f.name}")
    
    # 检查当前剧本
    current_script = runtime_dir / "plot" / "current_script.json"
    if current_script.exists():
        with open(current_script, "r", encoding="utf-8") as f:
            script_data = json.load(f)
        print(f"\n📜 当前剧本:")
        print(f"   - 幕次ID: {script_data.get('scene_id')}")
        print(f"   - 内容长度: {len(script_data.get('content', ''))} 字符")
    
    # ==========================================
    # 测试总结
    # ==========================================
    print_separator("测试总结")
    
    total_scenes = len(test_results["scenes"])
    successful_scenes = sum(1 for s in test_results["scenes"] if s["success"])
    total_dialogues = sum(s["dialogue_count"] for s in test_results["scenes"])
    
    print(f"\n📊 测试统计:")
    print(f"   - 完成幕数: {total_scenes}")
    print(f"   - 成功幕数: {successful_scenes}")
    print(f"   - 总对话数: {total_dialogues}")
    print(f"   - 归档文件数: {len(test_results['history_files'])}")
    
    if test_results["issues"]:
        print(f"\n⚠️ 发现的问题 ({len(test_results['issues'])} 个):")
        for i, issue in enumerate(test_results["issues"], 1):
            print(f"   {i}. {issue}")
    else:
        print(f"\n✅ 未发现问题")
    
    print(f"\n⏰ 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # 保存测试报告
    report_file = runtime_dir / "test_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump({
            "test_time": datetime.now().isoformat(),
            "results": test_results,
            "summary": {
                "total_scenes": total_scenes,
                "successful_scenes": successful_scenes,
                "total_dialogues": total_dialogues,
                "history_files": len(test_results["history_files"]),
                "issues_count": len(test_results["issues"])
            }
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 测试报告已保存: {report_file}")
    
    return test_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="三幕完整流程测试",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 自动检测并选择世界
  python tests/test_three_scenes_flow.py
  
  # 指定世界名称
  python tests/test_three_scenes_flow.py --world "江城市"
  
  # 指定世界名称（白垩纪往事）
  python tests/test_three_scenes_flow.py --world "白垩纪往事"
        """
    )
    
    parser.add_argument(
        "--world",
        type=str,
        help="世界名称（如果不指定，将自动检测或提示选择）"
    )
    
    args = parser.parse_args()
    
    try:
        result = run_three_scenes_test(world_name=args.world)
        
        if result is None:
            print("\n❌ 测试未执行")
            sys.exit(1)
        
        overall_success = (
            len(result["scenes"]) >= 3 and
            all(s["success"] for s in result["scenes"]) and
            len(result["issues"]) == 0
        )
        
        print(f"\n最终结果: {'完全成功 ✅' if overall_success else '部分完成 ⚠️'}")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()

