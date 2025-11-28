"""
[已弃用] 架构师模块 - 已更名为创世组 (Genesis Group)

此文件保留用于向后兼容，请使用新的模块：
    from agents.offline.genesis_group import GenesisGroup, create_world

创世组成员：
- 大中正 (The Censor): 角色普查与重要性评估
- Demiurge (造物主): 世界规则与背景提取  
- 许劭 (角色雕刻师): 角色档案与角色卡制作
"""
import warnings

# 向后兼容：从新模块导入
from .genesis_group import GenesisGroup, create_world

# 兼容旧名称
ArchitectAgent = GenesisGroup

# 发出弃用警告
warnings.warn(
    "architect模块已弃用，请使用genesis_group模块。"
    "ArchitectAgent已更名为GenesisGroup。",
    DeprecationWarning,
    stacklevel=2
)
