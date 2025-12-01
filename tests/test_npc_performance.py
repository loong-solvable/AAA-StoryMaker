"""
测试 NPC Agent 演绎功能

测试 NPC Agent 能否正确读取小剧本并进行演绎
"""
import sys
import json
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def test_npc_performance():
    """测试 NPC 演绎功能"""
    print("=" * 60)
    print("测试 NPC Agent 演绎功能")
    print("=" * 60)
    
    from config.settings import settings
    
    # 1. 导入 NPC Agent
    print("\n1. 导入 NPC Agent...")
    
    import importlib.util
    agent_file = PROJECT_ROOT / "agents" / "online" / "layer3" / "npc_001_林晨.py"
    
    spec = importlib.util.spec_from_file_location("npc_001_林晨", agent_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    agent = module.create_agent()
    print(f"   ✅ 创建 Agent: {agent.CHARACTER_NAME}")
    
    # 2. 加载小剧本
    print("\n2. 加载小剧本...")
    script_file = settings.DATA_DIR / "runtime" / "江城市_20251128_183246" / "npc" / "npc_001_script.json"
    
    if not script_file.exists():
        print(f"   ❌ 小剧本文件不存在: {script_file}")
        return False
    
    agent.load_script(script_file)
    print(f"   ✅ 加载小剧本: {script_file.name}")
    
    # 显示小剧本内容
    print("\n3. 小剧本内容:")
    print(f"   场景: {agent.current_script.get('global_context', '未知')[:60]}...")
    mission = agent.current_script.get('mission', {})
    print(f"   角色定位: {mission.get('role_in_scene', '未知')}")
    print(f"   核心目标: {mission.get('objective', '未知')[:50]}...")
    print(f"   情绪曲线: {mission.get('emotional_arc', '未知')}")
    
    # 4. 测试演绎
    print("\n4. 测试演绎 (调用 LLM 中，请稍候...)")
    
    # 模拟一个输入
    test_input = "你好，我注意到你刚才好像接了一个电话，脸色不太好。发生什么事了吗？"
    print(f"   输入: {test_input}")
    
    result = agent.react(current_input=test_input)
    
    # 5. 显示结果
    print("\n5. 演绎结果:")
    print(f"   内心活动: {result.get('thought', '无')}")
    print(f"   情绪: {result.get('emotion', '无')}")
    print(f"   动作: {result.get('action', '无')}")
    print(f"   台词: {result.get('content', '无')}")
    print(f"   场景结束: {result.get('is_scene_finished', False)}")
    
    # 6. 测试连续对话
    print("\n6. 测试连续对话...")
    
    follow_up = "鸿图科技？我之前也在调查他们。我是一名记者，苏晴雨。"
    print(f"   输入: {follow_up}")
    
    result2 = agent.react(current_input=follow_up)
    
    print(f"\n   内心活动: {result2.get('thought', '无')}")
    print(f"   情绪: {result2.get('emotion', '无')}")
    print(f"   动作: {result2.get('action', '无')}")
    print(f"   台词: {result2.get('content', '无')}")
    print(f"   场景结束: {result2.get('is_scene_finished', False)}")
    
    # 7. 查看对话历史
    print("\n7. 对话历史:")
    for entry in agent.dialogue_history:
        print(f"   【{entry['speaker']}】: {entry['content'][:50]}...")
    
    # 8. 查看角色状态
    print("\n8. 角色状态:")
    state = agent.get_state()
    print(f"   {json.dumps(state, ensure_ascii=False, indent=4)}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    try:
        success = test_npc_performance()
        print(f"\n测试结果: {'成功 ✅' if success else '失败 ❌'}")
    except Exception as e:
        print(f"\n测试异常: {e}")
        import traceback
        traceback.print_exc()

