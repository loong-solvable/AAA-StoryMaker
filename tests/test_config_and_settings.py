"""
测试配置和环境变量加载

测试内容：
1. settings模块加载
2. 环境变量读取
3. 路径配置正确性
4. LLM配置参数

创建日期：2025-12-01
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestConfigSettings:
    """配置和设置测试类"""
    
    def __init__(self):
        """初始化测试"""
        self.results = {
            "passed": 0,
            "failed": 0,
            "tests": []
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
    
    def test_settings_import(self):
        """
        测试1: settings模块能否正常导入
        
        验证config/settings.py能够被正确加载
        """
        try:
            from config.settings import settings
            self.log_result("settings模块导入", True, "成功导入config.settings")
            return True
        except Exception as e:
            self.log_result("settings模块导入", False, f"导入失败: {e}")
            return False
    
    def test_env_file_exists(self):
        """
        测试2: .env文件是否存在
        
        验证环境变量配置文件存在于项目根目录
        """
        env_path = PROJECT_ROOT / ".env"
        exists = env_path.exists()
        self.log_result(
            ".env文件存在检查", 
            exists,
            f"路径: {env_path}" if exists else f".env文件不存在: {env_path}"
        )
        return exists
    
    def test_path_configurations(self):
        """
        测试3: 路径配置正确性
        
        验证以下路径配置：
        - PROJECT_ROOT: 项目根目录（模块级变量）
        - DATA_DIR: 数据目录
        - PROMPTS_DIR: 提示词目录
        - LOGS_DIR: 日志目录
        """
        try:
            from config.settings import settings, PROJECT_ROOT
            
            all_passed = True
            paths_to_check = [
                ("PROJECT_ROOT", PROJECT_ROOT),
                ("DATA_DIR", settings.DATA_DIR),
                ("PROMPTS_DIR", settings.PROMPTS_DIR),
                ("LOGS_DIR", settings.LOGS_DIR)
            ]
            
            for name, path in paths_to_check:
                exists = Path(path).exists()
                self.log_result(
                    f"路径存在: {name}",
                    exists,
                    str(path)
                )
                if not exists:
                    all_passed = False
            
            return all_passed
        except Exception as e:
            self.log_result("路径配置检查", False, f"检查失败: {e}")
            return False
    
    def test_llm_provider_config(self):
        """
        测试4: LLM提供商配置
        
        验证LLM_PROVIDER配置正确且为支持的提供商之一
        支持的提供商: zhipu, openai, openrouter
        """
        try:
            from config.settings import settings
            
            supported_providers = ["zhipu", "openai", "openrouter"]
            provider = settings.LLM_PROVIDER
            
            is_supported = provider in supported_providers
            self.log_result(
                "LLM提供商配置",
                is_supported,
                f"当前提供商: {provider}"
            )
            return is_supported
        except Exception as e:
            self.log_result("LLM提供商配置", False, f"获取失败: {e}")
            return False
    
    def test_api_key_configuration(self):
        """
        测试5: API密钥配置
        
        验证根据LLM_PROVIDER配置了相应的API密钥
        不会显示密钥内容，只验证是否配置
        """
        try:
            from config.settings import settings
            
            provider = settings.LLM_PROVIDER
            
            # 根据提供商检查对应的API密钥
            if provider == "zhipu":
                key_var = "ZHIPU_API_KEY"
                key = getattr(settings, key_var, None)
            elif provider == "openai":
                key_var = "OPENAI_API_KEY"
                key = getattr(settings, key_var, None)
            elif provider == "openrouter":
                key_var = "OPENROUTER_API_KEY"
                key = getattr(settings, key_var, None)
            else:
                key_var = "UNKNOWN"
                key = None
            
            has_key = key is not None and len(str(key)) > 0
            self.log_result(
                f"API密钥配置 ({key_var})",
                has_key,
                "已配置" if has_key else "未配置或为空"
            )
            return has_key
        except Exception as e:
            self.log_result("API密钥配置", False, f"检查失败: {e}")
            return False
    
    def test_temperature_setting(self):
        """
        测试6: Temperature参数配置
        
        验证LLM的temperature参数在合理范围内 (0.0 - 2.0)
        """
        try:
            from config.settings import settings
            
            temp = settings.TEMPERATURE
            is_valid = 0.0 <= temp <= 2.0
            self.log_result(
                "Temperature参数",
                is_valid,
                f"当前值: {temp} {'(有效)' if is_valid else '(超出范围0-2)'}"
            )
            return is_valid
        except Exception as e:
            self.log_result("Temperature参数", False, f"获取失败: {e}")
            return False
    
    def test_worlds_directory(self):
        """
        测试7: 世界数据目录存在
        
        验证 data/worlds 目录存在且包含至少一个世界
        """
        try:
            from config.settings import settings
            
            worlds_dir = settings.DATA_DIR / "worlds"
            
            # 检查目录存在
            if not worlds_dir.exists():
                self.log_result("世界数据目录", False, f"目录不存在: {worlds_dir}")
                return False
            
            # 检查是否有世界
            worlds = [d for d in worlds_dir.iterdir() if d.is_dir() and (d / "world_setting.json").exists()]
            has_worlds = len(worlds) > 0
            
            self.log_result(
                "世界数据目录",
                has_worlds,
                f"发现 {len(worlds)} 个世界: {[w.name for w in worlds]}"
            )
            return has_worlds
        except Exception as e:
            self.log_result("世界数据目录", False, f"检查失败: {e}")
            return False
    
    def test_prompts_directory_structure(self):
        """
        测试8: 提示词目录结构
        
        验证prompts目录结构正确：
        - prompts/offline/  离线阶段提示词
        - prompts/online/   在线阶段提示词
        """
        try:
            from config.settings import settings
            
            prompts_dir = settings.PROMPTS_DIR
            
            subdirs = {
                "offline": prompts_dir / "offline",
                "online": prompts_dir / "online"
            }
            
            all_exist = True
            for name, path in subdirs.items():
                exists = path.exists()
                self.log_result(f"提示词子目录: {name}", exists, str(path))
                if not exists:
                    all_exist = False
            
            return all_exist
        except Exception as e:
            self.log_result("提示词目录结构", False, f"检查失败: {e}")
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("🧪 配置和环境设置测试")
        print("=" * 60)
        print()
        
        # 运行所有测试
        self.test_settings_import()
        self.test_env_file_exists()
        self.test_path_configurations()
        self.test_llm_provider_config()
        self.test_api_key_configuration()
        self.test_temperature_setting()
        self.test_worlds_directory()
        self.test_prompts_directory_structure()
        
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
    tester = TestConfigSettings()
    success = tester.run_all_tests()
    
    if success:
        print("✅ 所有配置测试通过！")
    else:
        print("❌ 部分测试失败，请检查配置")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())

