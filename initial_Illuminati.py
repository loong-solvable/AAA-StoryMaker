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
        ws_prompt_path = settings.BASE_DIR / "prompts" / "online" / "ws_system.txt"
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
        
        # 构建 Prompt（传入world_state）
        prompt = self._build_plot_prompt(world_state)
        
        logger.info("🤖 正在调用 LLM 生成起始场景和剧本...")
        logger.info(f"   依据: world_setting, characters_list, {len(self.characters_details)}个角色卡, world_state")
        
        try:
            # 调用 LLM
            response = self.llm.invoke(prompt)
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
            # 返回默认值
            return self._create_default_scene(), self._create_default_script()
    
    def _build_plot_prompt(self, world_state: Dict[str, Any]) -> str:
        """
        构建 Plot 的 Prompt
        
        数据来源：
        - self.world_setting: world_setting.json（世界名称、类型、描述、地点、社会规则）
        - self.characters_list: characters_list.json（角色花名册）
        - self.characters_details: characters/*.json（角色卡详情）
        - world_state: WS初始化生成的世界状态（当前场景、天气、在场角色）
        
        Args:
            world_state: WS初始化生成的世界状态
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
        
        prompt = f"""你是命运编织者（Plot Director），负责为互动叙事游戏生成开场剧本。

===== 世界设定 =====
世界名称: {world_name}
类型: {genre}
描述: {description}

【可用地点】
{locations_text}
你也可以自己创造地点，但需要符合世界观设定。

【社会规则】
{rules_text}

===== 角色信息 =====
【角色花名册】
{characters_list_text}

【角色详情】
{characters_detail_text}

===== 当前世界状态 =====
地点: {current_scene.get('location_name', '未知')}
时间: {current_scene.get('time_of_day', '傍晚')}
天气: {weather.get('condition', '晴朗')}，{weather.get('temperature', '温暖')}
世界形势: {world_situation.get('summary', '故事即将开始')}

【当前在场角色】
{present_chars_text if present_chars_text else '暂无'}

===== 任务 =====
请根据以上信息，创作一段约500字的开场剧本。要求：

1. 以第三人称视角书写，富有文学性和画面感
2. 描绘当前场景的氛围和环境
3. 让1-3个重要角色自然登场，展现他们的性格特征
4. 通过对话和行为推动情节，制造适当的戏剧张力
5. 为玩家角色的介入留下空间和契机
6. 符合世界观设定和社会规则

直接输出剧本内容，不要添加标题、格式标记或任何额外说明。"""
        
        return prompt
    
    def _parse_plot_response(self, content: str, world_state: Dict[str, Any]) -> tuple[InitialScene, InitialScript]:
        """
        解析 Plot 的响应
        
        Args:
            content: LLM 生成的纯文本剧本
            world_state: WS 生成的世界状态（用于构建场景数据）
        """
        # 场景数据从 world_state 获取（保持与 WS 一致）
        current_scene = world_state.get("current_scene", {})
        weather = world_state.get("weather", {})
        characters_present = world_state.get("characters_present", [])
        
        # 构建在场角色列表（标记为首次登场）
        present_characters = [
            {
                "id": char.get("id"),
                "name": char.get("name"),
                "first_appearance": True
            }
            for char in characters_present
        ]
        
        # 构建场景
        scene = InitialScene(
            location_id=current_scene.get("location_id", "unknown"),
            location_name=current_scene.get("location_name", "未知地点"),
            time_of_day=current_scene.get("time_of_day", "傍晚"),
            weather=f"{weather.get('condition', '晴朗')}，{weather.get('temperature', '温暖')}",
            present_characters=present_characters,
            scene_description=current_scene.get("description", ""),
            opening_narrative=content.strip()[:200]  # 取前200字作为开场旁白
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
        
        # 构建 Prompt（传入剧本内容）
        prompt = self._build_vibe_prompt(location, self.initial_script.content)
        
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
    
    def _build_vibe_prompt(self, location: Optional[Dict[str, Any]], script_content: str) -> str:
        """
        构建 Vibe 的 Prompt
        
        Args:
            location: 地点信息（包含感官描述）
            script_content: Plot 生成的剧本内容（核心依据）
        """
        # 获取世界信息
        meta = self.world_setting.get("meta", {})
        genre = meta.get("genre_type", "REALISTIC")
        
        # 获取地点感官信息
        sensory = location.get("sensory_profile", {}) if location else {}
        
        prompt = f"""你是氛围感受者（Atmosphere Creator），负责基于剧本内容创作沉浸式的环境氛围描写。

【世界类型】
{genre}

【当前场所】
位置名称: {self.initial_scene.location_name}
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

请基于上述剧本内容，提取并强化其中的环境氛围元素，创作一段让玩家身临其境的氛围描写。要求：

1. **必须与剧本内容一致**：氛围描写要反映剧本中的场景、角色状态和情节氛围
2. 融合视觉、听觉、嗅觉等多种感官
3. 体现剧本中的情绪基调和戏剧张力
4. 200-300字

请严格按照以下JSON格式输出（不要添加任何其他文字）：

{{
    "visual_description": "视觉描写（50-80字，基于剧本场景）",
    "auditory_description": "听觉描写（30-50字，基于剧本场景）",
    "olfactory_description": "嗅觉描写（20-30字，基于剧本场景）",
    "emotional_tone": "情绪基调（2-3个词，反映剧本氛围）",
    "full_atmosphere_text": "完整的氛围描写文本（200-300字，与剧本内容呼应）"
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

