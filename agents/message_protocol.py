"""
Agent间通信协议定义
定义统一的JSON消息格式，所有Agent通信必须遵循此协议
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """消息类型枚举"""
    # 系统控制消息
    SYSTEM_INIT = "system_init"           # 系统初始化
    SYSTEM_READY = "system_ready"         # 系统就绪
    
    # 用户交互消息
    USER_INPUT = "user_input"             # 用户输入
    USER_OUTPUT = "user_output"           # 输出给用户
    
    # 验证消息
    VALIDATION_REQUEST = "validation_request"   # 请求验证
    VALIDATION_RESPONSE = "validation_response" # 验证结果
    
    # 上下文同步
    CONTEXT_REQUEST = "context_request"   # 请求上下文
    CONTEXT_RESPONSE = "context_response" # 上下文响应
    
    # 决策与指令
    DECISION_REQUEST = "decision_request" # 请求决策
    DECISION_RESPONSE = "decision_response" # 决策响应
    INSTRUCTION = "instruction"           # 执行指令
    
    # 内容生成
    GENERATION_REQUEST = "generation_request"   # 请求生成内容
    GENERATION_RESPONSE = "generation_response" # 生成的内容
    
    # 错误处理
    ERROR = "error"                       # 错误消息
    WARNING = "warning"                   # 警告消息


class AgentRole(str, Enum):
    """Agent角色枚举"""
    # 离线构建
    GENESIS_GROUP = "genesis_group"       # 创世组（大中正+Demiurge+许劭）
    
    # 第一层
    OS = "os"                            # 信息中枢
    LOGIC = "logic"                      # 逻辑审查官
    
    # 第二层（光明会）
    WORLD_STATE = "ws"          # 世界状态运行者
    PLOT = "plot"                        # 命运编织者
    VIBE = "vibe"                        # 氛围感受者
    
    # 第三层
    NPC = "npc"                          # NPC角色
    
    # 用户
    USER = "user"                        # 用户
    SYSTEM = "system"                    # 系统


class Message(BaseModel):
    """标准消息格式"""
    
    # 基础字段
    message_id: str = Field(description="消息唯一ID")
    from_agent: AgentRole = Field(description="发送者")
    to_agent: AgentRole = Field(description="接收者")
    message_type: MessageType = Field(description="消息类型")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    # 内容字段
    payload: Dict[str, Any] = Field(default_factory=dict, description="消息载荷")
    
    # 元数据
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")
    
    class Config:
        use_enum_values = True


class ValidationResult(BaseModel):
    """验证结果数据结构"""
    is_valid: bool = Field(description="是否通过验证")
    errors: List[str] = Field(default_factory=list, description="错误列表")
    warnings: List[str] = Field(default_factory=list, description="警告列表")
    validated_content: Optional[str] = Field(default=None, description="验证后的内容")


class WorldContext(BaseModel):
    """世界上下文数据结构"""
    current_time: str = Field(description="当前游戏时间")
    current_location: str = Field(description="当前位置ID")
    present_characters: List[str] = Field(description="在场角色ID列表")
    recent_events: List[Dict[str, Any]] = Field(description="最近发生的事件")
    world_state: Dict[str, Any] = Field(description="世界状态快照")


class PlotInstruction(BaseModel):
    """剧情指令数据结构"""
    instruction_id: str = Field(description="指令ID")
    target_agent: AgentRole = Field(description="目标Agent")
    action: str = Field(description="要执行的动作")
    parameters: Dict[str, Any] = Field(description="动作参数")
    priority: int = Field(default=5, description="优先级1-10")


class GeneratedContent(BaseModel):
    """生成的内容数据结构"""
    content_type: str = Field(description="内容类型：description/dialogue/action")
    content: str = Field(description="生成的文本内容")
    character_id: Optional[str] = Field(default=None, description="相关角色ID")
    emotion: Optional[str] = Field(default=None, description="情绪标签")


# 便捷函数

def create_message(
    from_agent: AgentRole,
    to_agent: AgentRole,
    message_type: MessageType,
    payload: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None
) -> Message:
    """
    创建消息的便捷函数
    
    Args:
        from_agent: 发送者
        to_agent: 接收者
        message_type: 消息类型
        payload: 消息载荷
        metadata: 元数据（可选）
    
    Returns:
        Message对象
    """
    import uuid
    
    message_id = f"{from_agent.value}_{to_agent.value}_{uuid.uuid4().hex[:8]}"
    
    return Message(
        message_id=message_id,
        from_agent=from_agent,
        to_agent=to_agent,
        message_type=message_type,
        payload=payload,
        metadata=metadata or {}
    )


def create_validation_request(
    from_agent: AgentRole,
    content: str,
    context: Optional[Dict[str, Any]] = None
) -> Message:
    """创建验证请求消息"""
    return create_message(
        from_agent=from_agent,
        to_agent=AgentRole.LOGIC,
        message_type=MessageType.VALIDATION_REQUEST,
        payload={
            "content": content,
            "context": context or {}
        }
    )


def create_validation_response(
    is_valid: bool,
    errors: List[str] = None,
    warnings: List[str] = None,
    validated_content: Optional[str] = None
) -> Message:
    """创建验证响应消息"""
    result = ValidationResult(
        is_valid=is_valid,
        errors=errors or [],
        warnings=warnings or [],
        validated_content=validated_content
    )
    
    return create_message(
        from_agent=AgentRole.LOGIC,
        to_agent=AgentRole.OS,
        message_type=MessageType.VALIDATION_RESPONSE,
        payload=result.dict()
    )

