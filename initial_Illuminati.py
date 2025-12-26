"""
🏛️ 光明会初始化 (Illuminati Initialization)

初始化游戏运行阶段的核心 Agent 组（光明会）：
- WS（世界状态运行者）: 读取 world_setting.json 初始化世界状态
- Plot（命运编织者）: 读取所有创世组数据，生成起始场景和起始剧本
- Vibe（氛围感受者）: 读取世界设定和起始场景，生成初始氛围描写

生成的运行时数据保存在: data/runtime/<世界名>_<时间戳>/

使用方法：
    python initial_Illuminati.py               # 自动检测世界（单个则直接使用，多个则选择）
    python initial_Illuminati.py --world 江城市  # 指定世界名称
"""
import json
import argparse
import sys
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

from config.settings import settings
from utils.logger import setup_logger
from utils.llm_factory import get_llm
from langchain_core.messages import SystemMessage, HumanMessage

logger = setup_logger("Illuminati", "illuminati_init.log")


@dataclass
class InitialScene:
    """起始场景数据结构"""
    location_id: str
    location_name: str
    time_of_day: str
    weather: str
    present_characters: List[Dict[str, Any]]  # 包含 id, name, first_appearance
    scene_description: str
    opening_narrative: str


@dataclass
class InitialScript:
    """起始剧本数据结构（纯文本）"""
    content: str  # 约500字的纯文本剧本


@dataclass
class InitialAtmosphere:
    """初始氛围数据结构"""
    visual_description: str
    auditory_description: str
    olfactory_description: str
    emotional_tone: str
    full_atmosphere_text: str


