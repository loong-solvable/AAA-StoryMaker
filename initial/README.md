# 📦 Initial - 初始化模块

> 集中管理项目中所有初始化相关的功能代码

## 📁 模块结构

```
initial/
├── __init__.py           # 模块对外接口
├── init_llm.py          # LLM初始化
├── init_genesis.py      # Genesis数据加载（旧格式，兼容）
├── init_world.py        # World数据加载（新格式，拆分式）⭐
├── init_world_state.py  # 世界状态初始化
├── init_agents.py       # Agent初始化（Logic、Plot、Vibe）
├── init_npc.py          # NPC初始化
├── init_database.py     # 数据库初始化
└── README.md            # 本文档
```

## 🎯 设计原则

1. **模块化分离**：不同类型的初始化功能分别存放在独立文件中
2. **职责单一**：每个模块只负责一类初始化任务
3. **易于维护**：集中管理，便于修改和扩展
4. **可复用**：各模块可独立导入使用

## 📘 使用示例

### 方式1：导入完整模块

```python
from initial import (
    initialize_llm,
    load_genesis_data,
    initialize_world_state,
    initialize_agents,
    initialize_npc_manager,
    initialize_database
)

# 使用
llm = initialize_llm()
genesis_data = load_genesis_data(genesis_path)
world_state = initialize_world_state(genesis_data)
```

### 方式2：导入单个模块

```python
from initial.init_llm import initialize_llm
from initial.init_genesis import load_genesis_data

llm = initialize_llm(temperature=0.8)
genesis_data = load_genesis_data("data/genesis/genesis.json")
```

## 📚 模块详解

### 1️⃣ init_llm.py - LLM初始化

**功能：** 创建和配置LLM实例

**主要函数：**
- `initialize_llm()` - 初始化LLM实例，支持自定义provider、model、temperature等参数

**使用场景：**
- 游戏引擎启动时
- 各Agent创建时需要LLM实例

---

### 2️⃣ init_genesis.py - Genesis数据加载（旧格式）

**功能：** 加载和验证Genesis世界数据包（单文件格式，向后兼容）

**主要函数：**
- `load_genesis_data(genesis_path)` - 加载Genesis.json文件并验证数据结构
- `_validate_genesis_data()` - 内部验证函数

**使用场景：**
- 兼容旧版Genesis.json格式
- 旧项目迁移

---

### 2️⃣➕ init_world.py - World数据加载（新格式）⭐ 推荐

**功能：** 加载创世组生成的拆分式世界数据（world_setting.json + characters_list.json + characters/*.json）

**主要函数：**
- `load_world_data(world_dir)` - 加载完整的世界数据（三份文件）
- `load_world_setting(world_dir)` - 仅加载世界设定（Demiurge生成）
- `load_characters_list(world_dir)` - 仅加载角色列表（大中正生成）
- `load_character_details(world_dir, character_id)` - 加载单个角色档案（藻鉴生成）
- `load_all_characters(world_dir)` - 加载所有角色档案
- `list_available_worlds()` - 列出所有可用世界

**使用场景：**
- 加载创世组生成的新格式世界数据
- 按需加载世界的不同部分（提高性能）
- 管理多个世界

**示例：**
```python
from pathlib import Path
from initial import load_world_data

# 加载完整世界
world_dir = Path("data/worlds/修仙世界")
world_data = load_world_data(world_dir)

# 访问数据
world_setting = world_data["world_setting"]
characters = world_data["characters"]
```

---

### 3️⃣ init_world_state.py - 世界状态初始化

**功能：** 初始化世界上下文和世界状态管理器

**主要函数：**
- `initialize_world_context(genesis_data)` - 创建WorldContext实例
- `initialize_world_state(genesis_data)` - 创建WorldStateManager实例

**使用场景：**
- 游戏引擎初始化阶段
- 需要访问世界状态的Agent

---

### 4️⃣ init_agents.py - Agent初始化

**功能：** 初始化各种核心Agent（Logic、Plot、Vibe）

**主要函数：**
- `initialize_logic_agent(world_data)` - 初始化逻辑审查官
- `initialize_plot_agent(genesis_data)` - 初始化剧情导演
- `initialize_vibe_agent(genesis_data)` - 初始化氛围创造者
- `initialize_agents(genesis_data)` - 批量初始化所有核心Agent

**使用场景：**
- 游戏引擎启动时
- 需要协调多个Agent的场景

---

### 5️⃣ init_npc.py - NPC初始化

**功能：** 初始化NPC管理器和所有NPC Agent

**主要函数：**
- `initialize_single_npc(character_data)` - 初始化单个NPC
- `initialize_npc_manager(genesis_data)` - 初始化NPC管理器（推荐）
- `initialize_npc_list(characters_data)` - 批量手动初始化NPC

**使用场景：**
- 游戏启动时批量创建所有NPC
- 运行时动态创建新NPC

---

### 6️⃣ init_database.py - 数据库初始化

**功能：** 初始化StateManager和存储组件

**主要函数：**
- `initialize_database(game_id, game_name, genesis_path)` - 初始化状态管理器
- `initialize_character_cards_to_database(state_manager, genesis_data)` - 导入角色卡到数据库

**使用场景：**
- 游戏引擎启动时
- 需要持久化存储的场景

---

## 🔄 典型初始化流程

### 方式1：使用新格式（推荐）⭐

```python
from pathlib import Path
from initial import *

# 1. 加载世界数据（新格式）
world_dir = Path("data/worlds/修仙世界")
world_data = load_world_data(world_dir)

# 2. 初始化数据库
state_manager = initialize_database(
    game_name=world_data["world_setting"]["meta"]["title"],
    genesis_path=str(world_dir)
)

# 3. 导入角色卡到数据库
for char_id, char_data in world_data["characters"].items():
    state_manager.record_character_card(
        character_id=char_id,
        version=1,
        card_data=char_data,
        changes=None,
        changed_by="world_import"
    )

# 4. 初始化世界状态（需要适配新格式）
# world_state = initialize_world_state(world_data)

# 5. 初始化核心Agent（需要适配新格式）
# logic, plot, vibe = initialize_agents(world_data)

# 6. 初始化NPC管理器
# npc_manager = initialize_npc_manager(world_data)

# ✅ 初始化完成，开始游戏
```

### 方式2：使用旧格式（向后兼容）

```python
from pathlib import Path
from initial import *

# 1. 加载Genesis数据（旧格式）
genesis_path = Path("data/genesis/genesis.json")
genesis_data = load_genesis_data(genesis_path)

# 2-6. 与新格式相同的初始化步骤
# ...

# ✅ 初始化完成，开始游戏
```

## ⚠️ 注意事项

1. **初始化顺序很重要**：某些模块依赖其他模块的输出
2. **异常处理**：所有函数都会抛出异常，需要在调用时处理
3. **日志输出**：每个模块都会输出详细的初始化日志
4. **配置依赖**：部分函数依赖 `.env` 配置文件

## 📝 维护指南

### 添加新的初始化模块

1. 在 `initial/` 目录下创建新的 `init_xxx.py` 文件
2. 遵循命名规范：`init_<功能名>.py`
3. 在 `__init__.py` 中导出主要函数
4. 更新本README文档

### 修改现有模块

1. 确保向后兼容性
2. 更新相关文档
3. 测试所有依赖此模块的代码

---

**创建日期：** 2024-11-26  
**维护者：** AAA-StoryMaker Team

