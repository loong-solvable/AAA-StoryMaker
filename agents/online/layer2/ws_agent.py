"""
世界状态运行者 (World State Manager)
仿真引擎，负责模拟时间流逝、NPC状态、离屏事件
"""
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from utils.llm_factory import get_llm
from utils.logger import setup_logger
from config.settings import settings
from agents.message_protocol import Message, AgentRole, MessageType

logger = setup_logger("WorldState", "world_state.log")


class WorldStateManager:
    """
    世界状态运行者Agent
    模拟整个世界的动态运行
    """
    
    def __init__(self, genesis_data: Dict[str, Any]):
        """
        初始化世界状态运行者
        
        Args:
            genesis_data: Genesis世界数据
        """
        logger.info("🌍 初始化世界状态运行者...")
        
        # LLM实例
        self.llm = get_llm(temperature=0.7)
        
        # Genesis数据
        self.genesis_data = genesis_data
        self.world_info = genesis_data.get("world", {})
        self.characters = genesis_data.get("characters", [])
        self.locations = genesis_data.get("locations", [])
        self.plot_hints = genesis_data.get("plot_hints", [])
        
        # 加载提示词
        self.system_prompt = self._load_system_prompt()
        
        # 构建链
        self.chain = self._build_chain()
        
        # 当前世界状态
        self.current_time = self._parse_initial_time()
        self.npc_states: Dict[str, Dict[str, Any]] = {}
        self.triggered_plots: List[str] = []
        self.world_events: List[Dict[str, Any]] = []
        
        # 初始化NPC状态
        self._initialize_npc_states()
        
        logger.info("✅ 世界状态运行者初始化完成")
        logger.info(f"   - 追踪NPC数量: {len(self.npc_states)}")
        logger.info(f"   - 初始时间: {self.current_time}")
    
    def _load_system_prompt(self) -> str:
        """加载系统提示词"""
        prompt_file = settings.PROMPTS_DIR / "online" / "ws_system.txt"
        
        with open(prompt_file, "r", encoding="utf-8") as f:
            return f.read()
    
    def _build_chain(self):
        """构建处理链"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human", """请更新世界状态：

【当前世界信息】
世界：{world_name}
当前时间：{current_time}
当前天气：{weather}

【玩家行动】
行动：{player_action}
位置：{player_location}
预计耗时：{time_cost}

【当前NPC状态】
{npc_states}

【已触发剧情】
{triggered_plots}

