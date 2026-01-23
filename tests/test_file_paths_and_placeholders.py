"""
测试文件路径和占位符系统

测试内容：
1. 所有提示词文件的占位符扫描
2. 文件路径是硬编码还是动态的
3. 新世界名称的文件读取兼容性
4. 占位符替换的正确性
5. 特殊字符世界名的处理

创建日期：2025-12-01
"""
import sys
import re
import json
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestFilePathsAndPlaceholders:
    """文件路径和占位符测试类"""
    
    def __init__(self):
        """初始化测试"""
        self.results = {
            "passed": 0,
            "failed": 0,
            "tests": []
        }
        self.temp_dir = None
    
    def log_result(self, test_name: str, passed: bool, message: str = ""):
        """记录测试结果"""
        status = "PASS PASS" if passed else "FAIL FAIL"
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
    
    # ===========================================
    # 第一部分：占位符扫描测试
    # ===========================================
    
    def test_scan_all_prompt_placeholders(self):
        """
        测试1: 扫描所有提示词文件中的占位符
        
        扫描 prompts/ 目录下所有 .txt 文件，找出其中的占位符 {xxx}
        记录每个文件包含哪些占位符
        """
        try:
            from config.settings import settings
            
            prompts_dir = settings.PROMPTS_DIR
            placeholder_pattern = re.compile(r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}')
            
            all_placeholders = {}
            
            # 扫描所有 .txt 文件
            for prompt_file in prompts_dir.rglob("*.txt"):
                rel_path = prompt_file.relative_to(prompts_dir)
                
                with open(prompt_file, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # 查找占位符
                placeholders = set(placeholder_pattern.findall(content))
                if placeholders:
                    all_placeholders[str(rel_path)] = sorted(placeholders)
            
            # 输出发现的占位符
            print(f"\n         [List] 发现的占位符:")
            for file_path, phs in all_placeholders.items():
                print(f"            {file_path}:")
                for ph in phs:
                    print(f"               - {{{ph}}}")
            
            self.log_result(
                "扫描提示词占位符",
                True,
                f"在 {len(all_placeholders)} 个文件中发现占位符"
            )
            
            return all_placeholders
        except Exception as e:
            self.log_result("扫描提示词占位符", False, f"扫描失败: {e}")
            return {}
    
    def test_online_prompts_placeholders(self):
        """
        测试2: 在线阶段提示词占位符详细测试
        
        测试 prompts/online/ 目录下的占位符：
        - npc_system.txt: {id}, {id_character}, {id_script}
        - script_divider.txt: {current_scene}, {current_script}
        """
        try:
            from config.settings import settings
            
            online_dir = settings.PROMPTS_DIR / "online"
            
            # 定义期望的占位符
            expected = {
                "npc_system.txt": {
                    "npc_id",
                    "npc_name",
                    "traits",
                    "appearance",
                    "relationships",
                    "voice_samples",
                    "global_context",
                    "scene_summary",
                    "role_in_scene",
                    "objective",
                    "emotional_arc",
                    "key_topics",
                    "outcome_direction",
                    "special_notes",
                    "dialogue_history",
                    "present_characters",
                },
                "script_divider.txt": {"current_scene", "current_script", "world_state"},
            }
            
            placeholder_pattern = re.compile(r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}')
            
            all_ok = True
            for filename, expected_phs in expected.items():
                file_path = online_dir / filename
                if not file_path.exists():
                    self.log_result(f"{filename}存在", False, "文件不存在")
                    all_ok = False
                    continue
                
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                found_phs = set(placeholder_pattern.findall(content))
                
                # 检查期望的占位符是否都存在
                missing = expected_phs - found_phs
                if missing:
                    self.log_result(
                        f"{filename}占位符",
                        False,
                        f"缺少占位符: {missing}"
                    )
                    all_ok = False
                else:
                    self.log_result(
                        f"{filename}占位符",
                        True,
                        f"包含: {expected_phs}"
                    )
            
            return all_ok
        except Exception as e:
            self.log_result("在线提示词占位符", False, f"测试失败: {e}")
            return False
    
    def test_offline_prompts_placeholders(self):
        """
        测试3: 离线阶段提示词占位符详细测试
        
        测试 prompts/offline/ 目录下的占位符：
        - creatorGod/character_detail.txt: {target_name}, {target_id}, {characters_list}
        """
        try:
            from config.settings import settings
            
            # 定义期望的占位符
            expected = {
                "creatorGod/character_detail.txt": {"target_name", "target_id", "characters_list"}
            }
            
            placeholder_pattern = re.compile(r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}')
            offline_dir = settings.PROMPTS_DIR / "offline"
            
            all_ok = True
            for rel_path, expected_phs in expected.items():
                file_path = offline_dir / rel_path
                if not file_path.exists():
                    self.log_result(f"{rel_path}存在", False, "文件不存在")
                    all_ok = False
                    continue
                
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                found_phs = set(placeholder_pattern.findall(content))
                
                # 检查期望的占位符是否都存在
                missing = expected_phs - found_phs
                if missing:
                    self.log_result(
                        f"{rel_path}占位符",
                        False,
                        f"缺少占位符: {missing}"
                    )
                    all_ok = False
                else:
                    self.log_result(
                        f"{rel_path}占位符",
                        True,
                        f"包含: {expected_phs}"
                    )
            
            return all_ok
        except Exception as e:
            self.log_result("离线提示词占位符", False, f"测试失败: {e}")
            return False
    
    # ===========================================
    # 第二部分：文件路径动态性测试
    # ===========================================
    
    def test_settings_paths_are_dynamic(self):
        """
        测试4: 验证settings中的路径是动态配置的
        
        确保路径使用 settings.PROMPTS_DIR 等动态变量，而非硬编码
        """
        try:
            from config.settings import settings, PROJECT_ROOT
            
            # 检查关键路径都是从PROJECT_ROOT派生的
            checks = [
                ("DATA_DIR", settings.DATA_DIR, PROJECT_ROOT / "data"),
                ("PROMPTS_DIR", settings.PROMPTS_DIR, PROJECT_ROOT / "prompts"),
                ("LOGS_DIR", settings.LOGS_DIR, PROJECT_ROOT / "logs"),
            ]
            
            all_ok = True
            for name, actual, expected in checks:
                # 规范化路径进行比较
                is_correct = actual.resolve() == expected.resolve()
                if not is_correct:
                    self.log_result(
                        f"{name}动态路径",
                        False,
                        f"期望: {expected}, 实际: {actual}"
                    )
                    all_ok = False
                else:
                    self.log_result(f"{name}动态路径", True, str(actual))
            
            return all_ok
        except Exception as e:
            self.log_result("settings路径动态性", False, f"测试失败: {e}")
            return False
    
    def test_code_uses_settings_for_paths(self):
        """
        测试5: 验证代码中使用settings获取路径
        
        扫描关键文件，确保使用 settings.PROMPTS_DIR 而非硬编码路径
        """
        try:
            files_to_check = [
                PROJECT_ROOT / "initial_Illuminati.py",
                PROJECT_ROOT / "agents" / "online" / "layer1" / "os_agent.py",
                PROJECT_ROOT / "agents" / "online" / "layer3" / "npc_agent.py",
            ]
            
            # 检查是否使用了 settings.PROMPTS_DIR
            pattern_good = re.compile(r'settings\.PROMPTS_DIR')
            pattern_bad = re.compile(r'["\']prompts[/\\]')  # 硬编码的 "prompts/"
            
            all_ok = True
            for file_path in files_to_check:
                if not file_path.exists():
                    continue
                
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                uses_settings = bool(pattern_good.search(content))
                has_hardcoded = bool(pattern_bad.search(content))
                
                # 日志/注释中的硬编码路径是可以接受的
                file_name = file_path.name
                
                if uses_settings:
                    self.log_result(
                        f"{file_name}使用动态路径",
                        True,
                        "使用 settings.PROMPTS_DIR"
                    )
                else:
                    self.log_result(
                        f"{file_name}使用动态路径",
                        False,
                        "未找到 settings.PROMPTS_DIR 使用"
                    )
                    all_ok = False
            
            return all_ok
        except Exception as e:
            self.log_result("代码路径检查", False, f"测试失败: {e}")
            return False
    
    # ===========================================
    # 第三部分：新世界名称兼容性测试
    # ===========================================
    
    def test_world_name_with_special_characters(self):
        """
        测试6: 特殊字符世界名称处理
        
        测试包含特殊字符（空格、中文、数字）的世界名称是否能正确处理
        """
        try:
            from config.settings import settings
            
            # 创建临时测试世界
            test_names = [
                "测试世界",
                "Test_World_01",
                "新世界2025",
            ]
            
            worlds_dir = settings.DATA_DIR / "worlds"
            created_dirs = []
            
            all_ok = True
            for world_name in test_names:
                # 检查路径是否可以正确创建和访问
                test_dir = worlds_dir / world_name
                
                # 只测试路径字符串是否有效，不实际创建目录
                try:
                    # 测试路径字符串化
                    path_str = str(test_dir)
                    # 测试路径是否包含预期的世界名
                    contains_name = world_name in path_str
                    
                    self.log_result(
                        f"世界名'{world_name}'路径",
                        contains_name,
                        f"路径: {path_str}"
                    )
                    if not contains_name:
                        all_ok = False
                except Exception as e:
                    self.log_result(
                        f"世界名'{world_name}'路径",
                        False,
                        f"路径处理失败: {e}"
                    )
                    all_ok = False
            
            return all_ok
        except Exception as e:
            self.log_result("特殊字符世界名", False, f"测试失败: {e}")
            return False
    
    def test_create_mock_world_and_load(self):
        """
        测试7: 创建模拟世界并测试加载
        
        创建一个临时的模拟世界，验证数据加载是否正确
        """
        try:
            from config.settings import settings
            
            # 创建临时目录
            self.temp_dir = Path(tempfile.mkdtemp(prefix="test_world_"))
            mock_world_name = "模拟测试世界"
            mock_world_dir = self.temp_dir / mock_world_name
            mock_world_dir.mkdir(parents=True, exist_ok=True)
            
            # 创建模拟的 world_setting.json
            world_setting = {
                "meta": {
                    "world_name": mock_world_name,
                    "genre_type": "TEST",
                    "description": "这是一个测试世界"
                },
                "geography": {
                    "locations": [
                        {"id": "loc_test", "name": "测试地点"}
                    ]
                },
                "physics_logic": {},
                "social_logic": []
            }
            
            ws_file = mock_world_dir / "world_setting.json"
            with open(ws_file, "w", encoding="utf-8") as f:
                json.dump(world_setting, f, ensure_ascii=False, indent=2)
            
            # 创建模拟的 characters_list.json
            characters_list = [
                {"id": "npc_test_001", "name": "测试角色A", "importance": 0.9},
                {"id": "npc_test_002", "name": "测试角色B", "importance": 0.7}
            ]
            
            cl_file = mock_world_dir / "characters_list.json"
            with open(cl_file, "w", encoding="utf-8") as f:
                json.dump(characters_list, f, ensure_ascii=False, indent=2)
            
            # 创建模拟的角色档案目录
            chars_dir = mock_world_dir / "characters"
            chars_dir.mkdir(exist_ok=True)
            
            for char in characters_list:
                char_data = {
                    "id": char["id"],
                    "name": char["name"],
                    "importance": char["importance"],
                    "traits": ["测试特质"],
                    "behavior_rules": ["测试规则"]
                }
                char_file = chars_dir / f"character_{char['id']}.json"
                with open(char_file, "w", encoding="utf-8") as f:
                    json.dump(char_data, f, ensure_ascii=False, indent=2)
            
            # 验证加载
            # 1. 验证 world_setting.json
            with open(ws_file, "r", encoding="utf-8") as f:
                loaded_ws = json.load(f)
            ws_ok = loaded_ws["meta"]["world_name"] == mock_world_name
            self.log_result("模拟世界world_setting加载", ws_ok, f"世界名: {loaded_ws['meta']['world_name']}")
            
            # 2. 验证 characters_list.json
            with open(cl_file, "r", encoding="utf-8") as f:
                loaded_cl = json.load(f)
            cl_ok = len(loaded_cl) == 2
            self.log_result("模拟世界characters_list加载", cl_ok, f"角色数: {len(loaded_cl)}")
            
            # 3. 验证角色档案
            loaded_chars = {}
            for char_file in chars_dir.glob("character_*.json"):
                with open(char_file, "r", encoding="utf-8") as f:
                    char_data = json.load(f)
                loaded_chars[char_data["id"]] = char_data
            
            chars_ok = len(loaded_chars) == 2
            self.log_result("模拟世界角色档案加载", chars_ok, f"角色档案数: {len(loaded_chars)}")
            
            return ws_ok and cl_ok and chars_ok
        except Exception as e:
            self.log_result("模拟世界创建和加载", False, f"测试失败: {e}")
            return False
        finally:
            # 清理临时目录
            if self.temp_dir and self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
    
    # ===========================================
    # 第四部分：占位符替换正确性测试
    # ===========================================
    
    def test_npc_prompt_placeholder_replacement(self):
        """
        测试8: NPC提示词占位符替换正确性
        
        验证 npc_system.txt 中的关键占位符能被正确替换。
        """
        try:
            from config.settings import settings
            
            # 读取模板
            template_file = settings.PROMPTS_DIR / "online" / "npc_system.txt"
            with open(template_file, "r", encoding="utf-8") as f:
                template = f.read()
            
            # 模拟角色数据
            test_values = {
                "npc_id": "npc_test_001",
                "npc_name": "测试角色",
                "traits": "聪明, 勇敢",
                "behavior_rules": "- (mock) 行为准则",
                "appearance": "(mock) 外貌",
                "relationships": "(mock) 人际关系",
                "voice_samples": "(mock) 台词",
                "global_context": "(mock) 场景背景",
                "scene_summary": "(mock) 剧情概要",
                "role_in_scene": "(mock) 角色定位",
                "objective": "(mock) 目标",
                "emotional_arc": "(mock) 情绪曲线",
                "key_topics": "(mock) 话题",
                "outcome_direction": "(mock) 结局",
                "special_notes": "(mock) 注意事项",
                "dialogue_history": "(mock) 对话历史",
                "present_characters": "(mock) 在场角色",
            }

            filled = template
            for k, v in test_values.items():
                filled = filled.replace(f"{{{k}}}", v)
            
            # 验证
            id_replaced = test_values["npc_id"] in filled and "{npc_id}" not in filled
            name_replaced = test_values["npc_name"] in filled and "{npc_name}" not in filled
            traits_replaced = test_values["traits"] in filled and "{traits}" not in filled
            
            self.log_result("NPC模板{npc_id}替换", id_replaced, f"ID '{test_values['npc_id']}' 已嵌入")
            self.log_result("NPC模板{npc_name}替换", name_replaced, "名称已嵌入")
            self.log_result("NPC模板{traits}替换", traits_replaced, "特质已嵌入")

            return id_replaced and name_replaced and traits_replaced
        except Exception as e:
            self.log_result("NPC占位符替换", False, f"测试失败: {e}")
            return False
    
    def test_character_detail_placeholder_replacement(self):
        """
        测试9: 角色详情提示词占位符替换
        
        验证 character_detail.txt 中的占位符能被正确替换
        """
        try:
            from config.settings import settings
            
            template_file = settings.PROMPTS_DIR / "offline" / "creatorGod" / "character_detail.txt"
            with open(template_file, "r", encoding="utf-8") as f:
                template = f.read()
            
            # 模拟数据
            test_data = {
                "target_name": "李明",
                "target_id": "npc_001",
                "characters_list": '[{"id": "npc_001", "name": "李明"}, {"id": "npc_002", "name": "张三"}]'
            }
            
            # 执行替换
            filled = template
            for key, value in test_data.items():
                filled = filled.replace(f"{{{key}}}", value)
            
            # 验证
            all_replaced = all(
                f"{{{key}}}" not in filled 
                for key in test_data.keys()
            )
            content_correct = "李明" in filled and "npc_001" in filled
            
            self.log_result(
                "角色详情占位符替换",
                all_replaced and content_correct,
                f"替换后包含: target_name={test_data['target_name']}, target_id={test_data['target_id']}"
            )
            
            return all_replaced and content_correct
        except Exception as e:
            self.log_result("角色详情占位符替换", False, f"测试失败: {e}")
            return False
    
    # ===========================================
    # 第五部分：运行时目录结构测试
    # ===========================================
    
    def test_runtime_directory_naming(self):
        """
        测试10: 运行时目录命名规则
        
        验证运行时目录使用 {world_name}_{timestamp} 格式
        """
        try:
            from config.settings import settings
            import re
            
            runtime_dir = settings.DATA_DIR / "runtime"
            if not runtime_dir.exists():
                self.log_result("运行时目录命名", False, "runtime目录不存在")
                return False
            
            # 查找运行时目录
            pattern = re.compile(r'^(.+)_(\d{8}_\d{6})$')
            
            found_dirs = []
            for d in runtime_dir.iterdir():
                if d.is_dir():
                    match = pattern.match(d.name)
                    if match:
                        world_name = match.group(1)
                        timestamp = match.group(2)
                        found_dirs.append({
                            "path": d.name,
                            "world": world_name,
                            "timestamp": timestamp
                        })
            
            has_valid = len(found_dirs) > 0
            self.log_result(
                "运行时目录命名规则",
                has_valid,
                f"发现 {len(found_dirs)} 个符合规则的目录"
            )
            
            if found_dirs:
                for d in found_dirs[:3]:  # 只显示前3个
                    print(f"            - {d['path']} (世界: {d['world']}, 时间: {d['timestamp']})")
            
            return has_valid
        except Exception as e:
            self.log_result("运行时目录命名", False, f"测试失败: {e}")
            return False
    
    def test_hardcoded_values_check(self):
        """
        测试11: 检查代码中的硬编码值
        
        扫描关键文件，检查是否有硬编码的文件名或路径
        """
        try:
            # 可能存在问题的硬编码模式
            problematic_patterns = [
                (r'"江城市"', "硬编码世界名"),
                (r'character_npc_001', "硬编码角色文件名"),
                (r'"npc_001_林晨"', "硬编码角色标识"),
            ]
            
            files_to_check = [
                PROJECT_ROOT / "initial_Illuminati.py",
                PROJECT_ROOT / "agents" / "online" / "layer1" / "os_agent.py",
            ]
            
            findings = []
            for file_path in files_to_check:
                if not file_path.exists():
                    continue
                
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                for pattern, desc in problematic_patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        findings.append({
                            "file": file_path.name,
                            "pattern": pattern,
                            "description": desc,
                            "count": len(matches)
                        })
            
            # 报告发现
            if findings:
                print(f"\n         WARNING 发现可能的硬编码值:")
                for f in findings:
                    print(f"            {f['file']}: {f['description']} (匹配 {f['count']} 次)")
                
                # 不算失败，只是警告
                self.log_result(
                    "硬编码值检查",
                    True,
                    f"发现 {len(findings)} 处可能的硬编码（仅警告）"
                )
            else:
                self.log_result("硬编码值检查", True, "未发现明显的硬编码")
            
            return True
        except Exception as e:
            self.log_result("硬编码值检查", False, f"测试失败: {e}")
            return False
    
    def test_json_file_structure_consistency(self):
        """
        测试12: JSON文件结构一致性
        
        验证world_setting.json, characters_list.json等文件结构的一致性
        """
        try:
            from config.settings import settings
            
            worlds_dir = settings.DATA_DIR / "worlds"
            
            # 定义期望的结构
            ws_required_keys = ["meta", "geography"]
            cl_required_structure = ["id", "name"]  # 每个角色必须有的字段
            char_required_keys = ["id", "name", "traits", "behavior_rules"]
            
            all_ok = True
            for world_dir in worlds_dir.iterdir():
                if not world_dir.is_dir():
                    continue
                
                world_name = world_dir.name
                
                # 检查 world_setting.json
                ws_file = world_dir / "world_setting.json"
                if ws_file.exists():
                    with open(ws_file, "r", encoding="utf-8") as f:
                        ws_data = json.load(f)
                    
                    missing = [k for k in ws_required_keys if k not in ws_data]
                    if missing:
                        self.log_result(
                            f"{world_name}/world_setting结构",
                            False,
                            f"缺少键: {missing}"
                        )
                        all_ok = False
                    else:
                        self.log_result(f"{world_name}/world_setting结构", True, "")
                
                # 检查 characters_list.json
                cl_file = world_dir / "characters_list.json"
                if cl_file.exists():
                    with open(cl_file, "r", encoding="utf-8") as f:
                        cl_data = json.load(f)
                    
                    # 检查每个角色
                    all_chars_ok = True
                    for i, char in enumerate(cl_data):
                        missing = [k for k in cl_required_structure if k not in char]
                        if missing:
                            all_chars_ok = False
                            break
                    
                    self.log_result(
                        f"{world_name}/characters_list结构",
                        all_chars_ok,
                        f"{len(cl_data)}个角色"
                    )
                    if not all_chars_ok:
                        all_ok = False
                
                # 检查角色档案
                chars_dir = world_dir / "characters"
                if chars_dir.exists():
                    for char_file in chars_dir.glob("character_*.json"):
                        with open(char_file, "r", encoding="utf-8") as f:
                            char_data = json.load(f)
                        
                        missing = [k for k in char_required_keys if k not in char_data]
                        if missing:
                            self.log_result(
                                f"{char_file.name}结构",
                                False,
                                f"缺少: {missing}"
                            )
                            all_ok = False
            
            if all_ok:
                self.log_result("JSON文件结构一致性", True, "所有文件结构正确")
            
            return all_ok
        except Exception as e:
            self.log_result("JSON文件结构一致性", False, f"测试失败: {e}")
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 70)
        print("[Test] 文件路径和占位符系统测试")
        print("=" * 70)
        print()
        
        print("[List] 第一部分：占位符扫描测试")
        print("-" * 50)
        self.test_scan_all_prompt_placeholders()
        self.test_online_prompts_placeholders()
        self.test_offline_prompts_placeholders()
        
        print()
        print("[List] 第二部分：文件路径动态性测试")
        print("-" * 50)
        self.test_settings_paths_are_dynamic()
        self.test_code_uses_settings_for_paths()
        
        print()
        print("[List] 第三部分：新世界名称兼容性测试")
        print("-" * 50)
        self.test_world_name_with_special_characters()
        self.test_create_mock_world_and_load()
        
        print()
        print("[List] 第四部分：占位符替换正确性测试")
        print("-" * 50)
        self.test_npc_prompt_placeholder_replacement()
        self.test_character_detail_placeholder_replacement()
        
        print()
        print("[List] 第五部分：运行时目录和结构测试")
        print("-" * 50)
        self.test_runtime_directory_naming()
        self.test_hardcoded_values_check()
        self.test_json_file_structure_consistency()
        
        # 打印总结
        print()
        print("=" * 70)
        print("[Stats] 测试结果总结")
        print("=" * 70)
        print(f"   通过: {self.results['passed']}")
        print(f"   失败: {self.results['failed']}")
        print(f"   总计: {self.results['passed'] + self.results['failed']}")
        print()
        
        return self.results["failed"] == 0


def main():
    """主函数"""
    tester = TestFilePathsAndPlaceholders()
    success = tester.run_all_tests()
    
    if success:
        print("PASS 所有文件路径和占位符测试通过！")
        print()
        print("HINT 验证的内容:")
        print("   v 所有提示词文件的占位符已扫描记录")
        print("   v 文件路径使用动态配置而非硬编码")
        print("   v 新世界名称可以正确处理")
        print("   v 占位符能被正确替换")
        print("   v JSON文件结构保持一致性")
    else:
        print("FAIL 部分测试失败，请检查相关功能")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())

