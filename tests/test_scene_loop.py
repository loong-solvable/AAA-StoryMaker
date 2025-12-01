"""
场景对话循环测试

测试 OS 的 run_scene_loop 方法：
- 角色演绎 → 场景记忆板 + OS
- OS 使用 os_system.txt 决定下一位发言者
- 循环直到 is_scene_finished=true
"""
import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def run_scene_loop_test():
    """运行场景对话循环测试"""
    
    print("=" * 70)
    print("🎬 场景对话循环测试")
    print("=" * 70)
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    from config.settings import settings
    from initial_Illuminati import IlluminatiInitializer
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
    # 阶段 3: 运行场景对话循环
    # ==========================================
    print("\n" + "=" * 50)
    print("📌 阶段 3: 运行场景对话循环")
    print("=" * 50)
    
    # 模拟玩家输入的回调（测试模式：自动生成回复）
    user_responses = [
        "你好，我是来帮忙的。能告诉我发生了什么事吗？",
        "我明白了，这听起来很严重。我们应该怎么办？",
        "好的，我会配合你们的。"
    ]
    response_index = [0]  # 使用列表以便在闭包中修改
    
    def mock_user_input(prompt: str) -> str:
        """模拟玩家输入"""
        if response_index[0] < len(user_responses):
            response = user_responses[response_index[0]]
            response_index[0] += 1
            return response
        return "..."
    
    # 运行场景循环
    print("\n🎬 开始场景对话循环（最多 12 轮）...")
    print("-" * 50)
    
    result = os_agent.run_scene_loop(
        runtime_dir=runtime_dir,
        world_dir=world_dir,
        max_turns=12,
        user_input_callback=mock_user_input
    )
    
    # ==========================================
    # 阶段 4: 显示结果
    # ==========================================
    print("\n" + "=" * 50)
    print("📌 阶段 4: 场景结果")
    print("=" * 50)
    
    print(f"\n📊 执行结果:")
    print(f"   - 成功: {result.get('success')}")
    print(f"   - 总轮数: {result.get('total_turns')}")
    print(f"   - 场景结束: {result.get('scene_finished')}")
    print(f"   - 对话数: {result.get('dialogue_count')}")
    
    print(f"\n📋 对话历史:")
    print("-" * 50)
    
    for entry in result.get("dialogue_history", []):
        turn = entry.get("turn")
        speaker = entry.get("speaker_name", entry.get("speaker", "未知"))
        
        if "response" in entry:
            resp = entry["response"]
            content = resp.get("content", "")
            target = resp.get("addressing_target", "everyone")
            print(f"\n[{turn}] 【{speaker}】 → {target}")
            print(f"    「{content[:80]}{'...' if len(content) > 80 else ''}」")
        else:
            content = entry.get("content", "")
            print(f"\n[{turn}] 【{speaker}】")
            print(f"    「{content}」")
    
    print("\n" + "=" * 70)
    print("✅ 场景对话循环测试完成")
    print("=" * 70)
    print(f"⏰ 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return result


if __name__ == "__main__":
    try:
        result = run_scene_loop_test()
        print(f"\n最终结果: {'成功 ✅' if result.get('success') else '失败 ❌'}")
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()

