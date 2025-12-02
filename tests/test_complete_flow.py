"""
完整流程测试 - 从光明会初始化到角色对话

流程:
1. 🏛️ 光明会初始化 (CreatorGod/Illuminati)
   - WS（世界状态运行者）
   - Plot（命运编织者）
   - Vibe（氛围感受者）

2. 📜 剧本分发 (Script Dispatch)
   - 读取光明会生成的数据
   - 拆分总剧本为演员任务卡

3. 🎭 角色初始化 (Character Init)
   - 动态生成 NPC Agent

4. 💬 对话循环 (Dialogue Loop)
   - 场景记忆板
   - 对话路由
"""
import sys
import json
import time
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def print_banner(title: str, emoji: str = "🎬"):
    """打印横幅"""
    print("\n" + "=" * 70)
    print(f"{emoji} {title}")
    print("=" * 70)


def print_section(title: str):
    """打印章节"""
    print(f"\n{'─' * 50}")
    print(f"📌 {title}")
    print("─" * 50)


def print_file_op(op: str, path: Path, desc: str = ""):
    """打印文件操作"""
    rel = path.relative_to(PROJECT_ROOT) if path.is_relative_to(PROJECT_ROOT) else path
    emoji = "📖" if op == "READ" else "📝"
    print(f"   {emoji} [{op}] {rel}")
    if desc:
        print(f"       └─ {desc}")


