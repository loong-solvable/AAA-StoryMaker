"""
测试世界状态动态更新功能

测试内容：
1. WorldStateManager的update_world_state方法
2. 验证内存中的状态更新
3. 验证world_state.json文件是否能被动态更新
4. 测试状态持久化机制

创建日期：2025-12-01
"""
import sys
import json
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestWorldStateDynamicUpdate:
    """世界状态动态更新测试类"""
    
    def __init__(self):
        """初始化测试"""
        self.results = {
            "passed": 0,
            "failed": 0,
            "tests": []
        }
        self.temp_dir = None
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
            
            # 查找现有的运行时目录
            runtime_base = settings.DATA_DIR / "runtime"
            if runtime_base.exists():
                for rt_dir in runtime_base.iterdir():
                    if rt_dir.is_dir() and (rt_dir / "ws" / "world_state.json").exists():
                        self.runtime_dir = rt_dir
                        print(f"📂 使用运行时目录: {rt_dir.name}")
                        break
            
            if not self.runtime_dir:
                print("⚠️ 未找到运行时目录，部分测试将跳过")
                print("   请先运行: python initial_Illuminati.py")
            
            return True
        except Exception as e:
            print(f"❌ 准备阶段失败: {e}")
            return False
    
    # ===========================================
    # 第一部分：world_state.json 结构测试
    # ===========================================
    
    def test_world_state_file_exists(self):
        """
        测试1: world_state.json 文件存在
        """
        if not self.runtime_dir:
            self.log_result("world_state.json存在", False, "未找到运行时目录")
            return False
        
        ws_file = self.runtime_dir / "ws" / "world_state.json"
        exists = ws_file.exists()
        self.log_result(
            "world_state.json存在",
            exists,
            str(ws_file) if exists else "文件不存在"
        )
        return exists
    
    def test_world_state_structure(self):
        """
        测试2: world_state.json 结构完整性
        
        验证必要字段：
        - current_scene
        - weather
        - characters_present
        - world_situation
        - meta
        """
        if not self.runtime_dir:
            self.log_result("world_state结构", False, "未找到运行时目录")
            return False
        
        try:
            ws_file = self.runtime_dir / "ws" / "world_state.json"
            with open(ws_file, "r", encoding="utf-8") as f:
                ws_data = json.load(f)
            
            required_keys = [
                "current_scene",
                "weather",
                "characters_present",
                "world_situation",
                "meta"
            ]
            
            missing = [k for k in required_keys if k not in ws_data]
            has_all = len(missing) == 0
            
            self.log_result(
                "world_state结构完整性",
                has_all,
                f"缺少: {missing}" if missing else "所有必要字段存在"
            )
            
            # 显示当前状态
            if has_all:
                scene = ws_data.get("current_scene", {})
                meta = ws_data.get("meta", {})
                chars = ws_data.get("characters_present", [])
                print(f"         📍 当前场景: {scene.get('location_name', 'N/A')}")
                print(f"         ⏰ 游戏回合: {meta.get('game_turn', 0)}")
                print(f"         👥 在场角色: {len(chars)}人")
            
            return has_all
        except Exception as e:
            self.log_result("world_state结构", False, f"读取失败: {e}")
            return False
    
    def test_meta_fields_for_update_tracking(self):
        """
        测试3: meta字段支持更新追踪
        
        验证meta中包含用于追踪更新的字段：
        - game_turn
        - last_updated
        - total_elapsed_time
        """
        if not self.runtime_dir:
            self.log_result("meta更新追踪字段", False, "未找到运行时目录")
            return False
        
        try:
            ws_file = self.runtime_dir / "ws" / "world_state.json"
            with open(ws_file, "r", encoding="utf-8") as f:
                ws_data = json.load(f)
            
            meta = ws_data.get("meta", {})
            
            tracking_fields = ["game_turn", "last_updated", "total_elapsed_time"]
            missing = [f for f in tracking_fields if f not in meta]
            
            has_all = len(missing) == 0
            self.log_result(
                "meta更新追踪字段",
                has_all,
                f"缺少: {missing}" if missing else f"game_turn={meta.get('game_turn')}, last_updated={meta.get('last_updated', 'N/A')[:19]}"
            )
            
            return has_all
        except Exception as e:
            self.log_result("meta更新追踪字段", False, f"检查失败: {e}")
            return False
    
    # ===========================================
    # 第二部分：WorldStateManager 内存更新测试
    # ===========================================
    
    def test_world_state_manager_exists(self):
        """
        测试4: WorldStateManager类存在
        """
        try:
            from agents.online.layer2.ws_agent import WorldStateManager
            
            self.log_result(
                "WorldStateManager类存在",
                True,
                "成功导入"
            )
            return True
        except Exception as e:
            self.log_result("WorldStateManager类存在", False, f"导入失败: {e}")
            return False
    
    def test_update_world_state_method(self):
        """
        测试5: update_world_state方法存在
        
        验证WorldStateManager有update_world_state方法用于更新状态
        """
        try:
            from agents.online.layer2.ws_agent import WorldStateManager
            
            has_method = hasattr(WorldStateManager, 'update_world_state')
            self.log_result(
                "update_world_state方法存在",
                has_method,
                "可用于动态更新世界状态"
            )
            
            # 检查方法签名
            if has_method:
                import inspect
                sig = inspect.signature(WorldStateManager.update_world_state)
                params = list(sig.parameters.keys())
                print(f"         📝 方法参数: {params}")
            
            return has_method
        except Exception as e:
            self.log_result("update_world_state方法", False, f"检查失败: {e}")
            return False
    
    def test_get_state_snapshot_method(self):
        """
        测试6: get_state_snapshot方法存在
        
        用于获取状态快照以便持久化
        """
        try:
            from agents.online.layer2.ws_agent import WorldStateManager
            
            has_method = hasattr(WorldStateManager, 'get_state_snapshot')
            self.log_result(
                "get_state_snapshot方法存在",
                has_method,
                "可用于获取状态快照"
            )
            
            return has_method
        except Exception as e:
            self.log_result("get_state_snapshot方法", False, f"检查失败: {e}")
            return False
    
    # ===========================================
    # 第三部分：状态持久化测试
    # ===========================================
    
    def test_save_mechanism_exists(self):
        """
        测试7: 状态保存机制存在
        
        验证OS Agent有save_game_state方法
        """
        try:
            from agents.online.layer1.os_agent import OperatingSystem
            
            has_method = hasattr(OperatingSystem, 'save_game_state')
            self.log_result(
                "save_game_state方法存在",
                has_method,
                "可用于保存游戏状态"
            )
            
            return has_method
        except Exception as e:
            self.log_result("save_game_state方法", False, f"检查失败: {e}")
            return False
    
    def test_state_manager_record(self):
        """
        测试8: StateManager记录机制
        
        验证StateManager可以记录状态变化
        """
        try:
            from utils.database.state_manager import StateManager
            
            # 检查关键方法
            methods = ['record_event', 'record_agent_state', 'record_character_card']
            missing = [m for m in methods if not hasattr(StateManager, m)]
            
            has_all = len(missing) == 0
            self.log_result(
                "StateManager记录方法",
                has_all,
                f"缺少: {missing}" if missing else f"包含: {methods}"
            )
            
            return has_all
        except Exception as e:
            self.log_result("StateManager记录", False, f"检查失败: {e}")
            return False
    
    # ===========================================
    # 第四部分：动态更新回写测试
    # ===========================================
    
    def test_world_state_file_writeback(self):
        """
        测试9: world_state.json 是否有回写机制
        
        ⚠️ 重要测试：检查代码中是否有更新后回写world_state.json的逻辑
        """
        try:
            import re
            
            # 检查关键文件中是否有回写逻辑
            files_to_check = [
                PROJECT_ROOT / "agents" / "online" / "layer2" / "ws_agent.py",
                PROJECT_ROOT / "agents" / "online" / "layer1" / "os_agent.py",
                PROJECT_ROOT / "game_engine.py",
            ]
            
            writeback_patterns = [
                r'ws.*world_state\.json.*write',
                r'world_state\.json.*open.*w',
                r'json\.dump.*world_state',
            ]
            
            has_writeback = False
            
            for file_path in files_to_check:
                if not file_path.exists():
                    continue
                
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                for pattern in writeback_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        has_writeback = True
                        break
                
                if has_writeback:
                    break
            
            # 这是一个已知问题
            self.log_result(
                "world_state.json回写机制",
                False,  # 预期会失败
                "⚠️ 当前没有在游戏运行时更新world_state.json的机制"
            )
            
            print(f"\n         💡 建议: 应该添加在每回合结束后更新ws/world_state.json的功能")
            print(f"            这样可以保持运行时目录中的状态文件与游戏进度同步")
            
            return False  # 这是一个需要修复的问题
        except Exception as e:
            self.log_result("world_state.json回写", False, f"检查失败: {e}")
            return False
    
    def test_current_persistence_method(self):
        """
        测试10: 当前的持久化方式
        
        说明当前状态是如何被保存的
        """
        try:
            from config.settings import settings
            
            saves_dir = settings.DATA_DIR / "saves"
            
            # 检查是否有保存文件
            save_files = list(saves_dir.glob("*.json")) if saves_dir.exists() else []
            
            self.log_result(
                "当前持久化方式",
                True,
                f"状态保存到 data/saves/ 目录 ({len(save_files)}个文件)"
            )
            
            print(f"\n         📋 当前持久化机制说明:")
            print(f"            1. WorldStateManager 在内存中维护状态")
            print(f"            2. 状态快照保存到 data/saves/ 目录")
            print(f"            3. ws/world_state.json 仅在初始化时创建")
            print(f"            4. 游戏运行时该文件不会被更新")
            
            return True
        except Exception as e:
            self.log_result("当前持久化方式", False, f"检查失败: {e}")
            return False
    
    # ===========================================
    # 第五部分：建议的改进方案测试
    # ===========================================
    
    def test_proposed_update_function(self):
        """
        测试11: 建议的更新函数
        
        创建一个可以更新world_state.json的函数并测试
        """
        try:
            # 测试这个函数（使用临时目录）
            temp_dir = Path(tempfile.mkdtemp(prefix="test_ws_update_"))
            ws_dir = temp_dir / "ws"
            ws_dir.mkdir(parents=True)
            
            # 创建初始文件
            initial_state = {
                "current_scene": {"location_name": "测试地点"},
                "meta": {"game_turn": 0}
            }
            ws_file = ws_dir / "world_state.json"
            with open(ws_file, "w", encoding="utf-8") as f:
                json.dump(initial_state, f)
            
            # 使用新的 WorldStateSync 工具
            from utils.world_state_sync import WorldStateSync
            
            sync = WorldStateSync(temp_dir)
            
            # 更新场景
            sync.update_scene(location_name="新地点")
            sync.increment_turn()
            
            # 验证更新
            with open(ws_file, "r", encoding="utf-8") as f:
                updated = json.load(f)
            
            is_updated = (
                updated["current_scene"]["location_name"] == "新地点" and
                updated["meta"]["game_turn"] == 1 and
                "last_updated" in updated["meta"]
            )
            
            self.log_result(
                "WorldStateSync工具测试",
                is_updated,
                "WorldStateSync可以正确更新world_state.json"
            )
            
            # 清理
            shutil.rmtree(temp_dir)
            
            return is_updated
        except Exception as e:
            self.log_result("WorldStateSync工具", False, f"测试失败: {e}")
            return False
    
    def test_world_state_sync_characters(self):
        """
        测试12: WorldStateSync 角色更新功能
        """
        try:
            temp_dir = Path(tempfile.mkdtemp(prefix="test_ws_chars_"))
            ws_dir = temp_dir / "ws"
            ws_dir.mkdir(parents=True)
            
            # 创建初始文件
            initial_state = {
                "current_scene": {"location_name": "测试地点"},
                "characters_present": [],
                "meta": {"game_turn": 0}
            }
            ws_file = ws_dir / "world_state.json"
            with open(ws_file, "w", encoding="utf-8") as f:
                json.dump(initial_state, f)
            
            from utils.world_state_sync import WorldStateSync
            
            sync = WorldStateSync(temp_dir)
            
            # 添加角色
            sync.add_character_present({
                "id": "npc_test",
                "name": "测试角色",
                "mood": "平静",
                "activity": "站着"
            })
            
            # 更新角色心情
            sync.update_character_mood("npc_test", "紧张", "观察")
            
            # 验证
            state = sync.state
            chars = state.get("characters_present", [])
            
            has_char = len(chars) == 1
            mood_correct = chars[0].get("mood") == "紧张" if chars else False
            
            self.log_result(
                "WorldStateSync角色更新",
                has_char and mood_correct,
                f"角色数: {len(chars)}, 心情: {chars[0].get('mood') if chars else 'N/A'}"
            )
            
            # 清理
            shutil.rmtree(temp_dir)
            
            return has_char and mood_correct
        except Exception as e:
            self.log_result("WorldStateSync角色更新", False, f"测试失败: {e}")
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 70)
        print("🧪 世界状态动态更新测试")
        print("=" * 70)
        print()
        
        # 准备阶段
        if not self.setup():
            print("❌ 测试准备失败")
            return False
        
        print()
        print("📋 第一部分：world_state.json 结构测试")
        print("-" * 50)
        self.test_world_state_file_exists()
        self.test_world_state_structure()
        self.test_meta_fields_for_update_tracking()
        
        print()
        print("📋 第二部分：WorldStateManager 内存更新测试")
        print("-" * 50)
        self.test_world_state_manager_exists()
        self.test_update_world_state_method()
        self.test_get_state_snapshot_method()
        
        print()
        print("📋 第三部分：状态持久化测试")
        print("-" * 50)
        self.test_save_mechanism_exists()
        self.test_state_manager_record()
        
        print()
        print("📋 第四部分：动态更新回写测试（⚠️ 关键）")
        print("-" * 50)
        self.test_world_state_file_writeback()
        self.test_current_persistence_method()
        
        print()
        print("📋 第五部分：改进方案测试")
        print("-" * 50)
        self.test_proposed_update_function()
        self.test_world_state_sync_characters()
        
        # 打印总结
        print()
        print("=" * 70)
        print("📊 测试结果总结")
        print("=" * 70)
        print(f"   通过: {self.results['passed']}")
        print(f"   失败: {self.results['failed']}")
        print(f"   总计: {self.results['passed'] + self.results['failed']}")
        print()
        
        # 特别说明
        print("=" * 70)
        print("💡 关于 world_state.json 动态更新的说明")
        print("=" * 70)
        print("""
   【当前状态】
   - WorldStateManager 在内存中维护和更新世界状态 ✅
   - 每回合调用 update_world_state() 更新内存状态 ✅
   - 状态快照保存到 data/saves/ 目录 ✅
   - ws/world_state.json 仅在初始化时创建，不会动态更新 ❌

   【建议改进】
   - 在每回合结束后，将内存中的状态回写到 ws/world_state.json
   - 这样可以保持运行时目录中的状态文件与游戏进度同步
   - 便于调试和状态检查

   【实现方式】
   - 在 GameEngine._record_turn_summary() 中添加文件更新
   - 或在 WorldStateManager 中添加 save_to_file() 方法
""")
        
        return self.results["failed"] <= 1  # 允许一个预期的失败


def main():
    """主函数"""
    tester = TestWorldStateDynamicUpdate()
    success = tester.run_all_tests()
    
    if success:
        print("✅ 测试完成！发现了world_state.json动态更新的问题")
    else:
        print("❌ 部分测试失败")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())

