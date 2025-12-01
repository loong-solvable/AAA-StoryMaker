"""
完整场景流程测试

从剧本分发器开始，一直运行到角色完成该幕对话
流程: 剧本拆分 → 角色初始化 → 对话循环 → 场景结束
"""
import sys
import json
import time
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def run_full_scene():
    """运行完整场景流程"""
    print("=" * 70)
    print("🎬 完整场景流程测试")
    print("=" * 70)
    
    from config.settings import settings
    from utils.scene_memory import create_scene_memory
    
    runtime_dir = settings.DATA_DIR / "runtime" / "江城市_20251128_183246"
    world_dir = settings.DATA_DIR / "worlds" / "江城市"
    
    # ==========================================
    # 阶段 1: 初始化 OS Agent
    # ==========================================
    print("\n" + "=" * 50)
    print("📌 阶段 1: 初始化 OS Agent")
    print("=" * 50)
    
    import importlib.util
    os_file = PROJECT_ROOT / "agents" / "online" / "layer1" / "os_agent.py"
    
    spec = importlib.util.spec_from_file_location("os_agent", os_file)
    os_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(os_module)
    
    os_agent = os_module.OperatingSystem()
    print("✅ OS Agent 初始化完成")
    
    # ==========================================
    # 阶段 2: 剧本拆分
    # ==========================================
    print("\n" + "=" * 50)
    print("📌 阶段 2: 剧本拆分 (dispatch_script_to_actors)")
    print("=" * 50)
    
    print("正在调用 LLM 拆分剧本...")
    dispatch_result = os_agent.dispatch_script_to_actors(runtime_dir)
    
    if not dispatch_result.get("success"):
        print(f"❌ 剧本拆分失败: {dispatch_result.get('error')}")
        return False
    
    print(f"✅ 剧本拆分成功")
    print(f"   全局上下文: {dispatch_result.get('global_context', '')[:60]}...")
    
    for npc_id, script_path in dispatch_result.get("actor_scripts", {}).items():
        print(f"   📜 {npc_id}: {Path(script_path).name}")
    
    # ==========================================
    # 阶段 3: 初始化首次出场角色
    # ==========================================
    print("\n" + "=" * 50)
    print("📌 阶段 3: 初始化首次出场角色")
    print("=" * 50)
    
    init_result = os_agent.initialize_first_appearance_characters(
        runtime_dir=runtime_dir,
        world_dir=world_dir
    )
    
    initialized_chars = init_result.get("initialized", [])
    print(f"✅ 初始化了 {len(initialized_chars)} 个角色:")
    
    for char in initialized_chars:
        print(f"   🎭 {char['name']} ({char['id']})")
    
    # 获取初始化的 NPC Agents
    npc_agents = {}
    for char in initialized_chars:
        agent = os_agent.npc_agents.get(char["id"])
        if agent:
            npc_agents[char["id"]] = agent
    
    # ==========================================
    # 阶段 4: 创建场景记忆板
    # ==========================================
    print("\n" + "=" * 50)
    print("📌 阶段 4: 创建场景记忆板")
    print("=" * 50)
    
    # 清空旧记忆
    memory_file = runtime_dir / "npc" / "memory" / "scene_memory.json"
    if memory_file.exists():
        memory_file.unlink()
    
    scene_memory = create_scene_memory(runtime_dir, turn_id=1)
    print(f"✅ 场景记忆板创建成功")
    
    # 为所有 NPC 绑定记忆板并加载小剧本
    for npc_id, agent in npc_agents.items():
        agent.bind_scene_memory(scene_memory)
        script_file = runtime_dir / "npc" / f"{npc_id}_script.json"
        if script_file.exists():
            agent.load_script(script_file)
        print(f"   ✅ {agent.CHARACTER_NAME} 绑定记忆板并加载小剧本")
    
    # ==========================================
    # 阶段 5: 开始对话循环
    # ==========================================
    print("\n" + "=" * 50)
    print("📌 阶段 5: 开始对话循环")
    print("=" * 50)
    
    active_npcs = list(npc_agents.keys())
    print(f"在场角色: {active_npcs}")
    
    # 设置对话参数
    MAX_TURNS = 6  # 最大对话轮数
    current_turn = 0
    scene_finished = False
    
    # 选择第一个发言者（根据剧本中角色定位选择）
    current_speaker_id = active_npcs[0] if active_npcs else None
    
    print(f"\n🎬 场景开始！第一位发言者: {current_speaker_id}")
    print("-" * 50)
    
    while current_turn < MAX_TURNS and not scene_finished:
        current_turn += 1
        print(f"\n【第 {current_turn} 轮对话】")
        
        if current_speaker_id not in npc_agents:
            if current_speaker_id == "user":
                print("⏸️ 等待玩家输入...")
                # 模拟玩家输入
                if current_turn == 1:
                    user_input = "你们好，我注意到这里的气氛有些紧张。发生了什么事？"
                else:
                    user_input = "原来是这样，那我们应该一起合作揭露这个阴谋。"
                
                scene_memory.add_dialogue(
                    speaker_id="user",
                    speaker_name="玩家",
                    content=user_input,
                    addressing_target="everyone"
                )
                print(f"👤 玩家: {user_input}")
                
                # 玩家发言后，让第一个 NPC 接话
                current_speaker_id = active_npcs[0]
                continue
            else:
                print(f"⚠️ 未知发言者: {current_speaker_id}")
                break
        
        # 获取当前发言者 Agent
        current_agent = npc_agents[current_speaker_id]
        
        print(f"🎭 {current_agent.CHARACTER_NAME} 正在演绎...")
        
        # 演绎
        result = current_agent.react()
        
        # 显示演绎结果
        print(f"\n   💭 内心: {result.get('thought', '无')[:40]}...")
        print(f"   😊 情绪: {result.get('emotion', '无')}")
        print(f"   🎬 动作: {result.get('action', '无')}")
        print(f"   💬 台词: {result.get('content', '无')}")
        print(f"   🎯 对象: {result.get('addressing_target', 'everyone')}")
        print(f"   🏁 结束: {result.get('is_scene_finished', False)}")
        
        # 检查场景是否结束
        if result.get("is_scene_finished"):
            scene_finished = True
            print("\n🏁 演员判断场景已结束！")
            break
        
        # OS 路由决策
        routing = os_agent.route_dialogue(
            actor_response=result,
            active_npcs=active_npcs,
            scene_memory=scene_memory
        )
        
        print(f"\n   📨 路由: {routing.get('routing_reason')}")
        
        # 更新下一位发言者
        next_speaker = routing.get("next_speaker_id")
        
        if routing.get("should_pause_for_user"):
            current_speaker_id = "user"
        elif next_speaker:
            current_speaker_id = next_speaker
        else:
            # 没有下一位，场景结束
            scene_finished = True
        
        # 小延迟，避免请求过快
        time.sleep(0.5)
    
    # ==========================================
    # 阶段 6: 场景结束，输出总结
    # ==========================================
    print("\n" + "=" * 50)
    print("📌 阶段 6: 场景结束")
    print("=" * 50)
    
    if current_turn >= MAX_TURNS:
        print(f"⏰ 达到最大轮数限制 ({MAX_TURNS})")
    
    # 显示完整对话记录
    print("\n📋 完整对话记录:")
    print("-" * 50)
    
    for entry in scene_memory.get_dialogue_log():
        order_id = entry.get("order_id")
        speaker = entry.get("speaker_name")
        target = entry.get("addressing_target", "everyone")
        content = entry.get("content", "")
        action = entry.get("action", "")
        
        target_str = f" → {target}" if target != "everyone" else ""
        action_str = f"（{action}）" if action else ""
        
        print(f"\n[{order_id}] 【{speaker}】{target_str}{action_str}")
        print(f"    {content}")
    
    # 保存对话记录
    print("\n" + "-" * 50)
    print(f"💾 对话记录已保存到: {memory_file}")
    print(f"📊 总对话轮数: {scene_memory.get_dialogue_count()}")
    print(f"📊 场景状态: {scene_memory.get_scene_status()}")
    
    print("\n" + "=" * 70)
    print("🎬 完整场景流程测试完成")
    print("=" * 70)
    
    return True


if __name__ == "__main__":
    try:
        success = run_full_scene()
        print(f"\n最终结果: {'成功 ✅' if success else '失败 ❌'}")
    except Exception as e:
        print(f"\n测试异常: {e}")
        import traceback
        traceback.print_exc()

