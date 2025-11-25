"""
角色数据模型和工具
数据与逻辑分离：专门处理角色卡JSON数据的解析、验证和格式化
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class CharacterData:
    """
    角色数据模型
    将JSON角色卡数据结构化，提供类型安全和统一的访问接口
    """
    # ==========================================
    # 1. 基础元数据 (Meta Info)
    # ==========================================
    id: str
    name: str
    gender: str = "未知"
    age: str = "未知"
    importance: float = 50.0  # 剧情权重 0-100
    
    # ==========================================
    # 2. 核心特质与逻辑 (Core Identity)
    # ==========================================
    traits: List[str] = field(default_factory=list)  # 身份/性格/状态标签
    behavior_rules: List[str] = field(default_factory=list)  # 行为逻辑准则
    
    # ==========================================
    # 3. 社交矩阵 (Relationship Matrix)
    # ==========================================
    relationship_matrix: Dict[str, Dict[str, str]] = field(default_factory=dict)
    
    # ==========================================
    # 4. 资产与外观 (Assets & Visuals)
    # ==========================================
    possessions: List[str] = field(default_factory=list)
    current_appearance: str = ""
    
    # ==========================================
    # 5. 语言样本 (Mimesis Data)
    # ==========================================
    voice_samples: List[str] = field(default_factory=list)
    
    # ==========================================
    # 6. 初始状态
    # ==========================================
    initial_state: str = "日常活动"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CharacterData':
        """
        从字典创建角色数据对象
        
        Args:
            data: 角色JSON数据
        
        Returns:
            CharacterData对象
        """
        return cls(
            id=data.get("id", "unknown"),
            name=data.get("name", "未命名"),
            gender=data.get("gender", "未知"),
            age=data.get("age", "未知"),
            importance=data.get("importance", 50.0),
            traits=data.get("traits", []),
            behavior_rules=data.get("behavior_rules", []),
            relationship_matrix=data.get("relationship_matrix", {}),
            possessions=data.get("possessions", []),
            current_appearance=data.get("current_appearance", ""),
            voice_samples=data.get("voice_samples", []),
            initial_state=data.get("initial_state", "日常活动")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式
        
        Returns:
            角色数据字典
        """
        return {
            "id": self.id,
            "name": self.name,
            "gender": self.gender,
            "age": self.age,
            "importance": self.importance,
            "traits": self.traits,
            "behavior_rules": self.behavior_rules,
            "relationship_matrix": self.relationship_matrix,
            "possessions": self.possessions,
            "current_appearance": self.current_appearance,
            "voice_samples": self.voice_samples,
            "initial_state": self.initial_state
        }


class CharacterDataFormatter:
    """
    角色数据格式化工具
    将结构化的角色数据格式化为LLM提示词所需的文本格式
    数据格式化逻辑集中管理，修改时只需改这里
    """
    
    @staticmethod
    def format_traits(traits: List[str]) -> str:
        """
        格式化特质标签
        
        Args:
            traits: 特质列表
        
        Returns:
            格式化的特质字符串
        """
        return ", ".join(traits) if traits else "普通人"
    
    @staticmethod
    def format_behavior_rules(behavior_rules: List[str]) -> str:
        """
        格式化行为准则
        
        Args:
            behavior_rules: 行为准则列表
        
        Returns:
            格式化的行为准则字符串（带项目符号）
        """
        if not behavior_rules:
            return "无特殊行为准则"
        
        return "\n".join([f"- {rule}" for rule in behavior_rules])
    
    @staticmethod
    def format_relationship_matrix(relationship_matrix: Dict[str, Dict[str, str]]) -> str:
        """
        格式化社交矩阵
        
        Args:
            relationship_matrix: 关系矩阵字典
                {
                    "target_id": {
                        "address_as": "称呼",
                        "attitude": "态度描述"
                    }
                }
        
        Returns:
            格式化的关系描述字符串
        """
        if not relationship_matrix:
            return "暂无特殊关系"
        
        lines = []
        for target_id, rel_data in relationship_matrix.items():
            address = rel_data.get("address_as", target_id)
            attitude = rel_data.get("attitude", "普通")
            lines.append(f"- {target_id}: 称呼为'{address}', 态度: {attitude}")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_voice_samples(voice_samples: List[str], max_samples: int = 3) -> str:
        """
        格式化语言样本
        
        Args:
            voice_samples: 语言样本列表
            max_samples: 最多显示几个样本
        
        Returns:
            格式化的语言样本字符串
        """
        if not voice_samples:
            return "无语言样本"
        
        samples_to_show = voice_samples[:max_samples]
        return "\n".join([f'"{sample}"' for sample in samples_to_show])
    
    @staticmethod
    def format_possessions(possessions: List[str]) -> str:
        """
        格式化持有物列表
        
        Args:
            possessions: 持有物列表
        
        Returns:
            格式化的持有物字符串
        """
        if not possessions:
            return "无特殊物品"
        
        return "\n".join([f"- {item}" for item in possessions])
    
    @classmethod
    def format_for_prompt(cls, character_data: CharacterData) -> Dict[str, str]:
        """
        将角色数据格式化为提示词模板所需的所有字段
        
        Args:
            character_data: 角色数据对象
        
        Returns:
            格式化后的字段字典，可直接用于.format()
        """
        return {
            "character_name": character_data.name,
            "age": character_data.age,
            "gender": character_data.gender,
            "traits": cls.format_traits(character_data.traits),
            "behavior_rules": cls.format_behavior_rules(character_data.behavior_rules),
            "relationships": cls.format_relationship_matrix(character_data.relationship_matrix),
            "voice_samples": cls.format_voice_samples(character_data.voice_samples),
        }


def validate_character_data(data: Dict[str, Any]) -> tuple[bool, List[str]]:
    """
    验证角色数据的完整性和合法性
    
    Args:
        data: 角色JSON数据
    
    Returns:
        (是否有效, 错误消息列表)
    """
    errors = []
    
    # 必需字段检查
    if not data.get("id"):
        errors.append("缺少必需字段: id")
    if not data.get("name"):
        errors.append("缺少必需字段: name")
    
    # importance范围检查
    importance = data.get("importance", 50.0)
    if not (0 <= importance <= 100):
        errors.append(f"importance必须在0-100之间，当前值: {importance}")
    
    # relationship_matrix格式检查
    rel_matrix = data.get("relationship_matrix", {})
    if rel_matrix and not isinstance(rel_matrix, dict):
        errors.append("relationship_matrix必须是字典类型")
    else:
        for target_id, rel_data in rel_matrix.items():
            if not isinstance(rel_data, dict):
                errors.append(f"relationship_matrix[{target_id}]必须是字典类型")
            elif "address_as" not in rel_data and "attitude" not in rel_data:
                errors.append(f"relationship_matrix[{target_id}]至少需要address_as或attitude字段")
    
    return len(errors) == 0, errors


def get_high_importance_characters(
    characters: List[CharacterData],
    min_importance: float = 70.0
) -> List[CharacterData]:
    """
    筛选高权重角色
    
    Args:
        characters: 角色列表
        min_importance: 最低权重阈值
    
    Returns:
        高权重角色列表（按权重降序）
    """
    high_importance = [c for c in characters if c.importance >= min_importance]
    return sorted(high_importance, key=lambda c: c.importance, reverse=True)

