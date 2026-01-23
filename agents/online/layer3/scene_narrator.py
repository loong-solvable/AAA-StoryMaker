"""
场景演绎器 (Scene Narrator)

单Agent演绎多角色模式：
- 当场景中有多个NPC需要响应时，用单次LLM调用生成协调的多角色对话
- 避免多Agent并行导致的割裂感
- NPC之间可以互相看、接话、呼应
"""

import json
import re
from typing import Dict, Any, List, Optional
from pathlib import Path

from utils.llm_factory import get_llm
from utils.logger import setup_logger
from config.settings import settings

logger = setup_logger("SceneNarrator", "scene_narrator.log")


class SceneNarrator:
    """
    场景演绎器 - 单次LLM调用演绎多个NPC的协调对话
    """

    def __init__(self, genesis_data: Dict[str, Any] = None):
        """
        初始化场景演绎器

        Args:
            genesis_data: 世界数据（可选）
        """
        self.genesis_data = genesis_data or {}
        online_timeout = getattr(settings, "ONLINE_LLM_TIMEOUT", 90.0)
        online_retries = getattr(settings, "ONLINE_LLM_MAX_RETRIES", 1)
        self.llm = get_llm(
            temperature=0.8,
            timeout=online_timeout,
            max_retries=online_retries
        )

        # 加载提示词模板
        self.prompt_template = self._load_prompt_template()

        logger.info("SceneNarrator 初始化完成")

    def _load_prompt_template(self) -> str:
        """加载提示词模板"""
        prompt_path = Path(__file__).parent.parent.parent.parent / "prompts" / "online" / "scene_narrator_system.txt"
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8")
        else:
            # 默认模板
            return self._get_default_template()

    def _get_default_template(self) -> str:
        """默认提示词模板"""
        return """你是一个互动叙事游戏的场景演绎器。
你需要同时扮演场景中的多个NPC，生成协调、自然的多角色对话。

## 核心要求
1. 每个NPC必须符合自己的人设和性格
2. NPC之间要有互动（互相看、接话、呼应）
3. 对话要自然连贯，不是各说各的
4. 根据玩家行动决定谁主导回应、谁配合

## 场景信息
{scene_context}

## 在场NPC
{npc_profiles}

## 玩家行动
{player_input}

## 输出格式
请按以下JSON格式输出每个NPC的反应：
```json
{{
  "narration": "（可选）场景描写，如气氛变化",
  "responses": [
    {{
      "npc_id": "npc_001",
      "npc_name": "林晨",
      "action": "放下咖啡杯，抬头看向玩家",
      "dialogue": "你好，请问有什么事？",
      "inner_thought": "这人是谁？看起来有些眼熟...",
      "emotion": "好奇"
    }},
    {{
      "npc_id": "npc_002",
      "npc_name": "苏晴雨",
      "action": "看了林晨一眼，然后转向玩家",
      "dialogue": "你认识他吗？",
      "inner_thought": "来者不善的感觉...",
      "emotion": "警惕"
    }}
  ]
}}
```

注意：
- 不是每个NPC都必须说话，可以只有动作
- dialogue为空表示NPC只有动作没说话
- 主要回应者放在responses数组前面
- NPC的反应要互相呼应，体现他们是在同一个场景"""

    def narrate_scene(
        self,
        player_input: str,
        npcs: List[Dict[str, Any]],
        scene_context: Dict[str, Any],
        director_instruction: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        演绎场景 - 生成多NPC的协调对话

        Args:
            player_input: 玩家输入
            npcs: NPC列表，每个NPC包含 {
                "npc_id": "npc_001",
                "npc_name": "林晨",
                "traits": "谨慎、聪明",
                "background": "...",
                "current_mood": "警惕",
                "attitude_toward_player": 0.5,
                "relationship": "陌生人"
            }
            scene_context: 场景上下文 {
                "location": "咖啡馆",
                "time": "下午3点",
                "mood": "平静",
                "recent_events": "..."
            }
            director_instruction: 导演指令（可选）

        Returns:
            {
                "success": True,
                "narration": "场景描写",
                "responses": [
                    {
                        "npc_id": "npc_001",
                        "npc_name": "林晨",
                        "action": "...",
                        "dialogue": "...",
                        "inner_thought": "...",
                        "emotion": "..."
                    },
                    ...
                ]
            }
        """
        if not npcs:
            return {
                "success": False,
                "error": "没有NPC需要响应",
                "responses": []
            }

        # 如果只有一个NPC，可以简化处理
        # 但为了一致性，仍然走统一流程

        try:
            # 构建NPC档案
            npc_profiles = self._build_npc_profiles(npcs)

            # 构建场景描述
            scene_desc = self._build_scene_description(scene_context, director_instruction)

            # 构建完整提示词
            prompt = self.prompt_template.format(
                scene_context=scene_desc,
                npc_profiles=npc_profiles,
                player_input=player_input
            )

            logger.info(f"🎭 场景演绎: {len(npcs)}个NPC响应玩家: {player_input[:30]}...")

            # 调用LLM
            response = self.llm.invoke(prompt)
            result = self._parse_response(response.content, npcs)

            if result["success"]:
                logger.info(f"✅ 场景演绎完成: {len(result['responses'])}个NPC反应")
                for resp in result["responses"]:
                    dialogue_preview = resp.get("dialogue", "")[:20] if resp.get("dialogue") else "(无对话)"
                    logger.info(f"   - {resp['npc_name']}: {dialogue_preview}...")

            return result

        except Exception as e:
            logger.error(f"❌ 场景演绎失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "responses": []
            }

    async def async_narrate_scene(
        self,
        player_input: str,
        npcs: List[Dict[str, Any]],
        scene_context: Dict[str, Any],
        director_instruction: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """异步版本的场景演绎"""
        import asyncio
        return await asyncio.to_thread(
            self.narrate_scene,
            player_input,
            npcs,
            scene_context,
            director_instruction
        )

    def _build_npc_profiles(self, npcs: List[Dict[str, Any]]) -> str:
        """构建NPC档案描述"""
        profiles = []
        for i, npc in enumerate(npcs, 1):
            profile = f"""
### NPC {i}: {npc.get('npc_name', '未知')}
- ID: {npc.get('npc_id', 'unknown')}
- 性格特点: {npc.get('traits', '普通')}
- 背景: {npc.get('background', '无')[:100]}...
- 当前情绪: {npc.get('current_mood', '平静')}
- 对玩家态度: {self._attitude_to_text(npc.get('attitude_toward_player', 0.5))}
- 与玩家关系: {npc.get('relationship', '陌生人')}
"""
            profiles.append(profile.strip())

        return "\n\n".join(profiles)

    def _attitude_to_text(self, attitude: float) -> str:
        """将态度数值转换为文本"""
        if attitude >= 0.8:
            return "非常友好"
        elif attitude >= 0.6:
            return "友好"
        elif attitude >= 0.4:
            return "中立"
        elif attitude >= 0.2:
            return "冷淡"
        else:
            return "敌对"

    def _build_scene_description(
        self,
        scene_context: Dict[str, Any],
        director_instruction: Optional[Dict]
    ) -> str:
        """构建场景描述"""
        parts = []

        if scene_context.get("location"):
            parts.append(f"地点: {scene_context['location']}")
        if scene_context.get("time"):
            parts.append(f"时间: {scene_context['time']}")
        if scene_context.get("mood"):
            parts.append(f"氛围: {scene_context['mood']}")
        if scene_context.get("scene_summary"):
            parts.append(f"场景概要: {scene_context['scene_summary']}")

        if director_instruction:
            params = director_instruction.get("parameters", {})
            if params.get("guidance"):
                parts.append(f"导演提示: {params['guidance']}")

        return "\n".join(parts) if parts else "普通场景"

    def _parse_response(
        self,
        response_text: str,
        npcs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """解析LLM响应"""
        try:
            # 尝试提取JSON
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 尝试直接解析
                json_str = response_text

            data = json.loads(json_str)

            # 验证响应格式
            responses = data.get("responses", [])
            if not responses:
                # 尝试从其他格式提取
                responses = self._extract_responses_fallback(response_text, npcs)

            return {
                "success": True,
                "narration": data.get("narration", ""),
                "responses": responses
            }

        except json.JSONDecodeError:
            # JSON解析失败，尝试回退解析
            logger.warning("JSON解析失败，尝试回退解析")
            responses = self._extract_responses_fallback(response_text, npcs)
            return {
                "success": True,
                "narration": "",
                "responses": responses
            }

    def _extract_responses_fallback(
        self,
        text: str,
        npcs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """回退解析方法 - 从非JSON文本中提取NPC响应"""
        responses = []

        for npc in npcs:
            npc_name = npc.get("npc_name", "")
            npc_id = npc.get("npc_id", "")

            # 尝试找到该NPC的对话
            # 模式: "NPC名: 对话内容" 或 "NPC名：对话内容"
            pattern = rf'{re.escape(npc_name)}[：:]\s*[「""]?([^」""]+)[」""]?'
            match = re.search(pattern, text)

            if match:
                dialogue = match.group(1).strip()
                responses.append({
                    "npc_id": npc_id,
                    "npc_name": npc_name,
                    "action": "",
                    "dialogue": dialogue,
                    "inner_thought": "",
                    "emotion": npc.get("current_mood", "平静")
                })

        # 如果没找到任何响应，返回默认响应
        if not responses and npcs:
            main_npc = npcs[0]
            responses.append({
                "npc_id": main_npc.get("npc_id", ""),
                "npc_name": main_npc.get("npc_name", "NPC"),
                "action": "看向玩家",
                "dialogue": "...",
                "inner_thought": "",
                "emotion": "平静"
            })

        return responses


# 便捷函数
def narrate_multi_npc_scene(
    player_input: str,
    npcs: List[Dict[str, Any]],
    scene_context: Dict[str, Any],
    director_instruction: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    便捷函数：演绎多NPC场景

    用法:
        result = narrate_multi_npc_scene(
            player_input="你们好",
            npcs=[
                {"npc_id": "npc_001", "npc_name": "林晨", ...},
                {"npc_id": "npc_002", "npc_name": "苏晴雨", ...}
            ],
            scene_context={"location": "咖啡馆", "time": "下午3点"}
        )
    """
    narrator = SceneNarrator()
    return narrator.narrate_scene(player_input, npcs, scene_context, director_instruction)
