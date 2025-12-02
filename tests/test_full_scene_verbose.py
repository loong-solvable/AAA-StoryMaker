"""
完整场景流程测试 - 详细版

显示每一步操作、调用的文件、读取的内容
"""
import sys
import json
import time
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def print_section(title: str, level: int = 1):
    """打印章节标题"""
    if level == 1:
        print("\n" + "=" * 70)
        print(f"🎬 {title}")
        print("=" * 70)
    elif level == 2:
        print("\n" + "-" * 50)
        print(f"📌 {title}")
        print("-" * 50)
    else:
        print(f"\n▶ {title}")


def print_file_read(file_path: Path, description: str = ""):
    """显示文件读取操作"""
    rel_path = file_path.relative_to(PROJECT_ROOT) if file_path.is_relative_to(PROJECT_ROOT) else file_path
    print(f"   📖 读取文件: {rel_path}")
    if description:
        print(f"      └─ {description}")


def print_file_write(file_path: Path, description: str = ""):
    """显示文件写入操作"""
    rel_path = file_path.relative_to(PROJECT_ROOT) if file_path.is_relative_to(PROJECT_ROOT) else file_path
    print(f"   📝 写入文件: {rel_path}")
    if description:
        print(f"      └─ {description}")


def print_llm_call(description: str):
    """显示LLM调用"""
    print(f"   🤖 LLM调用: {description}")


def print_json_content(data: dict, max_len: int = 100):
    """简洁显示JSON内容"""
    for key, value in data.items():
        if isinstance(value, str):
            display = value[:max_len] + "..." if len(value) > max_len else value
            display = display.replace("\n", " ")
        elif isinstance(value, dict):
            display = f"{{...}} ({len(value)} keys)"
        elif isinstance(value, list):
            display = f"[...] ({len(value)} items)"
        else:
            display = str(value)
        print(f"      - {key}: {display}")


