"""
信息中枢 (OS - Operating System)

核心职能：
1. 剧本拆分：接收 Plot（命运编织者）产出的完整剧本
2. 智能分发：将剧本拆解为每个演员（NPC Agent）的专属小剧本
3. 消息路由：将小剧本分发给对应的演员 Agent
4. 状态管理：维护游戏全局状态和世界上下文
5. 角色初始化：动态初始化首次出场的角色Agent

数据流：
    Plot (完整剧本)
        │
        ▼
    OS (信息中枢)
        │ 解析剧本、提取角色戏份
        │
        ├─→ NPC-A 的小剧本 → NPC-A Agent
        ├─→ NPC-B 的小剧本 → NPC-B Agent
        └─→ NPC-C 的小剧本 → NPC-C Agent
"""
import json
import re
import importlib.util
import shutil
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from utils.logger import setup_logger
from utils.llm_factory import get_llm
from config.settings import settings
from agents.message_protocol import (
    Message, AgentRole, MessageType, WorldContext
)

logger = setup_logger("OS", "os.log")


@dataclass
class ActorScript:
    """
    演员小剧本 - 分发给单个 NPC Agent 的戏份
    """
    character_id: str           # 角色ID
    character_name: str         # 角色名称
    scene_context: str          # 场景上下文（简短描述当前场景）
    dialogue_lines: List[str]   # 该角色的台词列表
    action_directions: List[str] # 该角色的行为指示
    emotion_hint: str           # 情绪提示（如：愤怒、紧张、平静）
    interaction_targets: List[str] # 互动对象（其他在场角色ID）
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "character_id": self.character_id,
            "character_name": self.character_name,
            "scene_context": self.scene_context,
            "dialogue_lines": self.dialogue_lines,
            "action_directions": self.action_directions,
            "emotion_hint": self.emotion_hint,
            "interaction_targets": self.interaction_targets
        }


@dataclass 
class ParsedScript:
    """
    解析后的完整剧本结构
    """
    scene_description: str      # 场景描述
    involved_characters: List[str]  # 参与角色ID列表
    actor_scripts: Dict[str, ActorScript]  # 各角色的小剧本
    narrative_text: str         # 旁白/叙述文本
    plot_hints: List[str]       # Plot 给出的剧情提示


