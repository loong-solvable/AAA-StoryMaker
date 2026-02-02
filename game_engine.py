"""
游戏引擎 - 完整的游戏回合逻辑
整合所有Agent，实现完整的游戏循环
"""
import asyncio
import json
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
from agents.online.layer3.scene_narrator import SceneNarrator
from utils.interaction_parser import identify_interaction_target, should_npc_respond
from agents.message_protocol import AgentRole
from utils.memory_manager import MemoryManager
from agents.online.layer1.conductor import Conductor, TurnMode, TurnDecision
from utils.in_act_accumulator import InActAccumulator

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

        # 初始化Conductor（中枢指挥家）
        # 合并了 ActDirector + EventEngine + TurnModeClassifier
        self.conductor = Conductor(
            genesis_data=self.os.genesis_data,
            enable_async_predict=True
        )

        # 初始化幕内状态累积器（轻量交互优化核心组件）
        self.in_act_accumulator = InActAccumulator()

        # 后台IO任务队列
        self._pending_io_tasks: List[asyncio.Task] = []

        # 初始化NPC管理器
        self.npc_manager = NPCManager(self.os.genesis_data)

        # 初始化场景演绎器（单Agent演绎多角色）
        self.scene_narrator = SceneNarrator(self.os.genesis_data)

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

        # 对话历史（用于生成行动建议）
        self.dialogue_history: List[Dict[str, str]] = []
        
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

        # 将默认主角称谓替换为玩家自定义姓名（仅作用于当前 runtime）
        self._normalize_player_aliases()
        
        self._bootstrap_character_cards()
        self._record_agent_snapshots(turn_number=0)
        
        logger.info("✅ 游戏引擎初始化完成")
        logger.info(f"   - 世界: {self.os.genesis_data.get('world', {}).get('title', '未知')}")
        logger.info(f"   - NPC数量: {len(self.npc_manager.npcs)}")
        logger.info(f"   - 异步模式: {'ON' if self.async_mode else 'OFF'}")
        logger.info(f"   - Logic验证: {'ON' if self.enable_logic_check else 'OFF'}")
        logger.info(f"   - Vibe氛围: {'ON' if self.enable_vibe else 'OFF'}")
        logger.info(f"   - 轻量交互优化: ON")
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

            # Step 2.5: 事件检查
            logger.info("📍 Step 2.5: 事件检查")
            game_state_for_events = {
                "player_location": self.player_location,
                "npc_states": self.npc_manager.get_state_snapshot() if hasattr(self.npc_manager, 'get_state_snapshot') else {},
                "player_action": player_input
            }
            triggered_events = self.conductor.check_triggers(
                game_state=game_state_for_events,
                current_time=self.world_state.current_time,
                turn_number=self.os.turn_count
            )
            if triggered_events:
                logger.info(f"   - 触发事件: {len(triggered_events)} 个")
                for evt in triggered_events:
                    logger.info(f"     ⚡ {evt.event_name} (优先级:{evt.priority})")

            # Step 2.6: 幕目标评估
            logger.info("📍 Step 2.6: 幕目标评估")
            act_context = self.conductor.get_plot_context()
            act_evaluation = self.conductor.evaluate_progress({
                "player_location": self.player_location,
                "present_characters": self.os.world_context.present_characters,
                "npc_interactions": [],  # 将在回合结束后更新
                "triggered_events": [{"event_id": e.event_id} for e in triggered_events],
                "player_action": player_input
            })
            logger.info(f"   - 当前幕: {act_context.get('act_name')}")
            logger.info(f"   - 进度: {act_context.get('progress', 0) * 100:.0f}%, 紧迫度: {act_context.get('urgency', 0):.2f}")

            # 转换事件为Plot可用的格式
            triggered_events_for_plot = [
                {"event_id": e.event_id, "event_name": e.event_name, "description": e.description, "priority": e.priority}
                for e in triggered_events
            ] if triggered_events else None

            # Step 3: 剧情决策（Plot生成剧本，带幕目标和事件上下文）
            logger.info("📍 Step 3: 剧情决策")
            script = self.plot.generate_scene_script(
                player_action=player_input,
                player_location=self.player_location,
                present_characters=self.os.world_context.present_characters,
                world_context=self.world_state.get_context_summary(),
                story_history=self._get_story_history(),
                last_scene_dialogues=self._get_last_scene_dialogues(),
                act_context=act_context,
                triggered_events=triggered_events_for_plot
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
            
            # NPC反应 - 智能响应版本
            npc_reactions = []
            # 提取剧情推演作为场景摘要
            scene_summary = script.get("director_notes", "")
            scene_context = {
                "location": self.player_location,
                "time": self.world_state.current_time,
                "mood": script.get("scene_theme", {}).get("mood", "平静"),
                "scene_summary": scene_summary
            }

            # Step 4.1: 识别玩家交互目标
            present_chars = []
            for char_id in self.os.world_context.present_characters:
                if char_id == "user":
                    continue
                char_data = self.os.get_character_data(char_id)
                if char_data:
                    present_chars.append({
                        "id": char_id,
                        "name": char_data.get("name", char_id),
                        "gender": char_data.get("gender", "")
                    })

            interaction_info = identify_interaction_target(
                player_input=player_input,
                present_characters=present_chars,
                dialogue_history=self.dialogue_history[-10:] if self.dialogue_history else None
            )
            logger.info(f"🎯 交互目标识别: {interaction_info['target_type']} -> {interaction_info['target_names']} (置信度: {interaction_info['confidence']:.2f})")

            # Step 4.2: 根据交互目标决定每个NPC的响应模式
            for char_id in self.os.world_context.present_characters:
                if char_id == "user":
                    continue
                npc = self.npc_manager.get_npc(char_id)
                if not npc:
                    continue

                # 使用should_npc_respond进行细粒度判断
                npc_response_decision = should_npc_respond(
                    npc_id=char_id,
                    npc_name=npc.character_name,
                    interaction_info=interaction_info,
                    npc_emotional_state=npc.emotional_state
                )

                response_mode = npc_response_decision.get("response_mode", "ignore")
                logger.debug(f"   NPC[{npc.character_name}] 响应模式: {response_mode} ({npc_response_decision.get('reason', '')})")

                # 根据响应模式处理
                if response_mode == "respond":
                    # 正常响应：调用LLM生成反应
                    npc_instruction = self._find_instruction(script, f"npc_{char_id}")
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
                        scene_context=scene_context,
                        director_instruction=npc_instruction
                    )
                    npc_reactions.append({
                        "npc": npc,
                        "reaction": reaction,
                        "mode": "respond"
                    })

                elif response_mode == "observe":
                    # 旁观模式：记录但不输出对话
                    observation = npc.observe_scene(player_input, scene_context)
                    # 旁观结果可选择性加入（如果should_interject）
                    if observation.get("should_interject"):
                        npc_reactions.append({
                            "npc": npc,
                            "reaction": observation,
                            "mode": "observe"
                        })

                elif response_mode == "autonomous":
                    # 自主行为：NPC做自己的事
                    behavior = npc.decide_behavior(
                        is_interaction_target=False,
                        scene_context=scene_context,
                        other_npcs=[c for c in self.os.world_context.present_characters if c != char_id and c != "user"]
                    )
                    # 自主行为一般不输出，除非有特别行动
                    if behavior.get("mode") == "initiate":
                        initiative = npc.take_initiative(scene_context, player_available=True)
                        if initiative:
                            npc_reactions.append({
                                "npc": npc,
                                "reaction": initiative,
                                "mode": "initiate"
                            })
                # ignore模式：不做任何处理
            
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

            # 应用事件效果
            for event in triggered_events:
                self.conductor.apply_event_effects(event, game_state_for_events)

            # 检查幕转换
            if act_evaluation.get("should_advance"):
                if act_evaluation.get("progress", 0) >= 1.0:
                    self.conductor.advance_to_next_act("success")
                elif self.conductor.current_act and \
                     self.conductor.current_act.turns_in_act >= self.conductor.current_act.objective.max_turns:
                    self.conductor.advance_to_next_act("timeout")
                logger.info(f"🎬 幕转换: 进入 {self.conductor.current_act.act_name if self.conductor.current_act else '未知'}")

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
        异步版本的回合处理 - 三模式分流优化版

        模式：
        - DIALOGUE: 普通对话，仅NPC响应（~1-2秒）
        - PLOT_ADVANCE: 剧情推进，完整处理（~3-5秒）
        - ACT_TRANSITION: 幕转换，同步所有状态
        """
        logger.info("=" * 60)
        logger.info(f"🎮 [async] 处理回合 #{self.os.turn_count + 1}")
        logger.info(f"玩家输入: {player_input[:50]}...")

        current_turn = self.os.turn_count + 1

        try:
            # 清理已完成的后台IO任务
            self._cleanup_pending_tasks()

            # Step 1: Conductor决策（三层模型）
            game_context = {
                "player_location": self.player_location,
                "present_npcs": self.os.world_context.present_characters if self.os.world_context else [],
                "current_time": self.world_state.current_time,
                "npc_states": self.npc_manager.get_state_snapshot() if hasattr(self.npc_manager, 'get_state_snapshot') else {},
                "recent_dialogue": self.dialogue_history[-6:] if self.dialogue_history else []
            }
            decision = self.conductor.decide_turn_mode(player_input, game_context)
            turn_mode = decision.mode

            logger.info(f"📍 回合模式: {turn_mode.value} (Layer {decision.decision_layer})")
            if decision.should_advance_reason:
                logger.info(f"   原因: {decision.should_advance_reason}")
            logger.info("=" * 60)

            # Step 2: 根据模式分流处理
            if turn_mode == TurnMode.DIALOGUE:
                # 快速路径：仅NPC响应
                result = await self._process_dialogue_turn_fast(player_input, decision)
            elif turn_mode == TurnMode.ACT_TRANSITION:
                # 幕转换：完整同步 + 切换幕
                result = await self._process_act_transition_turn(player_input, decision)
            else:
                # 剧情推进：完整处理
                result = await self._process_plot_advance_turn(player_input, decision)

            # Step 3: 更新Conductor状态
            self.conductor.on_turn_complete(turn_mode, player_input, self.player_location)

            # Step 4: 后台异步预判下一回合（不阻塞返回）
            if result.get("success") and self.conductor.enable_async_predict:
                turn_result = {
                    "player_input": player_input,
                    "npc_reactions": result.get("npc_reactions", []),
                    "mode_used": turn_mode.value
                }
                asyncio.create_task(self.conductor.async_predict_next_turn(turn_result))

            # Step 5: 持久化数据（同步执行，避免SQLite线程问题）
            if result.get("success"):
                try:
                    self._persist_turn_data_sync(result, turn_mode, current_turn)
                except Exception as e:
                    logger.warning(f"⚠️ 数据持久化失败: {e}")

            return result

        except Exception as e:
            logger.error(f"❌ 回合处理出错 [async]: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "text": f"❌ 系统错误: {e}"
            }

    async def _process_dialogue_turn_fast(
        self,
        player_input: str,
        decision: TurnDecision
    ) -> Dict[str, Any]:
        """
        快速对话模式 - 仅调用NPC响应，跳过WS和Plot

        预期延迟: ~1-2秒

        多NPC场景使用单Agent演绎模式，避免割裂感
        """
        triggered_events = decision.triggered_events
        import time
        start_time = time.time()

        current_turn = self.os.turn_count + 1
        logger.info("⚡ 快速对话模式启动")

        # 使用累积器的缓存场景上下文
        scene_context = self.in_act_accumulator.get_scene_context_for_npc()
        scene_context["location"] = self.player_location

        # 直接收集所有在场NPC（不再使用关键词匹配判断谁响应）
        # 让 SceneNarrator 的 LLM 自己决定谁说话、谁旁观、谁不响应
        npcs_to_respond = []
        for char_id in self.os.world_context.present_characters:
            if char_id == "user":
                continue
            npc = self.npc_manager.get_npc(char_id)
            if npc:
                npcs_to_respond.append(npc)

        if npcs_to_respond:
            npc_names = [npc.character_name for npc in npcs_to_respond]
            logger.info(f"🎭 在场NPC: {npc_names}")

        # 根据响应NPC数量选择处理模式
        npc_reactions = []

        if len(npcs_to_respond) >= 2:
            # 多NPC场景：使用场景演绎模式（单次LLM调用）
            logger.info(f"🎭 场景演绎模式: {len(npcs_to_respond)}个NPC协调响应")
            npc_reactions = await self._narrate_multi_npc_scene(
                player_input=player_input,
                npcs=npcs_to_respond,
                scene_context=scene_context
            )
        elif len(npcs_to_respond) == 1:
            # 单NPC：直接调用
            npc = npcs_to_respond[0]
            logger.info(f"🎭 单NPC响应: {npc.character_name}")
            reaction = await npc.async_react(
                player_input=player_input,
                scene_context=scene_context,
                director_instruction=None
            )
            npc_reactions.append({
                "npc": npc,
                "reaction": reaction,
                "mode": "respond"
            })
        else:
            # 无NPC在场
            logger.info("ℹ️ 场景中无NPC")

        # 渲染输出（无氛围描写）
        output_text = self._render_output(None, npc_reactions, {})

        # 累积状态（不立即同步）
        self.in_act_accumulator.record_dialogue_turn(
            player_input=player_input,
            npc_reactions=npc_reactions,
            time_cost_minutes=3
        )

        # 记录触发的事件
        for event in triggered_events:
            self.in_act_accumulator.record_event({
                "event_id": event.event_id,
                "event_name": event.event_name
            })

        # 更新OS状态（本地）
        self.os.next_turn()
        self.os.add_to_history({
            "type": "player_action",
            "action": player_input,
            "location": self.player_location
        })

        elapsed = time.time() - start_time
        logger.info(f"⚡ 快速对话完成，耗时: {elapsed:.2f}秒")

        # 记录对话历史（用于生成行动建议）
        self._record_dialogue(player_input, npc_reactions)

        return {
            "success": True,
            "text": output_text,
            "mode": "dialogue",
            "npc_reactions": npc_reactions,
            "elapsed_time": elapsed,
            "player_input": player_input
        }

    async def _process_plot_advance_turn(
        self,
        player_input: str,
        decision: TurnDecision
    ) -> Dict[str, Any]:
        """
        剧情推进模式 - 完整处理流程

        预期延迟: ~3-5秒
        """
        triggered_events = decision.triggered_events
        import time
        start_time = time.time()

        current_turn = self.os.turn_count + 1
        logger.info("📖 剧情推进模式启动")

        # 先获取当前的world_context（上一回合状态），供Plot使用
        pre_update_context = self.world_state.get_context_summary()

        # 获取历史数据供Plot使用
        story_history = self._get_story_history()
        last_scene_dialogues = self._get_last_scene_dialogues()

        # 转换事件为Plot可用的格式
        triggered_events_for_plot = [
            {"event_id": e.event_id, "event_name": e.event_name, "description": e.description, "priority": e.priority}
            for e in triggered_events
        ] if triggered_events else None

        # 获取幕目标上下文
        act_context = self.conductor.get_plot_context()
        act_evaluation = self.conductor.evaluate_progress({
            "player_location": self.player_location,
            "present_characters": self.os.world_context.present_characters,
            "npc_interactions": [],
            "triggered_events": [{"event_id": e.event_id} for e in triggered_events] if triggered_events else [],
            "player_action": player_input
        })
        logger.info(f"📍 幕目标: {act_context.get('act_name')}, 紧迫度: {act_context.get('urgency', 0):.2f}")

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
                last_scene_dialogues=last_scene_dialogues,
                act_context=act_context,
                triggered_events=triggered_events_for_plot
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
                last_scene_dialogues=last_scene_dialogues,
                act_context=act_context,
                triggered_events=triggered_events_for_plot
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
        task_labels = []

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

        # NPC 任务 - 直接收集所有在场NPC，让SceneNarrator决定谁响应
        scene_summary = script.get("director_notes", "")
        scene_context = {
            "location": self.player_location,
            "time": self.world_state.current_time,
            "mood": script.get("scene_theme", {}).get("mood", "平静"),
            "scene_summary": scene_summary
        }

        # 直接收集所有在场NPC（不再使用关键词匹配判断谁响应）
        npcs_to_respond = []
        for char_id in self.os.world_context.present_characters:
            if char_id == "user":
                continue
            npc = self.npc_manager.get_npc(char_id)
            if npc:
                npcs_to_respond.append((char_id, npc))

        if npcs_to_respond:
            npc_names = [npc.character_name for _, npc in npcs_to_respond]
            logger.info(f"🎭 在场NPC: {npc_names}")

        # 根据响应NPC数量决定处理模式
        use_scene_narrator = len(npcs_to_respond) >= 2

        if use_scene_narrator:
            # 多NPC场景：使用场景演绎模式
            logger.info(f"🎭 场景演绎模式: {len(npcs_to_respond)}个NPC协调响应")
            # 构建导演指令
            director_instruction = None
            if scene_summary:
                director_instruction = {
                    "parameters": {
                        "scene_summary": scene_summary,
                        "guidance": script.get("director_notes", "")
                    }
                }
            all_tasks.append(
                self._narrate_multi_npc_scene(
                    player_input=player_input,
                    npcs=[npc for _, npc in npcs_to_respond],
                    scene_context=scene_context,
                    director_instruction=director_instruction
                )
            )
            task_labels.append(("scene_narrate", npcs_to_respond))
        else:
            # 单NPC或无NPC：传统方式
            for char_id, npc in npcs_to_respond:
                npc_instruction = self._find_instruction(script, f"npc_{char_id}")
                
                # 获取NPC幕级指令
                npc_briefing = self.conductor.get_npc_act_briefing(char_id) if self.conductor else None
                
                if not npc_instruction:
                    # 构建基于幕级指令的NPC指令
                    npc_instruction = {
                        "target": f"npc_{char_id}",
                        "parameters": {
                            "scene_summary": scene_summary,
                            "objective": npc_briefing.role_in_act if npc_briefing else "根据剧情推演自然反应",
                            "emotional_arc": npc_briefing.emotional_journey if npc_briefing else "",
                            "key_topics": npc_briefing.knowledge_scope if npc_briefing else [],
                            "urgency": act_context.get("urgency", 0) if act_context else 0
                        }
                    }
                elif npc_briefing:
                    # 补充幕级指令到现有指令
                    params = npc_instruction.get("parameters", {})
                    if not params.get("objective"):
                        params["objective"] = npc_briefing.role_in_act
                    if not params.get("emotional_arc"):
                        params["emotional_arc"] = npc_briefing.emotional_journey
                    if not params.get("key_topics"):
                        params["key_topics"] = npc_briefing.knowledge_scope
                    params["urgency"] = act_context.get("urgency", 0) if act_context else 0
                    npc_instruction["parameters"] = params
                
                all_tasks.append(
                    npc.async_react(
                        player_input=player_input,
                        scene_context=scene_context,
                        director_instruction=npc_instruction
                    )
                )
                task_labels.append(("npc_respond", npc))

        # 并行执行所有任务
        atmosphere = None
        npc_reactions: List[Dict[str, Any]] = []

        if all_tasks:
            results = await asyncio.gather(*all_tasks, return_exceptions=True)
            for (label_type, label_data), res in zip(task_labels, results):
                if isinstance(res, Exception):
                    if label_type == "vibe":
                        logger.error("❌ Vibe 并行生成失败: %s", res)
                    elif label_type == "scene_narrate":
                        logger.error("❌ 场景演绎失败: %s", res)
                    else:
                        logger.error("❌ NPC[%s] 并行演绎失败: %s", label_data.character_id, res)
                    continue

                if label_type == "vibe":
                    atmosphere = res
                elif label_type == "scene_narrate":
                    # 场景演绎结果直接是 npc_reactions 列表
                    npc_reactions.extend(res)
                elif label_type == "npc_respond":
                    npc_reactions.append({
                        "npc": label_data,
                        "reaction": res,
                        "mode": "respond"
                    })

        # 渲染输出（SceneNarrator已处理所有NPC的响应/旁观/不响应）
        logger.info("📍 Step 4: 最终渲染")
        output_text = self._render_output(atmosphere, npc_reactions, script)

        # 更新场景缓存（供后续DIALOGUE模式使用）
        self.in_act_accumulator.update_scene_cache(scene_context, scene_summary)
        self.in_act_accumulator.record_plot_turn(
            player_input=player_input,
            npc_reactions=npc_reactions,
            world_update=world_update,
            script=script
        )

        # 更新OS状态
        self.os.next_turn()
        self.os.add_to_history({
            "type": "player_action",
            "action": player_input,
            "location": self.player_location
        })

        # 应用事件效果
        game_state_for_events = {
            "player_location": self.player_location,
            "npc_states": self.npc_manager.get_state_snapshot() if hasattr(self.npc_manager, 'get_state_snapshot') else {},
            "player_action": player_input
        }
        for event in triggered_events:
            self.conductor.apply_event_effects(event, game_state_for_events)

        # 检查 Plot Agent 返回的幕完成信号
        act_completion = script.get("act_completion", {})
        act_signal = act_completion.get("signal", "CONTINUE")
        
        # 同时获取 Conductor 的进度评估
        conductor_evaluation = self.conductor.evaluate_progress({
            "player_location": self.player_location,
            "present_characters": self.os.world_context.present_characters,
            "npc_interactions": [],
            "triggered_events": [{"event_id": e.event_id} for e in triggered_events] if triggered_events else [],
            "player_action": player_input
        })
        
        # 综合判断是否应该转换幕
        should_transition = False
        transition_reason = ""
        outcome = "success"
        
        if act_signal == "FORCE_END":
            # Plot 强制结束信号
            should_transition = True
            transition_reason = f"Plot强制结束: {act_completion.get('reason', '无')}"
            outcome = "timeout"
        elif act_signal == "READY_TO_END":
            # Plot 建议结束，检查进度是否足够
            progress = conductor_evaluation.get("progress", 0)
            if progress >= 0.7:
                should_transition = True
                transition_reason = f"Plot建议结束且进度达{progress*100:.0f}%"
                outcome = "success"
            else:
                logger.info(f"📝 Plot建议结束但进度仅{progress*100:.0f}%，继续当前幕")
        elif conductor_evaluation.get("should_advance"):
            # Conductor 评估达成
            should_transition = True
            progress = conductor_evaluation.get("progress", 0)
            if progress >= 1.0:
                transition_reason = "Conductor评估：所有条件已完成"
                outcome = "success"
            else:
                transition_reason = "Conductor评估：回合数达上限"
                outcome = "timeout"
        
        if should_transition:
            logger.info(f"📢 触发幕转换: {transition_reason}")
            self.conductor.advance_to_next_act(outcome)
            
            new_act_name = self.conductor.current_act.act_name if self.conductor.current_act else "未知"
            new_act_objective = ""
            if self.conductor.current_act:
                new_act_objective = self.conductor.current_act.objective.description
            logger.info(f"🎬 幕转换完成: 进入 {new_act_name}")
            
            # 重置累积器
            self.in_act_accumulator.reset()
            
            # 添加幕转换提示到输出（包含新目标）
            transition_header = f"\n{'='*50}\n🎬 {new_act_name}\n"
            if new_act_objective:
                transition_header += f"🎯 目标: {new_act_objective}\n"
            transition_header += f"{'='*50}\n\n"
            output_text = transition_header + output_text

        elapsed = time.time() - start_time
        logger.info(f"📖 剧情推进完成，耗时: {elapsed:.2f}秒")

        # 记录对话历史（用于生成行动建议）
        self._record_dialogue(player_input, npc_reactions)

        return {
            "success": True,
            "text": output_text,
            "mode": "plot_advance",
            "world_state": world_update,
            "script": script,
            "atmosphere": atmosphere,
            "npc_reactions": npc_reactions,
            "elapsed_time": elapsed,
            "player_input": player_input
        }

    async def _process_act_transition_turn(
        self,
        player_input: str,
        decision: TurnDecision
    ) -> Dict[str, Any]:
        """
        幕转换模式 - 完整同步 + 切换幕

        预期延迟: ~5-8秒（包含状态同步）
        """
        triggered_events = decision.triggered_events
        import time
        start_time = time.time()

        logger.info("🎬 幕转换模式启动")

        # 先执行完整的剧情推进流程
        result = await self._process_plot_advance_turn(player_input, decision)

        if not result.get("success"):
            return result

        # 同步幕内累积状态到WS
        logger.info("📤 同步幕内累积状态...")
        sync_result = self.in_act_accumulator.flush_to_world_state(self.world_state)
        logger.info(f"   - 时间同步: {sync_result.get('time_synced')}")
        logger.info(f"   - NPC同步: {sync_result.get('npc_synced')}个")

        # 执行幕转换
        act_evaluation = self.conductor.evaluate_progress({
            "player_location": self.player_location,
            "present_characters": self.os.world_context.present_characters,
            "npc_interactions": [],
            "triggered_events": [{"event_id": e.event_id} for e in triggered_events] if triggered_events else [],
            "player_action": player_input
        })

        if act_evaluation.get("should_advance"):
            if act_evaluation.get("progress", 0) >= 1.0:
                self.conductor.advance_to_next_act("success")
            elif self.conductor.current_act and \
                 self.conductor.current_act.turns_in_act >= self.conductor.current_act.objective.max_turns:
                self.conductor.advance_to_next_act("timeout")

            new_act_name = self.conductor.current_act.act_name if self.conductor.current_act else "未知"
            new_act_objective = ""
            if self.conductor.current_act:
                new_act_objective = self.conductor.current_act.objective.description
            logger.info(f"🎬 幕转换完成: 进入 {new_act_name}")

            # 为在场NPC生成新幕的幕级指令
            try:
                present_npcs = []
                for char_id in self.os.world_context.present_characters:
                    if char_id == "user":
                        continue
                    char_data = self.os.get_character_data(char_id)
                    if char_data:
                        present_npcs.append(char_data)
                
                if present_npcs:
                    logger.info(f"📝 为 {len(present_npcs)} 个NPC生成幕级指令...")
                    await self.conductor.generate_npc_act_briefings(present_npcs)
            except Exception as e:
                logger.warning(f"⚠️ 生成NPC幕级指令失败: {e}")

            # 重置累积器
            self.in_act_accumulator.reset()

            # 添加幕转换提示到输出（包含新目标）
            transition_header = f"\n{'='*50}\n🎬 {new_act_name}\n"
            if new_act_objective:
                transition_header += f"🎯 目标: {new_act_objective}\n"
            transition_header += f"{'='*50}\n\n"
            result["text"] = transition_header + result.get("text", "")

        result["mode"] = "act_transition"
        elapsed = time.time() - start_time
        result["elapsed_time"] = elapsed
        logger.info(f"🎬 幕转换完成，耗时: {elapsed:.2f}秒")

        return result

    def _cleanup_pending_tasks(self):
        """清理已完成的后台IO任务"""
        self._pending_io_tasks = [
            t for t in self._pending_io_tasks
            if not t.done()
        ]

    def _persist_turn_data_sync(
        self,
        result: Dict[str, Any],
        turn_mode: TurnMode,
        turn_number: int
    ):
        """
        同步持久化回合数据（避免SQLite线程安全问题）
        """
        # 只在非DIALOGUE模式下记录完整数据
        if turn_mode != TurnMode.DIALOGUE:
            self._record_turn_summary(
                turn_number,
                result.get("player_input", ""),
                result.get("world_state"),
                result.get("script"),
                result.get("atmosphere"),
                result.get("npc_reactions")
            )

            # 同步world_state.json
            self._sync_world_state_file(
                turn_number,
                result.get("world_state")
            )
        else:
            # DIALOGUE模式：简化记录
            self._record_turn_summary(
                turn_number,
                result.get("player_input", ""),
                None,  # 无world_update
                None,  # 无script
                None,  # 无atmosphere
                result.get("npc_reactions")
            )

    async def _async_persist_turn_data(
        self,
        result: Dict[str, Any],
        turn_mode: TurnMode,
        turn_number: int
    ):
        """
        持久化回合数据（同步执行，避免SQLite线程安全问题）
        """
        try:
            # 只在非DIALOGUE模式下记录完整数据
            if turn_mode != TurnMode.DIALOGUE:
                self._record_turn_summary(
                    turn_number,
                    result.get("player_input", ""),
                    result.get("world_state"),
                    result.get("script"),
                    result.get("atmosphere"),
                    result.get("npc_reactions")
                )

                # 同步world_state.json
                self._sync_world_state_file(
                    turn_number,
                    result.get("world_state")
                )
            else:
                # DIALOGUE模式：简化记录
                self._record_turn_summary(
                    turn_number,
                    result.get("player_input", ""),
                    None,  # 无world_update
                    None,  # 无script
                    None,  # 无atmosphere
                    result.get("npc_reactions")
                )

        except Exception as e:
            logger.warning(f"后台IO任务失败: {e}")
    
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

    async def _narrate_multi_npc_scene(
        self,
        player_input: str,
        npcs: List,
        scene_context: Dict[str, Any],
        director_instruction: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        多NPC场景演绎 - 使用单次LLM调用生成协调的多角色对话

        Args:
            player_input: 玩家输入
            npcs: NPC对象列表
            scene_context: 场景上下文
            director_instruction: 导演指令（可选）

        Returns:
            npc_reactions 格式的列表
        """
        # 构建NPC档案
        npc_profiles = []
        npc_map = {}  # id -> npc对象

        for npc in npcs:
            npc_id = npc.character_id
            npc_map[npc_id] = npc

            # 获取角色数据
            char_data = self.os.get_character_data(npc_id) or {}

            profile = {
                "npc_id": npc_id,
                "npc_name": npc.character_name,
                "traits": char_data.get("traits", npc.character_name),
                "background": char_data.get("background", "")[:200],
                "current_mood": npc.emotional_state.get("current_mood", "平静"),
                "attitude_toward_player": npc.emotional_state.get("attitude_toward_player", 0.5),
                "relationship": npc.emotional_state.get("relationship", "陌生人")
            }
            npc_profiles.append(profile)

        # 调用场景演绎器
        result = await self.scene_narrator.async_narrate_scene(
            player_input=player_input,
            npcs=npc_profiles,
            scene_context=scene_context,
            director_instruction=director_instruction
        )

        # 转换为 npc_reactions 格式
        npc_reactions = []

        if result.get("success"):
            for resp in result.get("responses", []):
                npc_id = resp.get("npc_id", "")
                npc = npc_map.get(npc_id)

                if not npc:
                    continue

                # 更新NPC情感状态
                if resp.get("emotion"):
                    npc.emotional_state["current_mood"] = resp["emotion"]

                # 构建反应数据
                reaction = {
                    "content": resp.get("dialogue", ""),
                    "action": resp.get("action", ""),
                    "inner_thought": resp.get("inner_thought", ""),
                    "emotion": resp.get("emotion", "平静")
                }

                npc_reactions.append({
                    "npc": npc,
                    "reaction": reaction,
                    "mode": "respond"
                })

            # 如果有场景旁白，添加到第一个反应中
            if result.get("narration") and npc_reactions:
                npc_reactions[0]["narration"] = result["narration"]

        return npc_reactions

    def _record_dialogue(self, player_input: str, npc_reactions: List[Dict[str, Any]]):
        """
        记录对话历史（用于生成行动建议）

        Args:
            player_input: 玩家输入
            npc_reactions: NPC反应列表
        """
        # 记录玩家输入
        self.dialogue_history.append({
            "speaker": "玩家",
            "content": player_input
        })

        # 记录NPC响应
        for reaction_data in npc_reactions:
            npc = reaction_data.get("npc")
            reaction = reaction_data.get("reaction", {})

            if not npc:
                continue

            npc_name = getattr(npc, 'character_name', '未知NPC')
            content = reaction.get("content", reaction.get("dialogue", ""))

            if content:
                self.dialogue_history.append({
                    "speaker": npc_name,
                    "content": content[:200]  # 限制长度
                })

        # 保持对话历史在合理范围（最近10条）
        if len(self.dialogue_history) > 10:
            self.dialogue_history = self.dialogue_history[-10:]
    
    def _format_opening(self, atmosphere: Dict[str, Any], script: Dict[str, Any]) -> str:
        """格式化开场文本"""
        lines = []
        
        lines.append("=" * 70)
        lines.append(f"  🎭 {self.os.genesis_data.get('world', {}).get('title', '未知世界')}")
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

        # 场景旁白（来自场景演绎模式）
        if npc_reactions and npc_reactions[0].get("narration"):
            lines.append(f"\n{npc_reactions[0]['narration']}")

        # NPC反应
        if npc_reactions:
            lines.append("\n")
            for item in npc_reactions:
                npc = item["npc"]
                reaction = item["reaction"]

                lines.append(f"🎭 {npc.character_name}:")

                # 显示内心独白（支持 thought 和 inner_thought 两种格式）
                inner_thought = reaction.get("thought") or reaction.get("inner_thought")
                if inner_thought:
                    thought_text = inner_thought[:80]
                    lines.append(f"   💭 ({thought_text}...)")

                if reaction.get("action"):
                    lines.append(f"   {reaction['action']}")

                # 支持 dialogue 和 content 两种格式
                dialogue = reaction.get("dialogue") or reaction.get("content")
                if dialogue:
                    lines.append(f'   "{dialogue}"')

                # 显示情感状态
                if reaction.get("emotion"):
                    lines.append(f"   [情感: {reaction['emotion']}]")

                lines.append("")

        lines.append("─" * 70)

        return "\n".join(lines)
    
    def get_game_status(self) -> Dict[str, Any]:
        """获取游戏状态（包含幕目标信息）"""
        # 获取幕目标上下文
        act_context = self.conductor.get_plot_context() if self.conductor else {}
        
        return {
            "turn": self.os.turn_count,
            "time": self.world_state.current_time,
            "location": self.player_location,
            "plot_progress": self.plot.get_plot_status(),
            "npcs": {npc_id: npc.get_state() for npc_id, npc in self.npc_manager.npcs.items()},
            # 幕目标信息 - 供玩家查看
            "act": {
                "act_number": act_context.get("current_act", 1),
                "act_name": act_context.get("act_name", "自由探索"),
                "objective": act_context.get("objective_description", ""),
                "progress": act_context.get("progress", 0),
                "urgency": act_context.get("urgency", 0),
                "turns_remaining": act_context.get("turns_remaining", 999)
            }
        }
    
    def save_game(self, save_name: str = "quicksave"):
        """保存游戏"""
        save_path = settings.DATA_DIR / "saves" / f"{save_name}.json"
        extra_state = self._build_save_payload()
        self.os.save_game_state(
            save_path,
            runtime_dir=self.runtime_dir,
            extra_state=extra_state
        )
        logger.info(f"💾 游戏已保存: {save_name}")

    @classmethod
    def load_game(cls, save_path: Path) -> "GameEngine":
        """从存档恢复游戏引擎"""
        save_path = Path(save_path)
        if not save_path.exists():
            raise FileNotFoundError(f"存档不存在: {save_path}")

        with open(save_path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        metadata = payload.get("metadata", {})
        genesis_path = metadata.get("genesis_path") or payload.get("os_state", {}).get("genesis_path")
        if not genesis_path:
            raise ValueError("存档缺少 genesis_path，无法恢复游戏")

        engine = cls(Path(genesis_path))
        loaded_payload = engine.os.load_game_state(save_path, runtime_dir=engine.runtime_dir)

        extra_state = loaded_payload.get("extra_state", payload.get("extra_state", {}))
        engine._restore_agent_state(extra_state.get("agents", {}))
        engine._restore_player_state(extra_state.get("player_state", {}))
        return engine

    def _build_save_payload(self) -> Dict[str, Any]:
        """整理需要额外持久化的引擎状态"""
        return {
            "game_id": self.game_id,
            "player_state": {
                "player_location": self.player_location,
                "player_name": self.player_name
            },
            "agents": {
                "world_state": self.world_state.get_state_snapshot(),
                "plot": self.plot.get_state_snapshot(),
                "vibe": self.vibe.get_state_snapshot(),
                "npc": self.npc_manager.get_state_snapshot(),
            },
            "runtime": {"runtime_dir": str(self.runtime_dir) if self.runtime_dir else None},
        }

    def _restore_player_state(self, player_state: Dict[str, Any]) -> None:
        """从存档恢复玩家相关状态"""
        if not player_state:
            return
        location = player_state.get("player_location")
        if location:
            self.player_location = location
            if self.os.world_context:
                self.os.world_context.current_location = location
        if player_state.get("player_name"):
            self.player_name = player_state["player_name"]

    def _restore_agent_state(self, agent_state: Dict[str, Any]) -> None:
        """从存档恢复各 Agent 的快照"""
        if not agent_state:
            return
        ws_snapshot = agent_state.get("world_state")
        if ws_snapshot:
            self.world_state.load_state_snapshot(ws_snapshot)
        plot_snapshot = agent_state.get("plot")
        if plot_snapshot:
            self.plot.load_state_snapshot(plot_snapshot)
        vibe_snapshot = agent_state.get("vibe")
        if vibe_snapshot:
            self.vibe.load_state_snapshot(vibe_snapshot)
        npc_snapshot = agent_state.get("npc")
        if npc_snapshot:
            self.npc_manager.load_state_snapshot(npc_snapshot)

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
    
    def _normalize_player_aliases(self) -> None:
        """
        将默认主角称谓（如汪淼/小汪等）替换为玩家自定义姓名，避免 NPC 误称。
        仅在当前 runtime 目录内就地替换 JSON/TXT 文本，不修改世界模板。
        """
        if not self.runtime_dir:
            return
        target_name = self.player_name
        if not target_name:
            return
        
        alias_list = [
            "汪淼", "小汪", "汪教授", "汪老师", "汪院士", "汪先生", "汪博士", "老汪"
        ]
        
        for path in self.runtime_dir.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in {".json", ".txt"}:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except Exception:
                continue
            
            new_text = text
            for alias in alias_list:
                new_text = new_text.replace(alias, target_name)
            
            if new_text != text:
                try:
                    path.write_text(new_text, encoding="utf-8")
                    logger.info(f"🔄 已替换玩家称谓为自定义姓名: {path}")
                except Exception as e:
                    logger.warning(f"⚠️ 替换玩家称谓失败 {path}: {e}")
    
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

            # 获取最近的对话历史（使用 self.dialogue_history）
            dialogue_text = ""
            if self.dialogue_history:
                dialogue_lines = []
                for entry in self.dialogue_history[-6:]:  # 最近3轮对话
                    speaker = entry.get('speaker', '???')
                    content = entry.get('content', '')
                    dialogue_lines.append(f"{speaker}: {content}")
                dialogue_text = "\n".join(dialogue_lines)

            prompt = ChatPromptTemplate.from_messages([
                ("system", """你是一个互动叙事游戏的行动建议器。
根据当前场景和对话进展，为玩家生成2个有趣且合理的行动选项。

要求：
1. 每个选项应该是具体的行动描述，10-30字
2. 两个选项应该代表不同的方向（如：深入追问vs转换话题，直接行动vs继续观察）
3. 建议必须基于当前对话进展，推动剧情向前发展
4. 不要重复之前已经做过的行动
5. 不要使用编号，直接输出两个选项，用换行分隔"""),
                ("human", """当前场景信息：
- 玩家: {player_name}
- 位置: {location}
- 在场角色: {present_characters}
- 当前时间: {current_time}

最近对话记录：
{dialogue_history}

最近事件：{recent_events}

请根据对话进展生成2个行动建议（不要重复之前的行动）：""")
            ])

            chain = prompt | llm | StrOutputParser()

            response = chain.invoke({
                "player_name": player_name,
                "location": location_name,
                "present_characters": "、".join(present_chars) if present_chars else "无其他角色",
                "dialogue_history": dialogue_text if dialogue_text else "（尚无对话）",
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
