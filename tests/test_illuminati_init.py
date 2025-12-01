"""
测试光明会初始化流程

测试内容：
1. IlluminatiInitializer实例创建
2. WS（世界状态）初始化
3. Plot（命运编织）初始化
4. Vibe（氛围感受）初始化
5. 运行时目录结构验证
6. 生成的JSON数据结构验证

注意：此测试不会实际调用LLM，只测试初始化逻辑和数据结构
如需测试完整LLM调用，请运行 initial_Illuminati.py

创建日期：2025-12-01
"""
import sys
import json
from pathlib import Path
from typing import Dict, Any

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestIlluminatiInit:
    """光明会初始化测试类"""
    
    def __init__(self):
        """初始化测试"""
        self.results = {
            "passed": 0,
            "failed": 0,
            "tests": []
        }
        self.world_name = None
        self.world_dir = None
        self.runtime_dir = None
    
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
        """测试前准备"""
        try:
            from config.settings import settings
            
            # 找到可用的世界
            worlds_dir = settings.DATA_DIR / "worlds"
            for world in worlds_dir.iterdir():
                if world.is_dir() and (world / "world_setting.json").exists():
                    self.world_name = world.name
                    self.world_dir = world
                    print(f"📂 使用测试世界: {world.name}")
                    break
            
            # 找到现有的运行时目录（如果有）
            runtime_base = settings.DATA_DIR / "runtime"
            if runtime_base.exists():
                for rt_dir in runtime_base.iterdir():
                    if rt_dir.is_dir() and rt_dir.name.startswith(self.world_name):
                        self.runtime_dir = rt_dir
                        print(f"📂 发现运行时目录: {rt_dir.name}")
                        break
            
            return self.world_name is not None
        except Exception as e:
            print(f"❌ 准备阶段失败: {e}")
            return False
    
    def test_illuminati_import(self):
        """
        测试1: IlluminatiInitializer类导入
        
        验证initial_Illuminati.py模块能够正确导入
        """
        try:
            from initial_Illuminati import IlluminatiInitializer, InitialScene, InitialScript, InitialAtmosphere
            
            self.log_result(
                "IlluminatiInitializer导入",
                True,
                "成功导入所有必要类"
            )
            return True
        except Exception as e:
            self.log_result("IlluminatiInitializer导入", False, f"导入失败: {e}")
            return False
    
    def test_data_classes_structure(self):
        """
        测试2: 数据类结构验证
        
        验证InitialScene, InitialScript, InitialAtmosphere数据类的结构
        """
        try:
            from initial_Illuminati import InitialScene, InitialScript, InitialAtmosphere
            from dataclasses import fields
            
            # 验证InitialScene字段
            scene_fields = [f.name for f in fields(InitialScene)]
            expected_scene = ["location_id", "location_name", "time_of_day", "weather", 
                           "present_characters", "scene_description", "opening_narrative"]
            scene_ok = all(f in scene_fields for f in expected_scene)
            self.log_result(
                "InitialScene结构",
                scene_ok,
                f"字段: {scene_fields}"
            )
            
            # 验证InitialScript字段
            script_fields = [f.name for f in fields(InitialScript)]
            script_ok = "content" in script_fields
            self.log_result(
                "InitialScript结构",
                script_ok,
                f"字段: {script_fields}"
            )
            
            # 验证InitialAtmosphere字段
            atmo_fields = [f.name for f in fields(InitialAtmosphere)]
            expected_atmo = ["visual_description", "auditory_description", 
                           "emotional_tone", "full_atmosphere_text"]
            atmo_ok = all(f in atmo_fields for f in expected_atmo)
            self.log_result(
                "InitialAtmosphere结构",
                atmo_ok,
                f"字段: {atmo_fields}"
            )
            
            return scene_ok and script_ok and atmo_ok
        except Exception as e:
            self.log_result("数据类结构", False, f"验证失败: {e}")
            return False
    
    def test_initializer_creation(self):
        """
        测试3: IlluminatiInitializer实例创建
        
        验证：
        - 能够使用世界名称创建实例
        - 正确加载世界设定
        - 正确加载角色数据
        """
        try:
            from initial_Illuminati import IlluminatiInitializer
            
            # 创建实例（不调用run，只测试初始化）
            initializer = IlluminatiInitializer(self.world_name)
            
            # 验证世界数据加载
            has_ws = hasattr(initializer, 'world_setting') and initializer.world_setting
            has_chars = hasattr(initializer, 'characters_details') and len(initializer.characters_details) > 0
            
            self.log_result(
                "IlluminatiInitializer实例创建",
                has_ws and has_chars,
                f"世界设定: {has_ws}, 角色数据: {len(initializer.characters_details) if has_chars else 0}个"
            )
            
            # 验证genesis_data构建
            has_genesis = hasattr(initializer, 'genesis_data') and initializer.genesis_data
            if has_genesis:
                genesis_keys = list(initializer.genesis_data.keys())
                self.log_result(
                    "Genesis数据构建",
                    True,
                    f"包含键: {genesis_keys}"
                )
            
            return has_ws and has_chars
        except Exception as e:
            self.log_result("IlluminatiInitializer实例创建", False, f"创建失败: {e}")
            return False
    
    def test_runtime_directory_structure(self):
        """
        测试4: 运行时目录结构验证
        
        验证生成的运行时目录结构：
        - ws/world_state.json
        - plot/current_scene.json
        - plot/current_script.json
        - plot/history/
        - vibe/initial_atmosphere.json
        """
        if not self.runtime_dir:
            self.log_result("运行时目录结构", False, "未找到运行时目录，请先运行initial_Illuminati.py")
            return False
        
        try:
            expected_files = [
                "ws/world_state.json",
                "plot/current_scene.json",
                "plot/current_script.json",
                "vibe/initial_atmosphere.json",
                "init_summary.json"
            ]
            
            expected_dirs = [
                "ws",
                "plot",
                "plot/history",
                "vibe"
            ]
            
            # 检查目录
            for dir_path in expected_dirs:
                full_path = self.runtime_dir / dir_path
                exists = full_path.exists() and full_path.is_dir()
                self.log_result(
                    f"目录存在: {dir_path}",
                    exists,
                    str(full_path) if exists else "不存在"
                )
            
            # 检查文件
            all_files_exist = True
            for file_path in expected_files:
                full_path = self.runtime_dir / file_path
                exists = full_path.exists() and full_path.is_file()
                if not exists:
                    all_files_exist = False
                self.log_result(
                    f"文件存在: {file_path}",
                    exists,
                    ""
                )
            
            return all_files_exist
        except Exception as e:
            self.log_result("运行时目录结构", False, f"验证失败: {e}")
            return False
    
    def test_world_state_json_structure(self):
        """
        测试5: world_state.json结构验证
        
        验证WS生成的世界状态JSON结构
        """
        if not self.runtime_dir:
            self.log_result("world_state.json结构", False, "未找到运行时目录")
            return False
        
        try:
            ws_file = self.runtime_dir / "ws" / "world_state.json"
            if not ws_file.exists():
                self.log_result("world_state.json结构", False, "文件不存在")
                return False
            
            with open(ws_file, "r", encoding="utf-8") as f:
                ws_data = json.load(f)
            
            # 验证必要字段
            required_keys = ["current_scene", "weather", "characters_present", "meta"]
            missing = [k for k in required_keys if k not in ws_data]
            
            has_required = len(missing) == 0
            self.log_result(
                "world_state.json必要字段",
                has_required,
                f"缺少: {missing}" if missing else f"包含: {required_keys}"
            )
            
            # 验证current_scene结构
            scene = ws_data.get("current_scene", {})
            scene_fields = ["location_id", "location_name", "time_of_day"]
            scene_ok = all(f in scene for f in scene_fields)
            self.log_result(
                "current_scene结构",
                scene_ok,
                f"地点: {scene.get('location_name', 'N/A')}"
            )
            
            # 验证characters_present
            chars = ws_data.get("characters_present", [])
            self.log_result(
                "characters_present",
                True,
                f"在场角色: {len(chars)}个"
            )
            
            return has_required and scene_ok
        except Exception as e:
            self.log_result("world_state.json结构", False, f"验证失败: {e}")
            return False
    
    def test_current_scene_json_structure(self):
        """
        测试6: current_scene.json结构验证
        
        验证Plot生成的场景JSON结构
        """
        if not self.runtime_dir:
            self.log_result("current_scene.json结构", False, "未找到运行时目录")
            return False
        
        try:
            scene_file = self.runtime_dir / "plot" / "current_scene.json"
            if not scene_file.exists():
                self.log_result("current_scene.json结构", False, "文件不存在")
                return False
            
            with open(scene_file, "r", encoding="utf-8") as f:
                scene_data = json.load(f)
            
            # 验证字段
            required_keys = ["location_id", "location_name", "time_of_day", 
                           "weather", "present_characters"]
            missing = [k for k in required_keys if k not in scene_data]
            
            has_required = len(missing) == 0
            self.log_result(
                "current_scene.json结构",
                has_required,
                f"缺少: {missing}" if missing else f"地点: {scene_data.get('location_name')}"
            )
            
            # 验证present_characters格式
            chars = scene_data.get("present_characters", [])
            if chars and isinstance(chars[0], dict):
                has_id = "id" in chars[0]
                has_name = "name" in chars[0]
                self.log_result(
                    "present_characters结构",
                    has_id and has_name,
                    f"角色数: {len(chars)}"
                )
            
            return has_required
        except Exception as e:
            self.log_result("current_scene.json结构", False, f"验证失败: {e}")
            return False
    
    def test_initial_atmosphere_json_structure(self):
        """
        测试7: initial_atmosphere.json结构验证
        
        验证Vibe生成的氛围JSON结构
        """
        if not self.runtime_dir:
            self.log_result("initial_atmosphere.json结构", False, "未找到运行时目录")
            return False
        
        try:
            atmo_file = self.runtime_dir / "vibe" / "initial_atmosphere.json"
            if not atmo_file.exists():
                self.log_result("initial_atmosphere.json结构", False, "文件不存在")
                return False
            
            with open(atmo_file, "r", encoding="utf-8") as f:
                atmo_data = json.load(f)
            
            # 验证字段
            required_keys = ["visual_description", "auditory_description", 
                           "emotional_tone", "full_atmosphere_text"]
            missing = [k for k in required_keys if k not in atmo_data]
            
            has_required = len(missing) == 0
            self.log_result(
                "initial_atmosphere.json结构",
                has_required,
                f"缺少: {missing}" if missing else f"情绪基调: {atmo_data.get('emotional_tone', 'N/A')}"
            )
            
            # 验证内容非空
            full_text = atmo_data.get("full_atmosphere_text", "")
            has_content = len(full_text) > 10
            self.log_result(
                "氛围描写内容",
                has_content,
                f"内容长度: {len(full_text)}字符"
            )
            
            return has_required and has_content
        except Exception as e:
            self.log_result("initial_atmosphere.json结构", False, f"验证失败: {e}")
            return False
    
    def test_init_summary_json(self):
        """
        测试8: init_summary.json验证
        
        验证初始化摘要文件的结构和内容
        """
        if not self.runtime_dir:
            self.log_result("init_summary.json", False, "未找到运行时目录")
            return False
        
        try:
            summary_file = self.runtime_dir / "init_summary.json"
            if not summary_file.exists():
                self.log_result("init_summary.json", False, "文件不存在")
                return False
            
            with open(summary_file, "r", encoding="utf-8") as f:
                summary = json.load(f)
            
            # 验证字段
            required_keys = ["world_name", "initialized_at", "components", "ready_for_game"]
            missing = [k for k in required_keys if k not in summary]
            
            has_required = len(missing) == 0
            self.log_result(
                "init_summary.json结构",
                has_required,
                f"缺少: {missing}" if missing else f"世界: {summary.get('world_name')}"
            )
            
            # 验证组件状态
            components = summary.get("components", {})
            all_initialized = all(
                c.get("status") == "initialized" 
                for c in components.values()
            )
            self.log_result(
                "组件初始化状态",
                all_initialized,
                f"组件: {list(components.keys())}"
            )
            
            # 验证ready_for_game
            is_ready = summary.get("ready_for_game", False)
            self.log_result(
                "游戏就绪状态",
                is_ready,
                "ready_for_game: True" if is_ready else "ready_for_game: False"
            )
            
            return has_required and all_initialized
        except Exception as e:
            self.log_result("init_summary.json", False, f"验证失败: {e}")
            return False
    
    def test_prompt_files_availability(self):
        """
        测试9: 提示词文件可用性
        
        验证光明会初始化所需的提示词文件存在
        """
        try:
            from config.settings import settings
            
            required_prompts = [
                "online/ws_system.txt",
                "online/plot_system.txt",
                "online/vibe_system.txt"
            ]
            
            all_exist = True
            for prompt in required_prompts:
                path = settings.PROMPTS_DIR / prompt
                exists = path.exists()
                if not exists:
                    all_exist = False
                self.log_result(
                    f"提示词文件: {prompt}",
                    exists,
                    ""
                )
            
            return all_exist
        except Exception as e:
            self.log_result("提示词文件可用性", False, f"检查失败: {e}")
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("🧪 光明会初始化流程测试")
        print("=" * 60)
        print()
        
        # 准备阶段
        if not self.setup():
            print("❌ 测试准备失败，无法继续")
            return False
        
        print()
        
        # 运行所有测试
        self.test_illuminati_import()
        self.test_data_classes_structure()
        self.test_initializer_creation()
        self.test_prompt_files_availability()
        
        # 以下测试需要已运行过initial_Illuminati.py
        print()
        print("📋 以下测试验证已生成的运行时数据（需要先运行initial_Illuminati.py）:")
        print()
        
        self.test_runtime_directory_structure()
        self.test_world_state_json_structure()
        self.test_current_scene_json_structure()
        self.test_initial_atmosphere_json_structure()
        self.test_init_summary_json()
        
        # 打印总结
        print()
        print("=" * 60)
        print("📊 测试结果总结")
        print("=" * 60)
        print(f"   通过: {self.results['passed']}")
        print(f"   失败: {self.results['failed']}")
        print(f"   总计: {self.results['passed'] + self.results['failed']}")
        print()
        
        if not self.runtime_dir:
            print("💡 提示: 部分测试跳过，请先运行以下命令生成运行时数据:")
            print(f"   python initial_Illuminati.py --world {self.world_name}")
            print()
        
        return self.results["failed"] == 0


def main():
    """主函数"""
    tester = TestIlluminatiInit()
    success = tester.run_all_tests()
    
    if success:
        print("✅ 所有光明会初始化测试通过！")
    else:
        print("❌ 部分测试失败，请检查配置")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())

