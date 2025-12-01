"""
测试角色数据模型和验证功能

测试内容：
1. CharacterData.from_dict() - 从字典创建角色数据
2. CharacterData.to_dict() - 转换回字典
3. CharacterDataFormatter - 格式化工具类
4. validate_character_data() - 数据验证
5. get_high_importance_characters() - 高权重角色筛选

创建日期：2025-12-01
"""
import sys
from pathlib import Path
from typing import Dict, Any, List

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestCharacterDataModel:
    """角色数据模型测试类"""
    
    def __init__(self):
        """初始化测试"""
        self.results = {
            "passed": 0,
            "failed": 0,
            "tests": []
        }
        # 测试用角色数据
        self.sample_character = {
            "id": "npc_test_001",
            "name": "测试角色",
            "gender": "男",
            "age": "25岁",
            "importance": 85.0,
            "traits": ["聪明", "勇敢", "善良"],
            "behavior_rules": [
                "遇到危险时优先保护同伴",
                "对待敌人毫不留情"
            ],
            "relationship_matrix": {
                "npc_002": {
                    "address_as": "好友",
                    "attitude": "信任且亲近"
                },
                "npc_003": {
                    "address_as": "敌人",
                    "attitude": "警惕且敌视"
                }
            },
            "possessions": ["长剑", "护身符", "地图"],
            "current_appearance": "身穿铠甲的年轻战士，目光坚定",
            "voice_samples": [
                "为了正义，我绝不退缩！",
                "朋友们，跟我来！"
            ],
            "initial_state": "巡逻中"
        }
    
    def log_result(self, test_name: str, passed: bool, message: str = ""):
        """记录测试结果"""
        status = "✅ PASS" if passed else "❌ FAIL"
        self.results["tests"].append({
            "name": test_name,
            "passed": passed,
            "message": message
        })
        if passed:
            self.results["passed"] += 1
        else:
            self.results["failed"] += 1
        print(f"   {status}: {test_name}")
        if message:
            print(f"         {message}")
    
    def test_character_data_from_dict(self):
        """
        测试1: CharacterData.from_dict() 方法
        
        验证：
        - 能够正确从字典创建CharacterData对象
        - 所有字段正确映射
        - 默认值正确处理
        """
        try:
            from utils.character_data import CharacterData
            
            char = CharacterData.from_dict(self.sample_character)
            
            # 验证基本字段
            checks = [
                ("id", char.id == "npc_test_001"),
                ("name", char.name == "测试角色"),
                ("gender", char.gender == "男"),
                ("age", char.age == "25岁"),
                ("importance", char.importance == 85.0),
            ]
            
            all_passed = True
            for field, result in checks:
                if not result:
                    self.log_result(f"from_dict字段{field}", False, f"字段值不匹配")
                    all_passed = False
            
            if all_passed:
                self.log_result(
                    "CharacterData.from_dict()基本字段",
                    True,
                    f"id={char.id}, name={char.name}"
                )
            
            # 验证复杂字段
            has_traits = len(char.traits) == 3
            has_rules = len(char.behavior_rules) == 2
            has_relations = len(char.relationship_matrix) == 2
            
            self.log_result(
                "from_dict()复杂字段",
                has_traits and has_rules and has_relations,
                f"traits={len(char.traits)}, rules={len(char.behavior_rules)}, relations={len(char.relationship_matrix)}"
            )
            
            return all_passed and has_traits and has_rules and has_relations
        except Exception as e:
            self.log_result("CharacterData.from_dict()", False, f"执行失败: {e}")
            return False
    
    def test_character_data_to_dict(self):
        """
        测试2: CharacterData.to_dict() 方法
        
        验证：
        - 能够正确将CharacterData对象转换回字典
        - 转换后的字典结构正确
        - 往返转换（from_dict -> to_dict）不丢失数据
        """
        try:
            from utils.character_data import CharacterData
            
            # 往返转换
            char = CharacterData.from_dict(self.sample_character)
            result_dict = char.to_dict()
            
            # 验证关键字段
            keys_to_check = ["id", "name", "gender", "traits", "behavior_rules", "relationship_matrix"]
            
            all_match = True
            for key in keys_to_check:
                original = self.sample_character.get(key)
                converted = result_dict.get(key)
                if original != converted:
                    self.log_result(
                        f"to_dict字段{key}一致性",
                        False,
                        f"原始: {original}, 转换后: {converted}"
                    )
                    all_match = False
            
            if all_match:
                self.log_result(
                    "CharacterData.to_dict()往返转换",
                    True,
                    "所有关键字段一致"
                )
            
            return all_match
        except Exception as e:
            self.log_result("CharacterData.to_dict()", False, f"执行失败: {e}")
            return False
    
    def test_character_data_default_values(self):
        """
        测试3: CharacterData默认值处理
        
        验证：
        - 缺少字段时使用正确的默认值
        - 不会因为缺少可选字段而失败
        """
        try:
            from utils.character_data import CharacterData
            
            # 最小化数据
            minimal_data = {
                "id": "npc_minimal",
                "name": "最小角色"
            }
            
            char = CharacterData.from_dict(minimal_data)
            
            # 检查默认值
            defaults_correct = [
                ("gender", char.gender == "未知"),
                ("age", char.age == "未知"),
                ("importance", char.importance == 50.0),
                ("traits", char.traits == []),
                ("behavior_rules", char.behavior_rules == []),
                ("initial_state", char.initial_state == "日常活动"),
            ]
            
            all_correct = True
            for field, is_correct in defaults_correct:
                if not is_correct:
                    self.log_result(f"默认值{field}", False, f"默认值不正确")
                    all_correct = False
            
            if all_correct:
                self.log_result(
                    "CharacterData默认值",
                    True,
                    "所有默认值正确"
                )
            
            return all_correct
        except Exception as e:
            self.log_result("CharacterData默认值", False, f"执行失败: {e}")
            return False
    
    def test_formatter_format_traits(self):
        """
        测试4: CharacterDataFormatter.format_traits() 方法
        
        验证：
        - 正确格式化特质列表为字符串
        - 空列表返回默认值
        """
        try:
            from utils.character_data import CharacterDataFormatter
            
            # 正常列表
            traits = ["聪明", "勇敢", "善良"]
            result = CharacterDataFormatter.format_traits(traits)
            expected = "聪明, 勇敢, 善良"
            
            is_correct = result == expected
            self.log_result(
                "format_traits()正常列表",
                is_correct,
                f"结果: '{result}'"
            )
            
            # 空列表
            empty_result = CharacterDataFormatter.format_traits([])
            is_default = empty_result == "普通人"
            self.log_result(
                "format_traits()空列表默认值",
                is_default,
                f"结果: '{empty_result}'"
            )
            
            return is_correct and is_default
        except Exception as e:
            self.log_result("format_traits()", False, f"执行失败: {e}")
            return False
    
    def test_formatter_format_behavior_rules(self):
        """
        测试5: CharacterDataFormatter.format_behavior_rules() 方法
        
        验证：
        - 正确格式化行为准则列表
        - 每条规则前有项目符号
        - 空列表返回默认值
        """
        try:
            from utils.character_data import CharacterDataFormatter
            
            rules = ["规则一", "规则二"]
            result = CharacterDataFormatter.format_behavior_rules(rules)
            
            # 检查格式
            has_bullets = "- 规则一" in result and "- 规则二" in result
            self.log_result(
                "format_behavior_rules()格式正确",
                has_bullets,
                f"包含项目符号: {has_bullets}"
            )
            
            # 空列表
            empty_result = CharacterDataFormatter.format_behavior_rules([])
            is_default = empty_result == "无特殊行为准则"
            self.log_result(
                "format_behavior_rules()空列表",
                is_default,
                f"结果: '{empty_result}'"
            )
            
            return has_bullets and is_default
        except Exception as e:
            self.log_result("format_behavior_rules()", False, f"执行失败: {e}")
            return False
    
    def test_formatter_format_relationship_matrix(self):
        """
        测试6: CharacterDataFormatter.format_relationship_matrix() 方法
        
        验证：
        - 正确格式化关系矩阵
        - 包含称呼和态度信息
        - 空矩阵返回默认值
        """
        try:
            from utils.character_data import CharacterDataFormatter
            
            matrix = {
                "npc_002": {"address_as": "好友", "attitude": "信任"}
            }
            result = CharacterDataFormatter.format_relationship_matrix(matrix)
            
            # 检查格式
            has_info = "好友" in result and "信任" in result
            self.log_result(
                "format_relationship_matrix()内容正确",
                has_info,
                f"包含称呼和态度: {has_info}"
            )
            
            # 空矩阵
            empty_result = CharacterDataFormatter.format_relationship_matrix({})
            is_default = empty_result == "暂无特殊关系"
            self.log_result(
                "format_relationship_matrix()空矩阵",
                is_default,
                f"结果: '{empty_result}'"
            )
            
            return has_info and is_default
        except Exception as e:
            self.log_result("format_relationship_matrix()", False, f"执行失败: {e}")
            return False
    
    def test_formatter_format_for_prompt(self):
        """
        测试7: CharacterDataFormatter.format_for_prompt() 方法
        
        验证：
        - 返回包含所有必要字段的字典
        - 可直接用于提示词模板的 .format()
        """
        try:
            from utils.character_data import CharacterData, CharacterDataFormatter
            
            char = CharacterData.from_dict(self.sample_character)
            formatted = CharacterDataFormatter.format_for_prompt(char)
            
            # 必要的键
            required_keys = [
                "character_name", "age", "gender",
                "traits", "behavior_rules", "relationships", "voice_samples"
            ]
            
            missing = [k for k in required_keys if k not in formatted]
            has_all = len(missing) == 0
            
            self.log_result(
                "format_for_prompt()返回完整字典",
                has_all,
                f"缺少键: {missing}" if missing else f"包含所有必要键: {len(required_keys)}个"
            )
            
            # 验证可用于format
            if has_all:
                test_template = "角色{character_name}，年龄{age}"
                try:
                    formatted_str = test_template.format(**formatted)
                    can_format = "测试角色" in formatted_str
                    self.log_result(
                        "format_for_prompt()可用于模板",
                        can_format,
                        f"格式化结果: {formatted_str}"
                    )
                except KeyError as e:
                    self.log_result("format_for_prompt()可用于模板", False, f"格式化失败: {e}")
                    return False
            
            return has_all
        except Exception as e:
            self.log_result("format_for_prompt()", False, f"执行失败: {e}")
            return False
    
    def test_validate_character_data(self):
        """
        测试8: validate_character_data() 函数
        
        验证：
        - 有效数据返回 (True, [])
        - 缺少必要字段时返回错误列表
        - importance范围检查
        """
        try:
            from utils.character_data import validate_character_data
            
            # 有效数据
            is_valid, errors = validate_character_data(self.sample_character)
            self.log_result(
                "validate_character_data()有效数据",
                is_valid,
                "验证通过" if is_valid else f"错误: {errors}"
            )
            
            # 缺少id
            invalid_data = {"name": "无ID角色"}
            is_valid2, errors2 = validate_character_data(invalid_data)
            self.log_result(
                "validate_character_data()缺少id",
                not is_valid2 and any("id" in e for e in errors2),
                f"错误: {errors2}"
            )
            
            # importance超出范围
            out_of_range = {"id": "test", "name": "Test", "importance": 150.0}
            is_valid3, errors3 = validate_character_data(out_of_range)
            self.log_result(
                "validate_character_data()importance超范围",
                not is_valid3 and any("importance" in e for e in errors3),
                f"错误: {errors3}"
            )
            
            return True
        except Exception as e:
            self.log_result("validate_character_data()", False, f"执行失败: {e}")
            return False
    
    def test_get_high_importance_characters(self):
        """
        测试9: get_high_importance_characters() 函数
        
        验证：
        - 正确筛选高权重角色
        - 结果按权重降序排列
        """
        try:
            from utils.character_data import CharacterData, get_high_importance_characters
            
            # 创建测试角色列表
            chars = [
                CharacterData(id="c1", name="角色1", importance=90.0),
                CharacterData(id="c2", name="角色2", importance=50.0),
                CharacterData(id="c3", name="角色3", importance=80.0),
                CharacterData(id="c4", name="角色4", importance=75.0),
            ]
            
            # 筛选权重>=70的角色
            high = get_high_importance_characters(chars, min_importance=70.0)
            
            # 验证数量
            correct_count = len(high) == 3
            self.log_result(
                "get_high_importance_characters()筛选数量",
                correct_count,
                f"筛选结果: {len(high)}个 (预期3个)"
            )
            
            # 验证排序
            is_sorted = (
                high[0].importance >= high[1].importance >= high[2].importance
            )
            self.log_result(
                "get_high_importance_characters()降序排序",
                is_sorted,
                f"权重顺序: {[c.importance for c in high]}"
            )
            
            return correct_count and is_sorted
        except Exception as e:
            self.log_result("get_high_importance_characters()", False, f"执行失败: {e}")
            return False
    
    def test_with_real_character_data(self):
        """
        测试10: 使用真实角色数据测试
        
        从实际的角色档案中读取数据进行测试
        验证模型能正确处理实际游戏中的角色数据
        """
        try:
            from config.settings import settings
            from utils.character_data import CharacterData, CharacterDataFormatter
            import json
            
            # 查找一个真实的角色档案
            worlds_dir = settings.DATA_DIR / "worlds"
            char_file = None
            
            for world_dir in worlds_dir.iterdir():
                if world_dir.is_dir():
                    chars_dir = world_dir / "characters"
                    if chars_dir.exists():
                        for f in chars_dir.glob("character_*.json"):
                            char_file = f
                            break
                    if char_file:
                        break
            
            if not char_file:
                self.log_result("真实角色数据测试", False, "未找到角色档案文件")
                return False
            
            # 读取并解析
            with open(char_file, "r", encoding="utf-8") as f:
                char_data = json.load(f)
            
            char = CharacterData.from_dict(char_data)
            formatted = CharacterDataFormatter.format_for_prompt(char)
            
            self.log_result(
                "真实角色数据加载",
                True,
                f"角色: {char.name} (ID: {char.id})"
            )
            
            # 验证格式化结果
            has_name = formatted.get("character_name") == char.name
            has_traits = len(formatted.get("traits", "")) > 0
            
            self.log_result(
                "真实角色数据格式化",
                has_name and has_traits,
                f"name正确: {has_name}, traits非空: {has_traits}"
            )
            
            return has_name and has_traits
        except Exception as e:
            self.log_result("真实角色数据测试", False, f"执行失败: {e}")
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("🧪 角色数据模型测试")
        print("=" * 60)
        print()
        
        # 运行所有测试
        self.test_character_data_from_dict()
        self.test_character_data_to_dict()
        self.test_character_data_default_values()
        self.test_formatter_format_traits()
        self.test_formatter_format_behavior_rules()
        self.test_formatter_format_relationship_matrix()
        self.test_formatter_format_for_prompt()
        self.test_validate_character_data()
        self.test_get_high_importance_characters()
        self.test_with_real_character_data()
        
        # 打印总结
        print()
        print("=" * 60)
        print("📊 测试结果总结")
        print("=" * 60)
        print(f"   通过: {self.results['passed']}")
        print(f"   失败: {self.results['failed']}")
        print(f"   总计: {self.results['passed'] + self.results['failed']}")
        print()
        
        return self.results["failed"] == 0


def main():
    """主函数"""
    tester = TestCharacterDataModel()
    success = tester.run_all_tests()
    
    if success:
        print("✅ 所有角色数据模型测试通过！")
    else:
        print("❌ 部分测试失败，请检查代码")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())

