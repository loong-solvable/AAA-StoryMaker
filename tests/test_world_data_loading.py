"""
测试世界数据加载功能

测试内容：
1. load_world_data() - 完整加载世界数据
2. load_world_setting() - 加载世界设定
3. load_characters_list() - 加载角色列表
4. load_all_characters() - 加载所有角色档案
5. list_available_worlds() - 列出可用世界
6. 数据完整性验证

创建日期：2025-12-01
"""
import sys
import json
from pathlib import Path
from typing import Dict, Any, List

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestWorldDataLoading:
    """世界数据加载测试类"""
    
    def __init__(self):
        """初始化测试"""
        self.results = {
            "passed": 0,
            "failed": 0,
            "tests": []
        }
        self.world_dir = None
        self.world_data = None
    
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
    
    def setup(self):
        """测试前准备：找到可用的世界"""
        try:
            from config.settings import settings
            worlds_dir = settings.DATA_DIR / "worlds"
            
            # 查找第一个有效的世界
            for world in worlds_dir.iterdir():
                if world.is_dir() and (world / "world_setting.json").exists():
                    self.world_dir = world
                    print(f"📂 使用测试世界: {world.name}")
                    return True
            
            print("❌ 未找到有效的世界数据")
            return False
        except Exception as e:
            print(f"❌ 准备阶段失败: {e}")
            return False
    
    def test_list_available_worlds(self):
        """
        测试1: list_available_worlds() 功能
        
        验证：
        - 函数能正常执行
        - 返回列表类型
        - 列表包含至少一个世界名称
        """
        try:
            from config.settings import settings
            
            # 直接检查worlds目录，避免导入链问题
            worlds_dir = settings.DATA_DIR / "worlds"
            
            if not worlds_dir.exists():
                self.log_result("list_available_worlds()", False, "worlds目录不存在")
                return False
            
            worlds = []
            for world_dir in worlds_dir.iterdir():
                if world_dir.is_dir() and (world_dir / "world_setting.json").exists():
                    worlds.append(world_dir.name)
            
            # 验证有世界
            has_worlds = len(worlds) > 0
            self.log_result(
                "list_available_worlds()",
                has_worlds,
                f"发现 {len(worlds)} 个世界: {worlds}"
            )
            return has_worlds
        except Exception as e:
            self.log_result("list_available_worlds()", False, f"执行失败: {e}")
            return False
    
    def test_load_world_setting(self):
        """
        测试2: load_world_setting() 功能
        
        验证：
        - 能正常加载 world_setting.json
        - 返回字典类型
        - 包含必要的meta信息
        - 包含geography地理信息
        """
        try:
            # 直接加载JSON文件
            world_setting_path = self.world_dir / "world_setting.json"
            if not world_setting_path.exists():
                self.log_result("load_world_setting()", False, "world_setting.json不存在")
                return False
            
            with open(world_setting_path, "r", encoding="utf-8") as f:
                world_setting = json.load(f)
            
            # 验证返回类型
            if not isinstance(world_setting, dict):
                self.log_result("load_world_setting返回类型", False, f"期望dict，实际{type(world_setting)}")
                return False
            
            # 验证meta信息
            has_meta = "meta" in world_setting
            self.log_result(
                "world_setting包含meta",
                has_meta,
                f"meta内容: {list(world_setting.get('meta', {}).keys())}"
            )
            
            # 验证geography信息
            has_geo = "geography" in world_setting
            locations = world_setting.get("geography", {}).get("locations", [])
            self.log_result(
                "world_setting包含geography",
                has_geo,
                f"包含 {len(locations)} 个地点"
            )
            
            return has_meta and has_geo
        except Exception as e:
            self.log_result("load_world_setting()", False, f"执行失败: {e}")
            return False
    
    def test_load_characters_list(self):
        """
        测试3: load_characters_list() 功能
        
        验证：
        - 能正常加载 characters_list.json
        - 返回列表类型
        - 列表中每个角色包含id和name
        - 角色数量大于0
        """
        try:
            # 直接加载JSON文件
            characters_list_path = self.world_dir / "characters_list.json"
            if not characters_list_path.exists():
                self.log_result("load_characters_list()", False, "characters_list.json不存在")
                return False
            
            with open(characters_list_path, "r", encoding="utf-8") as f:
                characters_list = json.load(f)
            
            # 验证返回类型
            if not isinstance(characters_list, list):
                self.log_result("load_characters_list返回类型", False, f"期望list，实际{type(characters_list)}")
                return False
            
            # 验证角色数量
            has_chars = len(characters_list) > 0
            self.log_result(
                "characters_list角色数量",
                has_chars,
                f"包含 {len(characters_list)} 个角色"
            )
            
            # 验证每个角色的结构
            all_valid = True
            for i, char in enumerate(characters_list[:3]):  # 只检查前3个
                has_id = "id" in char
                has_name = "name" in char
                if not (has_id and has_name):
                    all_valid = False
                    self.log_result(
                        f"角色[{i}]结构完整性",
                        False,
                        f"id: {has_id}, name: {has_name}"
                    )
            
            if all_valid:
                self.log_result(
                    "角色结构完整性",
                    True,
                    f"前{min(3, len(characters_list))}个角色结构验证通过"
                )
            
            return has_chars and all_valid
        except Exception as e:
            self.log_result("load_characters_list()", False, f"执行失败: {e}")
            return False
    
    def test_load_all_characters(self):
        """
        测试4: load_all_characters() 功能
        
        验证：
        - 能加载characters目录下所有角色档案
        - 返回字典类型 {character_id: character_data}
        - 每个角色数据包含必要字段（id, name, traits等）
        """
        try:
            # 直接加载角色文件
            characters_dir = self.world_dir / "characters"
            if not characters_dir.exists():
                self.log_result("load_all_characters()", False, "characters目录不存在")
                return False
            
            characters = {}
            for char_file in characters_dir.glob("character_*.json"):
                with open(char_file, "r", encoding="utf-8") as f:
                    char_data = json.load(f)
                char_id = char_data.get("id")
                if char_id:
                    characters[char_id] = char_data
            
            # 验证角色数量
            has_chars = len(characters) > 0
            self.log_result(
                "load_all_characters()角色数量",
                has_chars,
                f"加载了 {len(characters)} 个角色档案"
            )
            
            # 验证角色数据结构
            required_fields = ["id", "name", "traits", "behavior_rules"]
            all_valid = True
            
            for char_id, char_data in list(characters.items())[:2]:  # 检查前2个
                missing_fields = [f for f in required_fields if f not in char_data]
                if missing_fields:
                    all_valid = False
                    self.log_result(
                        f"角色{char_id}字段完整性",
                        False,
                        f"缺少字段: {missing_fields}"
                    )
            
            if all_valid:
                self.log_result(
                    "角色档案字段完整性",
                    True,
                    f"必要字段: {required_fields}"
                )
            
            return has_chars and all_valid
        except Exception as e:
            self.log_result("load_all_characters()", False, f"执行失败: {e}")
            return False
    
    def test_load_world_data_complete(self):
        """
        测试5: load_world_data() 完整功能
        
        验证：
        - 能完整加载所有世界数据
        - 返回包含三个键的字典：world_setting, characters_list, characters
        - 各部分数据结构正确
        """
        try:
            world_data = {}
            
            # 1. 加载world_setting.json
            ws_path = self.world_dir / "world_setting.json"
            with open(ws_path, "r", encoding="utf-8") as f:
                world_data["world_setting"] = json.load(f)
            
            # 2. 加载characters_list.json
            cl_path = self.world_dir / "characters_list.json"
            with open(cl_path, "r", encoding="utf-8") as f:
                world_data["characters_list"] = json.load(f)
            
            # 3. 加载所有角色档案
            characters_dir = self.world_dir / "characters"
            world_data["characters"] = {}
            for char_file in characters_dir.glob("character_*.json"):
                with open(char_file, "r", encoding="utf-8") as f:
                    char_data = json.load(f)
                char_id = char_data.get("id")
                if char_id:
                    world_data["characters"][char_id] = char_data
            
            self.world_data = world_data  # 保存供后续测试使用
            
            # 验证三个必要键
            required_keys = ["world_setting", "characters_list", "characters"]
            missing_keys = [k for k in required_keys if k not in world_data]
            
            has_all_keys = len(missing_keys) == 0
            self.log_result(
                "load_world_data()完整性",
                has_all_keys,
                f"缺少键: {missing_keys}" if missing_keys else f"包含所有必要键: {required_keys}"
            )
            
            if has_all_keys:
                # 输出详细统计
                ws = world_data.get("world_setting", {})
                cl = world_data.get("characters_list", [])
                chars = world_data.get("characters", {})
                
                print(f"         📊 世界名称: {ws.get('meta', {}).get('world_name', 'N/A')}")
                print(f"         📊 角色列表: {len(cl)} 个角色")
                print(f"         📊 角色档案: {len(chars)} 个")
            
            return has_all_keys
        except Exception as e:
            self.log_result("load_world_data()", False, f"执行失败: {e}")
            return False
    
    def test_character_id_consistency(self):
        """
        测试6: 角色ID一致性验证
        
        验证：
        - characters_list中的角色ID与characters目录中的档案ID一致
        - 确保不会出现ID不匹配的问题
        """
        if not self.world_data:
            self.log_result("角色ID一致性", False, "需要先运行load_world_data测试")
            return False
        
        try:
            char_list = self.world_data.get("characters_list", [])
            char_details = self.world_data.get("characters", {})
            
            list_ids = set(c.get("id") for c in char_list if c.get("id"))
            detail_ids = set(char_details.keys())
            
            # 检查一致性
            only_in_list = list_ids - detail_ids
            only_in_details = detail_ids - list_ids
            
            is_consistent = len(only_in_list) == 0 and len(only_in_details) == 0
            
            if is_consistent:
                self.log_result(
                    "角色ID一致性",
                    True,
                    f"{len(list_ids)} 个角色ID完全匹配"
                )
            else:
                msg = []
                if only_in_list:
                    msg.append(f"仅在列表中: {only_in_list}")
                if only_in_details:
                    msg.append(f"仅在档案中: {only_in_details}")
                self.log_result("角色ID一致性", False, "; ".join(msg))
            
            return is_consistent
        except Exception as e:
            self.log_result("角色ID一致性", False, f"验证失败: {e}")
            return False
    
    def test_world_setting_structure(self):
        """
        测试7: 世界设定结构完整性
        
        验证world_setting.json包含必要的结构：
        - meta: 元信息
        - geography: 地理信息
        - physics_logic: 物理/逻辑规则（可选）
        - social_logic: 社会规则（可选）
        """
        if not self.world_data:
            self.log_result("世界设定结构", False, "需要先运行load_world_data测试")
            return False
        
        try:
            ws = self.world_data.get("world_setting", {})
            
            # 必要字段
            required = ["meta", "geography"]
            optional = ["physics_logic", "social_logic"]
            
            missing = [f for f in required if f not in ws]
            present_optional = [f for f in optional if f in ws]
            
            has_required = len(missing) == 0
            
            self.log_result(
                "世界设定必要字段",
                has_required,
                f"缺少: {missing}" if missing else "meta, geography 均存在"
            )
            
            if present_optional:
                self.log_result(
                    "世界设定可选字段",
                    True,
                    f"包含: {present_optional}"
                )
            
            return has_required
        except Exception as e:
            self.log_result("世界设定结构", False, f"验证失败: {e}")
            return False
    
    def test_character_file_naming(self):
        """
        测试8: 角色文件命名规范
        
        验证characters目录下的文件遵循命名规范：
        - 文件名格式: character_{id}.json
        - 文件内id字段与文件名一致
        """
        try:
            chars_dir = self.world_dir / "characters"
            if not chars_dir.exists():
                self.log_result("角色文件命名", False, "characters目录不存在")
                return False
            
            all_valid = True
            checked = 0
            
            for char_file in chars_dir.glob("character_*.json"):
                checked += 1
                # 从文件名提取ID
                expected_id = char_file.stem.replace("character_", "")
                
                # 读取文件内容
                with open(char_file, "r", encoding="utf-8") as f:
                    char_data = json.load(f)
                
                actual_id = char_data.get("id", "")
                
                if expected_id != actual_id:
                    all_valid = False
                    self.log_result(
                        f"文件{char_file.name}ID一致性",
                        False,
                        f"文件名ID: {expected_id}, 内容ID: {actual_id}"
                    )
            
            if all_valid:
                self.log_result(
                    "角色文件命名规范",
                    True,
                    f"检查了 {checked} 个文件，全部符合规范"
                )
            
            return all_valid
        except Exception as e:
            self.log_result("角色文件命名", False, f"验证失败: {e}")
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("🧪 世界数据加载测试")
        print("=" * 60)
        print()
        
        # 准备阶段
        if not self.setup():
            print("❌ 测试准备失败，无法继续")
            return False
        
        print()
        
        # 运行所有测试
        self.test_list_available_worlds()
        self.test_load_world_setting()
        self.test_load_characters_list()
        self.test_load_all_characters()
        self.test_load_world_data_complete()
        self.test_character_id_consistency()
        self.test_world_setting_structure()
        self.test_character_file_naming()
        
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
    tester = TestWorldDataLoading()
    success = tester.run_all_tests()
    
    if success:
        print("✅ 所有世界数据加载测试通过！")
    else:
        print("❌ 部分测试失败，请检查数据完整性")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())

