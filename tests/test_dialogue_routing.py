"""
测试对话路由功能

测试 NPC Agent 的 addressing_target 字段和 OS 的路由调度
"""
import sys
import json
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def test_dialogue_routing():
    """测试对话路由功能"""
    print("=" * 60)
    print("测试对话路由功能")
    print("=" * 60)
    
    from config.settings import settings
    from utils.scene_memory import create_scene_memory
    
    # 1. 创建场景记忆板
    print("\n1. 创建场景记忆板...")
    runtime_dir = settings.DATA_DIR / "runtime" / "江城市_20251128_183246"
    
    # 清空旧的记忆重新开始
    memory_file = runtime_dir / "npc" / "memory" / "scene_memory.json"
    if memory_file.exists():
        memory_file.unlink()
    
    scene_memory = create_scene_memory(runtime_dir, turn_id=1)
    print(f"   ✅ 记忆板创建成功")
    
    # 2. 导入 OS Agent
    print("\n2. 导入 OS Agent...")
    
    import importlib.util
    os_file = PROJECT_ROOT / "agents" / "online" / "layer1" / "os_agent.py"
    
    spec = importlib.util.spec_from_file_location("os_agent", os_file)
    os_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(os_module)
    
    os_agent = os_module.OperatingSystem()
    print(f"   ✅ OS Agent 创建成功")
    
    # 3. 导入 NPC Agent
    print("\n3. 导入 NPC Agent...")
    
    agent_file = PROJECT_ROOT / "agents" / "online" / "layer3" / "npc_001_林晨.py"
    spec = importlib.util.spec_from_file_location("npc_001_林晨", agent_file)
    npc_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(npc_module)
    
    agent = npc_module.create_agent()
    print(f"   ✅ NPC Agent 创建成功: {agent.CHARACTER_NAME}")
    
    # 加载小剧本
    script_file = runtime_dir / "npc" / "npc_001_script.json"
    if script_file.exists():
        agent.load_script(script_file)
        print(f"   ✅ 加载小剧本")
    
    # 绑定场景记忆板
    agent.bind_scene_memory(scene_memory)
    print(f"   ✅ 绑定场景记忆板")
    
    # 4. 模拟玩家发言
    print("\n4. 模拟玩家发言...")
    scene_memory.add_dialogue(
        speaker_id="user",
        speaker_name="玩家",
        content="你好，我是记者苏晴雨。我注意到你刚才接了一个电话，脸色很不好。发生什么事了？",
        action="走近林晨，关切地问道",
        addressing_target="npc_001"
    )
    print("   ✅ 添加玩家对话")
    
    # 5. NPC 演绎
    print("\n5. NPC 演绎 (调用 LLM 中，请稍候...)")
    result = agent.react()
    
    print(f"\n   演绎结果:")
    print(f"   - 内心活动: {result.get('thought', '无')[:50]}...")
    print(f"   - 情绪: {result.get('emotion', '无')}")
    print(f"   - 动作: {result.get('action', '无')}")
    print(f"   - 台词: {result.get('content', '无')[:50]}...")
    print(f"   - 对话对象: {result.get('addressing_target', '无')}")
    print(f"   - 场景结束: {result.get('is_scene_finished', False)}")
    
    # 6. OS 路由决策
    print("\n6. OS 路由决策...")
    
    active_npcs = ["npc_001", "npc_002"]  # 在场角色
    
    routing_result = os_agent.route_dialogue(
        actor_response=result,
        active_npcs=active_npcs,
        scene_memory=scene_memory
    )
    
    print(f"\n   路由结果:")
    print(f"   - 下一位发言者: {routing_result.get('next_speaker_id')}")
    print(f"   - 等待玩家: {routing_result.get('should_pause_for_user')}")
    print(f"   - 场景结束: {routing_result.get('is_scene_finished')}")
    print(f"   - 路由原因: {routing_result.get('routing_reason')}")
    
    # 7. 查看场景记忆板
    print("\n7. 场景记忆板内容:")
    for entry in scene_memory.get_dialogue_log():
        order_id = entry.get("order_id")
        speaker = entry.get("speaker_name")
        target = entry.get("addressing_target", "everyone")
        content = entry.get("content", "")[:40]
        print(f"   [{order_id}] {speaker} -> {target}: {content}...")
    
    # 8. 查看记忆文件
    print("\n8. 记忆文件内容:")
    if memory_file.exists():
        with open(memory_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        print(f"   幕次: {data.get('meta', {}).get('turn_id')}")
        print(f"   状态: {data.get('meta', {}).get('scene_status')}")
        print(f"   对话数: {len(data.get('dialogue_log', []))}")
        
        # 显示最后一条对话的 addressing_target
        if data.get("dialogue_log"):
            last = data["dialogue_log"][-1]
            print(f"   最后对话对象: {last.get('addressing_target', '未指定')}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    try:
        success = test_dialogue_routing()
        print(f"\n测试结果: {'成功 ✅' if success else '失败 ❌'}")
    except Exception as e:
        print(f"\n测试异常: {e}")
        import traceback
        traceback.print_exc()

