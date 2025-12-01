"""
测试剧本拆分功能

测试 OS Agent 的 dispatch_script_to_actors 方法
"""
import sys
import json
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def test_script_dispatch():
    """测试剧本拆分功能"""
    print("=" * 60)
    print("开始测试剧本拆分功能")
    print("=" * 60)
    
    # 延迟导入
    from config.settings import settings
    
    # 直接导入 os_agent 模块
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
    
    print(f"\n2. 运行时目录: {runtime_dir}")
    
    # 3. 检查必要文件
    print("\n3. 检查必要文件...")
    required_files = [
        runtime_dir / "plot" / "current_scene.json",
        runtime_dir / "plot" / "current_script.json",
        runtime_dir / "ws" / "world_state.json"
    ]
    
    all_exist = True
    for f in required_files:
        if f.exists():
            print(f"   ✅ {f.name}")
        else:
            print(f"   ❌ {f.name} 不存在")
            all_exist = False
    
    if not all_exist:
        print("\n❌ 缺少必要文件，测试终止")
        return False
    
    # 4. 执行剧本拆分
    print("\n4. 执行剧本拆分...")
    print("   (调用 LLM 中，请稍候...)")
    
    results = os_agent.dispatch_script_to_actors(runtime_dir)
    
    # 5. 检查结果
    print("\n5. 拆分结果:")
    
    if not results.get("success"):
        print(f"   ❌ 拆分失败: {results.get('error', '未知错误')}")
        return False
    
    print(f"   ✅ 拆分成功")
    print(f"   📋 全局上下文: {results.get('global_context', '')[:100]}...")
    
    # 显示生成的小剧本
    print("\n6. 生成的小剧本:")
    for npc_id, script_path in results.get("actor_scripts", {}).items():
        print(f"   📝 {npc_id}: {Path(script_path).name}")
    
    # 显示归档的旧剧本
    if results.get("archived"):
        print("\n7. 归档的旧剧本:")
        for archived in results["archived"]:
            print(f"   📦 {Path(archived).name}")
    
    # 8. 查看生成的小剧本内容
    print("\n8. 小剧本内容预览:")
    npc_dir = runtime_dir / "npc"
    
    for script_file in npc_dir.glob("*_script.json"):
        print(f"\n   --- {script_file.name} ---")
        with open(script_file, "r", encoding="utf-8") as f:
            content = json.load(f)
        
        # 显示关键信息
        print(f"   角色: {content.get('character_name', '未知')}")
        mission = content.get("mission", {})
        print(f"   角色定位: {mission.get('role_in_scene', '未知')}")
        print(f"   核心目标: {mission.get('objective', '未知')}")
        print(f"   情绪曲线: {mission.get('emotional_arc', '未知')}")
        print(f"   关键话题: {mission.get('key_topics', [])}")
        print(f"   预定结局: {mission.get('outcome_direction', '未知')}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    try:
        success = test_script_dispatch()
        print(f"\n测试结果: {'成功 ✅' if success else '失败 ❌'}")
    except Exception as e:
        print(f"\n测试异常: {e}")
        import traceback
        traceback.print_exc()

