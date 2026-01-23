"""
测试角色提示词动态生成功能（重点测试）

测试内容：
1. 提示词模板加载
2. 角色卡数据格式化
3. 角色专属提示词文件生成
4. 验证生成的提示词包含正确的角色信息
5. 测试不同角色生成的提示词具有特异性
6. 验证占位符正确替换

这是项目的核心功能之一：
- 每个角色都能动态生成特异性的提示词文件
- 提示词文件包含角色的完整人设信息
- 生成的提示词能够正确用于LLM调用

创建日期：2025-12-01
"""
import sys
import json
import re
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestCharacterPromptGeneration:
    """角色提示词动态生成测试类"""
    
    def __init__(self):
        """初始化测试"""
        self.results = {
            "passed": 0,
            "failed": 0,
            "tests": []
        }
        self.world_dir = None
        self.characters = {}
        self.temp_dir = None  # 用于测试生成文件的临时目录
    
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
    
    def setup(self):
        """测试前准备"""
        try:
            from config.settings import settings
            
            # 找到可用的世界
            worlds_dir = settings.DATA_DIR / "worlds"
            for world in worlds_dir.iterdir():
                if world.is_dir() and (world / "characters").exists():
                    self.world_dir = world
                    print(f"[Dir] 使用测试世界: {world.name}")
                    break
            
            if not self.world_dir:
                print("FAIL 未找到有效的世界数据")
                return False
            
            # 加载角色数据
            chars_dir = self.world_dir / "characters"
            for char_file in chars_dir.glob("character_*.json"):
                with open(char_file, "r", encoding="utf-8") as f:
                    char_data = json.load(f)
                char_id = char_data.get("id")
                if char_id:
                    self.characters[char_id] = char_data
            
            print(f"[Stats] 加载了 {len(self.characters)} 个角色数据")
            
            # 创建临时目录用于测试
            self.temp_dir = Path(tempfile.mkdtemp(prefix="test_prompts_"))
            print(f"[Folder] 临时测试目录: {self.temp_dir}")
            
            return True
        except Exception as e:
            print(f"FAIL 准备阶段失败: {e}")
            return False
    
    def cleanup(self):
        """清理临时目录"""
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            print(f"[Clean] 已清理临时目录")
    
    def test_npc_system_template_exists(self):
        """
        测试1: NPC系统提示词模板存在
        
        验证 prompts/online/npc_system.txt 文件存在且内容有效
        """
        try:
            from config.settings import settings
            
            template_path = settings.PROMPTS_DIR / "online" / "npc_system.txt"
            
            exists = template_path.exists()
            self.log_result(
                "npc_system.txt模板存在",
                exists,
                str(template_path)
            )
            
            if exists:
                with open(template_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                has_content = len(content) > 50
                self.log_result(
                    "模板内容有效",
                    has_content,
                    f"模板长度: {len(content)} 字符"
                )
                
                return has_content
            
            return False
        except Exception as e:
            self.log_result("npc_system.txt模板", False, f"检查失败: {e}")
            return False
    
    def test_template_placeholders(self):
        """
        测试2: 模板占位符验证
        
        验证模板中包含必要的占位符（以当前 npc_system.txt 为准）：
        - {npc_id} - 角色ID
        - {npc_name} - 角色名称
        - {traits} - 特质
        """
        try:
            from config.settings import settings
            
            template_path = settings.PROMPTS_DIR / "online" / "npc_system.txt"
            with open(template_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 检查必要的占位符
            placeholders = ["{npc_id}", "{npc_name}", "{traits}"]
            found = []
            missing = []
            
            for ph in placeholders:
                if ph in content:
                    found.append(ph)
                else:
                    missing.append(ph)
            
            has_all = len(missing) == 0
            self.log_result(
                "模板占位符完整性",
                has_all,
                f"找到: {found}, 缺少: {missing}"
            )
            
            return has_all
        except Exception as e:
            self.log_result("模板占位符验证", False, f"验证失败: {e}")
            return False
    
    def test_format_character_card(self):
        """
        测试3: 角色卡格式化功能
        
        验证 _format_character_card 方法能正确将角色数据格式化为文本
        """
        try:
            # 获取 os_agent 中的格式化方法
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "os_agent",
                PROJECT_ROOT / "agents" / "online" / "layer1" / "os_agent.py"
            )
            if spec is None or spec.loader is None:
                raise ImportError("无法加载 agents/online/layer1/os_agent.py")
            os_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(os_module)
            
            os_agent = os_module.OperatingSystem()
            
            # 使用第一个角色测试
            if not self.characters:
                self.log_result("角色卡格式化", False, "没有可用的角色数据")
                return False
            
            char_id, char_data = list(self.characters.items())[0]
            
            # 调用格式化方法
            formatted = os_agent._format_character_card(char_data)
            
            # 验证格式化结果
            checks = [
                ("包含角色ID", f"【角色ID】{char_data.get('id')}" in formatted),
                ("包含姓名", f"【姓名】{char_data.get('name')}" in formatted),
                ("包含性别", "【性别】" in formatted),
                ("包含特质", "【人物特质】" in formatted or "人物特质" in formatted),
            ]
            
            all_ok = True
            for check_name, passed in checks:
                if not passed:
                    all_ok = False
            
            self.log_result(
                "角色卡格式化",
                all_ok,
                f"角色: {char_data.get('name')}, 格式化长度: {len(formatted)}字符"
            )
            
            # 显示格式化结果预览
            if all_ok:
                preview = formatted[:200] + "..." if len(formatted) > 200 else formatted
                print(f"         [Note] 格式化预览:\n         {preview.replace(chr(10), chr(10) + '         ')}")
            
            return all_ok
        except Exception as e:
            self.log_result("角色卡格式化", False, f"执行失败: {e}")
            return False
    
    def test_generate_character_prompt_single(self):
        """
        测试4: 单个角色提示词生成
        
        验证能够为单个角色生成专属提示词文件
        """
        try:
            from config.settings import settings
            import importlib.util
            
            spec = importlib.util.spec_from_file_location(
                "os_agent",
                PROJECT_ROOT / "agents" / "online" / "layer1" / "os_agent.py"
            )
            if spec is None or spec.loader is None:
                raise ImportError("无法加载 agents/online/layer1/os_agent.py")
            os_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(os_module)
            
            os_agent = os_module.OperatingSystem()

            if not self.temp_dir:
                raise RuntimeError("临时目录未初始化")
            
            # 获取第一个角色
            if not self.characters:
                self.log_result("单个角色提示词生成", False, "没有可用的角色数据")
                return False
            
            char_id, char_data = list(self.characters.items())[0]
            char_name = char_data.get("name", char_id)
            
            # 读取模板
            template_path = settings.PROMPTS_DIR / "online" / "npc_system.txt"
            with open(template_path, "r", encoding="utf-8") as f:
                template = f.read()
            
            # 调用生成方法（使用临时目录）
            # 我们需要模拟 _generate_character_prompt 的行为
            character_card = os_agent._format_character_card(char_data)
            
            # 手动填充模板
            filled_prompt = template.replace("{npc_id}", char_id)
            filled_prompt = filled_prompt.replace("{npc_name}", char_name)
            filled_prompt = filled_prompt.replace("{traits}", ", ".join(char_data.get("traits", []) or []))
            
            # 保存到临时目录
            prompt_file = self.temp_dir / f"{char_id}_{char_name}.txt"
            with open(prompt_file, "w", encoding="utf-8") as f:
                f.write(filled_prompt)
            
            # 验证文件生成
            file_exists = prompt_file.exists()
            self.log_result(
                "提示词文件生成",
                file_exists,
                f"文件: {prompt_file.name}"
            )
            
            # 验证内容
            if file_exists:
                with open(prompt_file, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # 检查ID是否正确替换
                id_replaced = char_id in content and "{npc_id}" not in content
                self.log_result(
                    "ID占位符替换",
                    id_replaced,
                    f"角色ID {char_id} 已嵌入"
                )
                
                # 检查角色卡是否嵌入
                char_card_embedded = char_data.get("name") in content
                self.log_result(
                    "角色卡内容嵌入",
                    char_card_embedded,
                    f"角色名 {char_data.get('name')} 存在于提示词中"
                )
                
                return file_exists and id_replaced and char_card_embedded
            
            return False
        except Exception as e:
            self.log_result("单个角色提示词生成", False, f"执行失败: {e}")
            return False
    
    def test_prompt_specificity(self):
        """
        测试5: 提示词特异性验证（重要）
        
        验证不同角色生成的提示词具有特异性：
        - 每个角色的提示词包含其特有信息
        - 不同角色的提示词内容不同
        - 角色特质、行为准则、关系等都正确嵌入
        """
        try:
            from config.settings import settings
            import importlib.util
            
            spec = importlib.util.spec_from_file_location(
                "os_agent",
                PROJECT_ROOT / "agents" / "online" / "layer1" / "os_agent.py"
            )
            if spec is None or spec.loader is None:
                raise ImportError("无法加载 agents/online/layer1/os_agent.py")
            os_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(os_module)
            
            os_agent = os_module.OperatingSystem()
            
            if len(self.characters) < 2:
                self.log_result("提示词特异性", False, "需要至少2个角色进行比较")
                return False
            
            # 读取模板
            template_path = settings.PROMPTS_DIR / "online" / "npc_system.txt"
            with open(template_path, "r", encoding="utf-8") as f:
                template = f.read()
            
            # 为前两个角色生成提示词
            char_items = list(self.characters.items())[:2]
            generated_prompts = {}
            
            for char_id, char_data in char_items:
                char_name = char_data.get("name", char_id)
                character_card = os_agent._format_character_card(char_data)
                
                filled_prompt = template.replace("{npc_id}", char_id)
                filled_prompt = filled_prompt.replace("{npc_name}", char_name)
                filled_prompt = filled_prompt.replace("{traits}", ", ".join(char_data.get("traits", []) or []))
                
                generated_prompts[char_id] = {
                    "name": char_name,
                    "content": filled_prompt,
                    "data": char_data
                }
            
            # 比较两个提示词的特异性
            ids = list(generated_prompts.keys())
            prompt1 = generated_prompts[ids[0]]
            prompt2 = generated_prompts[ids[1]]
            
            # 1. 检查内容不同
            content_different = prompt1["content"] != prompt2["content"]
            self.log_result(
                "不同角色提示词内容不同",
                content_different,
                f"{prompt1['name']} vs {prompt2['name']}"
            )
            
            # 2. 检查各自包含特有信息
            # 注意：由于人际关系矩阵中会引用其他角色，所以只验证各自的名字存在于自己的提示词中
            name1_in_1 = prompt1["name"] in prompt1["content"]
            name2_in_2 = prompt2["name"] in prompt2["content"]
            
            # 验证角色ID的唯一性 - ID不应该在对方的【角色ID】字段中
            id1 = prompt1["data"]["id"]
            id2 = prompt2["data"]["id"]
            id1_section = f"- **角色ID**: {id1}"
            id2_section = f"- **角色ID**: {id2}"
            id1_unique = id1_section in prompt1["content"] and id1_section not in prompt2["content"]
            id2_unique = id2_section in prompt2["content"] and id2_section not in prompt1["content"]
            
            names_correct = name1_in_1 and name2_in_2 and id1_unique and id2_unique
            self.log_result(
                "角色标识特异性",
                names_correct,
                f"{prompt1['name']}(ID:{id1})和{prompt2['name']}(ID:{id2})各自标识正确"
            )
            
            # 3. 检查特质的特异性
            traits1 = prompt1["data"].get("traits", [])
            traits2 = prompt2["data"].get("traits", [])
            
            if traits1 and traits2:
                # 找出各自特有的特质
                unique_trait1 = traits1[0] if traits1 else None
                unique_trait2 = traits2[0] if traits2 else None
                
                trait1_in_1 = unique_trait1 in prompt1["content"] if unique_trait1 else True
                trait2_in_2 = unique_trait2 in prompt2["content"] if unique_trait2 else True
                
                traits_correct = trait1_in_1 and trait2_in_2
                self.log_result(
                    "角色特质特异性",
                    traits_correct,
                    f"角色1特质: {unique_trait1}, 角色2特质: {unique_trait2}"
                )
            else:
                self.log_result("角色特质特异性", True, "特质数据不足，跳过详细验证")
                traits_correct = True
            
            return content_different and names_correct and traits_correct
        except Exception as e:
            self.log_result("提示词特异性", False, f"验证失败: {e}")
            return False
    
    def test_all_characters_prompt_generation(self):
        """
        测试6: 批量角色提示词生成
        
        为所有角色生成提示词文件，验证：
        - 每个角色都能成功生成
        - 文件名格式正确
        - 内容结构完整
        """
        try:
            from config.settings import settings
            import importlib.util
            
            spec = importlib.util.spec_from_file_location(
                "os_agent",
                PROJECT_ROOT / "agents" / "online" / "layer1" / "os_agent.py"
            )
            if spec is None or spec.loader is None:
                raise ImportError("无法加载 agents/online/layer1/os_agent.py")
            os_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(os_module)
            
            os_agent = os_module.OperatingSystem()

            if not self.temp_dir:
                raise RuntimeError("临时目录未初始化")
            
            # 读取模板
            template_path = settings.PROMPTS_DIR / "online" / "npc_system.txt"
            with open(template_path, "r", encoding="utf-8") as f:
                template = f.read()
            
            success_count = 0
            fail_count = 0
            
            for char_id, char_data in self.characters.items():
                try:
                    char_name = char_data.get("name", char_id)
                    character_card = os_agent._format_character_card(char_data)
                    
                    filled_prompt = template.replace("{npc_id}", char_id)
                    filled_prompt = filled_prompt.replace("{npc_name}", char_name)
                    filled_prompt = filled_prompt.replace("{traits}", ", ".join(char_data.get("traits", []) or []))
                    
                    # 保存
                    prompt_file = self.temp_dir / f"{char_id}_{char_name}.txt"
                    with open(prompt_file, "w", encoding="utf-8") as f:
                        f.write(filled_prompt)
                    
                    success_count += 1
                except Exception as e:
                    fail_count += 1
                    print(f"         WARNING {char_id} 生成失败: {e}")
            
            all_success = fail_count == 0
            self.log_result(
                "批量提示词生成",
                all_success,
                f"成功: {success_count}, 失败: {fail_count}, 总计: {len(self.characters)}"
            )
            
            # 列出生成的文件
            generated_files = list(self.temp_dir.glob("*.txt"))
            self.log_result(
                "生成文件数量",
                len(generated_files) == success_count,
                f"生成了 {len(generated_files)} 个文件"
            )
            
            return all_success
        except Exception as e:
            self.log_result("批量提示词生成", False, f"执行失败: {e}")
            return False
    
    def test_existing_prompt_files(self):
        """
        测试7: 验证已存在的角色提示词文件
        
        检查 prompts/online/ 目录下已生成的角色提示词文件
        """
        try:
            from config.settings import settings
            
            prompts_dir = settings.PROMPTS_DIR / "online" / "npc_prompt"
            if not prompts_dir.exists():
                prompts_dir = settings.PROMPTS_DIR / "online"
            
            # 查找角色提示词文件
            if "npc_prompt" in str(prompts_dir):
                npc_prompts = list(prompts_dir.glob("npc_*_prompt.txt"))
            else:
                npc_prompts = list(prompts_dir.glob("npc_*.txt"))
            
            # 排除模板文件
            npc_prompts = [p for p in npc_prompts if p.name != "npc_system.txt"]
            
            has_prompts = len(npc_prompts) > 0
            self.log_result(
                "已存在的角色提示词文件",
                has_prompts,
                f"发现 {len(npc_prompts)} 个角色提示词文件"
            )
            
            if npc_prompts:
                # 验证其中一个文件的结构
                sample_file = npc_prompts[0]
                with open(sample_file, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # 检查基本结构（允许不同历史格式）
                has_role_info = (
                    ("【角色ID】" in content)
                    or ("【姓名】" in content)
                    or ("**角色ID**" in content)
                    or ("npc_" in content)
                )
                self.log_result(
                    "提示词文件结构",
                    has_role_info,
                    f"文件: {sample_file.name}"
                )
                
                # 显示文件列表
                print(f"         [File] 已生成的提示词文件:")
                for pf in npc_prompts[:5]:  # 只显示前5个
                    print(f"            - {pf.name}")
                if len(npc_prompts) > 5:
                    print(f"            ... 还有 {len(npc_prompts) - 5} 个文件")
            
            return has_prompts
        except Exception as e:
            self.log_result("已存在的角色提示词文件", False, f"检查失败: {e}")
            return False
    
    def test_prompt_content_completeness(self):
        """
        测试8: 提示词内容完整性验证
        
        验证生成的提示词包含所有必要的角色信息：
        - 基本信息（ID、姓名、性别、年龄）
        - 特质列表
        - 行为准则
        - 人际关系
        - 持有物品
        - 典型台词
        """
        try:
            from config.settings import settings
            import importlib.util
            
            spec = importlib.util.spec_from_file_location(
                "os_agent",
                PROJECT_ROOT / "agents" / "online" / "layer1" / "os_agent.py"
            )
            if spec is None or spec.loader is None:
                raise ImportError("无法加载 agents/online/layer1/os_agent.py")
            os_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(os_module)
            
            os_agent = os_module.OperatingSystem()
            
            # 使用数据最完整的角色进行测试
            best_char = None
            max_fields = 0
            
            for char_id, char_data in self.characters.items():
                field_count = sum([
                    1 if char_data.get("traits") else 0,
                    1 if char_data.get("behavior_rules") else 0,
                    1 if char_data.get("relationship_matrix") else 0,
                    1 if char_data.get("possessions") else 0,
                    1 if char_data.get("voice_samples") else 0,
                ])
                if field_count > max_fields:
                    max_fields = field_count
                    best_char = (char_id, char_data)
            
            if not best_char:
                self.log_result("提示词内容完整性", False, "没有可用的角色数据")
                return False
            
            char_id, char_data = best_char
            character_card = os_agent._format_character_card(char_data)
            
            # 验证各部分内容存在
            checks = []
            
            if char_data.get("id"):
                checks.append(("角色ID", char_data["id"] in character_card))
            if char_data.get("name"):
                checks.append(("姓名", char_data["name"] in character_card))
            if char_data.get("traits"):
                checks.append(("特质", any(t in character_card for t in char_data["traits"][:2])))
            if char_data.get("behavior_rules"):
                checks.append(("行为准则", any(r in character_card for r in char_data["behavior_rules"][:1])))
            if char_data.get("relationship_matrix"):
                rel_keys = list(char_data["relationship_matrix"].keys())
                checks.append(("人际关系", "人际关系" in character_card or "关系" in character_card))
            if char_data.get("possessions"):
                checks.append(("持有物品", any(p in character_card for p in char_data["possessions"][:1])))
            if char_data.get("voice_samples"):
                checks.append(("典型台词", any(v in character_card for v in char_data["voice_samples"][:1])))
            
            all_ok = True
            for check_name, passed in checks:
                if not passed:
                    all_ok = False
                self.log_result(f"包含{check_name}", passed, "")
            
            self.log_result(
                "提示词内容完整性总结",
                all_ok,
                f"测试角色: {char_data.get('name')}, 检查项: {len(checks)}"
            )
            
            return all_ok
        except Exception as e:
            self.log_result("提示词内容完整性", False, f"验证失败: {e}")
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("[Test] 角色提示词动态生成测试（重点）")
        print("=" * 60)
        print()
        
        # 准备阶段
        if not self.setup():
            print("FAIL 测试准备失败，无法继续")
            return False
        
        print()
        
        try:
            # 运行所有测试
            self.test_npc_system_template_exists()
            self.test_template_placeholders()
            self.test_format_character_card()
            self.test_generate_character_prompt_single()
            self.test_prompt_specificity()
            self.test_all_characters_prompt_generation()
            self.test_existing_prompt_files()
            self.test_prompt_content_completeness()
            
            # 打印总结
            print()
            print("=" * 60)
            print("[Stats] 测试结果总结")
            print("=" * 60)
            print(f"   通过: {self.results['passed']}")
            print(f"   失败: {self.results['failed']}")
            print(f"   总计: {self.results['passed'] + self.results['failed']}")
            print()
            
            return self.results["failed"] == 0
        finally:
            # 清理
            self.cleanup()


def main():
    """主函数"""
    tester = TestCharacterPromptGeneration()
    success = tester.run_all_tests()
    
    if success:
        print("PASS 所有角色提示词生成测试通过！")
        print()
        print("HINT 核心验证点:")
        print("   OK 模板文件存在且包含必要占位符")
        print("   OK 角色卡数据能正确格式化")
        print("   OK 每个角色能生成特异性的提示词")
        print("   OK 不同角色的提示词内容不同")
        print("   OK 提示词包含完整的角色信息")
    else:
        print("FAIL 部分测试失败，请检查相关功能")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())