请计算时间流逝后的世界状态，返回JSON格式。""")
        ])
        
        return prompt | self.llm | StrOutputParser()
    
    def _parse_initial_time(self) -> str:
        """解析初始时间"""
        world_start = self.genesis_data.get("world_start_context", {})
        # 根据建议时间生成具体时间
        suggested_time = world_start.get("suggested_time", "下午")
        time_map = {
            "早晨": "08:00",
            "上午": "10:00",
            "中午": "12:00",
            "下午": "15:00",
            "傍晚": "18:00",
            "晚上": "20:00",
            "深夜": "23:00"
        }
        time_str = time_map.get(suggested_time, "15:00")
        return f"2024-11-26 {time_str}"
    
    def _initialize_npc_states(self):
        """初始化所有NPC的状态"""
        world_start = self.genesis_data.get("world_start_context", {})
        key_chars = world_start.get("key_characters", [])
        suggested_loc = world_start.get("suggested_location", "loc_001")
        
        # 智能初始化：关键角色在建议位置，其他角色根据特征合理分配
        for char in self.characters:
            char_id = char.get("id")

            # 玩家由真人控制，不纳入仿真 NPC 状态
            if char_id == "user":
                continue
            
            # 确定初始位置和活动
            if char_id in key_chars:
                init_location = suggested_loc
                init_activity = self._infer_activity_from_location(char, suggested_loc)
            else:
                init_location = self._infer_location_from_traits(char)
                init_activity = self._infer_activity_from_location(char, init_location)
            
            self.npc_states[char_id] = {
                "name": char.get("name"),
                "current_location": init_location,
                "current_activity": init_activity,
                "mood": "平静",
                "schedule": []
            }
        
        logger.info(f"✅ 初始化了 {len(self.npc_states)} 个NPC的状态")
    
    def _infer_location_from_traits(self, char: Dict[str, Any]) -> str:
        """根据角色特征推断合理的初始位置"""
        traits = char.get("traits", [])
        possessions = char.get("possessions", [])
        
        # 简单的特征→位置映射逻辑
        if any("CEO" in t or "老板" in t or "总裁" in t for t in traits):
            # 查找办公楼类型的位置
            for loc in self.locations:
                if "公司" in loc.get("name", "") or "办公" in loc.get("name", ""):
                    return loc.get("id", "loc_001")
        
        if any("记者" in t or "调查" in t for t in traits):
            # 查找咖啡厅或公共场所
            for loc in self.locations:
                if "咖啡" in loc.get("name", "") or "餐厅" in loc.get("name", ""):
                    return loc.get("id", "loc_001")
        
        if any("工程师" in t or "程序员" in t or "技术" in t for t in traits):
            # 查找家/工作室
            for loc in self.locations:
                if "公寓" in loc.get("name", "") or "家" in loc.get("name", ""):
                    return loc.get("id", "loc_001")
        
        # 默认返回第一个位置
        return self.locations[0].get("id", "loc_001") if self.locations else "loc_001"
    
    def _infer_activity_from_location(self, char: Dict[str, Any], location_id: str) -> str:
        """根据角色特征和位置推断当前活动"""
        # 查找位置信息
        location = None
        for loc in self.locations:
            if loc.get("id") == location_id:
                location = loc
                break
        
        if not location:
            return "日常活动"
        
        loc_name = location.get("name", "")
        traits = char.get("traits", [])
        
        # 简单的位置→活动映射
        if "公司" in loc_name or "办公" in loc_name:
            return "处理公司事务"
        elif "咖啡" in loc_name:
            if any("记者" in t for t in traits):
                return "整理调查资料"
            return "享用咖啡"
        elif "公寓" in loc_name or "家" in loc_name:
            if any("工程师" in t or "程序员" in t for t in traits):
                return "远程工作"
            return "休息"
        elif "街道" in loc_name:
            return "行走"
        else:
            return "日常活动"
    
    def update_world_state(
        self,
        player_action: str,
        player_location: str,
        time_cost: int = 10
    ) -> Dict[str, Any]:
        """
        根据玩家行动更新世界状态
        
        Args:
            player_action: 玩家的行动描述
            player_location: 玩家所在位置ID
            time_cost: 行动耗时（分钟）
        
        Returns:
            世界状态更新结果
        """
        logger.info(f"🔄 更新世界状态: {player_action[:30]}...")
        
        # 构建NPC状态描述
        npc_states_str = self._format_npc_states()
        
        # 调用LLM
        try:
            response = self.chain.invoke({
                "world_name": self.world_info.get("title", "未知世界"),
                "current_time": self.current_time,
                "weather": "晴朗",  # 简化处理
                "player_action": player_action,
                "player_location": player_location,
                "time_cost": f"{time_cost}分钟",
                "npc_states": npc_states_str,
                "triggered_plots": ", ".join(self.triggered_plots) if self.triggered_plots else "无"
            })
            
            # 解析结果
            update_data = self._parse_update_result(response)
            
            # 应用更新
            self._apply_updates(update_data, time_cost)
            
            logger.info(f"✅ 世界状态更新完成")
            logger.info(f"   - 新时间: {self.current_time}")
            logger.info(f"   - NPC更新: {len(update_data.get('npc_updates', []))}")
            logger.info(f"   - 离屏事件: {len(update_data.get('offscreen_events', []))}")
            
            return update_data
            
        except Exception as e:
            logger.error(f"❌ 世界状态更新失败: {e}", exc_info=True)
            # 返回最小更新
            return self._create_minimal_update(time_cost)
    
    def _format_npc_states(self) -> str:
        """格式化NPC状态为文本"""
        lines = []
        for npc_id, state in self.npc_states.items():
            lines.append(
                f"- {state['name']} ({npc_id}): "
                f"位置={state['current_location']}, "
                f"活动={state['current_activity']}, "
                f"心情={state['mood']}"
            )
        return "\n".join(lines) if lines else "无NPC"
    
    def _parse_update_result(self, response: str) -> Dict[str, Any]:
        """解析LLM返回的更新结果"""
        # 清理markdown
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        
        try:
            data = json.loads(response)
            return data
        except json.JSONDecodeError as e:
            logger.error(f"❌ 解析世界状态更新失败: {e}")
            logger.error(f"原始响应: {response[:200]}...")
            return {}
    
    def _apply_updates(self, update_data: Dict[str, Any], time_cost: int):
        """应用世界状态更新"""
        # 更新时间
        if "timestamp" in update_data:
            self.current_time = update_data["timestamp"]
        else:
            # 手动推进时间
            try:
                dt = datetime.strptime(self.current_time, "%Y-%m-%d %H:%M")
                dt += timedelta(minutes=time_cost)
                self.current_time = dt.strftime("%Y-%m-%d %H:%M")
            except:
                pass
        
        # 更新NPC状态
        for npc_update in update_data.get("npc_updates", []):
            npc_id = npc_update.get("npc_id")
            if npc_id in self.npc_states:
                self.npc_states[npc_id].update({
                    "current_location": npc_update.get("current_location", self.npc_states[npc_id]["current_location"]),
                    "current_activity": npc_update.get("current_activity", self.npc_states[npc_id]["current_activity"]),
                    "mood": npc_update.get("mood", self.npc_states[npc_id]["mood"])
                })
        
        # 记录离屏事件
        for event in update_data.get("offscreen_events", []):
            self.world_events.append(event)
        
        # 记录潜在的剧情发展（仅供Plot Agent参考，不触发硬编码分支）
        plot_developments = update_data.get("potential_plot_developments", [])
        if plot_developments:
            logger.debug(f"💡 潜在剧情发展: {plot_developments}")
    
    def _create_minimal_update(self, time_cost: int) -> Dict[str, Any]:
        """创建最小更新（出错时使用）"""
        try:
            dt = datetime.strptime(self.current_time, "%Y-%m-%d %H:%M")
            dt += timedelta(minutes=time_cost)
            new_time = dt.strftime("%Y-%m-%d %H:%M")
        except:
            new_time = self.current_time
        
        return {
            "timestamp": new_time,
            "time_passed": f"{time_cost}分钟",
            "npc_updates": [],
            "offscreen_events": [],
            "environment_changes": [],
            "potential_plot_developments": []
        }
    
    def get_npc_state(self, npc_id: str) -> Optional[Dict[str, Any]]:
        """获取指定NPC的状态"""
        return self.npc_states.get(npc_id)
    
    def get_context_summary(self) -> Dict[str, Any]:
        """获取世界上下文摘要"""
        return {
            "current_time": self.current_time,
            "npc_states": self.npc_states,
            "triggered_plots": self.triggered_plots,
            "recent_events": self.world_events[-5:] if self.world_events else []
        }

    def get_state_snapshot(self) -> Dict[str, Any]:
        """用于持久化的完整状态快照"""
        snapshot = dict(self.get_context_summary())
        snapshot.update(
            {
                "world_events_count": len(self.world_events),
                "triggered_plots_count": len(self.triggered_plots),
                "last_event": self.world_events[-1] if self.world_events else None,
            }
        )
        return snapshot
    
    def handle_message(self, message: Message) -> Optional[Message]:
        """处理消息（OS接口）"""
        if message.message_type == MessageType.CONTEXT_REQUEST:
            # 返回世界上下文
            from agents.message_protocol import create_message
            
            return create_message(
                from_agent=AgentRole.WORLD_STATE,
                to_agent=message.from_agent,
                message_type=MessageType.CONTEXT_RESPONSE,
                payload=self.get_context_summary()
            )
        
        return None
