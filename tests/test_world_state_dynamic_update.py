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
            import os

            os.environ.setdefault("LLM_PROVIDER", "mock")
            
            # 查找现有的运行时目录
            runtime_base = settings.DATA_DIR / "runtime"
            if runtime_base.exists():
                rts = sorted([d for d in runtime_base.iterdir() if d.is_dir() and (d / "ws" / "world_state.json").exists()], key=lambda x: x.stat().st_mtime, reverse=True)
                if rts:
                    self.runtime_dir = rts[0]
                    print(f"[Dir] 使用运行时目录: {self.runtime_dir.name}")
            
            if not self.runtime_dir:
                # 自动生成一个新的 runtime，避免依赖手工步骤
                from initial_Illuminati import get_available_worlds, IlluminatiInitializer

                worlds = get_available_worlds()
                if worlds:
                    world_name = worlds[0]
                    suffix = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    initializer = IlluminatiInitializer(world_name, runtime_name=suffix, overwrite_runtime=False)
                    self.runtime_dir = initializer.run()
                    print(f"[Dir] 已自动生成运行时目录: {self.runtime_dir.name}")
                else:
                    print("WARNING 未找到可用世界数据，跳过 runtime 相关测试")
            
            return True
        except Exception as e:
            print(f"FAIL 准备阶段失败: {e}")
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
                print(f"         [Loc] 当前场景: {scene.get('location_name', 'N/A')}")
                print(f"         [Time] 游戏回合: {meta.get('game_turn', 0)}")
                print(f"         [Chars] 在场角色: {len(chars)}人")
            
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
                print(f"         [Note] 方法参数: {params}")
            
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
        
        检查游戏引擎是否具备回写机制（通过 WorldStateSync 或显式写文件）。
        """
        try:
            game_engine_file = PROJECT_ROOT / "game_engine.py"
            if not game_engine_file.exists():
                self.log_result("world_state.json回写机制", False, "game_engine.py 不存在")
                return False

            content = game_engine_file.read_text(encoding="utf-8")
            has_sync = ("WorldStateSync" in content) and ("_sync_world_state_file" in content)

            self.log_result(
                "world_state.json回写机制",
                has_sync,
                "检测到 WorldStateSync + _sync_world_state_file" if has_sync else "未检测到回写机制"
            )

            return has_sync
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
            
            print(f"\n         [List] 当前持久化机制说明:")
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
        print("[Test] 世界状态动态更新测试")
        print("=" * 70)
        print()
        
        # 准备阶段
        if not self.setup():
            print("FAIL 测试准备失败")
            return False
        
        print()
        print("[List] 第一部分：world_state.json 结构测试")
        print("-" * 50)
        self.test_world_state_file_exists()
        self.test_world_state_structure()
        self.test_meta_fields_for_update_tracking()
        
        print()
        print("[List] 第二部分：WorldStateManager 内存更新测试")
        print("-" * 50)
        self.test_world_state_manager_exists()
        self.test_update_world_state_method()
        self.test_get_state_snapshot_method()
        
        print()
        print("[List] 第三部分：状态持久化测试")
        print("-" * 50)
        self.test_save_mechanism_exists()
        self.test_state_manager_record()
        
        print()
        print("[List] 第四部分：动态更新回写测试（WARNING 关键）")
        print("-" * 50)
        self.test_world_state_file_writeback()
        self.test_current_persistence_method()
        
        print()
        print("[List] 第五部分：改进方案测试")
        print("-" * 50)
        self.test_proposed_update_function()
        self.test_world_state_sync_characters()
        
        # 打印总结
        print()
        print("=" * 70)
        print("[Stats] 测试结果总结")
        print("=" * 70)
        print(f"   通过: {self.results['passed']}")
        print(f"   失败: {self.results['failed']}")
        print(f"   总计: {self.results['passed'] + self.results['failed']}")
        print()
        
        # 特别说明
        print("=" * 70)
        print("HINT 关于 world_state.json 动态更新的说明")
        print("=" * 70)
        print("""
    【当前状态】
    - WorldStateManager 在内存中维护和更新世界状态 PASS
    - 状态快照保存到 data/saves/ 目录 PASS
    - GameEngine 通过 WorldStateSync 具备 world_state.json 回写能力 PASS

    【备注】
    - 本测试仅验证“回写机制存在”。是否在每个模式/每个回合都执行回写，需要结合实际游戏回路进一步覆盖。
""")
        
        return self.results["failed"] == 0


def main():
    """主函数"""
    tester = TestWorldStateDynamicUpdate()
    success = tester.run_all_tests()
    
    if success:
        print("PASS 世界状态动态更新测试通过")
    else:
        print("FAIL 部分测试失败")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())

