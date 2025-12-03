"""
测试增强后的JSON解析功能

验证 parse_json_response 函数能够正确处理各种格式错误的JSON响应
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agents.offline.creatorGod.utils import parse_json_response


def test_case_1_extra_data_after_json():
    """测试：JSON后面有多余内容"""
    response = '''{
  "id": "npc_003",
  "name": "亮哥",
  "gender": "男"
}
这是额外的说明文字，不应该出现在JSON中。'''
    
    try:
        result = parse_json_response(response)
        print("✅ 测试1通过：成功提取JSON（后面有多余内容）")
        print(f"   结果: {result.get('name')}")
        return True
    except Exception as e:
        print(f"❌ 测试1失败: {e}")
        return False


def test_case_2_markdown_wrapped():
    """测试：JSON被markdown包裹"""
    response = '''```json
{
  "id": "npc_001",
  "name": "测试角色"
}
```'''
    
    try:
        result = parse_json_response(response)
        print("✅ 测试2通过：成功解析markdown包裹的JSON")
        print(f"   结果: {result.get('name')}")
        return True
    except Exception as e:
        print(f"❌ 测试2失败: {e}")
        return False


def test_case_3_with_comments():
    """测试：JSON中包含注释"""
    response = '''{
  // 这是注释
  "id": "npc_002",
  "name": "测试角色2",
  /* 多行注释 */
  "gender": "女"
}'''
    
    try:
        result = parse_json_response(response)
        print("✅ 测试3通过：成功去除注释")
        print(f"   结果: {result.get('name')}")
        return True
    except Exception as e:
        print(f"❌ 测试3失败: {e}")
        return False


def test_case_4_complex_nested():
    """测试：复杂嵌套JSON，后面有多余内容"""
    response = '''{
  "id": "npc_003",
  "name": "亮哥",
  "relationship_matrix": {
    "npc_001": {
      "address_as": "南西",
      "attitude": "有趣的新同事"
    }
  },
  "voice_samples": ["台词1", "台词2"]
}
这是额外的说明文字，不应该出现在JSON中。'''
    
    try:
        result = parse_json_response(response)
        print("✅ 测试4通过：成功提取复杂嵌套JSON")
        print(f"   结果: {result.get('name')}")
        print(f"   关系矩阵: {list(result.get('relationship_matrix', {}).keys())}")
        return True
    except Exception as e:
        print(f"❌ 测试4失败: {e}")
        return False


def test_case_5_multiline_extra_data():
    """测试：多行多余内容"""
    response = '''{
  "id": "npc_004",
  "name": "小张"
}

这是第一行多余内容
这是第二行多余内容
还有更多内容...'''
    
    try:
        result = parse_json_response(response)
        print("✅ 测试5通过：成功处理多行多余内容")
        print(f"   结果: {result.get('name')}")
        return True
    except Exception as e:
        print(f"❌ 测试5失败: {e}")
        return False


def test_case_6_real_world_example():
    """测试：真实世界的错误案例（基于日志）"""
    response = '''{"id":"npc_003","name":"亮哥","gender":"男","age":"二十多岁","importance":0.3,"traits":["UI设计师","游戏爱好者","幽默八卦","办公室闲人"],"behavior_rules":["下班后戴耳机打游戏点外卖","喜欢调侃同事感情八卦","对公司外趣闻感兴趣吐槽"],"relationship_matrix":{"npc_001":{"address_as":"南西","attitude":"有趣的新同事，适合八卦对象"},"npc_002":{"address_as":"程哥","attitude":"可靠的上司，工作安排人"},"npc_004":{"address_as":"小张","attitude":"八卦搭档，办公室闲聊伙伴"}},"possessions":["耳机","电脑","外卖"],"current_appearance":"办公室里一个年轻男性UI设计师，戴着耳机，身体前倾专注打游戏，同时手指滑动点外卖，穿着随意休闲的工位日常装。","voice_samples":["那是暗恋你。"]} 这是额外的说明文字'''
    
    try:
        result = parse_json_response(response)
        print("✅ 测试6通过：成功处理真实世界的错误案例")
        print(f"   结果: {result.get('name')}")
        print(f"   ID: {result.get('id')}")
        return True
    except Exception as e:
        print(f"❌ 测试6失败: {e}")
        return False


def main():
    """运行所有测试"""
    print("=" * 60)
    print("🧪 测试增强后的JSON解析功能")
    print("=" * 60)
    print()
    
    tests = [
        test_case_1_extra_data_after_json,
        test_case_2_markdown_wrapped,
        test_case_3_with_comments,
        test_case_4_complex_nested,
        test_case_5_multiline_extra_data,
        test_case_6_real_world_example,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
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

