"""
测试 JSON 解析器的健壮性
"""
import sys
import unittest
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.json_parser import parse_json_response, safe_parse_npc_response


class TestJsonParser(unittest.TestCase):
    """测试 JSON 解析器"""
    
    def test_standard_json(self):
        """测试标准 JSON"""
        response = '{"thought": "test", "emotion": "calm"}'
        result = parse_json_response(response)
        self.assertIsNotNone(result)
        self.assertEqual(result["thought"], "test")
        self.assertEqual(result["emotion"], "calm")
    
    def test_markdown_wrapped_json(self):
        """测试带 markdown 代码块的 JSON"""
        response = '''```json
{"thought": "test", "emotion": "calm"}
```'''
        result = parse_json_response(response)
        self.assertIsNotNone(result)
        self.assertEqual(result["thought"], "test")
    
    def test_json_with_comments(self):
        """测试带注释的 JSON"""
        response = '''{
    "thought": "test",  // 内心想法
    "emotion": "calm"   /* 情绪 */
}'''
        result = parse_json_response(response)
        self.assertIsNotNone(result)
        self.assertEqual(result["thought"], "test")
    
    def test_json_with_extra_text(self):
        """测试 JSON 后面有多余文字"""
        response = '''好的，这是我的回应：
{"thought": "test", "emotion": "calm"}
希望这个回答对你有帮助。'''
        result = parse_json_response(response)
        self.assertIsNotNone(result)
        self.assertEqual(result["thought"], "test")
    
    def test_invalid_text(self):
        """测试完全无效的文本"""
        response = "这是一段普通文字，没有任何 JSON"
        result = parse_json_response(response)
        self.assertIsNone(result)
    
    def test_empty_response(self):
        """测试空响应"""
        result = parse_json_response("")
        self.assertIsNone(result)
        
        result = parse_json_response("   ")
        self.assertIsNone(result)
    
    def test_safe_parse_npc_response(self):
        """测试安全解析 NPC 响应"""
        # 有效 JSON
        response = '{"thought": "thinking", "emotion": "happy", "content": "Hello!"}'
        result = safe_parse_npc_response(response)
        self.assertEqual(result["thought"], "thinking")
        self.assertEqual(result["content"], "Hello!")
        self.assertIn("addressing_target", result)
        
        # 无效响应，应返回默认值
        response = "无效的响应"
        result = safe_parse_npc_response(response)
        self.assertIn("thought", result)
        self.assertEqual(result["thought"], "（解析失败）")


if __name__ == '__main__':
    unittest.main()
