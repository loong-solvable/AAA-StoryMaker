"""
测试角色动态初始化功能

测试 OS Agent 的 initialize_first_appearance_characters 方法
"""
import sys
import json
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def test_character_initialization():
    """测试首次出场角色初始化"""
    print("=" * 60)
    print("开始测试角色动态初始化功能")
    print("=" * 60)
    
    # 延迟导入，避免模块链的问题
    from config.settings import settings
    
    # 直接导入 os_agent 模块，不经过 __init__.py
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "os_agent",
        PROJECT_ROOT / "agents" / "online" / "layer1" / "os_agent.py"
    )
    os_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(os_module)
    OperatingSystem = os_module.OperatingSystem
    
    # 1. 创建 OS 实例
    print("\n1. 创建 OS 实例...")
    os_agent = OperatingSystem()
    print("   ✅ OS 实例创建成功")
    
    # 2. 设置路径
    runtime_dir = settings.DATA_DIR / "runtime" / "江城市_20251128_183246"
    world_dir = settings.DATA_DIR / "worlds" / "江城市"
    
    print(f"\n2. 路径配置:")
    print(f"   运行时目录: {runtime_dir}")
    print(f"   世界目录: {world_dir}")
    
    # 3. 检查目录是否存在
    if not runtime_dir.exists():
        print(f"   ❌ 运行时目录不存在: {runtime_dir}")
        return False
    
    if not world_dir.exists():
        print(f"   ❌ 世界目录不存在: {world_dir}")
        return False
    
    print("   ✅ 目录检查通过")
    
    # 4. 执行初始化
    print("\n3. 执行角色初始化...")
    results = os_agent.initialize_first_appearance_characters(
        runtime_dir=runtime_dir,
        world_dir=world_dir
    )
    
    # 5. 检查结果
    print("\n4. 初始化结果:")
    
    if "error" in results:
        print(f"   ❌ 初始化失败: {results['error']}")
        return False
    
    # 显示成功初始化的角色
    for char in results.get("initialized", []):
        print(f"   ✅ 成功: {char['name']} ({char['id']})")
        print(f"      - Agent文件: {Path(char['agent_file']).name}")
        print(f"      - 提示词文件: {Path(char['prompt_file']).name}")
    
    # 显示失败的角色
    for char in results.get("failed", []):
        print(f"   ❌ 失败: {char.get('name', char['id'])} - {char['error']}")
    
    # 6. 验证生成的文件
    print("\n5. 验证生成的文件...")
    
    layer3_dir = PROJECT_ROOT / "agents" / "online" / "layer3"
    prompts_dir = settings.PROMPTS_DIR / "online"
    
    all_files_exist = True
    for char in results.get("initialized", []):
        char_id = char["id"]
        char_name = char["name"]
        
        # 检查 agent.py 文件
        agent_file = layer3_dir / f"{char_id}_{char_name}.py"
        if agent_file.exists():
            print(f"   ✅ Agent文件存在: {agent_file.name}")
        else:
            print(f"   ❌ Agent文件不存在: {agent_file}")
            all_files_exist = False
        
        # 检查提示词文件
        prompt_file = prompts_dir / f"{char_id}_{char_name}.txt"
        if prompt_file.exists():
            print(f"   ✅ 提示词文件存在: {prompt_file.name}")
        else:
            print(f"   ❌ 提示词文件不存在: {prompt_file}")
            all_files_exist = False
    
    # 7. 验证 Agent 是否已注册
    print("\n6. 验证Agent注册状态...")
    registered_chars = os_agent.get_initialized_characters()
    print(f"   已注册的角色: {registered_chars}")
    
    # 8. 显示生成的提示词内容预览
    print("\n7. 提示词内容预览:")
    for char in results.get("initialized", []):
        char_id = char["id"]
        char_name = char["name"]
        prompt_file = prompts_dir / f"{char_id}_{char_name}.txt"
        if prompt_file.exists():
            with open(prompt_file, "r", encoding="utf-8") as f:
                content = f.read()
            print(f"\n   --- {char_name} 的提示词 ({prompt_file.name}) ---")
            # 只显示前500字符
            preview = content[:500] + "..." if len(content) > 500 else content
            for line in preview.split("\n"):
                print(f"   {line}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    
    return len(results.get("initialized", [])) > 0 and all_files_exist


if __name__ == "__main__":
    try:
        success = test_character_initialization()
        print(f"\n测试结果: {'成功 ✅' if success else '失败 ❌'}")
    except Exception as e:
        print(f"\n测试异常: {e}")
        import traceback
        traceback.print_exc()
