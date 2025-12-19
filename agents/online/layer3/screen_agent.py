"""
荧幕层 Agent (Screen Layer Agent)
系统的"渲染引擎"和"视觉翻译官"

核心职责：
1. 数据清洗：过滤中间件日志，提取纯净的剧情内容
2. 视觉翻译：将抽象的文学描述转化为具体的视觉 Prompt
3. 双流输出：
   - 人流 (Human-Readable)：面向开发者的实时、干净的终端剧本流
   - 机流 (Machine-Readable)：面向媒体生成 AI 的结构化 JSON 数据流
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from utils.llm_factory import get_llm
from utils.logger import setup_logger
from config.settings import settings

logger = setup_logger("Screen", "screen.log")


# ==========================================
# 数据模型
# ==========================================

class DialogueEntry(BaseModel):
    """对话条目"""
    speaker: str
    speaker_id: str = ""
    content: str
    action: str = ""
    emotion: str = ""
    target: str = "everyone"


class ScreenInput(BaseModel):
    """Screen Agent 输入数据"""
    scene_id: int
    turn_id: int = 0
    timestamp: str = ""
    
    # 剧情数据
    dialogue_log: List[Dict[str, Any]] = []
    current_action: Optional[Dict[str, Any]] = None
    
    # 世界状态
    world_state: Dict[str, Any] = {}
    
    # 氛围数据 (预留接口)
    vibe_data: Optional[Dict[str, Any]] = None
    
    # 角色外观数据
    characters_in_scene: List[Dict[str, Any]] = []


class ScreenAgent:
    """
    荧幕层 Agent
    负责终端渲染和视觉翻译
    """
    
    # 终端颜色代码
    COLORS = {
        "RESET": "\033[0m",
        "BOLD": "\033[1m",
        "DIM": "\033[2m",
        "CYAN": "\033[36m",      # 场景头
        "YELLOW": "\033[33m",    # 角色名
        "GREEN": "\033[32m",     # 玩家
        "GRAY": "\033[90m",      # 动作/旁白
        "WHITE": "\033[97m",     # 台词
        "MAGENTA": "\033[35m",   # 环境描述
    }
    
    def __init__(self, runtime_dir: Optional[Path] = None, world_name: str = ""):
        """
        初始化荧幕层 Agent
        
        Args:
            runtime_dir: 运行时数据目录
            world_name: 世界名称
        """
        logger.info("🎬 初始化荧幕层 Agent...")
        
        self.runtime_dir = runtime_dir
        self.world_name = world_name
        
        # 初始化 LLM（用于视觉翻译）
        self.llm = get_llm(temperature=0.7)
        
        # 加载提示词
        self.system_prompt = self._load_system_prompt()
        
        # 构建处理链
        self.chain = self._build_chain()
        
        # 确保 screen 输出目录存在
        if runtime_dir:
            self.screen_dir = runtime_dir / "screen"
            self.screen_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.screen_dir = None
        
        # 渲染历史（用于去重）
        self.render_history: List[str] = []
        
        logger.info("✅ 荧幕层 Agent 初始化完成")
    
    def _load_system_prompt(self) -> str:
        """加载系统提示词"""
        prompt_file = settings.PROMPTS_DIR / "online" / "screen_system.txt"
        
        if not prompt_file.exists():
            logger.warning(f"⚠️ 提示词文件不存在: {prompt_file}")
            return ""
        
        with open(prompt_file, "r", encoding="utf-8") as f:
            template = f.read()
        
        # 转义花括号
        template = template.replace("{", "{{").replace("}", "}}")
        
        return template
    
    def _build_chain(self):
        """构建 LLM 处理链"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human", """请将以下剧情片段转化为视觉渲染数据：

【场景概要】
{scene_summary}

【环境信息】
地点：{location}
时间：{time_of_day}
天气：{weather}

【当前动作】
角色：{speaker}
台词：{content}
动作：{action}
情绪：{emotion}

【在场角色】
{characters_info}

请输出符合 JSON Schema 的视觉渲染数据。""")
        ])
        
        return prompt | self.llm | StrOutputParser()
    
    # ==========================================
    # 功能模块一：终端渲染 (Human-Readable)
    # ==========================================
    
    def render_scene_header(self, scene_id: int, location_name: str = "", description: str = ""):
        """
        渲染场景头
        
        Args:
            scene_id: 幕次
            location_name: 地点名称
            description: 环境描述
        """
        c = self.COLORS
        
        print()
        print(f"{c['CYAN']}{c['BOLD']}{'=' * 60}{c['RESET']}")
        print(f"{c['CYAN']}{c['BOLD']}  第 {scene_id} 幕：{location_name}{c['RESET']}")
        print(f"{c['CYAN']}{'=' * 60}{c['RESET']}")
        
        if description:
            print(f"{c['MAGENTA']}[环境] {description}{c['RESET']}")
        
        print()
    
    def render_dialogue(self, entry: Dict[str, Any], is_player: bool = False):
        """
        渲染单条对话
        
        Args:
            entry: 对话数据 (speaker, content, action, emotion)
            is_player: 是否是玩家
        """
        c = self.COLORS
        
        speaker = entry.get("speaker", entry.get("character_name", "???"))
        content = entry.get("content", entry.get("dialogue", ""))
        action = entry.get("action", "")
        
        # 选择颜色
        name_color = c['GREEN'] if is_player else c['YELLOW']
        
        # 格式化动作
        action_str = f" {c['GRAY']}({action}){c['RESET']}" if action else ""
        
        # 打印
        print(f"{name_color}{c['BOLD']}[{speaker}]{c['RESET']}:{action_str} {c['WHITE']}{content}{c['RESET']}")
    
    def render_narration(self, text: str):
        """
        渲染旁白/叙述
        
        Args:
            text: 旁白文本
        """
        c = self.COLORS
        print(f"{c['DIM']}{c['GRAY']}【旁白】{text}{c['RESET']}")
    
    def render_to_terminal(self, input_data: ScreenInput):
        """
        将输入数据渲染到终端（人流输出）
        
        这是主要的终端渲染入口，会清洗数据并格式化输出
        
        Args:
            input_data: ScreenInput 数据
        """
        # 渲染场景头（如果有新场景）
        ws = input_data.world_state
        location = ws.get("location", {})
        
        # 渲染当前动作
        if input_data.current_action:
            action = input_data.current_action
            is_player = action.get("speaker_id", "") == "user" or action.get("speaker", "") == "玩家"
            self.render_dialogue(action, is_player=is_player)
    
    def render_dialogue_log(self, dialogue_log: List[Dict[str, Any]]):
        """
        渲染完整的对话记录
        
        Args:
            dialogue_log: 对话记录列表
        """
        for entry in dialogue_log:
            speaker_id = entry.get("speaker_id", "")
            is_player = speaker_id == "user"
            self.render_dialogue(entry, is_player=is_player)
    
    # ==========================================
    # 功能模块二：视觉翻译 (Machine-Readable)
    # ==========================================
    
    def translate_to_visual(self, input_data: ScreenInput) -> Dict[str, Any]:
        """
        将输入数据翻译为视觉渲染数据（机流输出）
        
        调用 LLM 将文本转化为 AI 可理解的视觉语言
        
        Args:
            input_data: ScreenInput 数据
            
        Returns:
            视觉渲染数据 JSON
        """
        logger.info("🎨 执行视觉翻译...")
        
        # 准备输入参数
        ws = input_data.world_state
        location = ws.get("location", {})
        current_action = input_data.current_action or {}
        
        # 格式化角色信息
        characters_info = self._format_characters_info(input_data.characters_in_scene)
        
        try:
            response = self.chain.invoke({
                "scene_summary": self._generate_scene_summary(input_data),
                "location": location.get("name", "未知地点") + " - " + location.get("description", ""),
                "time_of_day": ws.get("time_of_day", ""),
                "weather": ws.get("weather", ""),
                "speaker": current_action.get("speaker", ""),
                "content": current_action.get("content", ""),
                "action": current_action.get("action", ""),
                "emotion": current_action.get("emotion", ""),
                "characters_info": characters_info
            })
            
            # 解析响应
            visual_data = self._parse_visual_response(response)
            if not visual_data:
                logger.warning("⚠️ 视觉解析为空，使用兜底模板")
                return self._create_fallback_visual_data(input_data)
            
            # 添加元数据
            result = {
                "meta": {
                    "world_name": self.world_name,
                    "scene_id": input_data.scene_id,
                    "turn_id": input_data.turn_id,
                    "timestamp": input_data.timestamp or datetime.now().isoformat()
                },
                "visual_render_data": visual_data
            }
            
            logger.info("✅ 视觉翻译完成")
            return result
            
        except Exception as e:
            logger.error(f"❌ 视觉翻译失败: {e}", exc_info=True)
            return self._create_fallback_visual_data(input_data)
    
    def _format_characters_info(self, characters: List[Dict[str, Any]]) -> str:
        """格式化角色信息"""
        if not characters:
            return "无角色信息"
        
        lines = []
        for char in characters:
            name = char.get("name", "未知")
            appearance = char.get("appearance", char.get("current_appearance", "外观未知"))
            is_focus = char.get("is_focus", False)
            focus_tag = " [焦点]" if is_focus else ""
            lines.append(f"- {name}{focus_tag}: {appearance}")
        
        return "\n".join(lines)
    
    def _generate_scene_summary(self, input_data: ScreenInput) -> str:
        """生成场景概要"""
        ws = input_data.world_state
        location = ws.get("location", {}).get("name", "未知地点")
        
        # 从对话日志中提取关键信息
        if input_data.dialogue_log:
            speakers = list(set([d.get("speaker", "") for d in input_data.dialogue_log if d.get("speaker")]))
            return f"在{location}，{', '.join(speakers[:3])}等人的对话场景"
        
        return f"在{location}的场景"
    
    def _parse_visual_response(self, response: str) -> Dict[str, Any]:
        """解析 LLM 的视觉翻译响应"""
        response = response.strip()
        
        # 清理 markdown 代码块
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        
        try:
            data = json.loads(response)
            # 如果返回的是完整结构，提取 visual_render_data
            if "visual_render_data" in data:
                return data["visual_render_data"]
            return data
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON 解析失败: {e}")
            logger.error(f"原始响应: {response[:300]}...")
            return {}
    
    def _create_fallback_visual_data(self, input_data: ScreenInput) -> Dict[str, Any]:
        """创建兜底的视觉数据（解析失败时使用）"""
        ws = input_data.world_state
        location = ws.get("location", {})
        current_action = input_data.current_action or {}
        dialogue_text = current_action.get("content", "")
        action_text = current_action.get("action", "")
        
        return {
            "meta": {
                "world_name": self.world_name,
                "scene_id": input_data.scene_id,
                "turn_id": input_data.turn_id,
                "timestamp": datetime.now().isoformat()
            },
            "visual_render_data": {
                "summary": f"{location.get('name', '未知地点')} 的场景",
                "environment": {
                    "location": location.get("name", "未知"),
                    "lighting": "自然光，基础布光",
                    "weather": ws.get("weather", "晴朗"),
                    "composition": "中景构图"
                },
                "characters_in_shot": [
                    {
                        "name": current_action.get("speaker", ""),
                        "visual_tags": "",
                        "pose": "",
                        "expression": current_action.get("emotion", ""),
                        "dialogue": dialogue_text,
                        "action": action_text,
                        "screen_position": "center"
                    }
                ] if current_action else [],
                "media_prompts": {
                    "image_gen_prompt": f"{location.get('name', '一个场景')} 的镜头，电影质感，8k，写实",
                    "video_gen_script": "镜头对准当前场景，缓慢推进。",
                    "negative_prompt": "text, watermark, low quality, blurry, bad anatomy"
                }
            }
        }
    
    # ==========================================
    # 功能模块三：数据持久化
    # ==========================================
    
    def save_visual_data(self, visual_data: Dict[str, Any], scene_id: int, turn_id: int = 0):
        """
        保存视觉渲染数据到 JSON 文件
        
        Args:
            visual_data: 视觉渲染数据
            scene_id: 场景ID
            turn_id: 对话轮次
        """
        if not self.screen_dir:
            logger.warning("⚠️ 未设置 runtime_dir，跳过数据保存")
            return
        
        # 按场景保存
        filename = f"scene_{scene_id:03d}.json"
        filepath = self.screen_dir / filename
        
        # 如果文件存在，追加到 turns 数组
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
            
            # 追加新的 turn
            if "turns" not in existing_data:
                existing_data["turns"] = []
            
            visual_data["meta"]["turn_id"] = turn_id
            existing_data["turns"].append(visual_data)
            
            # 更新最新状态
            existing_data["latest"] = visual_data
            
            data_to_save = existing_data
        else:
            # 新文件
            data_to_save = {
                "scene_id": scene_id,
                "created_at": datetime.now().isoformat(),
                "latest": visual_data,
                "turns": [visual_data]
            }
        
        # 保存
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 视觉数据已保存: {filepath}")
    
    # ==========================================
    # 主入口
    # ==========================================
    
    def render(
        self,
        input_data: ScreenInput,
        render_terminal: bool = True,
        generate_visual: bool = True,
        save_json: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        主渲染入口 - 执行完整的渲染流程
        
        Args:
            input_data: 输入数据
            render_terminal: 是否渲染到终端
            generate_visual: 是否生成视觉数据
            save_json: 是否保存 JSON
            
        Returns:
            视觉渲染数据（如果 generate_visual=True）
        """
        visual_data = None
        
        # 1. 终端渲染（实时）
        if render_terminal:
            self.render_to_terminal(input_data)
        
        # 2. 视觉翻译（可选）
        if generate_visual:
            visual_data = self.translate_to_visual(input_data)
            
            # 3. 数据持久化（可选）
            if save_json and visual_data:
                self.save_visual_data(
                    visual_data, 
                    scene_id=input_data.scene_id,
                    turn_id=input_data.turn_id
                )
        
        return visual_data
    
    def render_single_dialogue(
        self,
        speaker: str,
        content: str,
        action: str = "",
        emotion: str = "",
        is_player: bool = False
    ):
        """
        便捷方法：渲染单条对话到终端
        
        Args:
            speaker: 说话者
            content: 台词内容
            action: 动作描述
            emotion: 情绪
            is_player: 是否是玩家
        """
        entry = {
            "speaker": speaker,
            "content": content,
            "action": action,
            "emotion": emotion
        }
        self.render_dialogue(entry, is_player=is_player)


# ==========================================
# 便捷函数
# ==========================================

def create_screen_agent(runtime_dir: Path, world_name: str = "") -> ScreenAgent:
    """
    创建 Screen Agent 实例的便捷函数
    
    Args:
        runtime_dir: 运行时目录
        world_name: 世界名称
        
    Returns:
        ScreenAgent 实例
    """
    return ScreenAgent(runtime_dir=runtime_dir, world_name=world_name)
