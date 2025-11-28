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
    present_characters: List[str]
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
        
        读取 world_setting.json，初始化世界状态
        """
        logger.info("")
        logger.info("─" * 60)
        logger.info("🌍 初始化 WS（世界状态运行者）")
        logger.info("─" * 60)
        
        # 提取地点信息
        locations = self.world_setting.get("geography", {}).get("locations", [])
        
        # 选择初始地点（默认第一个）
        initial_location = locations[0] if locations else {"id": "unknown", "name": "未知地点"}
        
        # 初始化 NPC 状态
        npc_states = {}
        for char in self.characters_details.values():
            char_id = char.get("id", "unknown")
            npc_states[char_id] = {
                "name": char.get("name", char_id),
                "current_location": initial_location.get("id"),
                "current_activity": "日常活动",
                "mood": "平静",
                "last_interaction": None
            }
        
        # 构建世界状态
        world_state = {
            "world_name": self.world_setting.get("meta", {}).get("world_name", self.world_name),
            "current_time": "傍晚",
            "weather": "晴朗",
            "locations": locations,
            "npc_states": npc_states,
            "physics_rules": self.world_setting.get("physics_logic", {}),
            "social_rules": self.world_setting.get("social_logic", []),
            "triggered_events": [],
            "game_turn": 0
        }
        
        # 保存世界状态
        state_file = self.runtime_dir / "world_state.json"
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(world_state, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ WS 初始化完成")
        logger.info(f"   - 地点数量: {len(locations)}")
        logger.info(f"   - NPC数量: {len(npc_states)}")
        logger.info(f"   - 状态文件: {state_file}")
        
        return world_state
    
    # ==========================================
    # Plot 初始化
    # ==========================================
    
    def init_plot_and_generate_opening(self) -> tuple[InitialScene, InitialScript]:
        """
        初始化 Plot（命运编织者）并生成起始场景和剧本
        
        读取创世组生成的所有 json 文件，生成：
        - 起始场景 (initial_scene.json)
        - 起始剧本 (initial_script.json)
        """
        logger.info("")
        logger.info("─" * 60)
        logger.info("🎬 初始化 Plot（命运编织者）")
        logger.info("─" * 60)
        
        # 构建 Prompt
        prompt = self._build_plot_prompt()
        
        logger.info("🤖 正在调用 LLM 生成起始场景和剧本...")
        
        try:
            # 调用 LLM
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # 解析响应
            scene, script = self._parse_plot_response(content)
            
            self.initial_scene = scene
            self.initial_script = script
            
            # 保存起始场景
            scene_file = self.runtime_dir / "initial_scene.json"
            with open(scene_file, "w", encoding="utf-8") as f:
                json.dump(asdict(scene), f, ensure_ascii=False, indent=2)
            
            # 保存起始剧本
            script_file = self.runtime_dir / "initial_script.json"
            with open(script_file, "w", encoding="utf-8") as f:
                json.dump(asdict(script), f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ Plot 初始化完成")
            logger.info(f"   - 起始地点: {scene.location_name}")
            logger.info(f"   - 在场角色: {', '.join(scene.present_characters)}")
            logger.info(f"   - 场景文件: {scene_file}")
            logger.info(f"   - 剧本文件: {script_file}")
            
            return scene, script
            
        except Exception as e:
            logger.error(f"❌ Plot 生成失败: {e}", exc_info=True)
            # 返回默认值
            return self._create_default_scene(), self._create_default_script()
    
    def _build_plot_prompt(self) -> str:
        """构建 Plot 的 Prompt"""
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
        
        # 获取角色信息
        characters_text = "\n".join([
            f"- {char.get('name', char.get('id'))} (重要性: {char.get('importance', 0.5)}): {', '.join(char.get('traits', []))}"
            for char in self.characters_details.values()
        ])
        
        # 获取社会规则
        social_rules = self.world_setting.get("social_logic", [])
        rules_text = "\n".join([
            f"- {rule.get('rule_name', '')}: {rule.get('trigger_condition', '')} → {rule.get('consequence', '')}"
            for rule in social_rules
        ])
        
        prompt = f"""你是命运编织者（Plot Director），负责为互动叙事游戏生成起始场景和开场剧本。

【世界背景】
世界名称: {world_name}
类型: {genre}
描述: {description}

【可用地点】
{locations_text}

【主要角色】
{characters_text}

【社会规则】
{rules_text}

请生成一个引人入胜的起始场景和开场剧本。要求：
1. 选择一个合适的开场地点
2. 安排2-3个重要角色出场
3. 设置一个有张力的开场情境
4. 为玩家的介入留下空间

请严格按照以下JSON格式输出（不要添加任何其他文字）：

{{
    "scene": {{
        "location_id": "地点ID",
        "location_name": "地点名称",
        "time_of_day": "时间段（如：傍晚、深夜、清晨）",
        "weather": "天气",
        "present_characters": ["角色ID1", "角色ID2"],
        "scene_description": "场景描述（100字以内）",
        "opening_narrative": "开场旁白（200字以内，用于展示给玩家）"
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
        
        # 获取重要角色
        important_chars = [c["id"] for c in self.characters_list if c.get("importance", 0) >= 0.8][:2]
        
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
        
        try:
            # 调用 LLM
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # 解析响应
            atmosphere = self._parse_vibe_response(content)
            
            self.initial_atmosphere = atmosphere
            
            # 保存氛围数据
            atmo_file = self.runtime_dir / "initial_atmosphere.json"
            with open(atmo_file, "w", encoding="utf-8") as f:
                json.dump(asdict(atmosphere), f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ Vibe 初始化完成")
            logger.info(f"   - 情绪基调: {atmosphere.emotional_tone}")
            logger.info(f"   - 氛围文件: {atmo_file}")
            
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
        for char_id in self.initial_scene.present_characters:
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
        
        # 2. 初始化 Plot 并生成起始场景/剧本
        scene, script = self.init_plot_and_generate_opening()
        
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
            "components": {
                "WS": {
                    "status": "initialized",
                    "file": "world_state.json"
                },
                "Plot": {
                    "status": "initialized",
                    "files": ["initial_scene.json", "initial_script.json"],
                    "opening_location": self.initial_scene.location_name if self.initial_scene else None
                },
                "Vibe": {
                    "status": "initialized",
                    "file": "initial_atmosphere.json",
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
        print("  📖 生成的文件:")
        print(f"     - world_state.json        # WS 初始化的世界状态")
        print(f"     - initial_scene.json      # Plot 生成的起始场景")
        print(f"     - initial_script.json     # Plot 生成的起始剧本")
        print(f"     - initial_atmosphere.json # Vibe 生成的初始氛围")
        print(f"     - init_summary.json       # 初始化摘要")
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

