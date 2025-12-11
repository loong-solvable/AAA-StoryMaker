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
        # 已废弃！！！这个是不调用llm拆分剧本的逻辑
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
        from_role = message.from_agent
        to_role = message.to_agent
        msg_type = message.message_type

        from_name = getattr(from_role, "value", str(from_role))
        to_name = getattr(to_role, "value", str(to_role))
        type_name = getattr(msg_type, "value", str(msg_type))

        logger.info(f"📨 路由消息: {from_name} → {to_name} ({type_name})")
        
        # 记录消息
        self.message_queue.append(message)
        
        # 查找目标Agent的处理器
        target_role = to_role
        if not isinstance(target_role, AgentRole):
            try:
                target_role = AgentRole(str(target_role))
            except ValueError:
                target_role = None
        
        if target_role is None or target_role not in self.message_handlers:
            logger.warning(f"⚠️  未找到Agent处理器: {to_name}")
            return None
        
        # 调用处理器
        handler = self.message_handlers[target_role]
        try:
            response = handler(message)
            
            if response:
                resp_from = response.from_agent
                resp_to = response.to_agent
                resp_from_name = getattr(resp_from, "value", str(resp_from))
                resp_to_name = getattr(resp_to, "value", str(resp_to))
                logger.info(f"✅ 收到响应: {resp_from_name} → {resp_to_name}")
            
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
        
        # 支持 characters 和 present_characters 两种字段名
        present_characters = scene_data.get("characters", scene_data.get("present_characters", []))
        
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
        # 1. 读取角色卡文件（支持两种命名方式）
        character_file = world_dir / "characters" / f"character_{char_id}.json"
        if not character_file.exists():
            # 尝试另一种命名方式
            character_file = world_dir / "characters" / f"{char_id}.json"
        if not character_file.exists():
            return {"success": False, "error": f"角色卡文件不存在: {character_file}"}
        
        with open(character_file, "r", encoding="utf-8") as f:
            character_data = json.load(f)
        
        # 2. 检查提示词模板是否存在
        template_file = settings.PROMPTS_DIR / "online" / "npc_system.txt"
        if not template_file.exists():
            return {"success": False, "error": f"提示词模板不存在: {template_file}"}
        
        # 3. 生成角色专属提示词文件
        prompt_file = self._generate_npc_prompt_file(
            char_id=char_id,
            char_name=char_name,
            character_data=character_data,
            template_file=template_file
        )
        logger.info(f"   📝 生成提示词文件: {prompt_file.name}")
        
        # 4. 生成专属 agent.py 文件
        agent_file = self._generate_character_agent(
            char_id=char_id,
            char_name=char_name,
            character_data=character_data,
            prompt_file=prompt_file
        )
        
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
    
    def _generate_npc_prompt_file(
        self,
        char_id: str,
        char_name: str,
        character_data: Dict[str, Any],
        template_file: Path
    ) -> Path:
        """
        生成 NPC 角色专属提示词文件
        
        结合角色卡数据和 npc_system.txt 模板，生成专属提示词文件。
        角色相关的占位符（npc_id, npc_name, traits 等）会被填充，
        剧本相关的占位符（global_context, objective 等）保留给运行时填充。
        
        Args:
            char_id: 角色ID
            char_name: 角色名称
            character_data: 角色卡数据
            template_file: 模板文件路径 (npc_system.txt)
        
        Returns:
            生成的提示词文件路径
        """
        # 读取模板
        with open(template_file, "r", encoding="utf-8") as f:
            template = f.read()
        
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
        relationships = "\n".join(relationships_lines) if relationships_lines else "无已知关系"
        
        # 格式化语音样本
        voice_samples = character_data.get("voice_samples", [])
        voice_samples_str = "\n".join([f"「{s}」" for s in voice_samples[:5]])
        
        # 填充角色相关的占位符（这些是静态的，初始化时就确定）
        filled_prompt = template
        filled_prompt = filled_prompt.replace("{npc_id}", char_id)
        filled_prompt = filled_prompt.replace("{npc_name}", char_name)
        filled_prompt = filled_prompt.replace("{traits}", traits)
        filled_prompt = filled_prompt.replace("{behavior_rules}", behavior_rules)
        filled_prompt = filled_prompt.replace("{appearance}", appearance)
        filled_prompt = filled_prompt.replace("{relationships}", relationships)
        filled_prompt = filled_prompt.replace("{voice_samples}", voice_samples_str)
        
        # 剧本相关的占位符保留（运行时动态填充）:
        # {global_context}, {scene_summary}, {role_in_scene}, {objective},
        # {emotional_arc}, {key_topics}, {outcome_direction}, {special_notes},
        # {dialogue_history}
        
        # 确保目录存在
        npc_prompt_dir = settings.PROMPTS_DIR / "online" / "npc_prompt"
        npc_prompt_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存到 prompts/online/npc_prompt/ 目录
        prompt_file = npc_prompt_dir / f"{char_id}_{char_name}_prompt.txt"
        
        with open(prompt_file, "w", encoding="utf-8") as f:
            f.write(filled_prompt)
        
        return prompt_file
    
    def _generate_character_prompt(
        self,
        char_id: str,
        char_name: str,
        character_data: Dict[str, Any],
        prompt_template: str
    ) -> Path:
        """
        生成角色专属提示词文件（已废弃，使用 _generate_npc_prompt_file 代替）
        """
        return self._generate_npc_prompt_file(
            char_id, char_name, character_data,
            settings.PROMPTS_DIR / "online" / "npc_system.txt"
        )
    
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
        character_data: Dict[str, Any],
        prompt_file: Path = None
    ) -> Path:
        """
        生成角色专属 agent.py 文件
        
        Args:
            char_id: 角色ID
            char_name: 角色名称
            character_data: 角色卡数据
            prompt_file: 专属提示词文件路径
        
        Returns:
            生成的 agent.py 文件路径
        """
        # 生成 agent.py 文件内容
        agent_code = self._generate_agent_code(char_id, char_name, character_data, prompt_file)
        
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
        character_data: Dict[str, Any],
        prompt_file: Path = None
    ) -> str:
        """
        生成角色 Agent 的 Python 代码
        
        Args:
            char_id: 角色ID
            char_name: 角色名称
            character_data: 角色卡数据
            prompt_file: 专属提示词文件路径
        
        Returns:
            生成的 Python 代码字符串
        """
        # 类名使用驼峰命名（移除下划线，首字母大写）
        class_name = "".join(word.capitalize() for word in char_id.split("_")) + "Agent"
        
        # 提示词文件名（相对于 prompts/online/npc_prompt/）
        prompt_filename = f"{char_id}_{char_name}_prompt.txt" if prompt_file else "npc_system.txt"
        
        code = f'''"""
{char_name} ({char_id}) - 角色专属Agent
自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

提示词文件: prompts/online/npc_prompt/{prompt_filename}
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
    
    提示词: 从 prompts/online/npc_prompt/{prompt_filename} 读取
    角色数据已预填充到提示词文件中，运行时只需填充剧本相关变量
    """
    
    CHARACTER_ID = "{char_id}"
    CHARACTER_NAME = "{char_name}"
    PROMPT_FILE = "npc_prompt/{prompt_filename}"  # 专属提示词文件
    
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
        
        # 场景记忆板
        self.scene_memory = None
        
        # 加载专属提示词文件（角色数据已预填充）
        self.prompt_template = self._load_prompt_template()
        
        logger.info(f"✅ {{self.CHARACTER_NAME}} 初始化完成")
        logger.info(f"   📝 提示词文件: {{self.PROMPT_FILE}}")
    
    def _load_prompt_template(self) -> str:
        """加载专属提示词文件"""
        prompt_file = settings.PROMPTS_DIR / "online" / self.PROMPT_FILE
        if not prompt_file.exists():
            logger.warning(f"⚠️ 专属提示词文件不存在，使用通用模板: {{prompt_file}}")
            prompt_file = settings.PROMPTS_DIR / "online" / "npc_system.txt"
        with open(prompt_file, "r", encoding="utf-8") as f:
            return f.read()
    
    def bind_scene_memory(self, scene_memory):
        """绑定场景记忆板"""
        self.scene_memory = scene_memory
        logger.info(f"📋 绑定场景记忆板，当前 {{scene_memory.get_dialogue_count()}} 条记录")
    
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
        """
        构建完整的提示词
        
        角色数据已在提示词文件中预填充，这里只需填充剧本相关的动态变量
        """
        mission = self.current_script.get("mission", {{}}) if self.current_script else {{}}
        
        # 从场景记忆板获取对话历史
        if self.scene_memory:
            dialogue_history = self.scene_memory.get_dialogue_for_prompt(limit=10)
        else:
            dialogue_history = "（这是对话的开始）"
        
        # 格式化关键话题
        key_topics = mission.get("key_topics", [])
        key_topics_str = ", ".join(key_topics) if isinstance(key_topics, list) else str(key_topics)
        
        # 只填充剧本相关的动态变量（角色数据已在提示词文件中）
        filled_prompt = self.prompt_template
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
        
        if scene_context:
            if "script" in scene_context:
                self.load_script_from_dict(scene_context["script"])
            if "scene_memory" in scene_context:
                self.bind_scene_memory(scene_context["scene_memory"])
        
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
            
            # 写入场景记忆板
            if self.scene_memory and result.get("content"):
                self.scene_memory.add_dialogue(
                    speaker_id=self.CHARACTER_ID,
                    speaker_name=self.CHARACTER_NAME,
                    content=result.get("content", ""),
                    action=result.get("action", ""),
                    emotion=result.get("emotion", ""),
                    addressing_target=result.get("addressing_target", "everyone")
                )
            
            if result.get("emotion"):
                self.current_mood = result["emotion"]
            
            if result.get("is_scene_finished") and self.scene_memory:
                self.scene_memory.set_scene_status("FINISHED")
            
            logger.info(f"✅ {{self.CHARACTER_NAME}} 演绎完成")
            logger.info(f"   对话对象: {{result.get('addressing_target', 'everyone')}}")
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
            data.setdefault("addressing_target", "everyone")
            data.setdefault("is_scene_finished", False)
            return data
        except json.JSONDecodeError:
            return {{
                "character_id": self.CHARACTER_ID,
                "character_name": self.CHARACTER_NAME,
                "thought": "（解析失败）",
                "emotion": self.current_mood,
                "action": "",
                "content": result[:200] if result else "...",
                "addressing_target": "everyone",
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
            "addressing_target": "everyone",
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
            
            # 5. 获取当前场景ID（用于归档命名）
            scene_id = current_script.get("scene_id", 1) if current_script else 1
            
            # 6. 确保 npc 目录存在
            npc_dir = runtime_dir / "npc"
            npc_dir.mkdir(parents=True, exist_ok=True)
            
            # 7. 为每个角色保存小剧本
            actor_missions = parsed_result.get("actor_missions", {})
            
            for npc_id, mission_data in actor_missions.items():
                char_name = mission_data.get("character_name", npc_id)
                logger.info(f"   📝 处理 {char_name} ({npc_id}) 的小剧本...")
                
                # 创建角色专属目录
                actor_dir = npc_dir / f"{npc_id}_{char_name}"
                actor_dir.mkdir(parents=True, exist_ok=True)
                
                # 归档旧的小剧本（如果存在）
                archived_path = self._archive_old_script(actor_dir, npc_id, char_name, scene_id)
                if archived_path:
                    results["archived"].append(str(archived_path))
                
                # 保存新的小剧本
                script_file = actor_dir / "script.json"
                script_data = {
                    "npc_id": npc_id,
                    "character_name": char_name,
                    "global_context": results["global_context"],
                    "scene_summary": parsed_result.get("scene_summary", ""),
                    "mission": mission_data,
                    "created_at": datetime.now().isoformat()
                }
                
                with open(script_file, "w", encoding="utf-8") as f:
                    json.dump(script_data, f, ensure_ascii=False, indent=2)
                
                results["actor_scripts"][npc_id] = str(script_file)
                logger.info(f"   ✅ 保存: {actor_dir.name}/script.json")
            
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
        actor_dir: Path,
        npc_id: str,
        char_name: str,
        scene_id: int
    ) -> Optional[Path]:
        """
        归档旧的小剧本
        
        Args:
            actor_dir: 角色专属目录
            npc_id: 角色 ID
            char_name: 角色名称
            scene_id: 当前场景ID（用于归档命名）
        
        Returns:
            归档后的文件路径（如果有归档）
        """
        current_script = actor_dir / "script.json"
        
        if not current_script.exists():
            return None
        
        # 创建历史目录
        history_dir = actor_dir / "history"
        history_dir.mkdir(parents=True, exist_ok=True)
        
        # 归档命名：script_scene_001.json
        archive_filename = f"script_scene_{scene_id:03d}.json"
        archive_path = history_dir / archive_filename
        
        # 移动文件
        shutil.move(str(current_script), str(archive_path))
        
        logger.info(f"   📦 归档: script.json -> history/{archive_filename}")
        return archive_path
    
    def get_actor_script(self, runtime_dir: Path, npc_id: str, char_name: str = None) -> Optional[Dict[str, Any]]:
        """
        获取指定角色的当前小剧本
        
        Args:
            runtime_dir: 运行时目录
            npc_id: 角色 ID
            char_name: 角色名称（可选，用于定位目录）
        
        Returns:
            小剧本数据
        """
        # 使用目录结构：npc/{npc_id}_{name}/script.json
        npc_dir = runtime_dir / "npc"
        
        # 尝试匹配目录
        if char_name:
            actor_dir = npc_dir / f"{npc_id}_{char_name}"
            script_file = actor_dir / "script.json"
            if script_file.exists():
                return self._read_json_file(script_file)
        
        # 遍历查找
        if npc_dir.exists():
            for subdir in npc_dir.iterdir():
                if subdir.is_dir() and subdir.name.startswith(f"{npc_id}_"):
                    script_file = subdir / "script.json"
                    if script_file.exists():
                        return self._read_json_file(script_file)
        
        return None
    
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
        for subdir in npc_dir.iterdir():
            if subdir.is_dir() and subdir.name.startswith("npc_"):
                # 提取 npc_id（目录名格式：npc_XXX_角色名）
                parts = subdir.name.split("_", 2)
                if len(parts) >= 2:
                    npc_id = f"{parts[0]}_{parts[1]}"  # npc_001
                    script_file = subdir / "script.json"
                    if script_file.exists():
                        script_data = self._read_json_file(script_file)
                        if script_data:
                            scripts[npc_id] = script_data
        
        return scripts
    
    # ==========================================
    # 对话路由调度功能
    # ==========================================
    
    def route_dialogue(
        self,
        actor_response: Dict[str, Any],
        active_npcs: List[str],
        scene_memory: Any = None
    ) -> Dict[str, Any]:
        """
        根据演员输出路由对话到下一位发言者
        
        Args:
            actor_response: 演员的响应数据（包含 addressing_target 等字段）
            active_npcs: 当前在场的 NPC ID 列表
            scene_memory: 场景记忆板实例（可选）
        
        Returns:
            路由决策结果
            {
                "next_speaker_id": str,  # 下一位发言者ID
                "should_pause_for_user": bool,  # 是否等待玩家
                "is_scene_finished": bool,  # 场景是否结束
                "routing_reason": str  # 路由原因
            }
        """
        logger.info("🎯 开始路由对话...")
        
        addressing_target = actor_response.get("addressing_target", "everyone")
        is_scene_finished = actor_response.get("is_scene_finished", False)
        current_speaker = actor_response.get("character_id", "")
        
        result = {
            "next_speaker_id": None,
            "should_pause_for_user": False,
            "is_scene_finished": is_scene_finished,
            "routing_reason": ""
        }
        
        # 如果场景已结束，不再路由
        if is_scene_finished:
            result["routing_reason"] = "场景已结束"
            logger.info("   🏁 场景已结束，停止路由")
            return result
        
        # 根据 addressing_target 决定下一位
        if addressing_target == "user":
            # 对话对象是玩家，暂停等待
            result["next_speaker_id"] = "user"
            result["should_pause_for_user"] = True
            result["routing_reason"] = "演员指定对话对象为玩家"
            logger.info("   ⏸️ 等待玩家输入")
            
        elif addressing_target in active_npcs:
            # 对话对象是特定 NPC
            result["next_speaker_id"] = addressing_target
            result["routing_reason"] = f"演员指定对话对象为 {addressing_target}"
            logger.info(f"   ➡️ 话筒递给: {addressing_target}")
            
        elif addressing_target == "everyone":
            # 对话对象是所有人，由 OS 裁决
            next_speaker = self._decide_next_speaker(
                current_speaker=current_speaker,
                active_npcs=active_npcs,
                scene_memory=scene_memory
            )
            result["next_speaker_id"] = next_speaker
            result["routing_reason"] = f"OS 裁决下一位发言者为 {next_speaker}"
            logger.info(f"   🎲 OS 裁决: {next_speaker}")
            
        else:
            # 未知的对话对象，尝试匹配
            if addressing_target in active_npcs:
                result["next_speaker_id"] = addressing_target
            else:
                # 默认找一个非当前发言者的 NPC
                candidates = [nid for nid in active_npcs if nid != current_speaker]
                if candidates:
                    result["next_speaker_id"] = candidates[0]
                else:
                    result["should_pause_for_user"] = True
                    result["next_speaker_id"] = "user"
            result["routing_reason"] = f"未知对话对象 {addressing_target}，使用默认逻辑"
            logger.info(f"   ⚠️ 未知对话对象，使用默认: {result['next_speaker_id']}")
        
        return result
    
    def _decide_next_speaker(
        self,
        current_speaker: str,
        active_npcs: List[str],
        scene_memory: Any = None
    ) -> str:
        """
        当 addressing_target 为 everyone 时，裁决下一位发言者
        
        简单策略：选择非当前发言者的第一个 NPC
        高级策略：可以调用 LLM 使用 os_system.txt 提示词进行智能裁决
        
        Args:
            current_speaker: 当前发言者ID
            active_npcs: 在场 NPC 列表
            scene_memory: 场景记忆板
        
        Returns:
            下一位发言者的 ID
        """
        # 排除当前发言者
        candidates = [nid for nid in active_npcs if nid != current_speaker]
        
        if not candidates:
            # 没有其他 NPC，返回玩家
            return "user"
        
        # 简单策略：轮询选择
        # 可以在这里扩展为使用 LLM 进行智能裁决
        return candidates[0]
    
    def route_dialogue_with_llm(
        self,
        actor_response: Dict[str, Any],
        active_npcs: Dict[str, Dict[str, Any]],
        scene_memory: Any = None
    ) -> Dict[str, Any]:
        """
        使用 LLM 进行智能对话路由（当 addressing_target 为 everyone 时）
        
        Args:
            actor_response: 演员的响应数据
            active_npcs: 在场 NPC 信息 {npc_id: {name: str, traits: str}}
            scene_memory: 场景记忆板实例
        
        Returns:
            路由决策结果
        """
        addressing_target = actor_response.get("addressing_target", "everyone")
        
        # 如果不是 everyone，使用简单路由
        if addressing_target != "everyone":
            return self.route_dialogue(
                actor_response,
                list(active_npcs.keys()),
                scene_memory
            )
        
        logger.info("🤖 使用 LLM 进行智能路由...")
        
        try:
            # 加载 OS 提示词
            prompt_file = settings.PROMPTS_DIR / "online" / "os_system.txt"
            if not prompt_file.exists():
                logger.warning("⚠️ os_system.txt 不存在，使用简单路由")
                return self.route_dialogue(
                    actor_response,
                    list(active_npcs.keys()),
                    scene_memory
                )
            
            with open(prompt_file, "r", encoding="utf-8") as f:
                prompt_template = f.read()
            
            # 格式化在场角色列表
            char_list_lines = []
            for npc_id, info in active_npcs.items():
                name = info.get("name", npc_id)
                traits = info.get("traits", "未知")
                char_list_lines.append(f"- {npc_id}: {name} ({traits})")
            active_char_list = "\n".join(char_list_lines)
            
            # 获取最近对话
            recent_dialogue = ""
            if scene_memory:
                recent_dialogue = scene_memory.get_dialogue_for_prompt(limit=5)
            
            # 填充提示词
            last_speaker_id = actor_response.get("character_id", "")
            last_speaker_name = actor_response.get("character_name", "")
            
            filled_prompt = prompt_template.replace(
                "{active_char_list}", active_char_list
            ).replace(
                "{recent_dialogue_log}", recent_dialogue
            ).replace(
                "{last_speaker_id}", last_speaker_id
            ).replace(
                "{last_speaker_name}", last_speaker_name
            ).replace(
                "{addressing_target}", addressing_target
            )
            
            # 转义花括号
            escaped_prompt = filled_prompt.replace("{", "{{").replace("}", "}}")
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", escaped_prompt),
                ("human", "请根据以上信息，决定下一位发言者。")
            ])
            
            chain = prompt | self.llm | StrOutputParser()
            response = chain.invoke({})
            
            # 解析响应
            result = self._parse_routing_response(response, list(active_npcs.keys()))
            
            logger.info(f"✅ LLM 路由决策: {result.get('next_speaker_id')}")
            return result
            
        except Exception as e:
            logger.error(f"❌ LLM 路由失败: {e}", exc_info=True)
            # 回退到简单路由
            return self.route_dialogue(
                actor_response,
                list(active_npcs.keys()),
                scene_memory
            )
    
    def _parse_routing_response(
        self,
        response: str,
        active_npcs: List[str]
    ) -> Dict[str, Any]:
        """解析 LLM 路由响应"""
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
            return {
                "next_speaker_id": data.get("next_speaker_id", active_npcs[0] if active_npcs else "user"),
                "should_pause_for_user": data.get("should_pause_for_user", False),
                "is_scene_finished": data.get("is_scene_finished", False),
                "routing_reason": data.get("analysis", "LLM 裁决")
            }
        except json.JSONDecodeError:
            # 解析失败，使用默认
            return {
                "next_speaker_id": active_npcs[0] if active_npcs else "user",
                "should_pause_for_user": False,
                "is_scene_finished": False,
                "routing_reason": "LLM 响应解析失败，使用默认"
            }
    
    # ==========================================
    # 场景对话循环
    # ==========================================
    
    def run_scene_loop(
        self,
        runtime_dir: Path,
        world_dir: Path,
        max_turns: int = 12,
        user_input_callback = None
    ) -> Dict[str, Any]:
        """
        运行完整的场景对话循环
        
        流程:
        1. 角色演绎 → 保存到场景记忆板 + 传递给 OS
        2. OS 使用 os_system.txt 决定下一位发言者
        3. 如果是 NPC，调用该 NPC 继续演绎
        4. 如果是 user，暂停等待玩家输入
        5. 循环直到 is_scene_finished=true 或达到最大轮数
        
        Args:
            runtime_dir: 运行时数据目录
            world_dir: 世界数据目录
            max_turns: 最大对话轮数
            user_input_callback: 获取玩家输入的回调函数，签名: (prompt: str) -> str
        
        Returns:
            场景执行结果
        """
        from utils.scene_memory import create_scene_memory
        
        logger.info("=" * 60)
        logger.info("🎬 开始场景对话循环")
        logger.info("=" * 60)
        
        # 获取当前场景ID（第几幕）
        current_scene_id = 1
        try:
            script_file = runtime_dir / "plot" / "current_script.json"
            if script_file.exists():
                with open(script_file, "r", encoding="utf-8") as f:
                    script_data = json.load(f)
                    current_scene_id = script_data.get("scene_id", 1)
        except Exception as e:
            logger.warning(f"⚠️ 读取场景ID失败: {e}")
        
        logger.info(f"🎬 当前幕次: 第 {current_scene_id} 幕")
        
        # 创建场景记忆板（使用 scene_id）
        scene_memory = create_scene_memory(runtime_dir, scene_id=current_scene_id)
        
        # === 清理不在场的NPC Agent ===
        scene_file = runtime_dir / "plot" / "current_scene.json"
        if scene_file.exists():
            try:
                with open(scene_file, "r", encoding="utf-8") as f:
                    scene_data = json.load(f)
                
                # 获取应该在场的角色ID列表
                present_chars = scene_data.get("characters", scene_data.get("present_characters", []))
                should_present_ids = {
                    char.get("id") if isinstance(char, dict) else char 
                    for char in present_chars
                }
                
                # 清理不在场的NPC Agent
                if should_present_ids:
                    npcs_to_remove = [
                        npc_id for npc_id in list(self.npc_agents.keys()) 
                        if npc_id not in should_present_ids
                    ]
                    
                    for npc_id in npcs_to_remove:
                        npc_name = self.npc_agents[npc_id].CHARACTER_NAME
                        logger.info(f"🚪 {npc_name} ({npc_id}) 不在本幕场景，移除Agent")
                        del self.npc_agents[npc_id]
            except Exception as e:
                logger.warning(f"⚠️ 读取场景文件失败: {e}")
        
        # 获取在场角色信息
        active_npc_info = {}
        for npc_id, agent in self.npc_agents.items():
            active_npc_info[npc_id] = {
                "name": agent.CHARACTER_NAME,
                "traits": getattr(agent, "CHARACTER_DATA", {}).get("traits", "")
            }
        
        active_npcs = list(self.npc_agents.keys())
        
        if not active_npcs:
            logger.warning("⚠️ 没有在场的 NPC，场景无法进行")
            return {"success": False, "error": "没有在场的 NPC"}
        
        # 为所有 NPC 绑定场景记忆板和加载小剧本
        for npc_id, agent in self.npc_agents.items():
            agent.bind_scene_memory(scene_memory)
            # 使用目录结构：npc/{npc_id}_{name}/script.json
            char_name = agent.CHARACTER_NAME
            actor_dir = runtime_dir / "npc" / f"{npc_id}_{char_name}"
            script_file = actor_dir / "script.json"
            if script_file.exists():
                agent.load_script(script_file)
        
        logger.info(f"👥 在场角色: {[active_npc_info[nid]['name'] for nid in active_npcs]}")
        
        # 选择第一个发言者
        current_speaker_id = active_npcs[0]
        
        turn_count = 0
        scene_finished = False
        dialogue_history = []
        
        # 记录每个角色在当前场景中的发言次数
        actor_turn_counts: Dict[str, int] = {npc_id: 0 for npc_id in active_npcs}
        
        logger.info(f"🎬 场景开始！第一位发言者: {active_npc_info[current_speaker_id]['name']}")
        
        while turn_count < max_turns and not scene_finished:
            turn_count += 1
            logger.info(f"\n{'─' * 40}")
            logger.info(f"【第 {turn_count} 轮对话】")
            
            # 处理玩家输入
            if current_speaker_id == "user":
                logger.info("⏸️ 等待玩家输入...")
                
                if user_input_callback:
                    user_input = user_input_callback("请输入你的回应: ")
                else:
                    user_input = "(玩家沉默)"
                
                if user_input:
                    # 将玩家输入写入场景记忆板
                    scene_memory.add_dialogue(
                        speaker_id="user",
                        speaker_name="玩家",
                        content=user_input,
                        addressing_target="everyone"
                    )
                    dialogue_history.append({
                        "turn": turn_count,
                        "speaker": "user",
                        "content": user_input
                    })
                    logger.info(f"👤 玩家: {user_input}")
                
                # 玩家发言后，选择下一个 NPC 发言
                # 简单策略：选择第一个 NPC
                current_speaker_id = active_npcs[0]
                continue
            
            # NPC 演绎
            if current_speaker_id not in self.npc_agents:
                logger.warning(f"⚠️ 未找到 NPC Agent: {current_speaker_id}")
                current_speaker_id = active_npcs[0] if active_npcs else "user"
                continue
            
            current_agent = self.npc_agents[current_speaker_id]
            speaker_name = current_agent.CHARACTER_NAME
            
            logger.info(f"🎭 {speaker_name} ({current_speaker_id}) 正在演绎...")
            
            # 调用 NPC 演绎
            actor_response = current_agent.react()
            
            # 记录对话历史
            dialogue_history.append({
                "turn": turn_count,
                "speaker": current_speaker_id,
                "speaker_name": speaker_name,
                "response": actor_response
            })
            
            # 更新该角色在当前场景中的发言次数
            actor_turn_counts[current_speaker_id] = actor_turn_counts.get(current_speaker_id, 0) + 1
            turn_in_scene = actor_turn_counts[current_speaker_id]
            
            # 保存到角色专属历史文件（包含 scene_id 和 turn_in_scene）
            self._save_actor_history(
                runtime_dir=runtime_dir,
                actor_id=current_speaker_id,
                actor_name=speaker_name,
                turn=turn_count,
                response=actor_response,
                scene_id=current_scene_id,
                turn_in_scene=turn_in_scene
            )
            
            # 显示演绎结果
            logger.info(f"   💭 {actor_response.get('thought', '')[:50]}...")
            logger.info(f"   😊 情绪: {actor_response.get('emotion', '')}")
            logger.info(f"   💬 台词: {actor_response.get('content', '')[:60]}...")
            logger.info(f"   🎯 对象: {actor_response.get('addressing_target', 'everyone')}")
            logger.info(f"   🏁 结束: {actor_response.get('is_scene_finished', False)}")
            
            # 检查场景是否结束
            if actor_response.get("is_scene_finished"):
                scene_finished = True
                logger.info("🏁 演员标记场景结束！")
                break
            
            # OS 进行路由决策
            logger.info("📨 OS 进行路由决策...")
            
            # 使用 LLM 进行智能路由（当 addressing_target 为 everyone 时）
            addressing_target = actor_response.get("addressing_target", "everyone")
            
            if addressing_target == "everyone":
                # 使用 LLM 智能裁决
                routing_result = self.route_dialogue_with_llm(
                    actor_response=actor_response,
                    active_npcs=active_npc_info,
                    scene_memory=scene_memory
                )
            else:
                # 使用简单路由
                routing_result = self.route_dialogue(
                    actor_response=actor_response,
                    active_npcs=active_npcs,
                    scene_memory=scene_memory
                )
            
            logger.info(f"   ➡️ 路由结果: {routing_result.get('routing_reason')}")
            logger.info(f"   🎯 下一位: {routing_result.get('next_speaker_id')}")
            
            # 更新下一位发言者
            next_speaker = routing_result.get("next_speaker_id")
            
            if routing_result.get("is_scene_finished"):
                scene_finished = True
                logger.info("🏁 OS 判断场景结束！")
                break
            
            if routing_result.get("should_pause_for_user"):
                current_speaker_id = "user"
            elif next_speaker:
                current_speaker_id = next_speaker
            else:
                # 没有下一位，结束
                scene_finished = True
                logger.info("🏁 没有可用的下一位发言者，场景结束")
        
        # 场景结束
        logger.info("\n" + "=" * 60)
        logger.info("🎬 场景对话循环结束")
        logger.info("=" * 60)
        
        if turn_count >= max_turns:
            logger.info(f"⏰ 达到最大轮数限制 ({max_turns})")
        
        # 设置场景状态
        scene_memory.set_scene_status("FINISHED")
        
        # 返回结果
        result = {
            "success": True,
            "total_turns": turn_count,
            "scene_finished": scene_finished,
            "dialogue_count": scene_memory.get_dialogue_count(),
            "dialogue_history": dialogue_history,
            "final_status": scene_memory.get_scene_status()
        }
        
        logger.info(f"📊 总对话轮数: {turn_count}")
        logger.info(f"📊 对话记录数: {scene_memory.get_dialogue_count()}")
        
        return result
    
    def continue_scene_from_user_input(
        self,
        user_input: str,
        scene_memory,
        active_npcs: List[str]
    ) -> Dict[str, Any]:
        """
        从玩家输入继续场景
        
        Args:
            user_input: 玩家的输入
            scene_memory: 场景记忆板
            active_npcs: 在场 NPC 列表
        
        Returns:
            下一步操作信息
        """
        # 将玩家输入写入场景记忆板
        scene_memory.add_dialogue(
            speaker_id="user",
            speaker_name="玩家",
            content=user_input,
            addressing_target="everyone"
        )
        
        logger.info(f"👤 玩家: {user_input}")
        
        # 选择下一个 NPC 响应
        # 可以使用 LLM 来决定谁最适合响应玩家
        if active_npcs:
            next_speaker = active_npcs[0]  # 简单策略：第一个 NPC
        else:
            next_speaker = None
        
        return {
            "next_speaker_id": next_speaker,
            "should_continue": next_speaker is not None
        }
    
    # ==========================================
    # 角色历史演绎记录
    # ==========================================
    
    def _save_actor_history(
        self,
        runtime_dir: Path,
        actor_id: str,
        actor_name: str,
        turn: int,
        response: Dict[str, Any],
        scene_id: int = 1,
        turn_in_scene: int = 1
    ) -> None:
        """
        保存角色的演绎历史
        
        存储位置: data/runtime/{world}/npc/{actor_id}_{name}/history.json
        
        Args:
            runtime_dir: 运行时目录
            actor_id: 角色ID
            actor_name: 角色名称
            turn: 对话轮次（全局）
            response: 角色的演绎响应
            scene_id: 场景ID（第几幕）
            turn_in_scene: 在该场景中的第几次发言
        """
        from datetime import datetime
        
        # 使用目录结构：npc/{actor_id}_{name}/
        actor_dir = runtime_dir / "npc" / f"{actor_id}_{actor_name}"
        actor_dir.mkdir(parents=True, exist_ok=True)
        
        history_file = actor_dir / "history.json"
        
        # 读取现有历史或创建新的
        if history_file.exists():
            with open(history_file, "r", encoding="utf-8") as f:
                history_data = json.load(f)
        else:
            history_data = {
                "actor_id": actor_id,
                "actor_name": actor_name,
                "created_at": datetime.now().isoformat(),
                "performances": []
            }
        
        # 添加本次演绎记录（包含 scene_id 和 turn_in_scene）
        performance = {
            "turn": turn,  # 全局轮次
            "scene_id": scene_id,  # 第几幕
            "turn_in_scene": turn_in_scene,  # 该幕中的第几次发言
            "timestamp": datetime.now().isoformat(),
            "thought": response.get("thought", ""),
            "emotion": response.get("emotion", ""),
            "action": response.get("action", ""),
            "content": response.get("content", ""),
            "addressing_target": response.get("addressing_target", "everyone"),
            "is_scene_finished": response.get("is_scene_finished", False)
        }
        
        history_data["performances"].append(performance)
        history_data["last_updated"] = datetime.now().isoformat()
        history_data["total_performances"] = len(history_data["performances"])
        
        # 保存
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"   📜 保存 {actor_name} 历史: history.json (第{scene_id}幕, 第{turn_in_scene}次发言)")
    
    # ==========================================
    # 幕间处理 (Scene Transition)
    # ==========================================
    
    def process_scene_transition(
        self,
        runtime_dir: Path,
        world_dir: Path,
        scene_memory,
        scene_summary: str = ""
    ) -> Dict[str, Any]:
        """
        幕间处理：一幕结束后，准备下一幕
        
        流程:
        1. 归档当前场景记忆到 all_scene_memory.json
        2. WS 读取场景记忆，更新 world_state.json
        3. Plot 生成下一幕剧本
        
        Args:
            runtime_dir: 运行时目录
            world_dir: 世界数据目录
            scene_memory: 当前幕的场景记忆板
            scene_summary: 本幕剧情摘要（可选）
        
        Returns:
            下一幕准备结果
        """
        from utils.scene_memory import create_all_scene_memory
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("🎭 开始幕间处理")
        logger.info("=" * 60)
        
        result = {
            "success": False,
            "scene_archived": False,
            "world_state_updated": False,
            "next_script_generated": False,
            "next_scene_id": 0
        }
        
        try:
            # 1. 归档当前场景记忆到全剧记事板
            logger.info("📚 步骤1: 归档场景记忆...")
            all_memory = create_all_scene_memory(runtime_dir)
            all_memory.archive_scene(scene_memory, scene_summary)
            result["scene_archived"] = True
            result["next_scene_id"] = all_memory.get_next_scene_id()
            logger.info(f"   ✅ 已归档到全剧记事板，下一幕ID: {result['next_scene_id']}")
            
            # 2. WS 更新 world_state.json
            logger.info("🌍 步骤2: WS 更新世界状态...")
            ws_result = self._update_world_state_from_scene(
                runtime_dir=runtime_dir,
                world_dir=world_dir,
                scene_memory=scene_memory
            )
            result["world_state_updated"] = ws_result.get("success", False)
            if ws_result.get("success"):
                logger.info("   ✅ 世界状态已更新")
            else:
                logger.warning(f"   ⚠️ 世界状态更新失败: {ws_result.get('error')}")
            
            # 3. Plot 生成下一幕剧本
            logger.info("🎬 步骤3: Plot 生成下一幕剧本...")
            plot_result = self._generate_next_scene_script(
                runtime_dir=runtime_dir,
                world_dir=world_dir,
                all_memory=all_memory,
                scene_memory=scene_memory
            )
            result["next_script_generated"] = plot_result.get("success", False)
            if plot_result.get("success"):
                logger.info("   ✅ 下一幕剧本已生成")
            else:
                logger.warning(f"   ⚠️ 剧本生成失败: {plot_result.get('error')}")
            
            result["success"] = (
                result["scene_archived"] and 
                result["world_state_updated"] and 
                result["next_script_generated"]
            )
            
            logger.info("")
            logger.info("=" * 60)
            if result["success"]:
                logger.info("✅ 幕间处理完成，可以开始下一幕")
            else:
                logger.info("⚠️ 幕间处理部分完成")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"❌ 幕间处理失败: {e}", exc_info=True)
            result["error"] = str(e)
        
        return result
    
    def _parse_json_from_llm(self, response: str) -> Optional[Dict[str, Any]]:
        """
        从 LLM 响应中解析 JSON
        
        Args:
            response: LLM 的响应文本
        
        Returns:
            解析后的字典，解析失败返回 None
        """
        result = response.strip()
        
        # 移除 markdown 代码块标记
        if result.startswith("```json"):
            result = result[7:]
        if result.startswith("```"):
            result = result[3:]
        if result.endswith("```"):
            result = result[:-3]
        result = result.strip()
        
        try:
            return json.loads(result)
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON 解析失败: {e}")
            logger.error(f"原始响应前200字符: {result[:200]}...")
            return None
    
    def _update_world_state_from_scene(
        self,
        runtime_dir: Path,
        world_dir: Path,
        scene_memory
    ) -> Dict[str, Any]:
        """
        WS 读取场景记忆板，更新 world_state.json
        """
        try:
            # 读取当前世界状态
            ws_file = runtime_dir / "ws" / "world_state.json"
            with open(ws_file, "r", encoding="utf-8") as f:
                current_world_state = json.load(f)
            
            # 读取世界设定（获取可用地点）
            world_setting_file = world_dir / "world_setting.json"
            with open(world_setting_file, "r", encoding="utf-8") as f:
                world_setting = json.load(f)
            
            # 获取场景记忆
            scene_data = scene_memory.to_dict()
            scene_dialogues = scene_memory.get_dialogue_for_prompt(limit=20)
            
            # 读取 WS 更新提示词
            prompt_file = settings.PROMPTS_DIR / "online" / "ws_update_system.txt"
            with open(prompt_file, "r", encoding="utf-8") as f:
                prompt_template = f.read()
            
            # 填充提示词
            filled_prompt = prompt_template.replace(
                "{current_world_state}", json.dumps(current_world_state, ensure_ascii=False, indent=2)
            ).replace(
                "{scene_memory}", scene_dialogues
            ).replace(
                "{world_setting}", json.dumps(
                    world_setting.get("geography", {}).get("locations", []),
                    ensure_ascii=False, indent=2
                )
            )
            
            # 转义花括号
            escaped_prompt = filled_prompt.replace("{", "{{").replace("}", "}}")
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", escaped_prompt),
                ("human", "请根据场景记录更新世界状态，输出 JSON。")
            ])
            
            chain = prompt | self.llm | StrOutputParser()
            response = chain.invoke({})
            
            # 解析响应
            new_world_state = self._parse_json_from_llm(response)
            
            if new_world_state:
                # 保存更新后的世界状态
                with open(ws_file, "w", encoding="utf-8") as f:
                    json.dump(new_world_state, f, ensure_ascii=False, indent=2)
                
                logger.info(f"   📍 新场景: {new_world_state.get('current_scene', {}).get('location_name', '未知')}")
                
                return {"success": True, "world_state": new_world_state}
            else:
                return {"success": False, "error": "JSON 解析失败"}
            
        except Exception as e:
            logger.error(f"❌ WS 更新失败: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def _archive_plot_files(self, runtime_dir: Path) -> bool:
        """
        归档当前剧本文件到 archive 文件夹
        
        在生成新剧本之前调用，将旧的 current_scene.json 和 current_script.json
        归档到 plot/archive 目录，使用统一的命名规则
        
        Args:
            runtime_dir: 运行时目录
            
        Returns:
            归档是否成功
        """
        import shutil
        
        plot_dir = runtime_dir / "plot"
        archive_dir = plot_dir / "archive"  # 新目录名：archive 而不是 history
        archive_dir.mkdir(parents=True, exist_ok=True)
        
        scene_file = plot_dir / "current_scene.json"
        script_file = plot_dir / "current_script.json"
        
        # 如果没有旧文件，跳过归档
        if not scene_file.exists() and not script_file.exists():
            logger.info("   📂 无旧剧本需要归档")
            return True
        
        # 获取场景ID（从current_script.json或current_scene.json中读取）
        scene_num = 1  # 默认值
        try:
            if script_file.exists():
                with open(script_file, "r", encoding="utf-8") as f:
                    script_data = json.load(f)
                    scene_num = script_data.get("scene_id", 1)
            elif scene_file.exists():
                with open(scene_file, "r", encoding="utf-8") as f:
                    scene_data = json.load(f)
                    scene_num = scene_data.get("scene_id", 1)
        except Exception as e:
            logger.warning(f"   ⚠️ 读取场景ID失败: {e}")
        
        try:
            # 归档 current_scene.json
            if scene_file.exists():
                archive_scene_name = f"scene_{scene_num:03d}.json"
                archive_scene_path = archive_dir / archive_scene_name
                shutil.copy2(scene_file, archive_scene_path)
                logger.info(f"   📁 归档场景: {archive_scene_name}")
            
            # 归档 current_script.json
            if script_file.exists():
                archive_script_name = f"script_{scene_num:03d}.json"
                archive_script_path = archive_dir / archive_script_name
                shutil.copy2(script_file, archive_script_path)
                logger.info(f"   📁 归档剧本: {archive_script_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"   ❌ 归档失败: {e}")
            return False
    
    def _generate_next_scene_script(
        self,
        runtime_dir: Path,
        world_dir: Path,
        all_memory,
        scene_memory
    ) -> Dict[str, Any]:
        """
        Plot 生成下一幕剧本
        """
        try:
            # 归档旧剧本到 history 文件夹
            logger.info("📂 归档旧剧本...")
            self._archive_plot_files(runtime_dir)
            
            # 读取所需数据
            # 1. 角色列表
            characters_file = world_dir / "characters_list.json"
            with open(characters_file, "r", encoding="utf-8") as f:
                characters_list = json.load(f)
            
            # 2. 世界设定
            world_setting_file = world_dir / "world_setting.json"
            with open(world_setting_file, "r", encoding="utf-8") as f:
                world_setting = json.load(f)
            
            # 3. 当前世界状态
            ws_file = runtime_dir / "ws" / "world_state.json"
            with open(ws_file, "r", encoding="utf-8") as f:
                world_state = json.load(f)
            
            # 4. 角色详情
            characters_dir = world_dir / "characters"
            characters_details = []
            if characters_dir.exists():
                for char_file in characters_dir.glob("character_*.json"):
                    with open(char_file, "r", encoding="utf-8") as f:
                        char_data = json.load(f)
                        characters_details.append(
                            f"【{char_data.get('name')}】(ID: {char_data.get('id')})\n"
                            f"  特征: {', '.join(char_data.get('traits', []))}\n"
                            f"  外观: {char_data.get('current_appearance', '无描述')[:100]}"
                        )
            
            # 读取 Plot 提示词
            prompt_file = settings.PROMPTS_DIR / "online" / "plot_system.txt"
            with open(prompt_file, "r", encoding="utf-8") as f:
                prompt_template = f.read()
            
            # 填充提示词
            filled_prompt = prompt_template.replace(
                "{characters_list}", json.dumps(characters_list, ensure_ascii=False, indent=2)
            ).replace(
                "{world_setting}", json.dumps(world_setting, ensure_ascii=False, indent=2)
            ).replace(
                "{world_state}", json.dumps(world_state, ensure_ascii=False, indent=2)
            ).replace(
                "{story_history}", all_memory.get_story_summary(max_scenes=5)
            ).replace(
                "{last_scene_dialogues}", scene_memory.get_dialogue_for_prompt(limit=15)
            ).replace(
                "{characters_details}", "\n\n".join(characters_details)
            ).replace(
                "{user_action}", "（无玩家行动）"
            )
            
            # 转义花括号
            escaped_prompt = filled_prompt.replace("{", "{{").replace("}", "}}")
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", escaped_prompt),
                ("human", f"请生成【第{all_memory.get_next_scene_id()}幕】的导演场记单。")
            ])
            
            chain = prompt | self.llm | StrOutputParser()
            response = chain.invoke({})
            
            # 保存剧本
            script_file = runtime_dir / "plot" / "current_script.json"
            script_data = {
                "scene_id": all_memory.get_next_scene_id(),
                "content": response.strip(),
                "created_at": datetime.now().isoformat()
            }
            with open(script_file, "w", encoding="utf-8") as f:
                json.dump(script_data, f, ensure_ascii=False, indent=2)
            
            # 解析角色登场信息并更新 current_scene.json
            self._parse_and_update_scene_from_plot(runtime_dir, response, world_state)
            
            logger.info(f"   📜 剧本已保存: {script_file.name}")
            
            return {"success": True, "script": response}
            
        except Exception as e:
            logger.error(f"❌ 剧本生成失败: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def _parse_and_update_scene_from_plot(
        self,
        runtime_dir: Path,
        plot_content: str,
        world_state: Dict[str, Any]
    ):
        """
        从 Plot 输出解析角色登场信息，更新 current_scene.json
        
        采用双重策略：
        1. 优先解析明确格式的角色标记（入场/在场/离场）
        2. 兜底：从全文提取所有 npc_xxx ID，确保不遗漏
        
        通过查询已初始化的角色来判断是否首次登场
        """
        import re
        
        present_characters = []
        
        # 获取已初始化的角色列表（用于判断首次登场）
        initialized_chars = set(self.get_initialized_characters())
        
        # 从 genesis.json 获取角色名称映射
        genesis_file = runtime_dir / "genesis.json"
        char_name_map = {}  # {npc_id: name}
        if genesis_file.exists():
            try:
                with open(genesis_file, "r", encoding="utf-8") as f:
                    genesis_data = json.load(f)
                for char in genesis_data.get("characters", []):
                    char_name_map[char.get("id")] = char.get("name", char.get("id"))
            except Exception as e:
                logger.warning(f"⚠️ 读取genesis.json失败: {e}")
        
        # ========== 策略1：解析明确格式的角色标记 ==========
        
        # 解析入场角色（带 First Appearance 标记）
        entry_pattern = r'\*\*入场\*\*:\s*(\S+)\s*\((\w+)\)\s*\[First Appearance:\s*(True|False)\]'
        for match in re.finditer(entry_pattern, plot_content, re.IGNORECASE):
            name, char_id, first_app = match.groups()
            if char_id != "user":  # 跳过玩家
                present_characters.append({
                    "id": char_id,
                    "name": name,
                    "first_appearance": first_app.lower() == "true"
                })
                logger.info(f"      📥 入场: {name} ({char_id}) [首次: {first_app}]")
        
        # 解析离场角色（本幕有戏份，需要参与演绎）
        exit_pattern = r'\*\*离场\*\*:\s*(\S+)\s*\((\w+)\)'
        for match in re.finditer(exit_pattern, plot_content, re.IGNORECASE):
            name, char_id = match.groups()
            if char_id != "user" and not any(c["id"] == char_id for c in present_characters):
                # 判断是否首次登场：不在已初始化列表中就是首次
                is_first = char_id not in initialized_chars
                present_characters.append({
                    "id": char_id,
                    "name": name,
                    "first_appearance": is_first
                })
                logger.info(f"      📤 离场(本幕有戏份): {name} ({char_id}) [首次: {is_first}]")
        
        # ========== 策略2：从全文提取所有 npc_xxx ID（兜底） ==========
        # 这能捕获 LLM 以任意格式提及的角色
        
        all_npc_ids = set(re.findall(r'\b(npc_\d+)\b', plot_content))
        existing_ids = {c["id"] for c in present_characters}
        
        for char_id in all_npc_ids:
            if char_id not in existing_ids:
                # 从名称映射或剧本内容中提取角色名
                char_name = char_name_map.get(char_id)
                if not char_name:
                    # 尝试从剧本中提取：角色名 (npc_xxx)
                    name_match = re.search(rf'(\S+)\s*\({char_id}\)', plot_content)
                    char_name = name_match.group(1) if name_match else char_id
                
                # 判断是否首次登场
                is_first = char_id not in initialized_chars
                present_characters.append({
                    "id": char_id,
                    "name": char_name,
                    "first_appearance": is_first
                })
                logger.info(f"      🔍 发现角色: {char_name} ({char_id}) [首次: {is_first}]")
        
        # 更新 current_scene.json
        current_scene = world_state.get("current_scene", {})
        
        scene_data = {
            "location_id": current_scene.get("location_id", "unknown"),
            "location_name": current_scene.get("location_name", "未知地点"),
            "time_of_day": current_scene.get("time_of_day", "傍晚"),
            "weather": world_state.get("weather", {}).get("condition", "晴朗"),
            "present_characters": present_characters,
            "scene_description": current_scene.get("description", ""),
            "opening_narrative": plot_content[:500]
        }
        
        scene_file = runtime_dir / "plot" / "current_scene.json"
        with open(scene_file, "w", encoding="utf-8") as f:
            json.dump(scene_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"   👥 下一幕角色: {[c['name'] for c in present_characters]}")
