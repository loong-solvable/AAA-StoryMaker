"""
运行所有初始化阶段测试

这个脚本会依次运行以下测试：
1. test_config_and_settings.py - 配置和环境变量
2. test_world_data_loading.py - 世界数据加载
3. test_character_data_model.py - 角色数据模型
4. test_illuminati_init.py - 光明会初始化
5. test_character_prompt_generation.py - 角色提示词动态生成（重点）

使用方法：
    python tests/run_all_tests.py

创建日期：2025-12-01
"""
import os
import sys
import importlib.util
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# CI/离线测试默认使用 mock LLM，避免真实网络调用
os.environ.setdefault("LLM_PROVIDER", "mock")

# Windows/GBK 终端下避免编码崩溃：必须在 print 之前 reconfigure
if os.name == "nt":
    for _stream in (sys.stdout, sys.stderr):
        _reconfigure = getattr(_stream, "reconfigure", None)
        if callable(_reconfigure):
            try:
                _reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def load_and_run_test(test_file: Path, test_name: str) -> dict:
    """
    加载并运行单个测试模块
    
    Args:
        test_file: 测试文件路径
        test_name: 测试名称（用于显示）
    
    Returns:
        测试结果字典
    """
    print()
    print("=" * 70)
    print(f">  运行测试: {test_name}")
    print("=" * 70)
    
    try:
        # 动态加载模块
        spec = importlib.util.spec_from_file_location(
            test_file.stem,
            test_file
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"无法加载测试模块: {test_file}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # 运行测试
        if hasattr(module, 'main'):
            result = module.main()
            return {
                "name": test_name,
                "file": test_file.name,
                "passed": result == 0,
                "error": None
            }
        else:
            return {
                "name": test_name,
                "file": test_file.name,
                "passed": False,
                "error": "测试模块缺少main函数"
            }
    
    except Exception as e:
        return {
            "name": test_name,
            "file": test_file.name,
            "passed": False,
            "error": str(e)
        }


def main():
    """主函数：运行所有测试"""
    print()
    print("+" + "-" * 68 + "+")
    print("|" + " " * 20 + "[Test] AAA-StoryMaker 初始化测试" + " " * 19 + "|")
    print("|" + " " * 68 + "|")
    print(f"|  开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}" + " " * 35 + "|")
    print("+" + "-" * 68 + "+")
    
    tests_dir = Path(__file__).parent
    
    # 定义测试列表（按顺序执行）
    tests = [
        ("test_config_and_settings.py", "1  配置和环境设置测试"),
        ("test_world_data_loading.py", "2  世界数据加载测试"),
        ("test_character_data_model.py", "3  角色数据模型测试"),
        ("test_illuminati_init.py", "4  光明会初始化测试"),
        ("test_character_prompt_generation.py", "5  角色提示词动态生成测试（重点）"),
        ("test_file_paths_and_placeholders.py", "6  文件路径和占位符测试"),
        ("test_world_state_dynamic_update.py", "7  世界状态动态更新测试"),
    ]
    
    results = []
    
    for test_file_name, test_name in tests:
        test_file = tests_dir / test_file_name
        
        if not test_file.exists():
            results.append({
                "name": test_name,
                "file": test_file_name,
                "passed": False,
                "error": "测试文件不存在"
            })
            continue
        
        result = load_and_run_test(test_file, test_name)
        results.append(result)
    
    # 打印总结报告
    print()
    print()
    print("+" + "-" * 68 + "+")
    print("|" + " " * 25 + "[Report] 测试总结报告" + " " * 27 + "|")
    print("+" + "-" * 68 + "+")
    print()
    
    passed_count = sum(1 for r in results if r["passed"])
    failed_count = len(results) - passed_count
    
    for result in results:
        status = "PASS PASS" if result["passed"] else "FAIL FAIL"
        print(f"   {status}  {result['name']}")
        if result.get("error"):
            print(f"           错误: {result['error']}")
    
    print()
    print("-" * 70)
    print(f"   总计: {len(results)} 个测试套件")
    print(f"   通过: {passed_count}")
    print(f"   失败: {failed_count}")
    print("-" * 70)
    print()
    
    if failed_count == 0:
        print("SUCCESS 所有测试通过！项目初始化功能正常。")
        print()
        print("   已验证的功能:")
        print("   OK 配置文件和环境变量正确加载")
        print("   OK 世界数据能够完整加载")
        print("   OK 角色数据模型正确处理")
        print("   OK 光明会初始化流程正常")
        print("   OK 角色提示词能够动态特异性生成")
    else:
        print("WARNING  部分测试失败，请检查上述错误信息。")
    
    print()
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    exit(main())