def run_verbose_flow():
    """运行详细流程"""
    
    print_section("完整场景流程测试 - 详细版")
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 项目根目录: {PROJECT_ROOT}")
    
    # ==========================================
    # 阶段 0: 导入模块
    # ==========================================
    print_section("阶段 0: 导入模块", 2)
    
    print("   📦 导入 config.settings...")
    from config.settings import settings
    print(f"      └─ DATA_DIR: {settings.DATA_DIR}")
    print(f"      └─ PROMPTS_DIR: {settings.PROMPTS_DIR}")
    
    print("   📦 导入 utils.scene_memory...")
    from utils.scene_memory import create_scene_memory
    
    print("   📦 导入 os_agent 模块...")
    import importlib.util
    os_file = PROJECT_ROOT / "agents" / "online" / "layer1" / "os_agent.py"
    print_file_read(os_file, "OS Agent 主模块")
    
    spec = importlib.util.spec_from_file_location("os_agent", os_file)
    os_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(os_module)
    
    # 设置路径
    runtime_dir = settings.DATA_DIR / "runtime" / "江城市_20251128_183246"
    world_dir = settings.DATA_DIR / "worlds" / "江城市"
    
    print(f"\n   🗂️ 运行时目录: {runtime_dir}")
    print(f"   🗂️ 世界目录: {world_dir}")
    
    # ==========================================
    # 阶段 1: 初始化 OS Agent
    # ==========================================
    print_section("阶段 1: 初始化 OS Agent", 2)
    
    print("   🔧 创建 OperatingSystem 实例...")
    os_agent = os_module.OperatingSystem()
    print("   ✅ OS Agent 初始化完成")
    
    # ==========================================
    # 阶段 2: 剧本拆分
    # ==========================================
    print_section("阶段 2: 剧本拆分 (dispatch_script_to_actors)", 2)
    
    # 显示将要读取的文件
    scene_file = runtime_dir / "plot" / "current_scene.json"
    script_file = runtime_dir / "plot" / "current_script.json"
    world_state_file = runtime_dir / "ws" / "world_state.json"
    script_divider_prompt = settings.PROMPTS_DIR / "online" / "script_divider.txt"
    
    print("\n   📋 准备读取以下文件:")
    print_file_read(scene_file, "当前场景配置")
    print_file_read(script_file, "当前剧本")
    print_file_read(world_state_file, "世界状态")
    print_file_read(script_divider_prompt, "剧本拆分提示词")
    
    # 读取并显示文件内容
    print("\n   📄 文件内容预览:")
    
    with open(scene_file, "r", encoding="utf-8") as f:
        scene_data = json.load(f)
    print(f"\n   【current_scene.json】")
    print_json_content(scene_data)
    
    with open(script_file, "r", encoding="utf-8") as f:
        script_data = json.load(f)
    print(f"\n   【current_script.json】")
    print_json_content(script_data)
    
    with open(world_state_file, "r", encoding="utf-8") as f:
        world_data = json.load(f)
    print(f"\n   【world_state.json】")
    print_json_content(world_data)
    
    print("\n   🚀 开始调用剧本拆分...")
    print_llm_call("使用 script_divider.txt 提示词拆分剧本")
    
    dispatch_result = os_agent.dispatch_script_to_actors(runtime_dir)
    
    if not dispatch_result.get("success"):
        print(f"   ❌ 剧本拆分失败: {dispatch_result.get('error')}")
        return False
    
    print("\n   ✅ 剧本拆分成功！")
    print(f"   📝 全局上下文: {dispatch_result.get('global_context', '')[:80]}...")
    
    # 显示生成的小剧本
    print("\n   📜 生成的演员小剧本:")
    for npc_id, script_path in dispatch_result.get("actor_scripts", {}).items():
        script_path = Path(script_path)
        print_file_write(script_path, f"{npc_id} 的任务卡")
        
        # 读取并显示小剧本内容
        with open(script_path, "r", encoding="utf-8") as f:
            actor_script = json.load(f)
        print(f"      任务内容:")
        if "mission" in actor_script:
            for key, value in actor_script["mission"].items():
                display = str(value)[:60] + "..." if len(str(value)) > 60 else str(value)
                print(f"         - {key}: {display}")
    
    # ==========================================
    # 阶段 3: 初始化首次出场角色
    # ==========================================
    print_section("阶段 3: 初始化首次出场角色", 2)
    
    # 显示将要读取的角色卡
    characters_dir = world_dir / "characters"
    print(f"\n   📋 角色卡目录: {characters_dir}")
    
    # 列出角色卡文件
    char_files = list(characters_dir.glob("*.json"))
    print(f"   📁 发现 {len(char_files)} 个角色卡文件:")
    for cf in char_files:
        print(f"      - {cf.name}")
    
    print("\n   🚀 开始初始化角色...")
    init_result = os_agent.initialize_first_appearance_characters(
        runtime_dir=runtime_dir,
        world_dir=world_dir
    )
    
    initialized_chars = init_result.get("initialized", [])
    print(f"\n   ✅ 初始化了 {len(initialized_chars)} 个角色:")
    
    # 显示生成的文件
    for char in initialized_chars:
        char_id = char["id"]
        char_name = char["name"]
        
        # Agent 文件
        agent_file = PROJECT_ROOT / "agents" / "online" / "layer3" / f"{char_id}_{char_name}.py"
        print_file_write(agent_file, f"{char_name} 的 Agent 代码")
        
        # 角色提示词模板
        npc_prompt = settings.PROMPTS_DIR / "online" / "npc_system.txt"
        print_file_read(npc_prompt, f"通用 NPC 提示词模板")
    
    # 获取 NPC Agents
    npc_agents = {}
    for char in initialized_chars:
        agent = os_agent.npc_agents.get(char["id"])
        if agent:
            npc_agents[char["id"]] = agent
    
    # ==========================================
    # 阶段 4: 创建场景记忆板
    # ==========================================
    print_section("阶段 4: 创建场景记忆板", 2)
    
    memory_dir = runtime_dir / "npc" / "memory"
    memory_file = memory_dir / "scene_memory.json"
    
    # 清空旧记忆
    if memory_file.exists():
        print(f"   🗑️ 清空旧记忆: {memory_file}")
        memory_file.unlink()
    
    print_file_write(memory_file, "场景记忆板 (公屏)")
    
    scene_memory = create_scene_memory(runtime_dir, turn_id=1)
    print("   ✅ 场景记忆板创建成功")
    
    # 绑定记忆板和小剧本
    print("\n   🔗 为角色绑定记忆板和小剧本:")
    for npc_id, agent in npc_agents.items():
        agent.bind_scene_memory(scene_memory)
        script_file = runtime_dir / "npc" / f"{npc_id}_script.json"
        if script_file.exists():
            agent.load_script(script_file)
        print(f"      ✅ {agent.CHARACTER_NAME}: 绑定完成")
    
    # ==========================================
    # 阶段 5: 开始对话循环
    # ==========================================
    print_section("阶段 5: 开始对话循环", 2)
    
    active_npcs = list(npc_agents.keys())
    print(f"\n   👥 在场角色: {active_npcs}")
    
    MAX_TURNS = 12  # 每幕最多12轮对话
    current_turn = 0
    scene_finished = False
    current_speaker_id = active_npcs[0] if active_npcs else None
    
    print(f"   🎬 场景开始！第一位发言者: {current_speaker_id}")
    print("\n" + "=" * 50)
    
    while current_turn < MAX_TURNS and not scene_finished:
        current_turn += 1
        print(f"\n{'─' * 40}")
        print(f"【第 {current_turn} 轮对话】")
        print(f"{'─' * 40}")
        
        if current_speaker_id not in npc_agents:
            if current_speaker_id == "user":
                print("   ⏸️ 等待玩家输入...")
                user_input = "原来是这样，那我们应该一起合作揭露这个阴谋。"
                
                scene_memory.add_dialogue(
                    speaker_id="user",
                    speaker_name="玩家",
                    content=user_input,
                    addressing_target="everyone"
                )
                print(f"   👤 玩家: {user_input}")
                print_file_write(memory_file, "写入玩家对话")
                
                current_speaker_id = active_npcs[0]
                continue
            else:
                print(f"   ⚠️ 未知发言者: {current_speaker_id}")
                break
        
        current_agent = npc_agents[current_speaker_id]
        
        print(f"\n   🎭 当前发言者: {current_agent.CHARACTER_NAME} ({current_speaker_id})")
        
        # 显示读取的文件
        print(f"\n   📖 读取场景记忆板获取对话历史...")
        dialogue_count = scene_memory.get_dialogue_count()
        print(f"      └─ 当前已有 {dialogue_count} 条对话记录")
        
        print(f"\n   📖 读取 {current_speaker_id} 的小剧本...")
        if current_agent.current_script:
            mission = current_agent.current_script.get("mission", {})
            print(f"      └─ 目标: {mission.get('objective', '无')[:50]}...")
        
        print(f"\n   📖 加载提示词模板: npc_system.txt")
        print(f"      └─ 填充角色数据和剧本变量")
        
        print_llm_call(f"{current_agent.CHARACTER_NAME} 演绎中...")
        
        # 演绎
        result = current_agent.react()
        
        # 显示结果
        print(f"\n   📤 演绎结果:")
        print(f"      💭 内心: {result.get('thought', '无')[:50]}...")
        print(f"      😊 情绪: {result.get('emotion', '无')}")
        print(f"      🎬 动作: {result.get('action', '无')[:50]}...")
        print(f"      💬 台词: {result.get('content', '无')[:80]}...")
        print(f"      🎯 对话对象: {result.get('addressing_target', 'everyone')}")
        print(f"      🏁 场景结束: {result.get('is_scene_finished', False)}")
        
        print_file_write(memory_file, f"写入 {current_agent.CHARACTER_NAME} 的对话")
        
        # 检查场景是否结束
        if result.get("is_scene_finished"):
            scene_finished = True
            print("\n   🏁 演员判断场景已结束！")
            break
        
        # OS 路由
        print(f"\n   🔀 OS 路由决策...")
        routing = os_agent.route_dialogue(
            actor_response=result,
            active_npcs=active_npcs,
            scene_memory=scene_memory
        )
        
        print(f"      └─ 路由结果: {routing.get('routing_reason')}")
        print(f"      └─ 下一位: {routing.get('next_speaker_id')}")
        
        next_speaker = routing.get("next_speaker_id")
        
        if routing.get("should_pause_for_user"):
            current_speaker_id = "user"
        elif next_speaker:
            current_speaker_id = next_speaker
        else:
            scene_finished = True
        
        time.sleep(0.5)
    
    # ==========================================
    # 阶段 6: 场景结束，输出总结
    # ==========================================
    print_section("阶段 6: 场景结束总结", 2)
    
    if current_turn >= MAX_TURNS:
        print(f"   ⏰ 达到最大轮数限制 ({MAX_TURNS})")
    
    # 读取最终的记忆板
    print(f"\n   📖 读取最终场景记忆板:")
    print_file_read(memory_file, "完整对话记录")
    
    print("\n   📋 完整对话记录:")
    print("   " + "─" * 45)
    
    for entry in scene_memory.get_dialogue_log():
        order_id = entry.get("order_id")
        speaker = entry.get("speaker_name")
        target = entry.get("addressing_target", "everyone")
        content = entry.get("content", "")
        action = entry.get("action", "")
        
        target_str = f" → {target}" if target != "everyone" else ""
        action_str = f"\n      （{action}）" if action else ""
        
        print(f"\n   [{order_id}] 【{speaker}】{target_str}{action_str}")
        print(f"      「{content}」")
    
    print("\n   " + "─" * 45)
    print(f"   💾 对话记录保存位置: {memory_file}")
    print(f"   📊 总对话轮数: {scene_memory.get_dialogue_count()}")
    print(f"   📊 场景状态: {scene_memory.get_scene_status()}")
    
    # ==========================================
    # 文件操作汇总
    # ==========================================
    print_section("文件操作汇总", 2)
    
    print("\n   📖 读取的文件:")
    read_files = [
        "agents/online/layer1/os_agent.py",
        "data/runtime/江城市_20251128_183246/plot/current_scene.json",
        "data/runtime/江城市_20251128_183246/plot/current_script.json",
        "data/runtime/江城市_20251128_183246/ws/world_state.json",
        "prompts/online/script_divider.txt",
        "prompts/online/npc_system.txt",
        "data/worlds/江城市/characters/*.json",
    ]
    for f in read_files:
        print(f"      - {f}")
    
    print("\n   📝 写入/生成的文件:")
    write_files = [
        "agents/online/layer3/npc_001_林晨.py",
        "agents/online/layer3/npc_002_苏晴雨.py",
        "data/runtime/江城市_20251128_183246/npc/npc_001_script.json",
        "data/runtime/江城市_20251128_183246/npc/npc_002_script.json",
        "data/runtime/江城市_20251128_183246/npc/memory/scene_memory.json",
    ]
    for f in write_files:
        print(f"      - {f}")
    
    print_section("测试完成", 1)
    print(f"⏰ 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return True


if __name__ == "__main__":
    try:
        success = run_verbose_flow()
        print(f"\n最终结果: {'成功 ✅' if success else '失败 ❌'}")
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()

