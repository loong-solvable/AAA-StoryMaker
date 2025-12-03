"""
测试改进后的 escape_braces 函数，确保不会双重转义
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agents.offline.creatorGod.utils import escape_braces


def test_case_1_single_braces():
    """测试：单个大括号应该被转义"""
    text = '{"id": "test", "name": "value"}'
    result = escape_braces(text)
    expected = '{{"id": "test", "name": "value"}}'
    assert result == expected, f"期望: {expected}, 实际: {result}"
    print("✅ 测试1通过：单个大括号正确转义")


def test_case_2_already_escaped():
    """测试：已经转义的大括号不应该再次转义"""
    text = '{{"id": "test", "name": "value"}}'
    result = escape_braces(text)
    expected = '{{"id": "test", "name": "value"}}'
    assert result == expected, f"期望: {expected}, 实际: {result}"
    print("✅ 测试2通过：已转义的大括号不会被双重转义")


def test_case_3_mixed():
    """测试：混合情况"""
    text = '{{"id": "test"}}, {"other": "value"}'
    result = escape_braces(text)
    expected = '{{"id": "test"}}, {{"other": "value"}}'
    assert result == expected, f"期望: {expected}, 实际: {result}"
    print("✅ 测试3通过：混合情况正确处理")


def test_case_4_after_placeholder_replacement():
    """测试：占位符被替换后的情况（实际使用场景）"""
    # 在实际使用中，占位符会在调用 escape_braces 之前被替换
    # 例如："{target_name}" 会被替换为 "角色名"
    text = '{"id": "npc_001", "name": "角色名"}'
    result = escape_braces(text)
    expected = '{{"id": "npc_001", "name": "角色名"}}'
    assert result == expected, f"期望: {expected}, 实际: {result}"
    print("✅ 测试4通过：占位符替换后的情况正确处理")


def test_case_5_complex_json():
    """测试：复杂JSON结构"""
    text = '''{{
  "id": "npc_001",
  "relationship_matrix": {{
    "npc_002": {{
      "address_as": "test"
    }}
  }}
}}'''
    result = escape_braces(text)
    # 应该保持原样，因为已经是转义后的格式
    expected = text
    assert result == expected, f"期望: {expected}, 实际: {result}"
    print("✅ 测试5通过：复杂JSON结构正确处理")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("🧪 测试改进后的 escape_braces 函数")
    print("=" * 60)
    print()
    
    tests = [
        test_case_1_single_braces,
        test_case_2_already_escaped,
        test_case_3_mixed,
        test_case_4_after_placeholder_replacement,
        test_case_5_complex_json,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"❌ {test_func.__name__} 失败: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ {test_func.__name__} 异常: {e}")
            failed += 1
        print()
    
    print("=" * 60)
    print(f"📊 测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

