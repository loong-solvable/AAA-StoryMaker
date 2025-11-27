"""
信息中枢 (OS - Operating System)
系统的总线与路由器，负责Agent间消息传递和全局状态管理
"""
import json
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path
from datetime import datetime
from utils.logger import setup_logger
from config.settings import settings
from agents.message_protocol import (
    Message, AgentRole, MessageType, WorldContext
)

logger = setup_logger("OS", "os.log")


class OperatingSystem:
    """
    信息中枢 - 游戏的操作系统
    非LLM Agent，纯逻辑组件
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
        
        # 消息队列
        self.message_queue: List[Message] = []
        self.message_handlers: Dict[AgentRole, Callable] = {}
        
        # 加载Genesis数据
        if genesis_path:
            self.load_genesis(genesis_path)
        
        logger.info("✅ 信息中枢OS初始化完成")
    
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