def run_complete_flow():
    """运行完整流程"""
    
    print_banner("完整流程测试 - 从光明会到角色对话", "🏛️")
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 项目目录: {PROJECT_ROOT}")
    
    # ==========================================
    # 阶段 1: 光明会初始化
    # ==========================================
    print_banner("阶段 1: 光明会初始化 (Illuminati)", "🏛️")
    
    print("\n📋 光明会将初始化以下组件:")
    print("   - WS（世界状态运行者）: 读取世界设定，生成初始世界状态")
    print("   - Plot（命运编织者）: 生成起始场景和剧本")
    print("   - Vibe（氛围感受者）: 生成初始氛围描写")
    
    from config.settings import settings
    world_name = "江城市"
    world_dir = settings.DATA_DIR / "worlds" / world_name
    
    print(f"\n📖 读取世界数据:")
    print_file_op("READ", world_dir / "world_setting.json", "世界设定")
    print_file_op("READ", world_dir / "characters_list.json", "角色列表")
    print_file_op("READ", world_dir / "characters" / "character_npc_001.json", "林晨角色卡")
    print_file_op("READ", world_dir / "characters" / "character_npc_002.json", "苏晴雨角色卡")
    
    print("\n🚀 开始光明会初始化...")
    
    from initial_Illuminati import IlluminatiInitializer
    
    initializer = IlluminatiInitializer(world_name)
    runtime_dir = initializer.run()  # 返回 Path 对象
    
    if not runtime_dir or not runtime_dir.exists():
        print(f"❌ 光明会初始化失败")
        return False
    
    print(f"\n✅ 光明会初始化成功！")
    print(f"📁 运行时目录: {runtime_dir}")
    
    print(f"\n📝 生成的文件:")
    print_file_op("WRITE", runtime_dir / "ws" / "world_state.json", "世界状态")
    print_file_op("WRITE", runtime_dir / "plot" / "current_scene.json", "当前场景")
    print_file_op("WRITE", runtime_dir / "plot" / "current_script.json", "当前剧本")
    print_file_op("WRITE", runtime_dir / "vibe" / "initial_atmosphere.json", "初始氛围")
    
    # 显示开场氛围
    with open(runtime_dir / "vibe" / "initial_atmosphere.json", "r", encoding="utf-8") as f:
        atmosphere = json.load(f)
    
    print(f"\n🎨 开场氛围预览:")
    print("─" * 50)
    full_text = atmosphere.get("full_atmosphere_text", "")
    print(f"   {full_text[:200]}..." if len(full_text) > 200 else f"   {full_text}")
    print("─" * 50)
    
    # ==========================================
    # 阶段 2: 剧本分发
    # ==========================================
    print_banner("阶段 2: 剧本分发 (Script Dispatch)", "📜")
    
    print(f"\n📖 读取光明会生成的数据:")
    print_file_op("READ", runtime_dir / "plot" / "current_scene.json", "当前场景")
    print_file_op("READ", runtime_dir / "plot" / "current_script.json", "当前剧本")
    print_file_op("READ", runtime_dir / "ws" / "world_state.json", "世界状态")
    print_file_op("READ", settings.PROMPTS_DIR / "online" / "script_divider.txt", "剧本拆分提示词")
    
    import importlib.util
    os_file = PROJECT_ROOT / "agents" / "online" / "layer1" / "os_agent.py"
    spec = importlib.util.spec_from_file_location("os_agent", os_file)
    os_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(os_module)
    
    print("\n🔧 初始化 OS Agent...")
    os_agent = os_module.OperatingSystem()
    
    print("\n🤖 调用 LLM 拆分剧本为演员任务卡...")
    dispatch_result = os_agent.dispatch_script_to_actors(runtime_dir)
    
    if not dispatch_result.get("success"):
        print(f"❌ 剧本拆分失败: {dispatch_result.get('error')}")
        return False
    
    print(f"\n✅ 剧本拆分成功！")
    print(f"📝 生成的演员任务卡:")
    for npc_id, script_path in dispatch_result.get("actor_scripts", {}).items():
        print_file_op("WRITE", Path(script_path), f"{npc_id} 的任务卡")
        
        # 显示任务卡内容
        with open(script_path, "r", encoding="utf-8") as f:
            script_data = json.load(f)
        mission = script_data.get("mission", {})
        print(f"       目标: {mission.get('objective', 'N/A')[:50]}...")
    
    # ==========================================
    # 阶段 3: 角色初始化
    # ==========================================
    print_banner("阶段 3: 角色初始化 (Character Init)", "🎭")
    
    print(f"\n📖 读取角色卡:")
    for char_file in (world_dir / "characters").glob("character_*.json"):
        print_file_op("READ", char_file, "角色数据")
    
    print_file_op("READ", settings.PROMPTS_DIR / "online" / "npc_system.txt", "NPC提示词模板")
    
    print("\n🚀 初始化首次出场角色...")
    init_result = os_agent.initialize_first_appearance_characters(
        runtime_dir=runtime_dir,
        world_dir=world_dir
    )
    
    initialized_chars = init_result.get("initialized", [])
    print(f"\n✅ 初始化了 {len(initialized_chars)} 个角色:")
    
    for char in initialized_chars:
        agent_file = PROJECT_ROOT / "agents" / "online" / "layer3" / f"{char['id']}_{char['name']}.py"
        print_file_op("WRITE", agent_file, f"{char['name']} 的 Agent 代码")
    
    # 获取 NPC Agents
    npc_agents = {}
    for char in initialized_chars:
        agent = os_agent.npc_agents.get(char["id"])
        if agent:
            npc_agents[char["id"]] = agent
    
    # ==========================================
    # 阶段 4: 对话循环
    # ==========================================
    print_banner("阶段 4: 对话循环 (Dialogue Loop)", "💬")
    
    from utils.scene_memory import create_scene_memory
    
    # 创建场景记忆板
    memory_file = runtime_dir / "npc" / "memory" / "scene_memory.json"
    print_file_op("WRITE", memory_file, "场景记忆板（公屏）")
    
    scene_memory = create_scene_memory(runtime_dir, turn_id=1)
    
    # 绑定记忆板和小剧本
    print(f"\n🔗 为角色绑定资源:")
    for npc_id, agent in npc_agents.items():
        agent.bind_scene_memory(scene_memory)
        script_file = runtime_dir / "npc" / f"{npc_id}_script.json"
        if script_file.exists():
            agent.load_script(script_file)
        print(f"   ✅ {agent.CHARACTER_NAME}: 绑定记忆板 + 加载小剧本")
    
    active_npcs = list(npc_agents.keys())
    print(f"\n👥 在场角色: {[npc_agents[nid].CHARACTER_NAME for nid in active_npcs]}")
    
    MAX_TURNS = 12  # 每幕最多12轮对话
    current_turn = 0
    scene_finished = False
    current_speaker_id = active_npcs[0] if active_npcs else None
    
    print(f"\n🎬 场景开始！第一位发言者: {npc_agents[current_speaker_id].CHARACTER_NAME if current_speaker_id else 'None'}")
    print("\n" + "═" * 50)
    
    while current_turn < MAX_TURNS and not scene_finished:
        current_turn += 1
        
        if current_speaker_id not in npc_agents:
            break
        
        current_agent = npc_agents[current_speaker_id]
        
        print(f"\n【第 {current_turn} 轮】 🎭 {current_agent.CHARACTER_NAME}")
        print("─" * 40)
        
        # 演绎
        print(f"   🤖 调用 LLM 演绎角色...")
        result = current_agent.react()
        
        # 显示结果
        print(f"\n   💭 内心: {result.get('thought', '')[:40]}...")
        print(f"   😊 情绪: {result.get('emotion', '')}")
        print(f"   🎬 动作: {result.get('action', '')[:40]}...")
        print(f"   💬 台词: {result.get('content', '')[:60]}...")
        print(f"   🎯 对象: {result.get('addressing_target', 'everyone')}")
        
        if result.get("is_scene_finished"):
            scene_finished = True
            print(f"\n   🏁 场景结束!")
            break
        
        # OS 路由
        routing = os_agent.route_dialogue(
            actor_response=result,
            active_npcs=active_npcs,
            scene_memory=scene_memory
        )
        
        print(f"   📨 路由: {routing.get('routing_reason')}")
        
        next_speaker = routing.get("next_speaker_id")
        if routing.get("should_pause_for_user"):
            current_speaker_id = "user"
            print(f"   ⏸️ 等待玩家...")
            break
        elif next_speaker:
            current_speaker_id = next_speaker
        else:
            scene_finished = True
        
        time.sleep(0.3)
    
    # ==========================================
    # 总结
    # ==========================================
    print_banner("流程完成", "✅")
    
    print(f"\n📋 完整对话记录:")
    print("─" * 50)
    
    for entry in scene_memory.get_dialogue_log():
        order_id = entry.get("order_id")
        speaker = entry.get("speaker_name")
        target = entry.get("addressing_target", "everyone")
        content = entry.get("content", "")
        action = entry.get("action", "")
        
        target_str = f" → {target}" if target != "everyone" else ""
        print(f"\n[{order_id}] 【{speaker}】{target_str}")
        if action:
            print(f"    （{action[:40]}...）" if len(action) > 40 else f"    （{action}）")
        print(f"    「{content[:60]}...」" if len(content) > 60 else f"    「{content}」")
    
    print("\n" + "─" * 50)
    print(f"📊 总对话轮数: {scene_memory.get_dialogue_count()}")
    print(f"📊 场景状态: {scene_memory.get_scene_status()}")
    print(f"💾 记忆板: {memory_file}")
    
    print(f"\n⏰ 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return True


if __name__ == "__main__":
    try:
        success = run_complete_flow()
        print(f"\n最终结果: {'成功 ✅' if success else '失败 ❌'}")
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()

