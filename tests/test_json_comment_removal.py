"""
测试JSON注释移除功能
验证_parse_json_response能否正确处理带注释的JSON
"""
import json
import re


def remove_json_comments(response: str) -> str:
    """移除JSON中的注释"""
    # 处理单行注释：// ...
    response = re.sub(r'//.*?(?=\n|$)', '', response)
    # 处理多行注释：/* ... */
    response = re.sub(r'/\*.*?\*/', '', response, flags=re.DOTALL)
    # 移除空行和多余空白
    response = '\n'.join(line for line in response.split('\n') if line.strip())
    return response


def test_single_line_comments():
    """测试单行注释移除"""
    json_with_comments = """{
  // This is a comment
  "name": "test",
  "value": 123  // inline comment
}"""
    
    cleaned = remove_json_comments(json_with_comments)
    print("测试1：单行注释")
    print("原始JSON:")
    print(json_with_comments)
    print("\n清理后:")
    print(cleaned)
    
    try:
        data = json.loads(cleaned)
        print("\n✅ 解析成功！")
        print(f"数据: {data}")
        return True
    except json.JSONDecodeError as e:
        print(f"\n❌ 解析失败: {e}")
        return False


def test_multi_line_comments():
    """测试多行注释移除"""
    json_with_comments = """{
  /* This is a 
     multi-line comment */
  "name": "test",
  "value": 123
}"""
    
    cleaned = remove_json_comments(json_with_comments)
    print("\n" + "="*60)
    print("测试2：多行注释")
    print("原始JSON:")
    print(json_with_comments)
    print("\n清理后:")
    print(cleaned)
    
    try:
        data = json.loads(cleaned)
        print("\n✅ 解析成功！")
        print(f"数据: {data}")
        return True
    except json.JSONDecodeError as e:
        print(f"\n❌ 解析失败: {e}")
        return False


def test_complex_json():
    """测试复杂的带注释JSON（模拟LLM实际返回）"""
    json_with_comments = """{
  // ==========================================
  // 1. 核心元数据 (Meta Control)
  // ==========================================
  "meta": {
    "world_name": "江城迷局",
    "genre_type": "REALISTIC",
    "description": "2024年现代都市背景下，AI工程师与记者联手揭露科技巨头数据交易阴谋的故事"
  },

  // ==========================================
  // 2. 物理与逻辑法则 (Physics & Logic)
  // 核心消费者: 逻辑审查官 (Logic Firewall)
  // ==========================================
  "physics_logic": {
    // 基础物理模式
    "mode": "STANDARD_REALITY",
    "rules": [
      "遵循现实世界物理法则",
      "无超自然现象"
    ]
  },

  /* 地点信息 */
  "locations": [
    {
      "name": "江城",
      "type": "城市"  // 主要场景
    }
  ]
}"""
    
    cleaned = remove_json_comments(json_with_comments)
    print("\n" + "="*60)
    print("测试3：复杂JSON（模拟LLM返回）")
    print("原始JSON（前300字符）:")
    print(json_with_comments[:300] + "...")
    print("\n清理后（前300字符）:")
    print(cleaned[:300] + "...")
    
    try:
        data = json.loads(cleaned)
        print("\n✅ 解析成功！")
        print(f"元数据: {data.get('meta', {})}")
        print(f"地点数量: {len(data.get('locations', []))}")
        return True
    except json.JSONDecodeError as e:
        print(f"\n❌ 解析失败: {e}")
        print("\n完整清理后内容:")
        print(cleaned)
        return False


def main():
    """运行所有测试"""
    print("="*60)
    print("🧪 JSON注释移除功能测试")
    print("="*60)
    
    results = []
    
    results.append(("单行注释", test_single_line_comments()))
    results.append(("多行注释", test_multi_line_comments()))
    results.append(("复杂JSON", test_complex_json()))
    
    print("\n" + "="*60)
    print("📊 测试结果汇总")
    print("="*60)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n🎉 所有测试通过！JSON注释移除功能正常工作。")
    else:
        print("\n⚠️  部分测试失败，需要调整正则表达式。")


if __name__ == "__main__":
    main()



