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
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

from config.settings import settings
from utils.logger import setup_logger
from utils.llm_factory import get_llm

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
    """起始剧本数据结构"""
    scene: str
    characters: List[str]
    actions: List[Dict[str, Any]]
    narrative: str
    hints: List[str]


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
    
    def __init__(self, world_name: str):
        """
        初始化光明会
        
        Args:
            world_name: 世界名称（对应 data/worlds/<world_name>/ 目录）
        """
        logger.info("=" * 60)
        logger.info("🏛️  启动光明会初始化流程")
        logger.info("=" * 60)
        
        self.world_name = world_name
        self.world_dir = settings.DATA_DIR / "worlds" / world_name
        
        # 验证世界数据存在
        if not self.world_dir.exists():
            raise FileNotFoundError(f"世界数据目录不存在: {self.world_dir}")
        
        # 创建运行时数据目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.runtime_dir = settings.DATA_DIR / "runtime" / f"{world_name}_{timestamp}"
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"📁 世界数据目录: {self.world_dir}")
        logger.info(f"📁 运行时数据目录: {self.runtime_dir}")
        
        # 加载世界数据
        self.world_setting = self._load_world_setting()
        self.characters_list = self._load_characters_list()
        self.characters_details = self._load_all_characters()
        
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
            "plot_hints": []  # 由 Plot 动态生成
        }
    
    # ==========================================
    # WS 初始化
    # ==========================================
    
    def init_world_state(self) -> Dict[str, Any]:
        """
        初始化 WS（世界状态运行者）
        
        依据数据：
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
        
        # 提取地点信息
        locations = self.world_setting.get("geography", {}).get("locations", [])
        
        # 选择初始地点（默认第一个）
        initial_location = locations[0] if locations else {"id": "unknown", "name": "未知地点"}
        
        # 获取初始在场角色（从 characters_list 中选择重要性较高的角色，确保 ID 一致性）
        characters_present = []
        # 按重要性排序 characters_list
        sorted_chars = sorted(
            self.characters_list,
            key=lambda x: x.get("importance", 0),
            reverse=True
        )[:3]  # 初始场景最多3个角色
        
        for char_info in sorted_chars:
            char_id = char_info.get("id")  # 使用 characters_list 中的 ID
            char_name = char_info.get("name", "")
            # 从角色档案中获取详细信息
            char_detail = self.characters_details.get(char_id, {})
            characters_present.append({
                "id": char_id,  # 确保使用 characters_list 中的 ID
                "name": char_name,
                "mood": "平静",
                "activity": "在场",
                "appearance_note": char_detail.get("current_appearance", "")
            })
        
        # NPC关系矩阵初始化时留空
        # 只有当角色在Plot生成的剧本中登场后，才会被加入关系矩阵
        # WS会在后续根据Plot的剧本来更新关系矩阵
        relationship_matrix = {}
        
        # 构建世界整体形势
        meta = self.world_setting.get("meta", {})
        world_situation = {
            "summary": f"故事在{meta.get('world_name', self.world_name)}展开，一切刚刚开始。",
            "tension_level": "平静",
            "key_developments": []
        }
        
        # 构建符合新格式的世界状态
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
            "characters_absent": [],  # 初始化时为空
            "relationship_matrix": relationship_matrix,
            "world_situation": world_situation,
            "meta": {
                "game_turn": 0,
                "last_updated": datetime.now().isoformat(),
                "total_elapsed_time": "0分钟"
            }
        }
        
        # 保存世界状态到 ws 目录
        state_file = ws_dir / "world_state.json"
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(world_state, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ WS 初始化完成")
        logger.info(f"   - 初始场景: {initial_location.get('name', '未知')}")
        logger.info(f"   - 在场角色: {len(characters_present)} 人")
        logger.info(f"   - 关系矩阵: {len(relationship_matrix)} 个角色")
        logger.info(f"   - 状态文件: {state_file}")
        
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
        - 起始剧本 (plot/script/script_001.json)
        """
        logger.info("")
        logger.info("─" * 60)
        logger.info("🎬 初始化 Plot（命运编织者）")
        logger.info("─" * 60)
        
        # 创建 Plot 目录结构
        plot_dir = self.runtime_dir / "plot"
        plot_dir.mkdir(parents=True, exist_ok=True)
        script_dir = plot_dir / "script"
        script_dir.mkdir(parents=True, exist_ok=True)
        
        # 构建 Prompt（传入world_state）
        prompt = self._build_plot_prompt(world_state)
        
        logger.info("🤖 正在调用 LLM 生成起始场景和剧本...")
        logger.info(f"   依据: world_setting, characters_list, {len(self.characters_details)}个角色卡, world_state")
        
        try:
            # 调用 LLM
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # 解析响应
            scene, script = self._parse_plot_response(content)
            
            self.initial_scene = scene
            self.initial_script = script
            
            # 保存当前场景到 plot 目录
            scene_file = plot_dir / "current_scene.json"
            with open(scene_file, "w", encoding="utf-8") as f:
                json.dump(asdict(scene), f, ensure_ascii=False, indent=2)
            
            # 保存起始剧本到 plot/script 目录，使用序号命名
            script_number = 1
            script_file = script_dir / f"script_{script_number:03d}.json"
            script_data = asdict(script)
            script_data["script_number"] = script_number  # 添加序号标识
            script_data["is_initial"] = True  # 标记为初始剧本
            with open(script_file, "w", encoding="utf-8") as f:
                json.dump(script_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ Plot 初始化完成")
            logger.info(f"   - 起始地点: {scene.location_name}")
            # 从字典列表中提取角色名
            char_names = [c.get('name', c.get('id', '未知')) if isinstance(c, dict) else c for c in scene.present_characters]
            logger.info(f"   - 在场角色: {', '.join(char_names)}")
            logger.info(f"   - 场景文件: {scene_file}")
            logger.info(f"   - 剧本文件: {script_file}")
            
            return scene, script
            
        except Exception as e:
            logger.error(f"❌ Plot 生成失败: {e}", exc_info=True)
            # 返回默认值
            return self._create_default_scene(), self._create_default_script()
    
    def _build_plot_prompt(self, world_state: Dict[str, Any]) -> str:
        """
        构建 Plot 的 Prompt
        
        Args:
            world_state: WS生成的世界状态
        """
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
        
        # 获取角色花名册信息（Plot用于决定角色登场）
        characters_list_text = "\n".join([
            f"- {char.get('name')} (ID: {char.get('id')}, 重要性: {char.get('importance', 0.5)})"
            for char in self.characters_list
        ])
        
        # 获取角色详细信息（角色卡）
        characters_detail_text = "\n".join([
            f"【{char.get('name', char.get('id'))}】\n"
            f"  ID: {char.get('id')}\n"
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
        
        prompt = f"""你是命运编织者（Plot Director），负责为互动叙事游戏生成起始场景和开场剧本。

===== 世界设定 =====
【世界背景】
世界名称: {world_name}
类型: {genre}
描述: {description}

【可用地点】
{locations_text}

【社会规则】
{rules_text}

===== 角色花名册 =====
以下是所有可能登场的角色，由你（Plot）决定谁在何时登场：
{characters_list_text}

【角色详情（角色卡）】
{characters_detail_text}

===== 当前世界状态（来自WS） =====
【当前场景】
地点: {current_scene.get('location_name', '未知')} ({current_scene.get('location_id', '')})
时间: {current_scene.get('time_of_day', '傍晚')}
场景描述: {current_scene.get('description', '')}

【当前天气】
状况: {weather.get('condition', '晴朗')}
温度: {weather.get('temperature', '温暖')}

【当前在场角色】
{present_chars_text if present_chars_text else '暂无'}

【世界形势】
{world_situation.get('summary', '故事即将开始')}
紧张程度: {world_situation.get('tension_level', '平静')}

===== 任务 =====
请根据以上信息，生成第一幕的起始场景和开场剧本。要求：
1. 场景要与WS提供的当前场景保持一致
2. 从花名册中选择2-3个重要角色首次登场
3. 设置一个有张力的开场情境，为故事做好铺垫
4. 为玩家的介入留下空间
5. 所有角色ID必须使用花名册中的ID（如 npc_001）
6. 这是角色的首次登场，请在 present_characters 中标注 `first_appearance: true`

请严格按照以下JSON格式输出（不要添加任何其他文字）：

{{
    "scene": {{
        "location_id": "地点ID（使用world_state中的）",
        "location_name": "地点名称",
        "time_of_day": "时间段（使用world_state中的）",
        "weather": "天气（使用world_state中的）",
        "present_characters": [
            {{"id": "npc_001", "name": "角色名", "first_appearance": true}},
            {{"id": "npc_002", "name": "角色名", "first_appearance": true}}
        ],
        "scene_description": "场景描述（100字以内）",
        "opening_narrative": "开场旁白（200字以内，用于展示给玩家，要有氛围感）"
    }},
    "script": {{
        "scene": "场景简述",
        "characters": ["角色ID列表"],
        "actions": [
            {{"character": "角色ID", "action": "行为描述", "dialogue": "台词（可选）", "emotion": "情绪"}}
        ],
        "narrative": "旁白文本",
        "hints": ["剧情提示1", "剧情提示2"]
    }}
}}"""
        
        return prompt
    
    def _parse_plot_response(self, content: str) -> tuple[InitialScene, InitialScript]:
        """解析 Plot 的响应"""
        import re
        
        # 尝试提取 JSON
        json_match = re.search(r'\{[\s\S]*\}', content)
        if not json_match:
            raise ValueError("无法从响应中提取JSON")
        
        data = json.loads(json_match.group())
        
        # 解析场景
        scene_data = data.get("scene", {})
        scene = InitialScene(
            location_id=scene_data.get("location_id", "unknown"),
            location_name=scene_data.get("location_name", "未知地点"),
            time_of_day=scene_data.get("time_of_day", "傍晚"),
            weather=scene_data.get("weather", "晴朗"),
            present_characters=scene_data.get("present_characters", []),
            scene_description=scene_data.get("scene_description", ""),
            opening_narrative=scene_data.get("opening_narrative", "")
        )
        
        # 解析剧本
        script_data = data.get("script", {})
        script = InitialScript(
            scene=script_data.get("scene", ""),
            characters=script_data.get("characters", []),
            actions=script_data.get("actions", []),
            narrative=script_data.get("narrative", ""),
            hints=script_data.get("hints", [])
        )
        
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
        important_chars = [c["id"] for c in self.characters_list if c.get("importance", 0) >= 0.8][:2]
        
        return InitialScript(
            scene="开场场景",
            characters=important_chars,
            actions=[],
            narrative="故事即将展开...",
            hints=["探索周围环境", "与角色交谈"]
        )
    
    # ==========================================
    # Vibe 初始化
    # ==========================================
    
    def init_vibe_and_generate_atmosphere(self) -> InitialAtmosphere:
        """
        初始化 Vibe（氛围感受者）并生成初始氛围
        
        读取 world_setting.json 和 Plot 生成的起始场景，生成：
        - 初始氛围描写 (initial_atmosphere.json)
        """
        logger.info("")
        logger.info("─" * 60)
        logger.info("🎨 初始化 Vibe（氛围感受者）")
        logger.info("─" * 60)
        
        if not self.initial_scene:
            raise ValueError("请先运行 Plot 初始化")
        
        # 获取场景对应的地点信息
        location_id = self.initial_scene.location_id
        locations = self.world_setting.get("geography", {}).get("locations", [])
        location = next((loc for loc in locations if loc.get("id") == location_id), None)
        
        # 构建 Prompt
        prompt = self._build_vibe_prompt(location)
        
        logger.info("🤖 正在调用 LLM 生成初始氛围描写...")
        
        # 创建 Vibe 目录
        vibe_dir = self.runtime_dir / "vibe"
        vibe_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # 调用 LLM
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # 解析响应
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
    
    def _build_vibe_prompt(self, location: Optional[Dict[str, Any]]) -> str:
        """构建 Vibe 的 Prompt"""
        # 获取世界信息
        meta = self.world_setting.get("meta", {})
        genre = meta.get("genre_type", "REALISTIC")
        
        # 获取地点感官信息
        sensory = location.get("sensory_profile", {}) if location else {}
        
        # 获取在场角色外观
        appearances = []
        for char_info in self.initial_scene.present_characters:
            # 支持新格式（字典）和旧格式（字符串ID）
            char_id = char_info.get("id") if isinstance(char_info, dict) else char_info
            char = self.characters_details.get(char_id, {})
            appearance = char.get("current_appearance", f"{char.get('name', char_id)}在场")
            appearances.append(f"- {char.get('name', char_id)}: {appearance}")
        
        appearances_text = "\n".join(appearances) if appearances else "- 暂无在场角色"
        
        prompt = f"""你是氛围感受者（Atmosphere Creator），负责创作沉浸式的环境氛围描写。

【世界类型】
{genre}

【当前场所】
位置名称: {self.initial_scene.location_name}
时间: {self.initial_scene.time_of_day}
天气: {self.initial_scene.weather}
场景描述: {self.initial_scene.scene_description}

【感官参考】
视觉: {sensory.get('visual', '无')}
听觉: {sensory.get('auditory', '无')}
嗅觉: {sensory.get('olfactory', '无')}
氛围关键词: {sensory.get('atmosphere', '无')}

【在场角色外观】
{appearances_text}

请创作一段富有感染力的氛围描写，让玩家身临其境。要求：
1. 融合视觉、听觉、嗅觉等多种感官
2. 体现场景的情绪基调
3. 自然地描写在场角色的外观和状态
4. 200-300字

请严格按照以下JSON格式输出（不要添加任何其他文字）：

{{
    "visual_description": "视觉描写（50-80字）",
    "auditory_description": "听觉描写（30-50字）",
    "olfactory_description": "嗅觉描写（20-30字）",
    "emotional_tone": "情绪基调（2-3个词）",
    "full_atmosphere_text": "完整的氛围描写文本（200-300字）"
}}"""
        
        return prompt
    
    def _parse_vibe_response(self, content: str) -> InitialAtmosphere:
        """解析 Vibe 的响应"""
        import re
        
        # 尝试提取 JSON
        json_match = re.search(r'\{[\s\S]*\}', content)
        if not json_match:
            raise ValueError("无法从响应中提取JSON")
        
        data = json.loads(json_match.group())
        
        return InitialAtmosphere(
            visual_description=data.get("visual_description", ""),
            auditory_description=data.get("auditory_description", ""),
            olfactory_description=data.get("olfactory_description", ""),
            emotional_tone=data.get("emotional_tone", "平静"),
            full_atmosphere_text=data.get("full_atmosphere_text", "")
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
        summary = {
            "world_name": self.world_name,
            "initialized_at": datetime.now().isoformat(),
            "runtime_dir": str(self.runtime_dir),
            "directory_structure": {
                "ws": "ws/world_state.json",
                "plot": {
                    "scene": "plot/current_scene.json",
                    "script": "plot/script/script_001.json"
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
                    "script_directory": "plot/script/",
                    "initial_script": "plot/script/script_001.json",
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
    
    try:
        # 初始化光明会
        initializer = IlluminatiInitializer(world_name)
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
        print(f"        └─ script/")
        print(f"           └─ script_001.json     # 第1幕剧本")
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

