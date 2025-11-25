"""
游戏引擎 - 完整的游戏回合逻辑
整合所有Agent，实现完整的游戏循环
"""
from pathlib import Path
from typing import Dict, Any, List, Optional
from config.settings import settings
from utils.logger import setup_logger
from agents.online.layer1.os_agent import OperatingSystem
from agents.online.layer1.logic_agent import LogicValidator
from agents.online.layer2.ws_agent import WorldStateManager
from agents.online.layer2.plot_agent import PlotDirector
from agents.online.layer2.vibe_agent import AtmosphereCreator
from agents.online.layer3.npc_agent import NPCManager
from agents.message_protocol import (
    AgentRole, MessageType, create_message, create_validation_request
)

logger = setup_logger("GameEngine", "game_engine.log")


class GameEngine:
    """
    游戏引擎
    协调所有Agent，实现完整的游戏回合
    """
    
    def __init__(self, genesis_path: Path):
        """
        初始化游戏引擎
        
        Args:
            genesis_path: Genesis.json文件路径
        """
        logger.info("=" * 60)
        logger.info("🎮 初始化游戏引擎...")
        logger.info("=" * 60)
        
        # 初始化信息中枢OS
        self.os = OperatingSystem(genesis_path)
        
        # 初始化逻辑审查官Logic
        self.logic = LogicValidator()
        self.logic.set_world_rules(self.os.genesis_data['world'])
        
        # 初始化光明会
        self.world_state = WorldStateManager(self.os.genesis_data)
        self.plot = PlotDirector(self.os.genesis_data)
        self.vibe = AtmosphereCreator(self.os.genesis_data)
        
        # 初始化NPC管理器
        self.npc_manager = NPCManager(self.os.genesis_data)
        
        # 注册所有Agent到OS
        self.os.register_handler(AgentRole.LOGIC, self.logic.handle_message)
        self.os.register_handler(AgentRole.WORLD_STATE, self.world_state.handle_message)
        self.os.register_handler(AgentRole.PLOT, self.plot.handle_message)
        self.os.register_handler(AgentRole.VIBE, self.vibe.handle_message)
        
        # 玩家状态
        self.player_location = self.os.world_context.current_location
        self.player_name = "玩家"  # 可以让用户自定义
        
        logger.info("✅ 游戏引擎初始化完成")
        logger.info(f"   - 世界: {self.os.genesis_data['world']['title']}")
        logger.info(f"   - NPC数量: {len(self.npc_manager.npcs)}")
        logger.info("=" * 60)
    
    def start_game(self) -> str:
        """
        开始游戏，返回开场描述
        
        Returns:
            开场场景描述
        """
        logger.info("🎬 游戏开始！")
        
        # 生成开场剧本
        initial_script = self.plot.generate_scene_script(
            player_action="进入游戏世界",
            player_location=self.player_location,
            present_characters=self.os.world_context.present_characters,
            world_context=self.world_state.get_context_summary()
        )
        
        # 生成开场氛围
        atmosphere_instruction = self._find_instruction(initial_script, "vibe")
        atmosphere = self.vibe.create_atmosphere(
            location_id=self.player_location,
            director_instruction=atmosphere_instruction or {},
            current_time=self.os.world_context.current_time,
            present_characters=self.os.world_context.present_characters  # ✨传递在场角色
        )
        
        # 拼接开场文本
        opening = self._format_opening(atmosphere, initial_script)
        
        self.os.world_context.world_state["game_started"] = True
        
        return opening
    
    def process_turn(self, player_input: str) -> Dict[str, Any]:
        """
        处理一个完整的游戏回合
        
        Args:
            player_input: 玩家的输入
        
        Returns:
            回合结果（包含所有输出文本和状态）
        """
        logger.info("=" * 60)
        logger.info(f"🎮 处理回合 #{self.os.turn_count + 1}")
        logger.info(f"玩家输入: {player_input[:50]}...")
        logger.info("=" * 60)
        
        try:
            # Step 1: 输入拦截（Logic验证）
            logger.info("📍 Step 1: 输入拦截")
            validation_result = self._validate_input(player_input)
            
            if not validation_result['is_valid']:
                logger.warning("❌ 输入被拒绝")
                return {
                    "success": False,
                    "error": validation_result['errors'][0] if validation_result['errors'] else "输入不符合世界观",
                    "text": f"❌ {validation_result['errors'][0]}"
                }
            
            logger.info("✅ 输入验证通过")
            
            # Step 2: 世界状态更新
            logger.info("📍 Step 2: 世界状态更新")
            world_update = self.world_state.update_world_state(
                player_action=player_input,
                player_location=self.player_location,
                time_cost=10
            )
            
            # 更新NPC状态
            self.npc_manager.update_npc_states(world_update.get("npc_updates", []))
            
            # Step 3: 剧情决策（Plot生成剧本）
            logger.info("📍 Step 3: 剧情决策")
            script = self.plot.generate_scene_script(
                player_action=player_input,
                player_location=self.player_location,
                present_characters=self.os.world_context.present_characters,
                world_context=self.world_state.get_context_summary()
            )
            
            # Step 4: 内容生成（Vibe + NPC）
            logger.info("📍 Step 4: 内容生成")
            
            # 生成氛围描写
            atmosphere_instruction = self._find_instruction(script, "vibe")
            atmosphere = None
            if atmosphere_instruction:
                atmosphere = self.vibe.create_atmosphere(
                    location_id=self.player_location,
                    director_instruction=atmosphere_instruction,
                    current_time=self.world_state.current_time,
                    present_characters=self.os.world_context.present_characters  # ✨传递在场角色
                )
            
            # NPC反应
            npc_reactions = []
            for char_id in self.os.world_context.present_characters:
                npc = self.npc_manager.get_npc(char_id)
                if npc:
                    npc_instruction = self._find_instruction(script, f"npc_{char_id}")
                    reaction = npc.react(
                        player_input=player_input,
                        scene_context={
                            "location": self.player_location,
                            "time": self.world_state.current_time,
                            "mood": script.get("scene_theme", {}).get("mood", "平静")
                        },
                        director_instruction=npc_instruction
                    )
                    npc_reactions.append({
                        "npc": npc,
                        "reaction": reaction
                    })
            
            # Step 5: 输出审查（可选，避免过慢）
            # 为了性能，这里简化处理
            
            # Step 6: 最终渲染
            logger.info("📍 Step 6: 最终渲染")
            output_text = self._render_output(atmosphere, npc_reactions, script)
            
            # 更新OS状态
            self.os.next_turn()
            self.os.add_to_history({
                "type": "player_action",
                "action": player_input,
                "location": self.player_location
            })
            
            logger.info("✅ 回合处理完成")
            logger.info("=" * 60)
            
            return {
                "success": True,
                "text": output_text,
                "world_state": world_update,
                "script": script,
                "atmosphere": atmosphere,
                "npc_reactions": npc_reactions
            }
            
        except Exception as e:
            logger.error(f"❌ 回合处理出错: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "text": f"❌ 系统错误: {e}"
            }
    
    def _validate_input(self, user_input: str) -> Dict[str, Any]:
        """验证用户输入"""
        context = {
            "current_location": self.player_location,
            "current_time": self.world_state.current_time,
        }
        
        result = self.logic.validate_user_input(user_input, context)
        return result.dict()
    
    def _find_instruction(self, script: Dict[str, Any], target: str) -> Optional[Dict[str, Any]]:
        """从剧本中查找指定目标的指令"""
        for instruction in script.get("instructions", []):
            if instruction.get("target") == target or instruction.get("target", "").startswith(target):
                return instruction
        return None
    
    def _format_opening(self, atmosphere: Dict[str, Any], script: Dict[str, Any]) -> str:
        """格式化开场文本"""
        lines = []
        
        lines.append("=" * 70)
        lines.append(f"  🎭 {self.os.genesis_data['world']['title']}")
        lines.append("=" * 70)
        lines.append("")
        
        # 氛围描写
        if atmosphere:
            lines.append(atmosphere.get("atmosphere_description", ""))
            lines.append("")
        
        # 导演笔记
        if script.get("director_notes"):
            lines.append(f"💭 {script['director_notes']}")
            lines.append("")
        
        lines.append("你的故事开始了...")
        lines.append("")
        lines.append("=" * 70)
        
        return "\n".join(lines)
    
    def _render_output(
        self,
        atmosphere: Optional[Dict[str, Any]],
        npc_reactions: List[Dict[str, Any]],
        script: Dict[str, Any]
    ) -> str:
        """渲染输出文本"""
        lines = []
        
        lines.append("\n" + "─" * 70)
        
        # 氛围描写
        if atmosphere:
            lines.append("\n🌍 环境:")
            lines.append(atmosphere.get("atmosphere_description", ""))
        
        # NPC反应
        if npc_reactions:
            lines.append("\n")
            for item in npc_reactions:
                npc = item["npc"]
                reaction = item["reaction"]
                
                lines.append(f"🎭 {npc.character_name}:")
                
                if reaction.get("action"):
                    lines.append(f"   {reaction['action']}")
                
                if reaction.get("dialogue"):
                    lines.append(f'   "{reaction["dialogue"]}"')
                
                lines.append("")
        
        lines.append("─" * 70)
        
        return "\n".join(lines)
    
    def get_game_status(self) -> Dict[str, Any]:
        """获取游戏状态"""
        return {
            "turn": self.os.turn_count,
            "time": self.world_state.current_time,
            "location": self.player_location,
            "plot_progress": self.plot.get_plot_status(),
            "npcs": {npc_id: npc.get_state() for npc_id, npc in self.npc_manager.npcs.items()}
        }
    
    def save_game(self, save_name: str = "quicksave"):
        """保存游戏"""
        self.os.save_game_state(
            settings.DATA_DIR / "saves" / f"{save_name}.json"
        )
        logger.info(f"💾 游戏已保存: {save_name}")

