"""
测试场景记忆板功能

测试 NPC Agent 与场景记忆板的集成
"""
import sys
import json
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def test_scene_memory():
    """测试场景记忆板功能"""
    print("=" * 60)
    print("测试场景记忆板功能")
    print("=" * 60)
    
    from config.settings import settings
    from utils.scene_memory import SceneMemory, create_scene_memory
    
    # 1. 创建场景记忆板
    print("\n1. 创建场景记忆板...")
    runtime_dir = settings.DATA_DIR / "runtime" / "江城市_20251128_183246"
    
    scene_memory = create_scene_memory(runtime_dir, turn_id=1)
    print(f"   ✅ 记忆板创建成功")
    print(f"   状态: {scene_memory.get_scene_status()}")
    print(f"   已有记录: {scene_memory.get_dialogue_count()} 条")
    
    # 2. 添加一些测试对话
    print("\n2. 测试添加对话...")
    
    # 模拟用户发言
    scene_memory.add_dialogue(
        speaker_id="user",
        speaker_name="玩家",
        content="你好，我注意到你刚才接了一个电话，脸色不太好。发生什么事了吗？",
        action="走近林晨，关切地问道"
    )
    print("   ✅ 添加玩家对话")
    
    # 3. 导入 NPC Agent 并绑定记忆板
    print("\n3. 导入 NPC Agent...")
    
    import importlib.util
    agent_file = PROJECT_ROOT / "agents" / "online" / "layer3" / "npc_001_林晨.py"
    
    spec = importlib.util.spec_from_file_location("npc_001_林晨", agent_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    agent = module.create_agent()
    print(f"   ✅ 创建 Agent: {agent.CHARACTER_NAME}")
    
    # 加载小剧本
    script_file = runtime_dir / "npc" / "npc_001_script.json"
    if script_file.exists():
        agent.load_script(script_file)
        print(f"   ✅ 加载小剧本")
    
    # 绑定场景记忆板
    agent.bind_scene_memory(scene_memory)
    print(f"   ✅ 绑定场景记忆板")
    
    # 4. 测试演绎（NPC 会读取记忆板并写入响应）
    print("\n4. 测试演绎 (调用 LLM 中，请稍候...)")
    
    result = agent.react()  # 不传入 current_input，因为已经在记忆板中
    
    print(f"\n   内心活动: {result.get('thought', '无')[:50]}...")
    print(f"   情绪: {result.get('emotion', '无')}")
    print(f"   动作: {result.get('action', '无')}")
    print(f"   台词: {result.get('content', '无')[:50]}...")
    
    # 5. 查看记忆板内容
    print("\n5. 场景记忆板内容:")
    dialogue_log = scene_memory.get_dialogue_log()
    
    for entry in dialogue_log:
        order_id = entry.get("order_id")
        speaker = entry.get("speaker_name")
        content = entry.get("content", "")[:40]
        action = entry.get("action", "")
        print(f"   [{order_id}] 【{speaker}】")
        if action:
            print(f"       （{action}）")
        print(f"       {content}...")
    
    # 6. 测试格式化输出
    print("\n6. 提示词格式的对话历史:")
    formatted = scene_memory.get_dialogue_for_prompt()
    for line in formatted.split("\n"):
        print(f"   {line[:60]}...")
    
    # 7. 查看记忆文件
    print("\n7. 记忆文件内容:")
    memory_file = runtime_dir / "npc" / "memory" / "scene_memory.json"
    if memory_file.exists():
        with open(memory_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"   幕次: {data.get('meta', {}).get('turn_id')}")
        print(f"   状态: {data.get('meta', {}).get('scene_status')}")
        print(f"   对话数: {len(data.get('dialogue_log', []))}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    try:
        success = test_scene_memory()
        print(f"\n测试结果: {'成功 ✅' if success else '失败 ❌'}")
    except Exception as e:
        print(f"\n测试异常: {e}")
        import traceback
        traceback.print_exc()

