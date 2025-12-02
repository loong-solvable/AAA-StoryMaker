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


def run_three_scenes_test():
    """运行三幕完整测试"""
    
    print("=" * 70)
    print("🎬 三幕完整流程测试")
    print("=" * 70)
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    from config.settings import settings
    from initial_Illuminati import IlluminatiInitializer
    from utils.scene_memory import create_scene_memory, create_all_scene_memory
    import importlib.util
    
    world_name = "白垩纪往事"
    world_dir = settings.DATA_DIR / "worlds" / world_name
    
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
    
    # 本次测试不包含玩家参与，user_input_callback 设为 None
    
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
        
        loop_result = os_agent.run_scene_loop(
            runtime_dir=runtime_dir,
            world_dir=world_dir,
            max_turns=12,  # 每幕最多12轮对话
            user_input_callback=None  # 不包含玩家参与
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
            
            # 检查归档前的 history 目录
            history_dir = runtime_dir / "plot" / "history"
            files_before = list(history_dir.glob("*.json")) if history_dir.exists() else []
            print(f"\n📂 归档前 history 文件数: {len(files_before)}")
            
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
            
            # 检查归档后的 history 目录
            files_after = list(history_dir.glob("*.json")) if history_dir.exists() else []
            new_files = set(f.name for f in files_after) - set(f.name for f in files_before)
            
            print(f"\n📂 归档后 history 文件数: {len(files_after)}")
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
    
    # 检查 history 目录最终状态
    history_dir = runtime_dir / "plot" / "history"
    all_history_files = list(history_dir.glob("*.json")) if history_dir.exists() else []
    
    print(f"\n📂 History 目录最终状态:")
    print(f"   - 文件总数: {len(all_history_files)}")
    for f in all_history_files:
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
    try:
        result = run_three_scenes_test()
        
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

