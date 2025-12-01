"""
第二阶段Demo测试脚本
演示信息中枢OS和逻辑审查官Logic的基本功能

使用新的 data/worlds/ 格式，通过运行时目录加载数据
"""
import json
from pathlib import Path
from config.settings import settings
from utils.logger import default_logger as logger
from agents.online.layer1.os_agent import OperatingSystem
from agents.online.layer1.logic_agent import LogicValidator
from agents.message_protocol import (
    AgentRole, MessageType, create_message, create_validation_request
)


def print_separator(title: str = ""):
    """打印分隔线"""
    print("\n" + "=" * 70)
    if title:
        print(f"  {title}")
        print("=" * 70)
    print()


def find_or_create_genesis() -> Path:
    """
    查找或创建 genesis.json 文件
    
    优先级:
    1. 现有运行时目录中的 genesis.json
    2. 从 data/worlds/ 构建并保存到临时位置
    """
    # 查找现有运行时目录
    runtime_dir = settings.DATA_DIR / "runtime"
    if runtime_dir.exists():
        for rt_dir in sorted(runtime_dir.iterdir(), reverse=True):
            genesis_path = rt_dir / "genesis.json"
            if genesis_path.exists():
                print(f"✅ 找到现有 genesis.json: {genesis_path}")
                return genesis_path
    
    # 从 worlds 目录构建
    worlds_dir = settings.DATA_DIR / "worlds"
    if not worlds_dir.exists():
        raise FileNotFoundError("未找到 data/worlds/ 目录，请先运行 run_creator_god.py")
    
    # 使用第一个世界
    for world_dir in worlds_dir.iterdir():
        if world_dir.is_dir() and (world_dir / "world_setting.json").exists():
            print(f"📦 从世界目录构建 genesis 数据: {world_dir.name}")
            
            # 加载世界数据
            with open(world_dir / "world_setting.json", "r", encoding="utf-8") as f:
                world_setting = json.load(f)
            
            with open(world_dir / "characters_list.json", "r", encoding="utf-8") as f:
                characters_list = json.load(f)
            
            # 加载所有角色档案
            characters = []
            characters_dir = world_dir / "characters"
            if characters_dir.exists():
                for char_file in characters_dir.glob("character_*.json"):
                    with open(char_file, "r", encoding="utf-8") as f:
                        characters.append(json.load(f))
            
            # 构建 genesis 格式数据
            meta = world_setting.get("meta", {})
            genesis_data = {
                "world": {
                    "title": meta.get("world_name", world_dir.name),
                    "genre": meta.get("genre_type", "REALISTIC"),
                    "description": meta.get("description", "")
                },
                "characters": characters,
                "locations": world_setting.get("geography", {}).get("locations", []),
                "physics_logic": world_setting.get("physics_logic", {}),
                "social_logic": world_setting.get("social_logic", []),
                "plot_hints": [],
                "world_start_context": {
                    "suggested_time": "下午",
                    "suggested_location": "loc_001",
                    "key_characters": [c.get("id") for c in characters[:2] if c.get("id")]
                }
            }
            
            # 保存到临时位置
            temp_genesis = settings.DATA_DIR / "temp_genesis.json"
            with open(temp_genesis, "w", encoding="utf-8") as f:
                json.dump(genesis_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 已构建 genesis 数据: {temp_genesis}")
            return temp_genesis
    
    raise FileNotFoundError("未找到任何世界数据")


def test_os_initialization():
    """测试1: OS初始化和Genesis加载"""
    print_separator("测试1: 信息中枢OS初始化")
    
    # 查找或创建 genesis.json
    try:
        genesis_path = find_or_create_genesis()
    except FileNotFoundError as e:
        print(f"❌ {e}")
        print(f"   请先运行: python run_creator_god.py")
        return None
    
    # 初始化OS
    print("🖥️  正在初始化信息中枢...")
    os_system = OperatingSystem(genesis_path)
    
    # 显示系统状态
    state = os_system.get_game_state()
    print("✅ OS初始化成功!")
    print(f"\n📊 系统状态:")
    print(f"   - 回合数: {state['turn']}")
    print(f"   - 世界: {os_system.genesis_data['world']['title']}")
    print(f"   - 角色数: {len(os_system.genesis_data['characters'])}")
    print(f"   - 地点数: {len(os_system.genesis_data['locations'])}")
    
    # 显示世界上下文
    if state['world_context']:
        ctx = state['world_context']
        print(f"\n🌍 世界上下文:")
        print(f"   - 当前时间: {ctx['current_time']}")
        print(f"   - 当前位置: {ctx['current_location']}")
        print(f"   - 在场角色: {', '.join(ctx['present_characters'])}")
    
    return os_system


def test_logic_validation(os_system: OperatingSystem):
    """测试2: 逻辑审查官验证"""
    print_separator("测试2: 逻辑审查官Logic初始化与验证")
    
    print("🔍 正在初始化逻辑审查官...")
    logic = LogicValidator()
    
    # 设置世界观
    logic.set_world_rules(os_system.genesis_data['world'])
    
    # 注册到OS
    os_system.register_handler(AgentRole.LOGIC, logic.handle_message)
    print("✅ 逻辑审查官初始化成功!")
    
    # 测试用例
    test_cases = [
        {
            "description": "合理的用户输入",
            "input": "我走到窗边，看向外面的街道",
            "expected": True
        },
        {
            "description": "不合理的用户输入（超自然元素）",
            "input": "我念动咒语，召唤出一团火球",
            "expected": False
        },
        {
            "description": "正常的行为",
            "input": "我拿出手机，打开通讯录",
            "expected": True
        }
    ]
    
    print(f"\n🧪 运行验证测试...\n")
    
    for i, case in enumerate(test_cases, 1):
        print(f"测试用例 {i}: {case['description']}")
        print(f"   输入: \"{case['input']}\"")
        
        # 构建上下文
        context = {
            "current_location": os_system.world_context.current_location,
            "current_time": os_system.world_context.current_time,
        }
        
        # 创建验证请求消息
        request = create_validation_request(
            from_agent=AgentRole.OS,
            content=case['input'],
            context=context
        )
        request.payload["content_type"] = "user_input"
        
        # 通过OS路由消息
        response = os_system.route_message(request)
        
        if response:
            result = response.payload
            is_valid = result['is_valid']
            
            if is_valid:
                print(f"   结果: ✅ 通过验证")
                if result.get('warnings'):
                    print(f"   警告: {', '.join(result['warnings'])}")
            else:
                print(f"   结果: ❌ 验证失败")
                print(f"   错误: {', '.join(result['errors'])}")
            
            # 检查是否符合预期
            if is_valid == case['expected']:
                print(f"   ✅ 符合预期")
            else:
                print(f"   ⚠️  不符合预期（预期: {'通过' if case['expected'] else '拒绝'}）")
        else:
            print(f"   ❌ 未收到响应")
        
        print()
    
    return logic


def test_message_routing(os_system: OperatingSystem):
    """测试3: 消息路由"""
    print_separator("测试3: 消息路由系统")
    
    print("📨 测试消息路由功能...")
    print(f"   已注册的处理器: {list(os_system.message_handlers.keys())}")
    print(f"   消息队列长度: {len(os_system.message_queue)}")
    
    # 创建测试消息
    test_msg = create_message(
        from_agent=AgentRole.USER,
        to_agent=AgentRole.OS,
        message_type=MessageType.USER_INPUT,
        payload={"text": "这是一条测试消息"}
    )
    
    print(f"\n📤 发送测试消息:")
    print(f"   发送者: {test_msg.from_agent.value}")
    print(f"   接收者: {test_msg.to_agent.value}")
    print(f"   类型: {test_msg.message_type.value}")
    
    # 添加到消息队列
    os_system.message_queue.append(test_msg)
    
    print(f"\n✅ 消息已添加到队列")
    print(f"   当前队列长度: {len(os_system.message_queue)}")
    
    # 显示最近的消息
    print(f"\n📋 最近的5条消息:")
    for msg in os_system.message_queue[-5:]:
        print(f"   - {msg.from_agent.value} → {msg.to_agent.value}: {msg.message_type.value}")


def test_world_context_update(os_system: OperatingSystem):
    """测试4: 世界上下文更新"""
    print_separator("测试4: 世界上下文管理")
    
    print("🌍 测试世界上下文更新...")
    
    # 显示当前上下文
    ctx = os_system.get_world_context()
    print(f"\n当前世界上下文:")
    print(f"   - 当前时间: {ctx.current_time}")
    print(f"   - 当前位置: {ctx.current_location}")
    print(f"   - 回合数: {ctx.world_state['turn']}")
    
    # 更新上下文
    print(f"\n🔄 更新上下文...")
    os_system.update_world_context({
        "current_time": "深夜23:00"
    })
    
    # 进入下一回合
    os_system.next_turn()
    
    # 添加事件到历史
    os_system.add_to_history({
        "type": "test_event",
        "description": "测试事件"
    })
    
    # 显示更新后的上下文
    ctx = os_system.get_world_context()
    print(f"\n更新后的世界上下文:")
    print(f"   - 当前时间: {ctx.current_time}")
    print(f"   - 回合数: {ctx.world_state['turn']}")
    print(f"   - 历史事件数: {len(os_system.game_history)}")


def main():
    """主测试流程"""
    print("\n" + "=" * 70)
    print("  🎭 Infinite Story - 第二阶段Demo测试")
    print("  测试信息中枢OS和逻辑审查官Logic的基本功能")
    print("=" * 70)
    print()
    
    try:
        # 测试1: OS初始化
        os_system = test_os_initialization()
        if not os_system:
            return
        
        # 测试2: Logic验证
        input("\n按Enter继续测试逻辑审查官...")
        logic = test_logic_validation(os_system)
        
        # 测试3: 消息路由
        input("\n按Enter继续测试消息路由...")
        test_message_routing(os_system)
        
        # 测试4: 世界上下文
        input("\n按Enter继续测试世界上下文管理...")
        test_world_context_update(os_system)
        
        # 完成
        print_separator("测试完成")
        print("✅ 所有测试通过!")
        print("\n📊 最终系统状态:")
        state = os_system.get_game_state()
        for key, value in state.items():
            print(f"   - {key}: {value}")
        
        print("\n💾 正在保存游戏状态...")
        os_system.save_game_state()
        
        print("\n🎉 第二阶段Demo测试成功!")
        print("\n下一步:")
        print("   - 实现第三阶段：光明会系统（WS/Plot/Vibe）")
        print("   - 实现第四阶段：NPC动态生成")
        print("   - 创建完整的游戏循环")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
    except Exception as e:
        logger.error(f"❌ 测试过程出错: {e}", exc_info=True)
        print(f"\n❌ 测试失败: {e}")
        print("\n请查看日志文件获取详细信息:")
        print(f"   - {settings.LOGS_DIR}/os.log")
        print(f"   - {settings.LOGS_DIR}/logic.log")


if __name__ == "__main__":
    main()
