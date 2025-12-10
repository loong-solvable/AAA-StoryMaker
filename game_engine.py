"""
游戏引擎 - 完整的游戏回合逻辑
整合所有Agent，实现完整的游戏循环
"""
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from uuid import uuid4
from config.settings import settings
from utils.logger import setup_logger
from utils.database import StateManager
from utils.world_state_sync import WorldStateSync
from agents.online.layer1.os_agent import OperatingSystem
from agents.online.layer1.logic_agent import LogicValidator
from agents.online.layer2.ws_agent import WorldStateManager
from agents.online.layer2.plot_agent import PlotDirector
from agents.online.layer2.vibe_agent import AtmosphereCreator
from agents.online.layer3.npc_agent import NPCManager
from agents.message_protocol import (
    AgentRole, MessageType, create_message, create_validation_request
)
from utils.memory_manager import MemoryManager

logger = setup_logger("GameEngine", "game_engine.log")


class GameEngine:
    """
    游戏引擎
    协调所有Agent，实现完整的游戏回合
    """
    
    def __init__(
        self,
        genesis_path: Path,
        async_mode: bool = True,
        enable_logic_check: bool = False,  # Logic验证开关，默认关闭
        enable_vibe: bool = False,  # Vibe氛围开关，默认关闭
    ):
        """
        初始化游戏引擎

        Args:
            genesis_path: Genesis.json文件路径
            async_mode: 是否启用异步模式
            enable_logic_check: 是否启用Logic输入验证（默认关闭以提升速度）
            enable_vibe: 是否启用Vibe氛围描写（默认关闭以提升速度）
        """
        logger.info("=" * 60)
        logger.info("🎮 初始化游戏引擎...")
        logger.info("=" * 60)

        # 初始化信息中枢OS
        self.os = OperatingSystem(genesis_path)
        self.async_mode = async_mode
        self.enable_logic_check = enable_logic_check
        self.enable_vibe = enable_vibe

        self.game_id = uuid4().hex
        self.state_manager = StateManager(
            game_id=self.game_id,
            game_name=self.os.genesis_data.get("world", {}).get("title", "未知世界"),
            genesis_path=str(genesis_path)
        )

        # 初始化逻辑审查官Logic（可选）
        self.logic = None
        if self.enable_logic_check:
            self.logic = LogicValidator()
            self.logic.set_world_rules(self.os.genesis_data['world'])
        
        # 初始化光明会
        self.world_state = WorldStateManager(self.os.genesis_data)
        self.plot = PlotDirector(self.os.genesis_data)
        self.vibe = AtmosphereCreator(self.os.genesis_data)
        
        # 初始化NPC管理器
        self.npc_manager = NPCManager(self.os.genesis_data)
        
        # 注册所有Agent到OS（跳过禁用的Agent）
        if self.logic:
            self.os.register_handler(AgentRole.LOGIC, self.logic.handle_message)
        self.os.register_handler(AgentRole.WORLD_STATE, self.world_state.handle_message)
        self.os.register_handler(AgentRole.PLOT, self.plot.handle_message)
        self.os.register_handler(AgentRole.VIBE, self.vibe.handle_message)

        # 玩家状态
        self.player_location = self.os.world_context.current_location
        if "user" not in self.os.world_context.present_characters:
            self.os.world_context.present_characters.append("user")
        self.player_name = self._get_player_name()
        
        # 初始化世界状态同步器（用于同步 world_state.json）
        self.runtime_dir = genesis_path.parent if genesis_path else None
        self.world_state_sync: Optional[WorldStateSync] = None

        # 初始化长期记忆管理器（默认启用，失败不阻断）
        self.memory_manager = None
        try:
            self.memory_manager = MemoryManager(runtime_dir=self.runtime_dir)
            logger.info("🧠 长期记忆管理器已启用")
        except Exception as e:
            logger.warning(f"⚠️ 长期记忆管理器初始化失败: {e}")
        if self.runtime_dir and (self.runtime_dir / "ws").exists():
            try:
                self.world_state_sync = WorldStateSync(self.runtime_dir)
                logger.info("✅ 世界状态同步器已初始化")
            except Exception as e:
                logger.warning(f"⚠️ 世界状态同步器初始化失败: {e}")
        
        self._bootstrap_character_cards()
        self._record_agent_snapshots(turn_number=0)
        
        logger.info("✅ 游戏引擎初始化完成")
        logger.info(f"   - 世界: {self.os.genesis_data['world']['title']}")
        logger.info(f"   - NPC数量: {len(self.npc_manager.npcs)}")
        logger.info(f"   - 异步模式: {'ON' if self.async_mode else 'OFF'}")
        logger.info(f"   - Logic验证: {'ON' if self.enable_logic_check else 'OFF'}")
        logger.info(f"   - Vibe氛围: {'ON' if self.enable_vibe else 'OFF'}")
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
        atmosphere = None
        if self.enable_vibe:
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
        self._record_turn_summary(
            turn_number=0,
            player_input="进入游戏世界",
            world_update=None,
            script=initial_script,
            atmosphere=atmosphere,
            npc_reactions=[],
            event_type="game_start"
        )
        
        return opening
    
    def process_turn(self, player_input: str) -> Dict[str, Any]:
        """
        处理一个完整的游戏回合
        
        Args:
            player_input: 玩家的输入
        
        Returns:
            回合结果（包含所有输出文本和状态）
        """
        # 如果开启异步模式，委托给 async 版本并运行事件循环
        if self.async_mode:
            # 如果当前已有事件循环，提示直接使用 await
            try:
                asyncio.get_running_loop()
                raise RuntimeError(
                    "检测到已存在的事件循环，请直接调用 await process_turn_async() 而非 process_turn()"
                )
            except RuntimeError:
                # 没有运行中的事件循环，可以使用 asyncio.run
                return asyncio.run(self.process_turn_async(player_input))

        logger.info("=" * 60)
        logger.info(f"🎮 处理回合 #{self.os.turn_count + 1}")
        logger.info(f"玩家输入: {player_input[:50]}...")
        logger.info("=" * 60)
        
        current_turn = self.os.turn_count + 1
        
        try:
            # Step 1: 输入拦截（Logic验证，可选）
            logger.info("📍 Step 1: 输入拦截")
            if self.enable_logic_check and self.logic:
                validation_result = self._validate_input(player_input)
                
                if not validation_result['is_valid']:
                    logger.warning("❌ 输入被拒绝")
                    return {
                        "success": False,
                        "error": validation_result['errors'][0] if validation_result['errors'] else "输入不符合世界观",
                        "text": f"❌ {validation_result['errors'][0]}"
                    }
                
                logger.info("✅ 输入验证通过")
            else:
                logger.info("ℹ️ Logic验证已关闭，跳过输入拦截")
            
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
                world_context=self.world_state.get_context_summary(),
                story_history=self._get_story_history(),
                last_scene_dialogues=self._get_last_scene_dialogues()
            )
            
            # Step 4: 内容生成（Vibe 可选 + NPC）
            logger.info("📍 Step 4: 内容生成")
            logger.info(f"   - 在场 NPC: {len(self.os.world_context.present_characters) - 1}")
            
            atmosphere = None
            if self.enable_vibe:
                atmosphere_instruction = self._find_instruction(script, "vibe")
                if not atmosphere_instruction:
                    atmosphere_instruction = {
                        "target": "vibe",
                        "parameters": {
                            "emotional_tone": script.get("scene_theme", {}).get("mood", "平静"),
                            "focus": "环境变化与角色互动",
                            "sensory_details": ["视觉", "听觉", "嗅觉", "触觉"]
                        }
                    }
                atmosphere = self.vibe.create_atmosphere(
                    location_id=self.player_location,
                    director_instruction=atmosphere_instruction,
                    current_time=self.world_state.current_time,
                    present_characters=self.os.world_context.present_characters
                )
            else:
                logger.info("ℹ️ Vibe氛围已关闭，跳过生成")
            
            # NPC反应
            npc_reactions = []
            # 提取剧情推演作为场景摘要
            scene_summary = script.get("director_notes", "")
            for char_id in self.os.world_context.present_characters:
                if char_id == "user":
                    continue
                npc = self.npc_manager.get_npc(char_id)
                if npc:
                    npc_instruction = self._find_instruction(script, f"npc_{char_id}")
                    # 如果没有专属指令，用通用剧情作为指导
                    if not npc_instruction and scene_summary:
                        npc_instruction = {
                            "target": f"npc_{char_id}",
                            "parameters": {
                                "scene_summary": scene_summary,
                                "objective": "根据剧情推演自然反应"
                            }
                        }
                    reaction = npc.react(
                        player_input=player_input,
                        scene_context={
                            "location": self.player_location,
                            "time": self.world_state.current_time,
                            "mood": script.get("scene_theme", {}).get("mood", "平静"),
                            "scene_summary": scene_summary
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
            
            self._record_turn_summary(
                turn_number=current_turn,
                player_input=player_input,
                world_update=world_update,
                script=script,
                atmosphere=atmosphere,
                npc_reactions=npc_reactions
            )
            
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

    async def process_turn_async(self, player_input: str) -> Dict[str, Any]:
        """
        异步版本的回合处理，使用并发方式生成 NPC 反应。
        """
        logger.info("=" * 60)
        logger.info(f"🎮 [async] 处理回合 #{self.os.turn_count + 1}")
        logger.info(f"玩家输入: {player_input[:50]}...")
        logger.info("=" * 60)

        current_turn = self.os.turn_count + 1

        try:
            # 先获取当前的world_context（上一回合状态），供Plot使用
            pre_update_context = self.world_state.get_context_summary()

            # 获取历史数据供Plot使用
            story_history = self._get_story_history()
            last_scene_dialogues = self._get_last_scene_dialogues()

            # 根据开关决定并行任务
            if self.enable_logic_check and self.logic:
                # Logic开启：Logic + WS + Plot 全并行
                logger.info("📍 Step 1-3: 验证 + 世界状态 + 剧情（全并行）")
                logic_task = self._async_validate_input(player_input)
                ws_task = self.world_state.async_update_world_state(
                    player_action=player_input,
                    player_location=self.player_location,
                    time_cost=10
                )
                plot_task = self.plot.async_generate_scene_script(
                    player_action=player_input,
                    player_location=self.player_location,
                    present_characters=self.os.world_context.present_characters,
                    world_context=pre_update_context,
                    story_history=story_history,
                    last_scene_dialogues=last_scene_dialogues
                )

                validation_result, world_update, script = await asyncio.gather(
                    logic_task, ws_task, plot_task
                )

                # 检查Logic验证结果
                if not validation_result['is_valid']:
                    logger.warning("❌ 输入被拒绝")
                    return {
                        "success": False,
                        "error": validation_result['errors'][0] if validation_result['errors'] else "输入不符合世界观",
                        "text": f"❌ {validation_result['errors'][0]}"
                    }
            else:
                # Logic关闭：只执行 WS + Plot 并行
                logger.info("📍 Step 1-2: 世界状态 + 剧情（并行，Logic跳过）")
                ws_task = self.world_state.async_update_world_state(
                    player_action=player_input,
                    player_location=self.player_location,
                    time_cost=10
                )
                plot_task = self.plot.async_generate_scene_script(
                    player_action=player_input,
                    player_location=self.player_location,
                    present_characters=self.os.world_context.present_characters,
                    world_context=pre_update_context,
                    story_history=story_history,
                    last_scene_dialogues=last_scene_dialogues
                )

                world_update, script = await asyncio.gather(ws_task, plot_task)

            logger.info("✅ 世界状态 + 剧情决策完成")

            # WS完成后更新NPC状态
            self.npc_manager.update_npc_states(world_update.get("npc_updates", []))

            # Step 3: 内容生成（Vibe可选 + NPC 并行）
            vibe_status = "ON" if self.enable_vibe else "OFF"
            logger.info(f"📍 Step 3: 内容生成（Vibe:{vibe_status} + NPC 并行）")
            logger.info(f"   - 在场 NPC: {len(self.os.world_context.present_characters) - 1}")

            # 收集所有并行任务
            all_tasks = []
            task_labels = []  # 用于标识任务类型

            # Vibe 任务（仅在开启时执行）
            if self.enable_vibe:
                atmosphere_instruction = self._find_instruction(script, "vibe")
                if not atmosphere_instruction:
                    atmosphere_instruction = {
                        "target": "vibe",
                        "parameters": {
                            "emotional_tone": script.get("scene_theme", {}).get("mood", "平静"),
                            "focus": "环境变化与角色互动",
                            "sensory_details": ["视觉", "听觉", "嗅觉"]
                        }
                    }
                params = atmosphere_instruction.get("parameters", {})
                if not params.get("sensory_details"):
                    params["sensory_details"] = ["视觉", "听觉", "嗅觉", "触觉"]
                    atmosphere_instruction["parameters"] = params

                all_tasks.append(
                    self.vibe.async_create_atmosphere(
                        location_id=self.player_location,
                        director_instruction=atmosphere_instruction,
                        current_time=self.world_state.current_time,
                        present_characters=self.os.world_context.present_characters
                    )
                )
                task_labels.append(("vibe", None))

            # NPC 任务
            npc_objs = []
            # 提取剧情推演作为场景摘要（关键：让NPC知道当前剧情发展）
            scene_summary = script.get("director_notes", "")
            for char_id in self.os.world_context.present_characters:
                if char_id == "user":
                    continue
                npc = self.npc_manager.get_npc(char_id)
                if npc:
                    npc_instruction = self._find_instruction(script, f"npc_{char_id}")
                    # 如果没有专属指令，用通用剧情作为指导
                    if not npc_instruction and scene_summary:
                        npc_instruction = {
                            "target": f"npc_{char_id}",
                            "parameters": {
                                "scene_summary": scene_summary,
                                "objective": "根据剧情推演自然反应"
                            }
                        }
                    npc_objs.append((npc, npc_instruction))
                    all_tasks.append(
                        npc.async_react(
                            player_input=player_input,
                            scene_context={
                                "location": self.player_location,
                                "time": self.world_state.current_time,
                                "mood": script.get("scene_theme", {}).get("mood", "平静"),
                                "scene_summary": scene_summary  # 传递剧情摘要
                            },
                            director_instruction=npc_instruction
                        )
                    )
                    task_labels.append(("npc", npc))

            # 并行执行所有任务
            atmosphere = None
            npc_reactions: List[Dict[str, Any]] = []

            if all_tasks:
                results = await asyncio.gather(*all_tasks, return_exceptions=True)
                for (label_type, label_data), res in zip(task_labels, results):
                    if isinstance(res, Exception):
                        if label_type == "vibe":
                            logger.error("❌ Vibe 并行生成失败: %s", res)
                        else:
                            logger.error("❌ NPC[%s] 并行演绎失败: %s", label_data.character_id, res)
                        continue

                    if label_type == "vibe":
                        atmosphere = res
                    else:
                        npc_reactions.append({
                            "npc": label_data,
                            "reaction": res
                        })

            # Step 5: 输出审查（可选，避免过慢） - 保持简化

            # Step 6: 最终渲染
            logger.info("📍 Step 6: 最终渲染")
            output_text = self._render_output(atmosphere, npc_reactions, script)

            self._record_turn_summary(
                turn_number=current_turn,
                player_input=player_input,
                world_update=world_update,
                script=script,
                atmosphere=atmosphere,
                npc_reactions=npc_reactions
            )

            # 更新OS状态
            self.os.next_turn()
            self.os.add_to_history({
                "type": "player_action",
                "action": player_input,
                "location": self.player_location
            })

            logger.info("✅ 回合处理完成 [async]")
            logger.info("=" * 60)

            return {
                "success": True,
                "text": output_text,
                "world_state": world_update,
                "script": script,
                "atmosphere": atmosphere,
                "npc_reactions": npc_reactions
            }

        except Exception as e:  # noqa: BLE001
            logger.error(f"❌ 回合处理出错 [async]: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "text": f"❌ 系统错误: {e}"
            }
    
    def _validate_input(self, user_input: str) -> Dict[str, Any]:
        """验证用户输入"""
        if not self.logic:
            return {"is_valid": True, "errors": []}

        context = {
            "current_location": self.player_location,
            "current_time": self.world_state.current_time,
        }
        
        result = self.logic.validate_user_input(user_input, context)
        return result.dict()

    async def _async_validate_input(self, user_input: str) -> Dict[str, Any]:
        """异步版本的输入验证"""
        return await asyncio.to_thread(self._validate_input, user_input)
    
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

                # 显示内心独白（用斜体/淡色提示）
                if reaction.get("thought"):
                    thought = reaction["thought"][:80]
                    lines.append(f"   💭 ({thought}...)")

                if reaction.get("action"):
                    lines.append(f"   {reaction['action']}")

                if reaction.get("dialogue"):
                    lines.append(f'   "{reaction["dialogue"]}"')

                # 显示情感状态
                if reaction.get("emotion"):
                    lines.append(f"   [情感: {reaction['emotion']}]")

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

    def _bootstrap_character_cards(self):
        """将Genesis中的角色卡导入数据库系统"""
        characters = self.os.genesis_data.get("characters", [])
        for char in characters:
            char_id = char.get("id")
            if not char_id:
                continue
            try:
                self.state_manager.record_character_card(
                    character_id=char_id,
                    version=1,
                    card_data=char,
                    changes=None,
                    changed_by="genesis_import"
                )
            except Exception as exc:
                logger.warning(f"⚠️ 记录角色卡失败: {char_id} - {exc}")

    def _record_turn_summary(
        self,
        turn_number: int,
        player_input: str,
        world_update: Optional[Dict[str, Any]],
        script: Optional[Dict[str, Any]],
        atmosphere: Optional[Dict[str, Any]],
        npc_reactions: Optional[List[Dict[str, Any]]],
        event_type: str = "turn_summary"
    ):
        """记录每回合的汇总信息"""
        try:
            payload = {
                "player_input": player_input,
                "world_update": world_update or {},
                "script": script or {},
                "atmosphere": atmosphere or {},
                "npc_reactions": self._serialize_reactions(npc_reactions),
                "npc_snapshot": self.npc_manager.get_state_snapshot(),
            }
            self.state_manager.record_event(
                event_type=event_type,
                event_data=payload,
                agent_source="GameEngine",
                turn_number=turn_number,
            )
            self._record_agent_snapshots(turn_number=turn_number)

            # 同步世界状态到 world_state.json
            self._sync_world_state_file(turn_number, world_update)

            # 记录到长期记忆管理器
            if self.memory_manager:
                self._record_to_memory_manager(
                    turn_number, player_input, npc_reactions, atmosphere
                )

        except Exception as exc:
            logger.warning(f"⚠️ 记录回合数据失败: {exc}")
    
    def _sync_world_state_file(
        self,
        turn_number: int,
        world_update: Optional[Dict[str, Any]]
    ):
        """同步世界状态到 ws/world_state.json 文件"""
        if not self.world_state_sync:
            return
        
        try:
            # 获取当前世界状态快照
            ws_snapshot = self.world_state.get_state_snapshot()
            
            # 构建完整的世界状态数据
            world_state_data = {
                "current_scene": {
                    "location_id": self.player_location,
                    "location_name": self._get_location_name(self.player_location),
                    "time_of_day": self.world_state.current_time,
                    "description": ws_snapshot.get("current_situation", "")
                },
                "weather": ws_snapshot.get("weather", {}),
                "characters_present": [
                    {
                        "id": char_id,
                        "name": self._get_character_name(char_id),
                        "mood": self._get_character_mood(char_id),
                        "activity": "在场"
                    }
                    for char_id in self.os.world_context.present_characters
                ],
                "characters_absent": [],
                "relationship_matrix": ws_snapshot.get("relationship_changes", {}),
                "world_situation": world_update or {},
                "meta": {
                    "game_turn": turn_number,
                    "last_updated": self._get_current_timestamp(),
                    "total_elapsed_time": ws_snapshot.get("elapsed_time", "0分钟")
                }
            }
            
            self.world_state_sync.update_from_dict(world_state_data)
            logger.debug(f"✅ world_state.json 已同步 (回合 {turn_number})")
            
        except Exception as e:
            logger.warning(f"⚠️ 同步 world_state.json 失败: {e}")

    def _record_to_memory_manager(
        self,
        turn_number: int,
        player_input: str,
        npc_reactions: Optional[List[Dict[str, Any]]],
        atmosphere: Optional[Dict[str, Any]]  # noqa: ARG002 - 预留参数，后续可用于记录环境变化
    ):
        """记录到长期记忆管理器，用于跨幕记忆"""
        if not self.memory_manager:
            return
        try:
            scene_id = self._get_scene_id_from_script_or_turn(npc_reactions, turn_number)

            # 参与者统一使用 ID + name，避免歧义
            participants = [{"id": "user", "name": self.player_name}]
            emotional_shifts = {}

            for item in (npc_reactions or []):
                npc = item.get("npc")
                reaction = item.get("reaction", {})
                if npc:
                    char_id = getattr(npc, "character_id", None)
                    char_name = getattr(npc, "character_name", "未知角色")
                    if not char_id:
                        continue
                    participants.append({"id": char_id, "name": char_name})

                    # 记录情感变化
                    emotion = reaction.get("emotion", "")
                    if emotion:
                        emotional_shifts[char_id] = emotion

                    # 记录角色互动
                    # attitude_delta: 当前态度与中性值(0.5)的偏移，正数表示好感，负数表示敌意
                    emotional_state = getattr(npc, "emotional_state", {})
                    attitude_delta = emotional_state.get("attitude_toward_player", 0.5) - 0.5
                    self.memory_manager.record_interaction(
                        character_id=char_id,
                        player_action=player_input[:100],
                        character_response=reaction.get("dialogue", reaction.get("action", ""))[:100],
                        emotional_impact=attitude_delta,
                        is_significant=abs(attitude_delta) > 0.1
                    )

            # 提取关键事件（基于NPC对话和行为）
            key_events = []
            for item in (npc_reactions or []):
                reaction = item.get("reaction", {})
                npc = item.get("npc")
                npc_name = getattr(npc, "character_name", "某人") if npc else "某人"

                # 优先记录对话内容（最重要）
                dialogue = reaction.get("dialogue", "")
                if dialogue and len(dialogue) > 5:
                    key_events.append(f"{npc_name}说: {dialogue[:50]}")

                # 其次记录动作
                action = reaction.get("action", "")
                if action and len(action) > 10:
                    key_events.append(f"{npc_name}: {action[:30]}")

            # 记录场景摘要（场景ID 优先取 Plot/OS，缺省回退 turn_number）
            self.memory_manager.record_scene_summary(
                scene_number=scene_id,
                location=self.player_location,
                participants=participants,
                key_events=key_events[:6],  # 增加到6条，包含对话和动作
                emotional_shifts=emotional_shifts,
                player_action_summary=player_input[:80]
            )

            logger.debug(f"🧠 长期记忆已更新 (场景 {scene_id}, 回合 {turn_number})")

        except Exception as e:
            logger.warning(f"⚠️ 记录长期记忆失败: {e}")

    def _get_scene_id_from_script_or_turn(
        self,
        npc_reactions: Optional[List[Dict[str, Any]]],
        turn_number: int
    ) -> int:
        """
        获取当前场景ID，优先从 Plot/OS 的场景信息中读取，缺省回退为 turn_number。
        目前 Plot/OS 未暴露 scene_id，占位为 turn_number，便于后续对齐。
        """
        try:
            # future: 如果 script 或 world_state 返回 scene_id，可在调用 _record_to_memory_manager 时传入并使用
            return turn_number
        except Exception:
            return turn_number

    def _get_location_name(self, location_id: str) -> str:
        """获取地点名称"""
        for loc in self.os.genesis_data.get("locations", []):
            if loc.get("id") == location_id:
                return loc.get("name", location_id)
        return location_id
    
    def _get_character_name(self, char_id: str) -> str:
        """获取角色名称"""
        for char in self.os.genesis_data.get("characters", []):
            if char.get("id") == char_id:
                return char.get("name", char_id)
        return char_id

    def _get_player_name(self) -> str:
        """获取玩家名称（来自 genesis）"""
        for char in self.os.genesis_data.get("characters", []):
            if char.get("id") == "user":
                return char.get("name", "玩家")
        return "玩家"
    
    def _get_character_mood(self, char_id: str) -> str:
        """获取角色心情"""
        npc = self.npc_manager.get_npc(char_id)
        if npc:
            state = npc.get_state()
            return state.get("mood", "平静")
        return "平静"
    
    def _get_current_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()

    def _get_story_history(self) -> str:
        """获取历史剧情摘要（供Plot使用）"""
        if not self.memory_manager:
            return ""
        return self.memory_manager.get_scene_context(limit=5)

    def _get_last_scene_dialogues(self) -> str:
        """获取上一幕对话记录（供Plot使用）"""
        if not self.memory_manager:
            return ""
        # 从scene_summaries中获取最近场景的关键事件
        summaries = self.memory_manager.memories.get("scene_summaries", [])
        if not summaries:
            return ""
        last_summary = summaries[-1]
        key_events = last_summary.get("key_events", [])
        player_action = last_summary.get("player_action", "")
        participants = last_summary.get("participants", [])

        lines = []
        if participants:
            # participants可能是dict列表 [{"id": "x", "name": "y"}] 或字符串列表
            if participants and isinstance(participants[0], dict):
                names = [p.get("name", p.get("id", "")) for p in participants]
            else:
                names = participants
            lines.append(f"参与角色: {', '.join(names)}")
        if player_action:
            lines.append(f"玩家行动: {player_action}")
        if key_events:
            lines.append("发生的事件:")
            for event in key_events:
                lines.append(f"  - {event}")
        return "\n".join(lines) if lines else ""

    def _serialize_reactions(self, reactions: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """将NPC反应转换为可序列化的结构"""
        serialized = []
        for item in reactions or []:
            npc = item.get("npc")
            reaction = item.get("reaction", {})
            if not npc:
                continue
            serialized.append(
                {
                    "npc_id": npc.character_id,
                    "npc_name": npc.character_name,
                    "reaction": reaction,
                }
            )
        return serialized

    def _record_agent_snapshots(self, turn_number: int):
        """记录各核心Agent的状态快照"""
        try:
            self.state_manager.record_agent_state(
                agent_type="OS",
                turn_number=turn_number,
                state_snapshot=self.os.get_game_state(),
            )
            self.state_manager.record_agent_state(
                agent_type="WS",
                turn_number=turn_number,
                state_snapshot=self.world_state.get_state_snapshot(),
            )
            self.state_manager.record_agent_state(
                agent_type="Plot",
                turn_number=turn_number,
                state_snapshot=self.plot.get_state_snapshot(),
            )
            self.state_manager.record_agent_state(
                agent_type="Vibe",
                turn_number=turn_number,
                state_snapshot=self.vibe.get_state_snapshot(),
            )
        except Exception as exc:
            logger.warning(f"⚠️ 记录Agent状态失败: {exc}")

    def generate_action_suggestions(self) -> List[str]:
        """
        生成玩家行动建议（2个选项）

        Returns:
            包含2个行动建议的列表
        """
        try:
            from utils.llm_factory import get_llm
            from langchain_core.prompts import ChatPromptTemplate
            from langchain_core.output_parsers import StrOutputParser

            llm = get_llm(temperature=0.9)  # 高温度增加多样性

            # 构建上下文
            player_name = self._get_player_name()
            location_name = self._get_location_name(self.player_location)
            present_chars = [
                self._get_character_name(c)
                for c in self.os.world_context.present_characters
                if c != "user"
            ]
            recent_events = self.os.recent_events[-3:] if hasattr(self.os, 'recent_events') else []

            prompt = ChatPromptTemplate.from_messages([
                ("system", """你是一个互动叙事游戏的行动建议器。
根据当前场景，为玩家生成2个有趣且合理的行动选项。

要求：
1. 每个选项应该是具体的行动描述，10-30字
2. 两个选项应该代表不同的方向（如：探索vs对话，主动vs被动）
3. 行动应符合当前场景和世界观
4. 不要使用编号，直接输出两个选项，用换行分隔"""),
                ("human", """当前场景信息：
- 玩家: {player_name}
- 位置: {location}
- 在场角色: {present_characters}
- 最近事件: {recent_events}
- 当前时间: {current_time}

请生成2个行动建议：""")
            ])

            chain = prompt | llm | StrOutputParser()

            response = chain.invoke({
                "player_name": player_name,
                "location": location_name,
                "present_characters": "、".join(present_chars) if present_chars else "无其他角色",
                "recent_events": " | ".join(recent_events) if recent_events else "游戏刚开始",
                "current_time": self.world_state.current_time if self.world_state else "未知"
            })

            # 解析响应，分割成两个选项
            lines = [line.strip() for line in response.strip().split("\n") if line.strip()]
            # 清理可能的编号前缀
            suggestions = []
            for line in lines[:2]:
                # 移除常见的编号格式：1. 2. 1、2、① ② - 等
                cleaned = line.lstrip("0123456789.、①②③④⑤-) ").strip()
                if cleaned:
                    suggestions.append(cleaned)

            # 确保返回2个选项
            while len(suggestions) < 2:
                suggestions.append("观察周围环境")

            return suggestions[:2]

        except Exception as e:
            logger.warning(f"⚠️ 生成行动建议失败: {e}")
            return ["与在场角色交谈", "观察周围环境"]