class OperatingSystem:
    """
    信息中枢 - 游戏的操作系统
    
    核心职责：
    1. 剧本拆分：将 Plot 的完整剧本拆分为各演员的小剧本
    2. 消息分发：将小剧本分发给对应的 NPC Agent
    3. 状态管理：维护游戏全局状态
    """
    
    def __init__(self, genesis_path: Optional[Path] = None):
        """
        初始化信息中枢
        
        Args:
            genesis_path: Genesis.json文件路径
        """
        logger.info("🖥️  初始化信息中枢OS...")
        
        # 全局状态
        self.genesis_data: Optional[Dict[str, Any]] = None
        self.world_context: Optional[WorldContext] = None
        self.game_history: List[Dict[str, Any]] = []
        self.turn_count: int = 0
        
        # Agent注册表
        self.registered_agents: Dict[AgentRole, Any] = {}
        self.npc_agents: Dict[str, Any] = {}  # character_id -> NPC Agent
        
        # 消息队列
        self.message_queue: List[Message] = []
        self.message_handlers: Dict[AgentRole, Callable] = {}
        self.npc_handlers: Dict[str, Callable] = {}  # character_id -> handler
        
        # LLM 实例（用于剧本拆分等智能任务）
        self.llm = get_llm(temperature=0.7)
        
        # 加载Genesis数据
        if genesis_path:
            self.load_genesis(genesis_path)
        
        logger.info("✅ 信息中枢OS初始化完成")
    
    # ==========================================
    # 剧本拆分与分发（核心功能）
    # ==========================================
    
    def parse_script(self, plot_script: Dict[str, Any]) -> ParsedScript:
        """
        解析 Plot 产出的完整剧本
        
        Args:
            plot_script: Plot Agent 产出的剧本数据
                expected format:
                {
                    "scene": "场景描述",
                    "characters": ["char_id_1", "char_id_2"],
                    "actions": [
                        {"character": "char_id", "action": "行为", "dialogue": "台词", "emotion": "情绪"}
                    ],
                    "narrative": "旁白文本",
                    "hints": ["剧情提示"]
                }
        
        Returns:
            ParsedScript: 解析后的剧本结构
        """
        logger.info("📜 开始解析Plot剧本...")
        
        scene_description = plot_script.get("scene", "")
        involved_characters = plot_script.get("characters", [])
        actions = plot_script.get("actions", [])
        narrative = plot_script.get("narrative", "")
        hints = plot_script.get("hints", [])
        
        # 为每个角色创建小剧本
        actor_scripts: Dict[str, ActorScript] = {}
        
        for char_id in involved_characters:
            # 获取角色名称
            char_data = self.get_character_data(char_id)
            char_name = char_data.get("name", char_id) if char_data else char_id
            
            # 提取该角色的所有行动
            char_actions = [a for a in actions if a.get("character") == char_id]
            
            # 构建小剧本
            dialogue_lines = [a.get("dialogue", "") for a in char_actions if a.get("dialogue")]
            action_directions = [a.get("action", "") for a in char_actions if a.get("action")]
            emotion_hint = char_actions[0].get("emotion", "平静") if char_actions else "平静"
            
            # 互动对象（除自己外的其他在场角色）
            interaction_targets = [c for c in involved_characters if c != char_id]
            
            actor_scripts[char_id] = ActorScript(
                character_id=char_id,
                character_name=char_name,
                scene_context=scene_description,
                dialogue_lines=dialogue_lines,
                action_directions=action_directions,
                emotion_hint=emotion_hint,
                interaction_targets=interaction_targets
            )
            
            logger.info(f"   📝 {char_name}: {len(dialogue_lines)}条台词, {len(action_directions)}个行为")
        
        parsed = ParsedScript(
            scene_description=scene_description,
            involved_characters=involved_characters,
            actor_scripts=actor_scripts,
            narrative_text=narrative,
            plot_hints=hints
        )
        
        logger.info(f"✅ 剧本解析完成: {len(involved_characters)}个角色参与")
        return parsed
    
    def dispatch_script(self, parsed_script: ParsedScript) -> Dict[str, Any]:
        """
        将解析后的剧本分发给各个 NPC Agent
        
        Args:
            parsed_script: 解析后的剧本
        
        Returns:
            Dict: 各角色的响应结果
            {
                "character_id": {
                    "success": bool,
                    "response": Any,
                    "error": str (if failed)
                }
            }
        """
        logger.info(f"📤 开始分发剧本给 {len(parsed_script.actor_scripts)} 个演员...")
        
        results: Dict[str, Any] = {}
        
        for char_id, actor_script in parsed_script.actor_scripts.items():
            logger.info(f"   🎭 分发给 {actor_script.character_name}...")
            
            try:
                # 检查是否有注册的 NPC handler
                if char_id in self.npc_handlers:
                    handler = self.npc_handlers[char_id]
                    response = handler(actor_script.to_dict())
                    results[char_id] = {
                        "success": True,
                        "response": response,
                        "character_name": actor_script.character_name
                    }
                    logger.info(f"   ✅ {actor_script.character_name} 收到剧本")
                else:
                    # 没有注册的handler，创建消息放入队列
                    msg = Message(
                        from_agent=AgentRole.OS,
                        to_agent=AgentRole.NPC,
                        message_type=MessageType.SCRIPT,
                        content=actor_script.to_dict(),
                        context={"character_id": char_id}
                    )
                    self.message_queue.append(msg)
                    results[char_id] = {
                        "success": True,
                        "response": None,
                        "character_name": actor_script.character_name,
                        "note": "消息已入队，等待NPC Agent处理"
                    }
                    logger.info(f"   📬 {actor_script.character_name} 的剧本已入队")
                    
            except Exception as e:
                logger.error(f"   ❌ 分发给 {actor_script.character_name} 失败: {e}")
                results[char_id] = {
                    "success": False,
                    "error": str(e),
                    "character_name": actor_script.character_name
                }
        
        success_count = sum(1 for r in results.values() if r["success"])
        logger.info(f"✅ 剧本分发完成: {success_count}/{len(results)} 成功")
        
        return results
    
    def process_plot_output(self, plot_script: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理 Plot 的完整输出（解析 + 分发一站式）
        
        Args:
            plot_script: Plot Agent 产出的剧本
        
        Returns:
            处理结果，包含旁白文本和各角色响应
        """
        logger.info("🎬 处理Plot输出...")
        
        # 1. 解析剧本
        parsed = self.parse_script(plot_script)
        
        # 2. 分发给各演员
        dispatch_results = self.dispatch_script(parsed)
        
        # 3. 返回综合结果
        return {
            "narrative": parsed.narrative_text,
            "scene": parsed.scene_description,
            "actor_results": dispatch_results,
            "hints": parsed.plot_hints
        }
    
    def register_npc_handler(self, character_id: str, handler: Callable):
        """
        注册 NPC 消息处理器
        
        Args:
            character_id: 角色ID
            handler: 处理函数，接收 ActorScript dict，返回响应
        """
        self.npc_handlers[character_id] = handler
        logger.info(f"✅ 注册NPC处理器: {character_id}")
    
    def register_npc_agent(self, character_id: str, agent_instance: Any):
        """
        注册 NPC Agent 实例
        
        Args:
            character_id: 角色ID
            agent_instance: NPC Agent实例
        """
        self.npc_agents[character_id] = agent_instance
        logger.info(f"✅ 注册NPC Agent: {character_id}")
    
    # ==========================================
    # 基础消息路由功能
    # ==========================================
    
    def load_genesis(self, genesis_path: Path):
        """加载Genesis世界数据"""
        logger.info(f"📖 加载Genesis数据: {genesis_path}")
        
        if not genesis_path.exists():
            logger.error(f"❌ Genesis文件不存在: {genesis_path}")
            raise FileNotFoundError(f"Genesis文件不存在: {genesis_path}")
        
        with open(genesis_path, "r", encoding="utf-8") as f:
            self.genesis_data = json.load(f)
        
        logger.info(f"✅ Genesis数据加载成功")
        logger.info(f"   - 世界: {self.genesis_data.get('world', {}).get('title')}")
        logger.info(f"   - 角色数: {len(self.genesis_data.get('characters', []))}")
        logger.info(f"   - 地点数: {len(self.genesis_data.get('locations', []))}")
        
        # 初始化世界上下文
        self._initialize_world_context()
    
    def _initialize_world_context(self):
        """初始化世界上下文"""
        if not self.genesis_data:
            logger.warning("⚠️  未加载Genesis数据，无法初始化世界上下文")
            return
        
        world_start = self.genesis_data.get("world_start_context", {})
        
        self.world_context = WorldContext(
            current_time=world_start.get("suggested_time", "下午"),
            current_location=world_start.get("suggested_location", "loc_001"),
            present_characters=world_start.get("key_characters", []),
            recent_events=[],
            world_state={
                "turn": 0,
                "game_started": False
            }
        )
        
        logger.info("✅ 世界上下文初始化完成")
    
    def register_agent(self, role: AgentRole, agent_instance: Any):
        """
        注册Agent
        
        Args:
            role: Agent角色
            agent_instance: Agent实例
        """
        self.registered_agents[role] = agent_instance
        logger.info(f"✅ 注册Agent: {role.value}")
    
    def register_handler(self, role: AgentRole, handler: Callable):
        """
        注册消息处理器
        
        Args:
            role: Agent角色
            handler: 处理函数
        """
        self.message_handlers[role] = handler
        logger.info(f"✅ 注册消息处理器: {role.value}")
    
    def route_message(self, message: Message) -> Optional[Message]:
        """
        路由消息到目标Agent
        
        Args:
            message: 要路由的消息
        
        Returns:
            Agent的响应消息（如果有）
        """
        logger.info(f"📨 路由消息: {message.from_agent.value} → {message.to_agent.value} ({message.message_type.value})")
        
        # 记录消息
        self.message_queue.append(message)
        
        # 查找目标Agent的处理器
        target_role = message.to_agent
        
        if target_role not in self.message_handlers:
            logger.warning(f"⚠️  未找到Agent处理器: {target_role.value}")
            return None
        
        # 调用处理器
        handler = self.message_handlers[target_role]
        try:
            response = handler(message)
            
            if response:
                logger.info(f"✅ 收到响应: {response.from_agent.value} → {response.to_agent.value}")
            
            return response
        except Exception as e:
            logger.error(f"❌ 消息处理失败: {e}", exc_info=True)
            return None
    
    def broadcast_message(self, message: Message, target_roles: List[AgentRole]) -> List[Message]:
        """
        广播消息到多个Agent
        
        Args:
            message: 要广播的消息
            target_roles: 目标Agent列表
        
        Returns:
            所有响应消息列表
        """
        logger.info(f"📢 广播消息到 {len(target_roles)} 个Agent")
        
        responses = []
        for role in target_roles:
            # 创建副本并修改目标
            msg_copy = message.copy()
            msg_copy.to_agent = role
            
            response = self.route_message(msg_copy)
            if response:
                responses.append(response)
        
        return responses
    
    # ==========================================
    # 状态管理功能
    # ==========================================
    
    def get_world_context(self) -> Optional[WorldContext]:
        """获取当前世界上下文"""
        return self.world_context
    
    def update_world_context(self, updates: Dict[str, Any]):
        """
        更新世界上下文
        
        Args:
            updates: 要更新的字段
        """
        if not self.world_context:
            logger.warning("⚠️  世界上下文未初始化")
            return
        
        for key, value in updates.items():
            if hasattr(self.world_context, key):
                setattr(self.world_context, key, value)
                logger.info(f"✅ 更新世界上下文: {key} = {value}")
    
    def get_character_data(self, character_id: str) -> Optional[Dict[str, Any]]:
        """获取角色数据"""
        if not self.genesis_data:
            return None
        
        characters = self.genesis_data.get("characters", [])
        for char in characters:
            if char.get("id") == character_id:
                return char
        
        return None
    
    def get_location_data(self, location_id: str) -> Optional[Dict[str, Any]]:
        """获取地点数据"""
        if not self.genesis_data:
            return None
        
        locations = self.genesis_data.get("locations", [])
        for loc in locations:
            if loc.get("id") == location_id:
                return loc
        
        return None
    
    def add_to_history(self, event: Dict[str, Any]):
        """
        添加事件到游戏历史
        
        Args:
            event: 事件数据
        """
        event["timestamp"] = datetime.now().isoformat()
        event["turn"] = self.turn_count
        
        self.game_history.append(event)
        
        # 更新最近事件（只保留最近5条）
        if self.world_context:
            self.world_context.recent_events.append(event)
            if len(self.world_context.recent_events) > 5:
                self.world_context.recent_events.pop(0)
    
    def next_turn(self):
        """进入下一回合"""
        self.turn_count += 1
        logger.info(f"🔄 进入回合 #{self.turn_count}")
        
        if self.world_context:
            self.world_context.world_state["turn"] = self.turn_count
    
    def get_game_state(self) -> Dict[str, Any]:
        """获取完整的游戏状态"""
        return {
            "turn": self.turn_count,
            "world_context": self.world_context.dict() if self.world_context else None,
            "history_count": len(self.game_history),
            "registered_agents": [role.value for role in self.registered_agents.keys()],
            "registered_npcs": list(self.npc_agents.keys()),
            "message_count": len(self.message_queue)
        }
    
    def save_game_state(self, save_path: Optional[Path] = None):
        """
        保存游戏状态
        
        Args:
            save_path: 保存路径（可选）
        """
        if not save_path:
            save_path = settings.DATA_DIR / "saves" / f"save_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        state = {
            "genesis_data": self.genesis_data,
            "world_context": self.world_context.dict() if self.world_context else None,
            "game_history": self.game_history,
            "turn_count": self.turn_count
        }
        
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 游戏状态已保存: {save_path}")
    
    def shutdown(self):
        """关闭系统"""
        logger.info("🛑 信息中枢OS关闭中...")
        
        # 保存最终状态
        if self.turn_count > 0:
            self.save_game_state()
        
        logger.info("✅ 信息中枢OS已关闭")
    
    # ==========================================
    # 角色动态初始化功能
    # ==========================================
    
    def initialize_first_appearance_characters(
        self,
        runtime_dir: Path,
        world_dir: Path
    ) -> Dict[str, Any]:
        """
        初始化首次出场的角色
        
        读取 current_scene.json 中 first_appearance=true 的角色，
        为每个角色生成专属提示词文件和 agent.py 文件，并初始化 Agent 实例。
        
        Args:
            runtime_dir: 运行时目录路径，如 data/runtime/江城市_20251128_183246
            world_dir: 世界数据目录路径，如 data/worlds/江城市
        
        Returns:
            Dict: 初始化结果
            {
                "initialized": [{"id": "npc_001", "name": "林晨", "agent_file": "...", "prompt_file": "..."}],
                "failed": [{"id": "npc_003", "error": "..."}],
                "skipped": [{"id": "npc_002", "reason": "already initialized"}]
            }
        """
        logger.info("🎭 开始初始化首次出场角色...")
        
        results = {
            "initialized": [],
            "failed": [],
            "skipped": []
        }
        
        # 1. 读取 current_scene.json
        scene_file = runtime_dir / "plot" / "current_scene.json"
        if not scene_file.exists():
            logger.error(f"❌ 场景文件不存在: {scene_file}")
            return {"error": f"场景文件不存在: {scene_file}"}
        
        with open(scene_file, "r", encoding="utf-8") as f:
            scene_data = json.load(f)
        
        present_characters = scene_data.get("present_characters", [])
        
        # 2. 筛选 first_appearance=true 的角色
        first_appearance_chars = [
            char for char in present_characters 
            if char.get("first_appearance", False)
        ]
        
        logger.info(f"📋 发现 {len(first_appearance_chars)} 个首次出场角色")
        
        # 3. 为每个角色进行初始化
        for char_info in first_appearance_chars:
            char_id = char_info.get("id")
            char_name = char_info.get("name", char_id)
            
            logger.info(f"   🎭 初始化角色: {char_name} ({char_id})")
            
            try:
                result = self._initialize_single_character(
                    char_id=char_id,
                    char_name=char_name,
                    world_dir=world_dir
                )
                
                if result.get("success"):
                    results["initialized"].append({
                        "id": char_id,
                        "name": char_name,
                        "agent_file": result.get("agent_file"),
                        "prompt_file": result.get("prompt_file")
                    })
                    logger.info(f"   ✅ {char_name} 初始化成功")
                else:
                    results["failed"].append({
                        "id": char_id,
                        "name": char_name,
                        "error": result.get("error")
                    })
                    logger.error(f"   ❌ {char_name} 初始化失败: {result.get('error')}")
                    
            except Exception as e:
                results["failed"].append({
                    "id": char_id,
                    "name": char_name,
                    "error": str(e)
                })
                logger.error(f"   ❌ {char_name} 初始化异常: {e}", exc_info=True)
        
        logger.info(f"✅ 角色初始化完成: 成功 {len(results['initialized'])}, 失败 {len(results['failed'])}")
        return results
    
    def _initialize_single_character(
        self,
        char_id: str,
        char_name: str,
        world_dir: Path
    ) -> Dict[str, Any]:
        """
        初始化单个角色
        
        Args:
            char_id: 角色ID，如 "npc_001"
            char_name: 角色名称，如 "林晨"
            world_dir: 世界数据目录
        
        Returns:
            初始化结果
        """
        # 1. 读取角色卡文件
        character_file = world_dir / "characters" / f"character_{char_id}.json"
        if not character_file.exists():
            return {"success": False, "error": f"角色卡文件不存在: {character_file}"}
        
        with open(character_file, "r", encoding="utf-8") as f:
            character_data = json.load(f)
        
        # 2. 检查提示词模板是否存在
        template_file = settings.PROMPTS_DIR / "online" / "npc_system.txt"
        if not template_file.exists():
            return {"success": False, "error": f"提示词模板不存在: {template_file}"}
        
        # 3. 生成专属 agent.py 文件（包含角色数据）
        agent_file = self._generate_character_agent(
            char_id=char_id,
            char_name=char_name,
            character_data=character_data
        )
        
        # prompt_file 现在使用通用模板
        prompt_file = template_file
        
        # 5. 动态加载并注册 Agent
        agent_instance = self._load_and_register_agent(
            char_id=char_id,
            char_name=char_name,
            agent_file=agent_file,
            character_data=character_data
        )
        
        return {
            "success": True,
            "agent_file": str(agent_file),
            "prompt_file": str(prompt_file),
            "agent_instance": agent_instance
        }
    
    def _generate_character_prompt(
        self,
        char_id: str,
        char_name: str,
        character_data: Dict[str, Any],
        prompt_template: str
    ) -> Path:
        """
        生成角色专属提示词文件
        
        Args:
            char_id: 角色ID
            char_name: 角色名称
            character_data: 角色卡数据
            prompt_template: 提示词模板
        
        Returns:
            生成的提示词文件路径
        """
        # 格式化角色卡为可读文本
        character_card = self._format_character_card(character_data)
        
        # 填充模板中的占位符
        # 模板使用 {id}, {id_character}, {id_script} 等占位符
        filled_prompt = prompt_template.replace("{id}", char_id)
        filled_prompt = filled_prompt.replace("{id_character}", character_card)
        # {id_script} 会在运行时动态填充，这里保留占位符
        
        # 保存到 prompts/online/ 目录
        prompt_file = settings.PROMPTS_DIR / "online" / f"{char_id}_{char_name}.txt"
        
        with open(prompt_file, "w", encoding="utf-8") as f:
            f.write(filled_prompt)
        
        logger.info(f"   📝 生成提示词文件: {prompt_file.name}")
        return prompt_file
    
    def _format_character_card(self, character_data: Dict[str, Any]) -> str:
        """
        将角色卡数据格式化为可读文本
        
        Args:
            character_data: 角色卡 JSON 数据
        
        Returns:
            格式化后的角色卡文本
        """
        lines = []
        
        # 基本信息
        lines.append(f"【角色ID】{character_data.get('id', '未知')}")
        lines.append(f"【姓名】{character_data.get('name', '未知')}")
        lines.append(f"【性别】{character_data.get('gender', '未知')}")
        lines.append(f"【年龄】{character_data.get('age', '未知')}")
        lines.append(f"【剧情重要性】{character_data.get('importance', 0.5)}")
        
        # 特质
        traits = character_data.get('traits', [])
        if traits:
            lines.append(f"【人物特质】{', '.join(traits)}")
        
        # 行为准则
        behavior_rules = character_data.get('behavior_rules', [])
        if behavior_rules:
            lines.append("【行为准则】")
            for rule in behavior_rules:
                lines.append(f"  - {rule}")
        
        # 人际关系
        relationships = character_data.get('relationship_matrix', {})
        if relationships:
            lines.append("【人际关系】")
            for other_id, rel_info in relationships.items():
                address = rel_info.get('address_as', other_id)
                attitude = rel_info.get('attitude', '未知')
                lines.append(f"  - 对 {address}: {attitude}")
        
        # 持有物品
        possessions = character_data.get('possessions', [])
        if possessions:
            lines.append(f"【持有物品】{', '.join(possessions)}")
        
        # 外貌描述
        appearance = character_data.get('current_appearance', '')
        if appearance:
            lines.append(f"【外貌特征】{appearance}")
        
        # 语音样本
        voice_samples = character_data.get('voice_samples', [])
        if voice_samples:
            lines.append("【典型台词】")
            for sample in voice_samples[:3]:  # 只取前3个样本
                lines.append(f"  「{sample}」")
        
        return "\n".join(lines)
    
    def _generate_character_agent(
        self,
        char_id: str,
        char_name: str,
        character_data: Dict[str, Any]
    ) -> Path:
        """
        生成角色专属 agent.py 文件
        
        Args:
            char_id: 角色ID
            char_name: 角色名称
            character_data: 角色卡数据
        
        Returns:
            生成的 agent.py 文件路径
        """
        # 生成 agent.py 文件内容
        agent_code = self._generate_agent_code(char_id, char_name, character_data)
        
        # 保存到 agents/online/layer3/ 目录
        layer3_dir = Path(__file__).parent.parent / "layer3"
        agent_file = layer3_dir / f"{char_id}_{char_name}.py"
        
        with open(agent_file, "w", encoding="utf-8") as f:
            f.write(agent_code)
        
        logger.info(f"   🐍 生成Agent文件: {agent_file.name}")
        return agent_file
    
    def _generate_agent_code(
        self,
        char_id: str,
        char_name: str,
        character_data: Dict[str, Any]
    ) -> str:
        """
        生成角色 Agent 的 Python 代码
        
        Args:
            char_id: 角色ID
            char_name: 角色名称
            character_data: 角色卡数据
        
        Returns:
            生成的 Python 代码字符串
        """
        # 类名使用驼峰命名（移除下划线，首字母大写）
        class_name = "".join(word.capitalize() for word in char_id.split("_")) + "Agent"
        
        # 格式化角色数据
        traits = ", ".join(character_data.get("traits", []))
        behavior_rules = "; ".join(character_data.get("behavior_rules", []))
        appearance = character_data.get("current_appearance", "未知外貌")
        
        # 格式化人际关系
        relationships_lines = []
        for other_id, rel_info in character_data.get("relationship_matrix", {}).items():
            address = rel_info.get("address_as", other_id)
            attitude = rel_info.get("attitude", "未知")
            relationships_lines.append(f"- 对 {address}({other_id}): {attitude}")
        relationships = "\\n".join(relationships_lines) if relationships_lines else "无已知关系"
        
        # 格式化语音样本
        voice_samples = character_data.get("voice_samples", [])
        voice_samples_str = "\\n".join([f"「{s}」" for s in voice_samples[:5]])
        
        code = f'''"""
{char_name} ({char_id}) - 角色专属Agent
自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from utils.llm_factory import get_llm
from utils.logger import setup_logger
from config.settings import settings

logger = setup_logger("{char_id}", "{char_id}.log")


class {class_name}:
    """
    {char_name} 角色专属Agent
    
    角色ID: {char_id}
    角色名称: {char_name}
    """
    
    CHARACTER_ID = "{char_id}"
    CHARACTER_NAME = "{char_name}"
    PROMPT_FILE = "npc_system.txt"  # 使用通用模板
    
    # 角色静态数据（从角色卡提取）
    CHARACTER_DATA = {{
        "npc_id": "{char_id}",
        "npc_name": "{char_name}",
        "traits": "{traits}",
        "behavior_rules": "{behavior_rules}",
        "appearance": "{appearance}",
        "relationships": """{relationships}""",
        "voice_samples": """{voice_samples_str}"""
    }}
    
    def __init__(self):
        """初始化角色Agent"""
        logger.info(f"🎭 初始化角色Agent: {{self.CHARACTER_NAME}} ({{self.CHARACTER_ID}})")
        
        # LLM实例
        self.llm = get_llm(temperature=0.8)
        
        # 当前动态状态
        self.current_mood = "平静"
        self.current_location = ""
        self.current_activity = ""
        
        # 当前小剧本数据
        self.current_script: Optional[Dict[str, Any]] = None
        
        # 加载提示词模板
        self.prompt_template = self._load_prompt_template()
        
        # 对话历史
        self.dialogue_history: List[Dict[str, str]] = []
        
        logger.info(f"✅ {{self.CHARACTER_NAME}} 初始化完成")
    
    def _load_prompt_template(self) -> str:
        """加载提示词模板"""
        prompt_file = settings.PROMPTS_DIR / "online" / self.PROMPT_FILE
        with open(prompt_file, "r", encoding="utf-8") as f:
            return f.read()
    
    def load_script(self, script_path: Path) -> bool:
        """加载小剧本"""
        try:
            with open(script_path, "r", encoding="utf-8") as f:
                self.current_script = json.load(f)
            logger.info(f"📜 加载小剧本: {{script_path.name}}")
            return True
        except Exception as e:
            logger.error(f"❌ 加载小剧本失败: {{e}}")
            return False
    
    def load_script_from_dict(self, script_data: Dict[str, Any]) -> bool:
        """从字典加载小剧本"""
        self.current_script = script_data
        return True
    
    def _build_prompt(self, current_input: str = "") -> str:
        """构建完整的提示词"""
        mission = self.current_script.get("mission", {{}}) if self.current_script else {{}}
        
        # 格式化对话历史
        history_lines = []
        for entry in self.dialogue_history[-10:]:
            speaker = entry.get("speaker", "未知")
            content = entry.get("content", "")
            history_lines.append(f"【{{speaker}}】: {{content}}")
        if current_input:
            history_lines.append(f"【对方】: {{current_input}}")
        dialogue_history = "\\n".join(history_lines) if history_lines else "（这是对话的开始）"
        
        # 格式化关键话题
        key_topics = mission.get("key_topics", [])
        key_topics_str = ", ".join(key_topics) if isinstance(key_topics, list) else str(key_topics)
        
        # 填充模板
        filled_prompt = self.prompt_template
        for key, value in self.CHARACTER_DATA.items():
            filled_prompt = filled_prompt.replace("{{" + key + "}}", str(value))
        
        script_vars = {{
            "global_context": self.current_script.get("global_context", "未知场景") if self.current_script else "未知场景",
            "scene_summary": self.current_script.get("scene_summary", "未知剧情") if self.current_script else "未知剧情",
            "role_in_scene": mission.get("role_in_scene", "普通参与者"),
            "objective": mission.get("objective", "自然交流"),
            "emotional_arc": mission.get("emotional_arc", "保持平静"),
            "key_topics": key_topics_str,
            "outcome_direction": mission.get("outcome_direction", "自然结束"),
            "special_notes": mission.get("special_notes", "无特殊注意事项"),
            "dialogue_history": dialogue_history
        }}
        for key, value in script_vars.items():
            filled_prompt = filled_prompt.replace("{{" + key + "}}", str(value))
        
        return filled_prompt
    
    def react(
        self,
        current_input: str = "",
        scene_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """对输入做出反应"""
        logger.info(f"🎭 {{self.CHARACTER_NAME}} 正在演绎...")
        
        if scene_context and "script" in scene_context:
            self.load_script_from_dict(scene_context["script"])
        
        filled_prompt = self._build_prompt(current_input)
        escaped_prompt = filled_prompt.replace("{{", "{{{{").replace("}}", "}}}}")
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", escaped_prompt),
            ("human", "请根据以上信息，以角色身份做出反应。输出JSON格式。")
        ])
        
        chain = prompt | self.llm | StrOutputParser()
        
        try:
            response = chain.invoke({{}})
            result = self._parse_response(response)
            
            if current_input:
                self.dialogue_history.append({{"speaker": "对方", "content": current_input}})
            if result.get("content"):
                self.dialogue_history.append({{"speaker": self.CHARACTER_NAME, "content": result["content"]}})
            if result.get("emotion"):
                self.current_mood = result["emotion"]
            
            logger.info(f"✅ {{self.CHARACTER_NAME}} 演绎完成")
            return result
        except Exception as e:
            logger.error(f"❌ {{self.CHARACTER_NAME}} 演绎失败: {{e}}", exc_info=True)
            return self._create_fallback_response()
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """解析LLM响应"""
        result = response.strip()
        if result.startswith("```json"):
            result = result[7:]
        if result.startswith("```"):
            result = result[3:]
        if result.endswith("```"):
            result = result[:-3]
        result = result.strip()
        
        try:
            data = json.loads(result)
            data["character_id"] = self.CHARACTER_ID
            data["character_name"] = self.CHARACTER_NAME
            return data
        except json.JSONDecodeError:
            return {{
                "character_id": self.CHARACTER_ID,
                "character_name": self.CHARACTER_NAME,
                "thought": "（解析失败）",
                "emotion": self.current_mood,
                "action": "",
                "content": result[:200] if result else "...",
                "is_scene_finished": False
            }}
    
    def _create_fallback_response(self) -> Dict[str, Any]:
        """创建后备响应"""
        return {{
            "character_id": self.CHARACTER_ID,
            "character_name": self.CHARACTER_NAME,
            "thought": "（系统异常）",
            "emotion": self.current_mood,
            "action": "沉默了一会儿",
            "content": "嗯...",
            "is_scene_finished": False
        }}
    
    def update_state(self, location: str = None, activity: str = None, mood: str = None):
        """更新角色状态"""
        if location:
            self.current_location = location
        if activity:
            self.current_activity = activity
        if mood:
            self.current_mood = mood
    
    def get_state(self) -> Dict[str, Any]:
        """获取角色当前状态"""
        return {{
            "id": self.CHARACTER_ID,
            "name": self.CHARACTER_NAME,
            "location": self.current_location,
            "activity": self.current_activity,
            "mood": self.current_mood,
            "dialogue_count": len(self.dialogue_history)
        }}
    
    def clear_dialogue_history(self):
        """清空对话历史"""
        self.dialogue_history = []


