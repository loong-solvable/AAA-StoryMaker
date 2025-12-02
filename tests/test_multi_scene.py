"""
多幕剧本流程测试

测试完整的多幕流程：
1. 光明会初始化
2. 第一幕演绎
3. 幕间处理（归档 + WS更新 + Plot生成下一幕）
4. 第二幕演绎
"""
import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def run_multi_scene_test():
    """运行多幕测试"""
    
    print("=" * 70)
    print("🎬 多幕剧本流程测试")
    print("=" * 70)
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    from config.settings import settings
    from initial_Illuminati import IlluminatiInitializer
    from utils.scene_memory import create_scene_memory, create_all_scene_memory
    import importlib.util
    
    world_name = "江城市"
    world_dir = settings.DATA_DIR / "worlds" / world_name
    
    # ==========================================
    # 阶段 1: 光明会初始化
    # ==========================================
    print("\n" + "=" * 50)
    print("📌 阶段 1: 光明会初始化")
    print("=" * 50)
    
    initializer = IlluminatiInitializer(world_name)
    runtime_dir = initializer.run()
    
    print(f"✅ 光明会初始化完成")
    print(f"📁 运行时目录: {runtime_dir}")
    
    # 初始化全剧记事板
    all_memory = create_all_scene_memory(runtime_dir)
    print(f"📚 全剧记事板初始化完成")
    
    # ==========================================
    # 阶段 2: 初始化 OS 和角色
    # ==========================================
    print("\n" + "=" * 50)
    print("📌 阶段 2: 初始化 OS 和角色")
    print("=" * 50)
    
    os_file = PROJECT_ROOT / "agents" / "online" / "layer1" / "os_agent.py"
    spec = importlib.util.spec_from_file_location("os_agent", os_file)
    os_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(os_module)
    
    os_agent = os_module.OperatingSystem()
    print("✅ OS Agent 初始化完成")
    
    # 剧本拆分
    print("\n🤖 拆分剧本...")
    dispatch_result = os_agent.dispatch_script_to_actors(runtime_dir)
    if dispatch_result.get("success"):
        print(f"✅ 剧本拆分完成: {len(dispatch_result.get('actor_scripts', {}))} 个任务卡")
    
    # 角色初始化
    print("\n🎭 初始化角色...")
    init_result = os_agent.initialize_first_appearance_characters(
        runtime_dir=runtime_dir,
        world_dir=world_dir
    )
    
    initialized = init_result.get("initialized", [])
    print(f"✅ 初始化了 {len(initialized)} 个角色:")
    for char in initialized:
        print(f"   - {char['name']} ({char['id']})")
    
    # ==========================================
    # 阶段 3: 第一幕演绎
    # ==========================================
    print("\n" + "=" * 50)
    print("📌 阶段 3: 第一幕演绎")
    print("=" * 50)
    
    # 模拟玩家输入
    user_responses = [
        "这件事情很复杂，我们需要小心行事。",
        "好的，我同意你的计划。"
    ]
    response_index = [0]
    
    def mock_user_input(prompt: str) -> str:
        if response_index[0] < len(user_responses):
            response = user_responses[response_index[0]]
            response_index[0] += 1
            return response
        return "..."
    
    print("\n🎬 开始第一幕对话循环（最多 12 轮）...")
    print("-" * 50)
    
    result1 = os_agent.run_scene_loop(
        runtime_dir=runtime_dir,
        world_dir=world_dir,
        max_turns=12,  # 每幕最多12轮对话
        user_input_callback=mock_user_input
    )
    
    print(f"\n📊 第一幕结果:")
    print(f"   - 成功: {result1.get('success')}")
    print(f"   - 总轮数: {result1.get('total_turns')}")
    print(f"   - 对话数: {result1.get('dialogue_count')}")
    
    # 获取第一幕的场景记忆
    scene_memory_1 = create_scene_memory(runtime_dir, turn_id=1)
    
    # ==========================================
    # 阶段 4: 幕间处理
    # ==========================================
    print("\n" + "=" * 50)
    print("📌 阶段 4: 幕间处理")
    print("=" * 50)
    
    transition_result = os_agent.process_scene_transition(
        runtime_dir=runtime_dir,
        world_dir=world_dir,
        scene_memory=scene_memory_1,
        scene_summary="林晨和苏晴雨在出租屋交换情报，发现被追踪后决定转移。"
    )
    
    print(f"\n📊 幕间处理结果:")
    print(f"   - 场景归档: {transition_result.get('scene_archived')}")
    print(f"   - WS更新: {transition_result.get('world_state_updated')}")
    print(f"   - 剧本生成: {transition_result.get('next_script_generated')}")
    print(f"   - 下一幕ID: {transition_result.get('next_scene_id')}")
    
    # 检查全剧记事板
    all_memory_updated = create_all_scene_memory(runtime_dir)
    print(f"\n📚 全剧记事板状态:")
    print(f"   - 已归档幕数: {len(all_memory_updated.to_dict().get('scenes', []))}")
    
    # ==========================================
    # 阶段 5: 检查生成的文件
    # ==========================================
    print("\n" + "=" * 50)
    print("📌 阶段 5: 检查生成的文件")
    print("=" * 50)
    
    # 检查 all_scene_memory.json
    all_memory_file = runtime_dir / "all_scene_memory.json"
    print(f"\n📄 全剧记事板: {all_memory_file.name}")
    if all_memory_file.exists():
        print("   ✅ 文件存在")
    else:
        print("   ❌ 文件不存在")
    
    # 检查更新后的 world_state.json
    ws_file = runtime_dir / "ws" / "world_state.json"
    print(f"\n📄 世界状态: {ws_file.name}")
    if ws_file.exists():
        import json
        with open(ws_file, "r", encoding="utf-8") as f:
            ws_data = json.load(f)
        print(f"   ✅ 当前场景: {ws_data.get('current_scene', {}).get('location_name', '未知')}")
        print(f"   ✅ 时间: {ws_data.get('current_scene', {}).get('time_of_day', '未知')}")
    
    # 检查新剧本
    script_file = runtime_dir / "plot" / "current_script.json"
    print(f"\n📄 当前剧本: {script_file.name}")
    if script_file.exists():
        import json
        with open(script_file, "r", encoding="utf-8") as f:
            script_data = json.load(f)
        print(f"   ✅ 幕次ID: {script_data.get('scene_id', '未知')}")
        print(f"   ✅ 内容长度: {len(script_data.get('content', ''))} 字符")
    
    print("\n" + "=" * 70)
    print("✅ 多幕测试完成")
    print("=" * 70)
    print(f"⏰ 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return {
        "scene_1_result": result1,
        "transition_result": transition_result
    }


if __name__ == "__main__":
    try:
        result = run_multi_scene_test()
        overall_success = (
            result["scene_1_result"].get("success") and
            result["transition_result"].get("success")
        )
        print(f"\n最终结果: {'成功 ✅' if overall_success else '部分成功 ⚠️'}")
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()

