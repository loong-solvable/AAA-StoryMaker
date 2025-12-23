"""
Screen Adapter - Screen Agent 与 API 层的适配器

职责：
1. 将 GameEngine 返回的数据转换为 ScreenInput
2. 调用 Screen Agent 生成视觉数据
3. 将结果转换为 API Schema 格式
"""
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from agents.online.layer3.screen_agent import ScreenAgent, ScreenInput
from api.schemas import (
    VisualRenderData, VisualEnvironment, CharacterInShot, MediaPrompts
)
from utils.logger import setup_logger

logger = setup_logger("ScreenAdapter", "screen_adapter.log")


class ScreenAdapter:
    """Screen Agent 与 API 层的适配器"""

    def __init__(self, game_engine):
        """
        初始化适配器

        Args:
            game_engine: GameEngine 实例
        """
        self.game_engine = game_engine
        self.screen_agent: Optional[ScreenAgent] = None
        self._initialized = False

    def _ensure_initialized(self):
        """延迟初始化 Screen Agent"""
        if not self._initialized:
            runtime_dir = getattr(self.game_engine, 'runtime_dir', None)
            world_name = self.game_engine.os.genesis_data.get("world", {}).get("title", "")

            self.screen_agent = ScreenAgent(
                runtime_dir=runtime_dir,
                world_name=world_name
            )
            self._initialized = True
            logger.info(f"Screen Adapter 初始化完成，世界: {world_name}")

    def build_input(self, turn_result: Dict[str, Any]) -> ScreenInput:
        """
        从回合结果构建 ScreenInput

        Args:
            turn_result: GameEngine.process_turn_async() 的返回值

        Returns:
            ScreenInput 对象
        """
        npc_reactions = turn_result.get("npc_reactions", [])
        atmosphere = turn_result.get("atmosphere", {}) or {}
        world_state_data = turn_result.get("world_state", {}) or {}

        # 构建 current_action（从最后一个 NPC 反应）
        current_action = {}
        if npc_reactions and isinstance(npc_reactions, list) and len(npc_reactions) > 0:
            last_reaction = npc_reactions[-1]
            # 防御性检查：确保是字典
            if isinstance(last_reaction, dict):
                npc = last_reaction.get("npc")
                reaction = last_reaction.get("reaction", {})
                if isinstance(reaction, dict):
                    current_action = {
                        "speaker": getattr(npc, 'character_name', '') if npc else '',
                        "speaker_id": getattr(npc, 'character_id', '') if npc else '',
                        "content": reaction.get("dialogue", reaction.get("content", "")),
                        "action": reaction.get("action", ""),
                        "emotion": reaction.get("emotion", "")
                    }
            else:
                logger.warning(f"npc_reactions 格式异常: {type(last_reaction)}")

        # 获取在场角色的外观数据
        characters_in_scene = self._get_characters_appearance(
            current_speaker_id=current_action.get("speaker_id", "")
        )

        # 构建 world_state
        location_id = getattr(self.game_engine, 'player_location', '')
        location_name = self._get_location_name(location_id)

        world_state = {
            "location": {
                "name": location_name,
                "description": atmosphere.get("atmosphere_description", "")
            },
            "time_of_day": getattr(self.game_engine.world_state, 'current_time', '') if self.game_engine.world_state else '',
            "weather": atmosphere.get("weather", "晴朗")
        }

        return ScreenInput(
            scene_id=self.game_engine.os.turn_count,
            turn_id=self.game_engine.os.turn_count,
            timestamp=datetime.now().isoformat(),
            current_action=current_action,
            world_state=world_state,
            characters_in_scene=characters_in_scene,
            vibe_data=atmosphere
        )

    def _get_characters_appearance(self, current_speaker_id: str = "") -> List[Dict[str, Any]]:
        """
        获取在场角色的外观数据

        Args:
            current_speaker_id: 当前说话者的ID（用于标记焦点）

        Returns:
            角色列表，包含外观信息
        """
        characters = []
        present_chars = self.game_engine.os.world_context.present_characters

        for char_id in present_chars:
            if char_id == "user":
                continue

            # 从 genesis_data 获取角色数据
            char_data = self._get_character_data(char_id)
            if char_data:
                characters.append({
                    "name": char_data.get("name", char_id),
                    "appearance": char_data.get("current_appearance", ""),
                    "is_focus": char_id == current_speaker_id
                })

        return characters

    def _get_character_data(self, char_id: str) -> Optional[Dict[str, Any]]:
        """获取角色数据"""
        characters = self.game_engine.os.genesis_data.get("characters", [])
        # characters 是列表，遍历查找
        if isinstance(characters, list):
            for char in characters:
                if isinstance(char, dict) and char.get("id") == char_id:
                    return char
            return None
        # 兼容字典格式
        elif isinstance(characters, dict):
            return characters.get(char_id)
        return None

    def _get_location_name(self, location_id: str) -> str:
        """获取位置名称"""
        locations = self.game_engine.os.genesis_data.get("world", {}).get("geography", {}).get("locations", [])
        for loc in locations:
            if loc.get("id") == location_id:
                return loc.get("name", location_id)
        return location_id

    def generate_visual_data(self, turn_result: Dict[str, Any]) -> Optional[VisualRenderData]:
        """
        同步生成视觉数据

        Args:
            turn_result: GameEngine.process_turn_async() 的返回值

        Returns:
            VisualRenderData 或 None
        """
        import traceback
        try:
            self._ensure_initialized()

            # 构建输入
            logger.info("构建 ScreenInput...")
            screen_input = self.build_input(turn_result)
            logger.info(f"ScreenInput 构建完成: scene_id={screen_input.scene_id}")

            # 调用 Screen Agent
            logger.info("调用 Screen Agent...")
            result = self.screen_agent.translate_to_visual(screen_input)
            logger.info(f"Screen Agent 返回类型: {type(result)}")

            # 转换为 API Schema 格式
            return self._convert_to_schema(result)

        except Exception as e:
            logger.error(f"生成视觉数据失败: {e}")
            logger.error(f"详细堆栈: {traceback.format_exc()}")
            return None

    async def async_generate_visual_data(self, turn_result: Dict[str, Any]) -> Optional[VisualRenderData]:
        """
        异步生成视觉数据（在线程池中执行）

        Args:
            turn_result: GameEngine.process_turn_async() 的返回值

        Returns:
            VisualRenderData 或 None
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.generate_visual_data,
            turn_result
        )

    def _convert_to_schema(self, raw_result: Any) -> Optional[VisualRenderData]:
        """
        将 Screen Agent 的原始输出转换为 API Schema

        Args:
            raw_result: Screen Agent 返回的原始数据

        Returns:
            VisualRenderData 对象
        """
        if not raw_result:
            return None

        # 防御性检查：确保是字典
        if not isinstance(raw_result, dict):
            logger.warning(f"raw_result 不是字典类型: {type(raw_result)}")
            return None

        # 获取 visual_render_data（可能在根级别或嵌套）
        visual_data = raw_result.get("visual_render_data", raw_result)

        # 解析环境数据
        env_data = visual_data.get("environment", {})
        environment = VisualEnvironment(
            location=env_data.get("location", ""),
            lighting=env_data.get("lighting", ""),
            weather=env_data.get("weather", ""),
            composition=env_data.get("composition", "")
        )

        # 解析角色数据
        characters_in_shot = []
        for char in visual_data.get("characters_in_shot", []):
            characters_in_shot.append(CharacterInShot(
                name=char.get("name", ""),
                visual_tags=char.get("visual_tags", ""),
                pose=char.get("pose", ""),
                expression=char.get("expression", ""),
                dialogue=char.get("dialogue", ""),
                action=char.get("action", ""),
                screen_position=char.get("screen_position", "center")
            ))

        # 解析媒体提示词
        prompts_data = visual_data.get("media_prompts", {})
        media_prompts = MediaPrompts(
            image_gen_prompt=prompts_data.get("image_gen_prompt", ""),
            video_gen_script=prompts_data.get("video_gen_script", ""),
            negative_prompt=prompts_data.get("negative_prompt", "text, watermark, low quality, blurry, bad anatomy")
        )

        return VisualRenderData(
            summary=visual_data.get("summary", ""),
            environment=environment,
            characters_in_shot=characters_in_shot,
            media_prompts=media_prompts
        )