# 便捷函数：创建Agent实例
def create_agent() -> {class_name}:
    """创建 {char_name} Agent实例"""
    return {class_name}()
'''
        return code
    
    def _load_and_register_agent(
        self,
        char_id: str,
        char_name: str,
        agent_file: Path,
        character_data: Dict[str, Any]
    ) -> Any:
        """
        动态加载并注册 Agent
        
        Args:
            char_id: 角色ID
            char_name: 角色名称
            agent_file: agent.py 文件路径
            character_data: 角色卡数据
        
        Returns:
            Agent 实例
        """
        # 动态导入模块
        spec = importlib.util.spec_from_file_location(
            f"{char_id}_{char_name}",
            agent_file
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # 调用 create_agent 函数创建实例
        agent_instance = module.create_agent()
        
        # 注册到 OS
        self.register_npc_agent(char_id, agent_instance)
        
        # 注册处理器
        self.register_npc_handler(char_id, agent_instance.react)
        
        logger.info(f"   ✅ 注册Agent: {char_id} -> {char_name}")
        return agent_instance
    
    def get_initialized_characters(self) -> List[str]:
        """获取已初始化的角色ID列表"""
        return list(self.npc_agents.keys())
    
    # ==========================================
    # LLM 驱动的剧本拆分功能
    # ==========================================
    
    def dispatch_script_to_actors(self, runtime_dir: Path) -> Dict[str, Any]:
        """
        使用 LLM 将总剧本拆分为各演员的小剧本
        
        读取当前场景、剧本和世界状态，调用 LLM 进行智能拆分，
        然后将各角色的小剧本保存到 npc/ 目录。
        
        Args:
            runtime_dir: 运行时目录路径，如 data/runtime/江城市_20251128_183246
        
        Returns:
            Dict: 拆分结果
            {
                "success": bool,
                "global_context": str,
                "actor_scripts": {npc_id: script_path},
                "archived": [archived_file_paths]
            }
        """
        logger.info("📜 开始拆分剧本...")
        
        results = {
            "success": False,
            "global_context": "",
            "actor_scripts": {},
            "archived": []
        }
        
        try:
            # 1. 读取相关数据文件
            current_scene = self._read_json_file(runtime_dir / "plot" / "current_scene.json")
            current_script = self._read_json_file(runtime_dir / "plot" / "current_script.json")
            world_state = self._read_json_file(runtime_dir / "ws" / "world_state.json")
            
            if not all([current_scene, current_script, world_state]):
                logger.error("❌ 无法读取必要的数据文件")
                results["error"] = "无法读取必要的数据文件"
                return results
            
            # 2. 读取提示词模板
            prompt_template = self._load_script_divider_prompt()
            if not prompt_template:
                results["error"] = "无法加载提示词模板"
                return results
            
            # 3. 调用 LLM 进行剧本拆分
            logger.info("🤖 调用LLM拆分剧本...")
            llm_result = self._call_llm_for_script_division(
                prompt_template=prompt_template,
                current_scene=current_scene,
                current_script=current_script,
                world_state=world_state
            )
            
            if not llm_result:
                results["error"] = "LLM 返回结果为空"
                return results
            
            # 4. 解析 LLM 返回的结果
            parsed_result = self._parse_llm_script_result(llm_result)
            if not parsed_result:
                results["error"] = "无法解析 LLM 返回的结果"
                return results
            
            results["global_context"] = parsed_result.get("global_context", "")
            
            # 5. 确保 npc 目录存在
            npc_dir = runtime_dir / "npc"
            npc_dir.mkdir(parents=True, exist_ok=True)
            history_dir = npc_dir / "history"
            history_dir.mkdir(parents=True, exist_ok=True)
            
            # 6. 为每个角色保存小剧本
            actor_missions = parsed_result.get("actor_missions", {})
            
            for npc_id, mission_data in actor_missions.items():
                logger.info(f"   📝 处理 {npc_id} 的小剧本...")
                
                # 归档旧的小剧本（如果存在）
                archived_path = self._archive_old_script(npc_dir, history_dir, npc_id)
                if archived_path:
                    results["archived"].append(str(archived_path))
                
                # 保存新的小剧本
                script_file = npc_dir / f"{npc_id}_script.json"
                script_data = {
                    "npc_id": npc_id,
                    "character_name": mission_data.get("character_name", npc_id),
                    "global_context": results["global_context"],
                    "scene_summary": parsed_result.get("scene_summary", ""),
                    "mission": mission_data,
                    "created_at": datetime.now().isoformat()
                }
                
                with open(script_file, "w", encoding="utf-8") as f:
                    json.dump(script_data, f, ensure_ascii=False, indent=2)
                
                results["actor_scripts"][npc_id] = str(script_file)
                logger.info(f"   ✅ 保存: {script_file.name}")
            
            results["success"] = True
            logger.info(f"✅ 剧本拆分完成: 为 {len(actor_missions)} 个角色生成小剧本")
            
        except Exception as e:
            logger.error(f"❌ 剧本拆分失败: {e}", exc_info=True)
            results["error"] = str(e)
        
        return results
    
    def _read_json_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """读取 JSON 文件"""
        if not file_path.exists():
            logger.error(f"❌ 文件不存在: {file_path}")
            return None
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"❌ 读取文件失败 {file_path}: {e}")
            return None
    
    def _load_script_divider_prompt(self) -> Optional[str]:
        """加载剧本拆分提示词模板"""
        prompt_file = settings.PROMPTS_DIR / "online" / "script_divider.txt"
        
        if not prompt_file.exists():
            logger.error(f"❌ 提示词文件不存在: {prompt_file}")
            return None
        
        try:
            with open(prompt_file, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"❌ 读取提示词文件失败: {e}")
            return None
    
    def _call_llm_for_script_division(
        self,
        prompt_template: str,
        current_scene: Dict[str, Any],
        current_script: Dict[str, Any],
        world_state: Dict[str, Any]
    ) -> Optional[str]:
        """
        调用 LLM 进行剧本拆分
        
        Args:
            prompt_template: 提示词模板
            current_scene: 当前场景数据
            current_script: 当前剧本数据
            world_state: 世界状态数据
        
        Returns:
            LLM 返回的结果字符串
        """
        try:
            # 将 JSON 数据转为字符串
            scene_str = json.dumps(current_scene, ensure_ascii=False, indent=2)
            script_str = json.dumps(current_script, ensure_ascii=False, indent=2)
            state_str = json.dumps(world_state, ensure_ascii=False, indent=2)
            
            # 填充提示词模板中的占位符
            filled_prompt = prompt_template.replace(
                "{current_scene}", scene_str
            ).replace(
                "{current_script}", script_str
            ).replace(
                "{world_state}", state_str
            )
            
            # 转义 JSON 中的花括号，避免 LangChain 将其识别为变量
            # 将所有的 { 和 } 替换为 {{ 和 }}
            escaped_prompt = filled_prompt.replace("{", "{{").replace("}", "}}")
            
            # 构建 LangChain prompt
            prompt = ChatPromptTemplate.from_messages([
                ("system", escaped_prompt),
                ("human", "请根据以上信息，为每位在场演员生成任务卡。")
            ])
            
            chain = prompt | self.llm | StrOutputParser()
            
            response = chain.invoke({})
            
            logger.info("✅ LLM 返回剧本拆分结果")
            return response
            
        except Exception as e:
            logger.error(f"❌ LLM 调用失败: {e}", exc_info=True)
            return None
    
    def _parse_llm_script_result(self, llm_result: str) -> Optional[Dict[str, Any]]:
        """
        解析 LLM 返回的剧本拆分结果
        
        Args:
            llm_result: LLM 返回的原始字符串
        
        Returns:
            解析后的字典
        """
        # 清理 markdown 代码块标记
        result = llm_result.strip()
        
        # 尝试提取 JSON 块
        # 方法1: 查找 ```json ... ``` 格式
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', result)
        if json_match:
            result = json_match.group(1).strip()
        else:
            # 方法2: 查找 ``` ... ``` 格式
            code_match = re.search(r'```\s*([\s\S]*?)\s*```', result)
            if code_match:
                result = code_match.group(1).strip()
            else:
                # 方法3: 尝试找到第一个 { 和最后一个 } 之间的内容
                first_brace = result.find('{')
                last_brace = result.rfind('}')
                if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
                    result = result[first_brace:last_brace + 1]
        
        try:
            return json.loads(result)
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON 解析失败: {e}")
            logger.error(f"尝试解析的内容前500字符: {result[:500]}...")
            
            # 最后尝试：逐行解析找到有效的 JSON 对象
            try:
                # 找到 { 开始的行
                lines = result.split('\n')
                json_lines = []
                in_json = False
                brace_count = 0
                
                for line in lines:
                    if '{' in line and not in_json:
                        in_json = True
                    
                    if in_json:
                        json_lines.append(line)
                        brace_count += line.count('{') - line.count('}')
                        
                        if brace_count == 0:
                            break
                
                if json_lines:
                    json_str = '\n'.join(json_lines)
                    return json.loads(json_str)
            except:
                pass
            
            return None
    
    def _archive_old_script(
        self,
        npc_dir: Path,
        history_dir: Path,
        npc_id: str
    ) -> Optional[Path]:
        """
        归档旧的小剧本
        
        Args:
            npc_dir: NPC 目录
            history_dir: 历史归档目录
            npc_id: 角色 ID
        
        Returns:
            归档后的文件路径（如果有归档）
        """
        current_script = npc_dir / f"{npc_id}_script.json"
        
        if not current_script.exists():
            return None
        
        # 计算第几幕（通过统计 history 中该角色的历史剧本数量）
        existing_archives = list(history_dir.glob(f"{npc_id}_第*幕剧本.json"))
        act_number = len(existing_archives) + 1
        
        # 归档文件名
        archive_name = f"{npc_id}_第{act_number}幕剧本.json"
        archive_path = history_dir / archive_name
        
        # 移动文件
        shutil.move(str(current_script), str(archive_path))
        
        logger.info(f"   📦 归档: {current_script.name} -> history/{archive_name}")
        return archive_path
    
    def get_actor_script(self, runtime_dir: Path, npc_id: str) -> Optional[Dict[str, Any]]:
        """
        获取指定角色的当前小剧本
        
        Args:
            runtime_dir: 运行时目录
            npc_id: 角色 ID
        
        Returns:
            小剧本数据
        """
        script_file = runtime_dir / "npc" / f"{npc_id}_script.json"
        return self._read_json_file(script_file)
    
    def get_all_actor_scripts(self, runtime_dir: Path) -> Dict[str, Dict[str, Any]]:
        """
        获取所有角色的当前小剧本
        
        Args:
            runtime_dir: 运行时目录
        
        Returns:
            {npc_id: script_data} 字典
        """
        npc_dir = runtime_dir / "npc"
        if not npc_dir.exists():
            return {}
        
        scripts = {}
        for script_file in npc_dir.glob("*_script.json"):
            npc_id = script_file.stem.replace("_script", "")
            script_data = self._read_json_file(script_file)
            if script_data:
                scripts[npc_id] = script_data
        
        return scripts