class IlluminatiInitializer:
    """
    光明会初始化器
    
    负责初始化游戏运行阶段的三大核心 Agent：
    - WS（世界状态运行者）
    - Plot（命运编织者）
    - Vibe（氛围感受者）
    """
    
    def __init__(
        self,
        world_name: str,
        player_profile: Optional[Dict[str, Any]] = None,
        runtime_name: Optional[str] = None,
        overwrite_runtime: bool = False,
        skip_player: bool = False,
    ):
        """
        初始化光明会

        Args:
            world_name: 世界名称（对应 data/worlds/<world_name>/ 目录）
            player_profile: 玩家设定（可选），不提供则使用默认占位
            runtime_name: 运行时目录名（不含世界前缀），为空则使用时间戳
            overwrite_runtime: 若目录存在是否强制覆盖
            skip_player: 是否跳过玩家角色（True时不添加玩家）
        """
        logger.info("=" * 60)
        logger.info("🏛️  启动光明会初始化流程")
        logger.info("=" * 60)

        self.world_name = world_name
        self.skip_player = skip_player
        self.player_profile = self._normalize_player_profile(player_profile) if not skip_player else None
        self.player_card: Optional[Dict[str, Any]] = None
        self.world_dir = settings.DATA_DIR / "worlds" / world_name

        # 验证世界数据存在
        if not self.world_dir.exists():
            raise FileNotFoundError(f"世界数据目录不存在: {self.world_dir}")

        # 创建运行时数据目录（支持自定义/复用目录名）
        suffix = runtime_name or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.runtime_dir = settings.DATA_DIR / "runtime" / f"{world_name}_{suffix}"
        if self.runtime_dir.exists():
            if overwrite_runtime:
                shutil.rmtree(self.runtime_dir)
            else:
                raise FileExistsError(
                    f"运行时目录已存在: {self.runtime_dir}，使用 --overwrite-runtime 以覆盖，"
                    f"或使用 --runtime-name 指定新的目录名。"
                )
        self.runtime_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"📁 世界数据目录: {self.world_dir}")
        logger.info(f"📁 运行时数据目录: {self.runtime_dir}")
        
        # 加载世界数据
        self.world_setting = self._load_world_setting()
        self.characters_list = self._load_characters_list()
        self.characters_details = self._load_all_characters()
        
        # 只有在不跳过玩家时才注入玩家
        if not self.skip_player:
            self._inject_player_into_cast()
        else:
            logger.info("⏭️  跳过玩家角色注入")

        # 构建 Genesis 格式数据（兼容现有 Agent）
        self.genesis_data = self._build_genesis_data()
        
        # LLM 实例
        self.llm = get_llm(temperature=0.8)
        
        # 初始化结果
        self.initial_scene: Optional[InitialScene] = None
        self.initial_script: Optional[InitialScript] = None
        self.initial_atmosphere: Optional[InitialAtmosphere] = None
        
        logger.info("✅ 光明会初始化器准备就绪")
    
    def _load_world_setting(self) -> Dict[str, Any]:
        """加载世界设定"""
        path = self.world_dir / "world_setting.json"
        if not path.exists():
            raise FileNotFoundError(f"世界设定文件不存在: {path}")
        
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        logger.info(f"✅ 加载世界设定: {data.get('meta', {}).get('world_name', 'Unknown')}")
        return data
    
    def _load_characters_list(self) -> List[Dict[str, Any]]:
        """加载角色列表"""
        path = self.world_dir / "characters_list.json"
        if not path.exists():
            raise FileNotFoundError(f"角色列表文件不存在: {path}")
        
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        logger.info(f"✅ 加载角色列表: {len(data)} 个角色")
        return data
    
    def _load_all_characters(self) -> Dict[str, Dict[str, Any]]:
        """加载所有角色详情"""
        characters_dir = self.world_dir / "characters"
        if not characters_dir.exists():
            raise FileNotFoundError(f"角色目录不存在: {characters_dir}")
        
        characters = {}
        for char_file in characters_dir.glob("character_*.json"):
            with open(char_file, "r", encoding="utf-8") as f:
                char_data = json.load(f)
                char_id = char_data.get("id", char_file.stem.replace("character_", ""))
                characters[char_id] = char_data

        logger.info(f"✅ 加载角色详情: {len(characters)} 个角色档案")
        return characters

    # ==========================================
    # 玩家植入
    # ==========================================

    def _normalize_player_profile(self, profile: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """标准化玩家资料，确保最小字段存在，增强沉浸感"""
        base = {
            "id": "user",
            "name": "玩家",
            "gender": "未知",
            "age": "未知",
            "appearance": "",
            "importance": 0.8,
            # 增强字段：提升玩家角色认同感
            "background": "",  # 玩家背景故事
            "motivation": "",  # 玩家动机/目标
            "personality": "",  # 玩家性格倾向
            "skills": [],  # 玩家特长
        }
        if not profile:
            return base
        normalized = dict(base)
        for key, value in profile.items():
            if value not in (None, ""):
                normalized[key] = value
        return normalized

    def _generate_player_traits(self) -> List[str]:
        """根据玩家资料生成性格特质"""
        traits = ["由玩家实时展现"]
        personality = self.player_profile.get("personality", "")
        if personality:
            traits.append(personality)
        skills = self.player_profile.get("skills", [])
        if skills:
            traits.extend([f"擅长{s}" for s in skills[:2]])
        return traits

    def _inject_player_into_cast(self):
        """将玩家作为正式角色加入角色花名册与角色卡"""
        player_id = self.player_profile.get("id", "user")

        # 生成增强版玩家卡（提升角色认同感）
        self.player_card = {
            "id": player_id,
            "name": self.player_profile.get("name", "玩家"),
            "gender": self.player_profile.get("gender", "未知"),
            "age": self.player_profile.get("age", "未知"),
            "importance": self.player_profile.get("importance", 0.8),
            "traits": self._generate_player_traits(),
            "behavior_rules": ["遵从玩家实时选择"],
            "relationship_matrix": {},
            "possessions": [],
            "current_appearance": self.player_profile.get("appearance", ""),
            "voice_samples": [],
            # 增强字段：玩家角色认同
            "background": self.player_profile.get("background", ""),
            "motivation": self.player_profile.get("motivation", "探索这个世界的真相"),
            "personality": self.player_profile.get("personality", ""),
            "skills": self.player_profile.get("skills", []),
            "is_player": True  # 标记为玩家角色
        }

        # 加入角色列表（如未存在）
        if not any(c.get("id") == player_id for c in self.characters_list):
            self.characters_list.append({
                "id": player_id,
                "name": self.player_card["name"],
                "importance": self.player_card["importance"]
            })

        # 加入角色详情（如未存在）
        if player_id not in self.characters_details:
            self.characters_details[player_id] = self.player_card

    def _build_world_start_context(self) -> Dict[str, Any]:
        """为 genesis 构建世界开场提示，确保玩家在场"""
        locations = self.world_setting.get("geography", {}).get("locations", [])
        suggested_loc = locations[0].get("id", "loc_001") if locations else "loc_001"
        suggested_time = self.world_setting.get("meta", {}).get("suggested_time", "下午")

        # 选择重要角色 + 玩家
        key_chars = [
            c.get("id")
            for c in sorted(
                self.characters_list,
                key=lambda x: x.get("importance", 0),
                reverse=True
            )
            if c.get("id")
        ][:2]

        if self.player_card:
            if self.player_card["id"] not in key_chars:
                key_chars.insert(0, self.player_card["id"])
        else:
            if "user" not in key_chars:
                key_chars.insert(0, "user")

        return {
            "suggested_time": suggested_time,
            "suggested_location": suggested_loc,
            "key_characters": key_chars,
            "opening_hint": "玩家是真实参与者，保持自由表达，NPC 需留出回应空间。"
        }
    
    def _build_genesis_data(self) -> Dict[str, Any]:
        """构建 Genesis 格式数据（兼容现有 Agent）"""
        meta = self.world_setting.get("meta", {})

        return {
            "world": {
                "title": meta.get("world_name", self.world_name),
                "genre": meta.get("genre_type", "REALISTIC"),
                "description": meta.get("description", "")
            },
            "characters": list(self.characters_details.values()),
            "locations": self.world_setting.get("geography", {}).get("locations", []),
            "physics_logic": self.world_setting.get("physics_logic", {}),
            "social_logic": self.world_setting.get("social_logic", []),
            "plot_hints": [],  # 由 Plot 动态生成
            "world_start_context": self._build_world_start_context()
        }
    
    # ==========================================
    # WS 初始化
    # ==========================================
    
    def init_world_state(self) -> Dict[str, Any]:
        """
        初始化 WS（世界状态运行者）- 调用 LLM 生成初始世界状态
        
        提示词来源：prompts/online/ws_system.txt
        
        数据来源：
        - world_setting.json - 世界设定
        - characters_list.json - 角色列表（确保ID一致性）
        - characters/*.json - 角色详细档案
        
        保存到 data/runtime/{world_name}/ws/world_state.json
        """
        logger.info("")
        logger.info("─" * 60)
        logger.info("🌍 初始化 WS（世界状态运行者）")
        logger.info("─" * 60)
        logger.info(f"   依据: world_setting, characters_list({len(self.characters_list)}个), {len(self.characters_details)}个角色卡")
        
        # 创建 WS 目录
        ws_dir = self.runtime_dir / "ws"
        ws_dir.mkdir(parents=True, exist_ok=True)
        
        # 读取 WS 系统提示词
        ws_prompt_path = settings.PROMPTS_DIR / "online" / "ws_system.txt"
        with open(ws_prompt_path, "r", encoding="utf-8") as f:
            system_prompt = f.read()
        
        # 构建用户消息
        user_message = self._build_ws_user_message()
        
        logger.info("🤖 正在调用 LLM 生成初始世界状态...")
        
        try:
            # 调用 LLM（使用消息格式）
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_message)
            ]
            response = self.llm.invoke(messages)
            content = response.content if hasattr(response, 'content') else str(response)

            # 解析 JSON 响应
            world_state = self._parse_ws_response(content)
            world_state = self._ensure_player_in_world_state(world_state)

            # 补充 meta 信息（确保时间戳正确）
            if "meta" not in world_state:
                world_state["meta"] = {}
            world_state["meta"]["game_turn"] = 0
            world_state["meta"]["last_updated"] = datetime.now().isoformat()
            world_state["meta"]["total_elapsed_time"] = "0分钟"
            
            # 保存世界状态到 ws 目录
            state_file = ws_dir / "world_state.json"
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(world_state, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ WS 初始化完成")
            logger.info(f"   - 初始场景: {world_state.get('current_scene', {}).get('location_name', '未知')}")
            logger.info(f"   - 在场角色: {len(world_state.get('characters_present', []))} 人")
            logger.info(f"   - 状态文件: {state_file}")
            
            return world_state
            
        except Exception as e:
            logger.error(f"❌ WS 初始化失败: {e}", exc_info=True)
            # 返回默认世界状态
            return self._create_default_world_state(ws_dir)
    
    def _build_ws_user_message(self) -> str:
        """构建 WS 初始化的用户消息"""
        # 世界设定
        meta = self.world_setting.get("meta", {})
        
        # 地点信息
        locations = self.world_setting.get("geography", {}).get("locations", [])
        locations_text = "\n".join([
            f"- {loc['name']} ({loc['id']}): {loc.get('sensory_profile', {}).get('atmosphere', '')}"
            for loc in locations
        ])
        
        # 社会规则
        social_rules = self.world_setting.get("social_logic", [])
        rules_text = "\n".join([
            f"- {rule.get('rule_name', '')}: {rule.get('trigger_condition', '')} → {rule.get('consequence', '')}"
            for rule in social_rules
        ])
        
        # 角色花名册
        characters_list_text = json.dumps(self.characters_list, ensure_ascii=False, indent=2)
        
        # 角色详情
        characters_detail_text = "\n".join([
            f"【{char.get('name', char_id)}】(ID: {char_id})\n"
            f"  特征: {', '.join(char.get('traits', []))}\n"
            f"  外观: {char.get('current_appearance', '无描述')[:100]}"
            for char_id, char in self.characters_details.items()
        ])
        
        return f"""请以【初始化模式】生成初始世界状态。

===== 世界设定 (world_setting.json) =====
世界名称: {meta.get('world_name', self.world_name)}
类型: {meta.get('genre_type', 'REALISTIC')}
描述: {meta.get('description', '')}

【可用地点】
{locations_text}

【社会规则】
{rules_text}

===== 角色花名册 (characters_list.json) =====
{characters_list_text}

===== 角色详情 (角色档案) =====
{characters_detail_text}

===== 任务 =====
请生成初始世界状态 JSON。要求：
1. 选择一个合适的初始场景（从可用地点中选择，或创建符合世界观的新场景）
2. 设置合理的初始天气和时间
3. 选择1-3个重要角色作为初始在场角色（按重要性选择）
4. relationship_matrix 初始化时留空 {{}}
5. 描述世界初始形势
6. 所有角色ID必须使用 characters_list.json 中的ID

直接输出 JSON，不要添加其他文字。"""
    
    def _parse_ws_response(self, content: str) -> Dict[str, Any]:
        """解析 WS 的 JSON 响应"""
        import re

        # 尝试提取 JSON
        json_match = re.search(r'\{[\s\S]*\}', content)
        if not json_match:
            raise ValueError("无法从响应中提取JSON")

        return json.loads(json_match.group())

    def _ensure_player_in_world_state(self, world_state: Dict[str, Any]) -> Dict[str, Any]:
        """确保玩家出现在初始世界状态中"""
        if not self.player_card:
            return world_state

        present = world_state.setdefault("characters_present", [])
        if not any(c.get("id") == self.player_card["id"] for c in present):
            present.append({
                "id": self.player_card["id"],
                "name": self.player_card.get("name", "玩家"),
                "mood": "期待",
                "activity": "观察局势",
                "appearance_note": self.player_card.get("current_appearance", "")
            })

        # 保证 current_scene 存在基础字段
        world_state.setdefault("current_scene", {})
        world_state["current_scene"].setdefault("location_id", self._build_world_start_context().get("suggested_location", "loc_001"))
        world_state["current_scene"].setdefault("location_name", "未知地点")
        world_state["current_scene"].setdefault("time_of_day", self._build_world_start_context().get("suggested_time", "下午"))

        return world_state
    
    def _create_default_world_state(self, ws_dir: Path) -> Dict[str, Any]:
        """创建默认世界状态（LLM 调用失败时使用）"""
        locations = self.world_setting.get("geography", {}).get("locations", [])
        initial_location = locations[0] if locations else {"id": "unknown", "name": "未知地点"}
        
        # 获取重要角色
        sorted_chars = sorted(
            self.characters_list,
            key=lambda x: x.get("importance", 0),
            reverse=True
        )[:3]
        
        characters_present = []
        for char_info in sorted_chars:
            char_id = char_info.get("id")
            char_detail = self.characters_details.get(char_id, {})
            characters_present.append({
                "id": char_id,
                "name": char_info.get("name", ""),
                "mood": "平静",
                "activity": "在场",
                "appearance_note": char_detail.get("current_appearance", "")
            })

        # 确保玩家在场
        if self.player_card and not any(c.get("id") == self.player_card["id"] for c in characters_present):
            characters_present.insert(0, {
                "id": self.player_card["id"],
                "name": self.player_card.get("name", "玩家"),
                "mood": "期待",
                "activity": "观察局势",
                "appearance_note": self.player_card.get("current_appearance", "")
            })

        meta = self.world_setting.get("meta", {})
        world_state = {
            "current_scene": {
                "location_id": initial_location.get("id", "unknown"),
                "location_name": initial_location.get("name", "未知地点"),
                "time_of_day": "傍晚",
                "description": initial_location.get("sensory_profile", {}).get("atmosphere", "故事即将展开的地方")
            },
            "weather": {
                "condition": "晴朗",
                "temperature": "22°C"
            },
            "characters_present": characters_present,
            "characters_absent": [],
            "relationship_matrix": {},
            "world_situation": {
                "summary": f"故事在{meta.get('world_name', self.world_name)}展开，一切刚刚开始。",
                "tension_level": "平静",
                "key_developments": []
            },
            "meta": {
                "game_turn": 0,
                "last_updated": datetime.now().isoformat(),
                "total_elapsed_time": "0分钟"
            }
        }
        
        # 保存
        state_file = ws_dir / "world_state.json"
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(world_state, f, ensure_ascii=False, indent=2)
        
        logger.warning("⚠️ 使用默认世界状态")
        return world_state
    
    def _build_relationship_matrix(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        从角色档案中构建NPC关系矩阵
        """
        relationship_matrix = {}
        
        for char_id, char_data in self.characters_details.items():
            char_relations = char_data.get("relationship_matrix", {})
            if char_relations:
                relationship_matrix[char_id] = {}
                for target_id, relation_info in char_relations.items():
                    # 从角色档案的关系数据转换为WS格式
                    relationship_matrix[char_id][target_id] = {
                        "relation_type": "相关",  # 默认值，可根据attitude推断
                        "attitude": relation_info.get("attitude", "中立"),
                        "recent_change": None
                    }
        
        return relationship_matrix
    
    # ==========================================
    # Plot 初始化
    # ==========================================
    
    def init_plot_and_generate_opening(self, world_state: Dict[str, Any]) -> tuple[InitialScene, InitialScript]:
        """
        初始化 Plot（命运编织者）并生成起始场景和剧本
        
        Args:
            world_state: WS初始化生成的世界状态数据
        
        依据数据：
        - 角色卡 (characters_details)
        - 世界设定 (world_setting)
        - 角色列表 (characters_list)
        - WS世界状态 (world_state)
        
        生成：
        - 当前场景 (plot/current_scene.json)
        - 当前剧本 (plot/current_script.json)
        - 历史剧本存档目录 (plot/history/)
        """
        logger.info("")
        logger.info("─" * 60)
        logger.info("🎬 初始化 Plot（命运编织者）")
        logger.info("─" * 60)
        
        # 创建 Plot 目录结构
        plot_dir = self.runtime_dir / "plot"
        plot_dir.mkdir(parents=True, exist_ok=True)
        # 创建历史剧本存档文件夹（供运行时使用）
        history_dir = plot_dir / "history"
        history_dir.mkdir(parents=True, exist_ok=True)
        
        # 构建消息（使用外部提示词文件）
        messages = self._build_plot_messages(world_state)
        
        logger.info("🤖 正在调用 LLM 生成起始场景和剧本...")
        logger.info(f"   提示词: prompts/online/plot_system.txt")
        logger.info(f"   依据: world_setting, characters_list, {len(self.characters_details)}个角色卡, world_state")
        
        try:
            # 调用 LLM
            response = self.llm.invoke(messages)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # 解析响应（传入 world_state 用于构建场景数据）
            scene, script = self._parse_plot_response(content, world_state)
            
            self.initial_scene = scene
            self.initial_script = script
            
            # 保存当前场景到 plot 目录
            scene_file = plot_dir / "current_scene.json"
            with open(scene_file, "w", encoding="utf-8") as f:
                json.dump(asdict(scene), f, ensure_ascii=False, indent=2)
            
            # 保存当前剧本到 plot 目录（初始化只生成当前剧本）
            script_file = plot_dir / "current_script.json"
            script_data = asdict(script)
            script_data["scene_id"] = 1  # 初始剧本为第1幕
            script_data["is_initial"] = True  # 标记为初始剧本
            script_data["created_at"] = datetime.now().isoformat()  # 记录创建时间
            with open(script_file, "w", encoding="utf-8") as f:
                json.dump(script_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ Plot 初始化完成")
            logger.info(f"   - 起始地点: {scene.location_name}")
            # 从字典列表中提取角色名
            char_names = [c.get('name', c.get('id', '未知')) if isinstance(c, dict) else c for c in scene.present_characters]
            logger.info(f"   - 在场角色: {', '.join(char_names)}")
            logger.info(f"   - 场景文件: {scene_file}")
            logger.info(f"   - 当前剧本: {script_file}")
            logger.info(f"   - 历史存档: {history_dir}")
            
            return scene, script
            
        except Exception as e:
            logger.error(f"❌ Plot 生成失败: {e}", exc_info=True)
            # 设置并返回默认值，确保后续流程可以继续
            default_scene = self._create_default_scene()
            default_script = self._create_default_script()
            self.initial_scene = default_scene
            self.initial_script = default_script
            
            # 仍然保存默认文件
            try:
                scene_file = plot_dir / "current_scene.json"
                with open(scene_file, "w", encoding="utf-8") as f:
                    json.dump(asdict(default_scene), f, ensure_ascii=False, indent=2)
                
                script_file = plot_dir / "current_script.json"
                script_data = asdict(default_script)
                script_data["scene_id"] = 1
                script_data["is_initial"] = True
                script_data["is_fallback"] = True  # 标记为回退默认值
                with open(script_file, "w", encoding="utf-8") as f:
                    json.dump(script_data, f, ensure_ascii=False, indent=2)
                    
                logger.warning(f"⚠️ 使用默认场景和剧本继续初始化")
            except Exception as save_err:
                logger.error(f"❌ 保存默认文件失败: {save_err}")
            
            return default_scene, default_script
    
    def _build_plot_messages(self, world_state: Dict[str, Any]) -> list:
        """
        构建 Plot 的消息列表（使用外部提示词文件）
        
        提示词来源：prompts/online/plot_system.txt
        
        数据来源：
        - self.world_setting: world_setting.json（世界名称、类型、描述、地点、社会规则）
        - self.characters_list: characters_list.json（角色花名册）
        - self.characters_details: characters/*.json（角色卡详情）
        - world_state: WS初始化生成的世界状态（当前场景、天气、在场角色）
        
        Args:
            world_state: WS初始化生成的世界状态
        """
        # 读取 Plot 系统提示词
        plot_prompt_path = settings.PROMPTS_DIR / "online" / "plot_system.txt"
        with open(plot_prompt_path, "r", encoding="utf-8") as f:
            system_prompt = f.read()
        
        # 获取世界信息
        meta = self.world_setting.get("meta", {})
        world_name = meta.get("world_name", self.world_name)
        genre = meta.get("genre_type", "REALISTIC")
        description = meta.get("description", "")
        
        # 获取地点信息
        locations = self.world_setting.get("geography", {}).get("locations", [])
        locations_text = "\n".join([
            f"- {loc['name']} ({loc['id']}): {loc.get('sensory_profile', {}).get('atmosphere', '')}"
            for loc in locations
        ])
        
        # 获取角色花名册
        characters_list_text = json.dumps(self.characters_list, ensure_ascii=False, indent=2)
        
        # 获取角色详细信息（角色卡）
        characters_detail_text = "\n".join([
            f"【{char.get('name', char.get('id'))}】(ID: {char.get('id')})\n"
            f"  特征: {', '.join(char.get('traits', []))}\n"
            f"  行为规则: {'; '.join(char.get('behavior_rules', [])[:2])}\n"
            f"  外观: {char.get('current_appearance', '无描述')[:100]}"
            for char in self.characters_details.values()
        ])
        
        # 获取社会规则
        social_rules = self.world_setting.get("social_logic", [])
        rules_text = "\n".join([
            f"- {rule.get('rule_name', '')}: {rule.get('trigger_condition', '')} → {rule.get('consequence', '')}"
            for rule in social_rules
        ])
        
        # 从 world_state 获取当前场景和天气信息
        current_scene = world_state.get("current_scene", {})
        weather = world_state.get("weather", {})
        characters_present = world_state.get("characters_present", [])
        world_situation = world_state.get("world_situation", {})
        
        # 当前在场角色
        present_chars_text = "\n".join([
            f"- {char.get('name')} (ID: {char.get('id')}): {char.get('mood')}, {char.get('activity')}"
            for char in characters_present
        ])
        
        user_message = f"""请生成【第一幕】的导演场记单。

===== 花名册 (characters_list.json) =====
{characters_list_text}

===== 世界设定 =====
世界名称: {world_name}
类型: {genre}
描述: {description}

【可用地点】
{locations_text}

【社会规则】
{rules_text}

===== 当前状态 =====
地点: {current_scene.get('location_name', '未知')} ({current_scene.get('location_id', '')})
时间: {current_scene.get('time_of_day', '傍晚')}
天气: {weather.get('condition', '晴朗')}，{weather.get('temperature', '温暖')}
世界形势: {world_situation.get('summary', '故事即将开始')}

【当前在场角色】
{present_chars_text if present_chars_text else '暂无'}

===== 角色详情 =====
{characters_detail_text}

===== 历史剧本 =====
（空，这是第一幕开场）

===== 玩家行动 =====
（无，玩家尚未介入）

请按照你的输出格式，生成第一幕的导演场记单。"""
        
        return [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ]
    
    def _parse_plot_response(self, content: str, world_state: Dict[str, Any]) -> tuple[InitialScene, InitialScript]:
        """
        解析 Plot 的响应
        
        Args:
            content: LLM 生成的纯文本剧本
            world_state: WS 生成的世界状态（用于构建场景数据）
        """
        import re
        
        # 场景数据从 world_state 获取（保持与 WS 一致）
        current_scene = world_state.get("current_scene", {})
        weather = world_state.get("weather", {})
        characters_present_ws = world_state.get("characters_present", [])
        
        # 解析【角色登场与调度】部分
        present_characters = []
        
        # 尝试从 Plot 输出中解析入场/在场/离场角色
        # 匹配格式: - **入场**: 角色名 (ID: npc_xxx) [First Appearance: True/False]
        #          - **在场**: 角色名 (ID: npc_xxx) - 描述...
        #          - **离场**: 角色名 (ID: npc_xxx) - 描述...
        # 注意: ID: 前缀是可选的，支持 (npc_xxx) 和 (ID: npc_xxx) 两种格式
        entry_pattern = r'\*\*入场\*\*[：:]\s*(\S+)\s*\((?:ID[：:]?\s*)?(\w+)\)\s*\[First Appearance[：:]\s*(True|False)\]'
        present_pattern = r'\*\*在场\*\*[：:]\s*(\S+)\s*\((?:ID[：:]?\s*)?(\w+)\)'
        exit_pattern = r'\*\*离场\*\*[：:]\s*(\S+)\s*\((?:ID[：:]?\s*)?(\w+)\)'  # 离场角色也需要初始化
        
        # 解析入场角色
        for match in re.finditer(entry_pattern, content, re.IGNORECASE):
            name, char_id, first_app = match.groups()
            present_characters.append({
                "id": char_id,
                "name": name,
                "first_appearance": first_app.lower() == "true"
            })
            logger.info(f"   📥 解析到入场角色: {name} ({char_id}) [首次: {first_app}]")
        
        # 解析在场角色（对于初始化场景，所有在场角色都是首次登场）
        for match in re.finditer(present_pattern, content, re.IGNORECASE):
            name, char_id = match.groups()
            # 检查是否已添加
            if not any(c["id"] == char_id for c in present_characters):
                # 初始化阶段，所有角色都是首次登场
                present_characters.append({
                    "id": char_id,
                    "name": name,
                    "first_appearance": True  # 初始化时所有角色都是首次登场
                })
                logger.info(f"   📍 解析到在场角色: {name} ({char_id}) [首次登场]")
        
        # 解析离场角色（离场的角色在本幕中也有戏份，需要初始化）
        for match in re.finditer(exit_pattern, content, re.IGNORECASE):
            name, char_id = match.groups()
            # 检查是否已添加
            if not any(c["id"] == char_id for c in present_characters):
                # 离场角色在本幕中有戏份，需要初始化
                present_characters.append({
                    "id": char_id,
                    "name": name,
                    "first_appearance": True  # 初始化时所有角色都是首次登场
                })
                logger.info(f"   📤 解析到离场角色: {name} ({char_id}) [首次登场，本幕有戏份]")
        
        # 如果解析失败，回退到 WS 的数据
        if not present_characters:
            logger.warning("   ⚠️ 未能从 Plot 输出解析角色，使用 WS 数据")
            present_characters = [
                {
                    "id": char.get("id"),
                    "name": char.get("name"),
                    "first_appearance": True
                }
                for char in characters_present_ws
            ]
        
        logger.info(f"   👥 最终在场角色: {[c['name'] for c in present_characters]}")
        
        # 构建场景
        scene = InitialScene(
            location_id=current_scene.get("location_id", "unknown"),
            location_name=current_scene.get("location_name", "未知地点"),
            time_of_day=current_scene.get("time_of_day", "傍晚"),
            weather=f"{weather.get('condition', '晴朗')}，{weather.get('temperature', '温暖')}",
            present_characters=present_characters,
            scene_description=current_scene.get("description", ""),
            opening_narrative=content.strip()[:500]  # 增加到500字以包含更多剧情
        )
        
        # 剧本为纯文本
        script = InitialScript(content=content.strip())
        
        return scene, script
    
    def _create_default_scene(self) -> InitialScene:
        """创建默认起始场景"""
        locations = self.world_setting.get("geography", {}).get("locations", [])
        first_loc = locations[0] if locations else {"id": "unknown", "name": "未知地点"}
        
        # 获取重要角色（转换为字典格式）
        important_chars = [
            {"id": c["id"], "name": c["name"], "first_appearance": True}
            for c in self.characters_list if c.get("importance", 0) >= 0.8
        ][:2]
        
        return InitialScene(
            location_id=first_loc.get("id", "unknown"),
            location_name=first_loc.get("name", "未知地点"),
            time_of_day="傍晚",
            weather="晴朗",
            present_characters=important_chars,
            scene_description="故事即将开始...",
            opening_narrative="欢迎来到这个世界，一段新的冒险正在等待着你。"
        )
    
    def _create_default_script(self) -> InitialScript:
        """创建默认起始剧本"""
        return InitialScript(
            content="故事即将展开...这个世界正等待着新的冒险者。周围的一切都充满了神秘与期待，似乎有什么重要的事情即将发生。"
        )
    
    # ==========================================
    # Vibe 初始化
    # ==========================================
    
    def init_vibe_and_generate_atmosphere(self) -> InitialAtmosphere:
        """
        初始化 Vibe（氛围感受者）并生成初始氛围
        
        依据数据：
        - world_setting.json - 地点感官信息
        - initial_scene - Plot 生成的场景
        - initial_script - Plot 生成的剧本（核心依据）
        - characters/*.json - 角色外观
        
        生成：
        - 初始氛围描写 (initial_atmosphere.json)
        """
        logger.info("")
        logger.info("─" * 60)
        logger.info("🎨 初始化 Vibe（氛围感受者）")
        logger.info("─" * 60)
        
        if not self.initial_scene or not self.initial_script:
            raise ValueError("请先运行 Plot 初始化")
        
        # 获取场景对应的地点信息
        location_id = self.initial_scene.location_id
        locations = self.world_setting.get("geography", {}).get("locations", [])
        location = next((loc for loc in locations if loc.get("id") == location_id), None)
        
        # 构建消息（使用外部提示词文件）
        messages = self._build_vibe_messages(location, self.initial_script.content)
        
        logger.info("🤖 正在调用 LLM 生成初始氛围描写...")
        logger.info(f"   提示词: prompts/online/vibe_system.txt")
        
        # 创建 Vibe 目录
        vibe_dir = self.runtime_dir / "vibe"
        vibe_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # 调用 LLM
            response = self.llm.invoke(messages)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # 解析响应（适配 vibe_system.txt 的输出格式）
            atmosphere = self._parse_vibe_response(content)
            
            self.initial_atmosphere = atmosphere
            
            # 保存氛围数据到 vibe 目录
            atmo_file = vibe_dir / "initial_atmosphere.json"
            with open(atmo_file, "w", encoding="utf-8") as f:
                json.dump(asdict(atmosphere), f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ Vibe 初始化完成")
            logger.info(f"   - 情绪基调: {atmosphere.emotional_tone}")
            logger.info(f"   - 氛围目录: {vibe_dir}")
            
            return atmosphere
            
        except Exception as e:
            logger.error(f"❌ Vibe 生成失败: {e}", exc_info=True)
            return self._create_default_atmosphere()
    
    def _build_vibe_messages(self, location: Optional[Dict[str, Any]], script_content: str) -> list:
        """
        构建 Vibe 的消息列表（使用外部提示词文件）
        
        提示词来源：prompts/online/vibe_system.txt
        
        Args:
            location: 地点信息（包含感官描述）
            script_content: Plot 生成的剧本内容（核心依据）
        """
        # 读取 Vibe 系统提示词
        vibe_prompt_path = settings.PROMPTS_DIR / "online" / "vibe_system.txt"
        with open(vibe_prompt_path, "r", encoding="utf-8") as f:
            system_prompt = f.read()
        
        # 获取地点感官信息
        sensory = location.get("sensory_profile", {}) if location else {}
        
        # 构建导演指令（来自 Plot 的剧本）
        user_message = f"""请为以下场景生成氛围描写。

===== 导演指令 =====
场所: {self.initial_scene.location_name}
时间: {self.initial_scene.time_of_day}
天气: {self.initial_scene.weather}

【感官参考】
视觉: {sensory.get('visual', '无')}
听觉: {sensory.get('auditory', '无')}
嗅觉: {sensory.get('olfactory', '无')}
氛围关键词: {sensory.get('atmosphere', '无')}

===== Plot 生成的剧本（核心依据）=====
{script_content}
==========================================

请基于上述剧本内容，提取并强化其中的环境氛围元素，按照你的输出格式生成氛围描写 JSON。"""
        
        return [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ]
    
    def _parse_vibe_response(self, content: str) -> InitialAtmosphere:
        """
        解析 Vibe 的响应
        
        适配 vibe_system.txt 的输出格式，转换为 InitialAtmosphere 结构
        """
        import re
        
        # 尝试提取 JSON
        json_match = re.search(r'\{[\s\S]*\}', content)
        if not json_match:
            raise ValueError("无法从响应中提取JSON")
        
        data = json.loads(json_match.group())
        
        # 适配 vibe_system.txt 的输出格式
        sensory_details = data.get("sensory_details", {})
        
        # 将数组转换为字符串
        def join_list(items):
            if isinstance(items, list):
                return "；".join(items) if items else ""
            return str(items) if items else ""
        
        # 优先使用 vibe_system.txt 格式，兼容旧格式
        visual = join_list(sensory_details.get("visual", [])) or data.get("visual_description", "")
        auditory = join_list(sensory_details.get("auditory", [])) or data.get("auditory_description", "")
        olfactory = join_list(sensory_details.get("olfactory", [])) or data.get("olfactory_description", "")
        emotional = join_list(data.get("mood_keywords", [])) or data.get("emotional_tone", "平静")
        full_text = data.get("atmosphere_description", "") or data.get("full_atmosphere_text", "")
        
        return InitialAtmosphere(
            visual_description=visual,
            auditory_description=auditory,
            olfactory_description=olfactory,
            emotional_tone=emotional,
            full_atmosphere_text=full_text
        )
    
    def _create_default_atmosphere(self) -> InitialAtmosphere:
        """创建默认氛围"""
        return InitialAtmosphere(
            visual_description="周围的一切都显得平静而神秘。",
            auditory_description="远处传来若有若无的声响。",
            olfactory_description="空气中弥漫着淡淡的气息。",
            emotional_tone="神秘、期待",
            full_atmosphere_text="这是一个充满可能性的时刻，故事即将展开..."
        )
    
    # ==========================================
    # 完整初始化流程
    # ==========================================
    
    def run(self) -> Path:
        """
        运行完整的光明会初始化流程
        
        Returns:
            运行时数据目录路径
        """
        logger.info("")
        logger.info("=" * 60)
        logger.info("🚀 开始光明会完整初始化流程")
        logger.info("=" * 60)
        
        # 1. 初始化 WS
        world_state = self.init_world_state()
        
        # 2. 初始化 Plot 并生成起始场景/剧本（传入world_state作为依据）
        scene, script = self.init_plot_and_generate_opening(world_state)
        
        # 3. 初始化 Vibe 并生成氛围
        atmosphere = self.init_vibe_and_generate_atmosphere()
        
        # 4. 生成初始化摘要
        self._save_init_summary()
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ 光明会初始化完成！")
        logger.info("=" * 60)
        logger.info(f"📁 运行时数据目录: {self.runtime_dir}")
        
        return self.runtime_dir
    
    def _save_init_summary(self):
        """保存初始化摘要"""
        # 获取当前 LLM 配置信息
        llm_config = self._get_llm_config()
        
        summary = {
            "world_name": self.world_name,
            "initialized_at": datetime.now().isoformat(),
            "runtime_dir": str(self.runtime_dir),
            "llm_config": llm_config,
            "directory_structure": {
                "ws": "ws/world_state.json",
                "plot": {
                    "scene": "plot/current_scene.json",
                    "script": "plot/current_script.json",
                    "history": "plot/history/"
                },
                "vibe": "vibe/initial_atmosphere.json"
            },
            "components": {
                "WS": {
                    "status": "initialized",
                    "directory": "ws/",
                    "state_file": "ws/world_state.json"
                },
                "Plot": {
                    "status": "initialized",
                    "directory": "plot/",
                    "scene_file": "plot/current_scene.json",
                    "current_script": "plot/current_script.json",
                    "history_directory": "plot/history/",
                    "opening_location": self.initial_scene.location_name if self.initial_scene else None
                },
                "Vibe": {
                    "status": "initialized",
                    "directory": "vibe/",
                    "atmosphere_file": "vibe/initial_atmosphere.json",
                    "emotional_tone": self.initial_atmosphere.emotional_tone if self.initial_atmosphere else None
                }
            },
            "ready_for_game": True
        }
        
        summary_file = self.runtime_dir / "init_summary.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        logger.info(f"📋 初始化摘要: {summary_file}")
    
    def _get_llm_config(self) -> Dict[str, Any]:
        """获取当前 LLM 配置信息"""
        provider = settings.LLM_PROVIDER
        
        if provider == "openrouter":
            model = settings.OPENROUTER_MODEL
            api_base = settings.OPENROUTER_BASE_URL
        elif provider == "zhipu":
            model = settings.MODEL_NAME
            api_base = "https://open.bigmodel.cn/api/paas/v4/"
        elif provider == "openai":
            model = settings.MODEL_NAME
            api_base = "https://api.openai.com/v1"
        else:
            model = settings.MODEL_NAME
            api_base = "unknown"
        
        return {
            "provider": provider,
            "model": model,
            "temperature": settings.TEMPERATURE,
            "api_base": api_base
        }


def print_banner():
    """打印横幅"""
    print()
    print("=" * 70)
    print("  🏛️  光明会初始化 (Illuminati Initialization)")
    print("  初始化 WS（世界状态）、Plot（命运编织）、Vibe（氛围感受）")
    print("=" * 70)
    print()


def get_available_worlds() -> List[str]:
    """获取所有可用的世界列表"""
    worlds_dir = settings.DATA_DIR / "worlds"
    available = []
    if worlds_dir.exists():
        for w in worlds_dir.iterdir():
            if w.is_dir() and (w / "world_setting.json").exists():
                available.append(w.name)
    return available


def select_world(available_worlds: List[str]) -> Optional[str]:
    """让用户选择世界"""
    print("📂 检测到多个世界，请选择要初始化的世界：")
    print()
    for i, world in enumerate(available_worlds, 1):
        print(f"   [{i}] {world}")
    print()
    print(f"   [0] 退出")
    print()
    
    while True:
        try:
            choice = input("请输入数字选择 > ").strip()
            if choice == "0":
                return None
            idx = int(choice) - 1
            if 0 <= idx < len(available_worlds):
                return available_worlds[idx]
            else:
                print(f"❌ 请输入 0-{len(available_worlds)} 之间的数字")
        except ValueError:
            print("❌ 请输入有效的数字")
        except (KeyboardInterrupt, EOFError):
            print("\n已取消")
            return None


def collect_player_profile(args) -> Dict[str, Any]:
    """
    收集玩家角色的最小设定。
    优先使用命令行参数；缺失时在可交互环境下提示输入。
    """
    profile: Dict[str, Any] = {
        "name": args.player_name,
        "gender": args.player_gender,
        "appearance": args.player_appearance
    }

    # 非交互环境直接返回已有参数
    if not sys.stdin.isatty():
        return {k: v for k, v in profile.items() if v}

    try:
        if not profile["name"]:
            name = input("请输入玩家在世界中的名字（回车默认“玩家”） > ").strip()
            if name:
                profile["name"] = name
        if not profile["gender"]:
            gender = input("请输入玩家性别（可留空） > ").strip()
            if gender:
                profile["gender"] = gender
        if not profile["appearance"]:
            appearance = input("一句话描述玩家外观/风格（可留空） > ").strip()
            if appearance:
                profile["appearance"] = appearance
    except (KeyboardInterrupt, EOFError):
        print("\n使用默认玩家设定")

    return {k: v for k, v in profile.items() if v}


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="🏛️ 光明会初始化 - 初始化游戏运行阶段的核心 Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--world",
        type=str,
        required=False,
        default=None,
        help="世界名称（对应 data/worlds/<world>/ 目录），不指定则自动检测"
    )
    parser.add_argument(
        "--player-name",
        type=str,
        required=False,
        default=None,
        help="玩家在世界中的名字（可选）"
    )
    parser.add_argument(
        "--player-gender",
        type=str,
        required=False,
        default=None,
        help="玩家性别（可选）"
    )
    parser.add_argument(
        "--player-appearance",
        type=str,
        required=False,
        default=None,
        help="一句话外观/风格描述（可选）"
    )
    parser.add_argument(
        "--runtime-name",
        type=str,
        required=False,
        default=None,
        help="自定义运行时目录后缀（默认使用时间戳）"
    )
    parser.add_argument(
        "--overwrite-runtime",
        action="store_true",
        help="当指定的运行时目录已存在时强制覆盖"
    )
    
    args = parser.parse_args()
    
    print_banner()
    
    # 验证配置
    try:
        settings.validate()
    except ValueError as e:
        print(f"❌ 配置验证失败: {e}")
        print("请检查 .env 文件中的 API 密钥配置")
        return
    
    # 获取可用世界列表
    available_worlds = get_available_worlds()
    
    if not available_worlds:
        print("❌ 未找到任何可用的世界")
        print()
        print("请先运行创世组生成世界数据：")
        print("   python run_creator_god.py")
        return
    
    # 确定要使用的世界
    world_name = args.world
    
    if world_name:
        # 用户指定了世界，验证是否存在
        if world_name not in available_worlds:
            print(f"❌ 世界不存在: {world_name}")
            print()
            print("可用的世界:")
            for w in available_worlds:
                print(f"   - {w}")
            return
    else:
        # 自动检测
        if len(available_worlds) == 1:
            # 只有一个世界，直接使用
            world_name = available_worlds[0]
            print(f"📂 检测到唯一世界: {world_name}")
            print()
        else:
            # 多个世界，让用户选择
            world_name = select_world(available_worlds)
            if not world_name:
                print("已取消初始化")
                return
            print()

    print(f"🌍 选定世界: {world_name}")
    print()

    # 收集玩家设定（最小信息）
    player_profile = collect_player_profile(args)

    # 运行时目录配置
    runtime_name = args.runtime_name
    overwrite_runtime = args.overwrite_runtime

    # 显示当前 LLM 配置
    print("🤖 LLM 配置:")
    if settings.LLM_PROVIDER == "openrouter":
        print(f"   Provider: OpenRouter")
        print(f"   Model: {settings.OPENROUTER_MODEL}")
        print(f"   API Base: {settings.OPENROUTER_BASE_URL}")
    elif settings.LLM_PROVIDER == "zhipu":
        print(f"   Provider: 智谱清言 (ZhipuAI)")
        print(f"   Model: {settings.MODEL_NAME}")
    elif settings.LLM_PROVIDER == "openai":
        print(f"   Provider: OpenAI")
        print(f"   Model: {settings.MODEL_NAME}")
    else:
        print(f"   Provider: {settings.LLM_PROVIDER}")
        print(f"   Model: {settings.MODEL_NAME}")
    print(f"   Temperature: {settings.TEMPERATURE}")
    print()

    try:
        # 初始化光明会
        initializer = IlluminatiInitializer(
            world_name,
            player_profile=player_profile,
            runtime_name=runtime_name,
            overwrite_runtime=overwrite_runtime,
        )
        runtime_dir = initializer.run()
        
        print()
        print("=" * 70)
        print("  ✅ 光明会初始化成功！")
        print("=" * 70)
        print()
        print(f"  📁 运行时数据目录: {runtime_dir}")
        print()
        print("  📖 生成的目录结构:")
        print(f"     📂 ws/")
        print(f"        └─ world_state.json       # WS 世界状态")
        print(f"     📂 plot/")
        print(f"        ├─ current_scene.json     # 当前场景")
        print(f"        ├─ current_script.json    # 当前剧本")
        print(f"        └─ history/               # 历史剧本存档（运行时使用）")
        print(f"     📂 vibe/")
        print(f"        └─ initial_atmosphere.json # 初始氛围")
        print(f"     📄 init_summary.json          # 初始化摘要")
        print()
        
        # 显示开场内容预览
        if initializer.initial_scene and initializer.initial_atmosphere:
            print("  📜 开场预览:")
            print("  " + "─" * 66)
            print()
            print(f"  📍 {initializer.initial_scene.location_name}")
            print(f"  ⏰ {initializer.initial_scene.time_of_day} | 🌤️ {initializer.initial_scene.weather}")
            print()
            # 显示氛围文本（每行缩进）
            atmo_lines = initializer.initial_atmosphere.full_atmosphere_text.split('\n')
            for line in atmo_lines:
                if line.strip():
                    print(f"  {line.strip()}")
            print()
            print("  " + "─" * 66)
        
        print()
        print(f"  📋 日志文件: {settings.LOGS_DIR}/illuminati_init.log")
        print()
        print("=" * 70)
        
    except FileNotFoundError as e:
        print(f"❌ 文件未找到: {e}")
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        print(f"请查看日志: {settings.LOGS_DIR}/illuminati_init.log")


if __name__ == "__main__":
    main()
