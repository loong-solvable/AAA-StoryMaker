# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

Infinite Story（无限故事机）是一个基于LangChain的生成式互动叙事游戏引擎。用户上传小说后，AI自动解析并重构世界观，然后用户可以作为新角色进入该世界进行自然语言交互。

## 常用命令

```bash
# 安装依赖
pip install -r requirements.txt

# 离线构建：将小说转化为世界数据
python run_architect.py

# 运行完整游戏
python play_game.py

# 测试OS和Logic Agent
python test_phase2_demo.py

# 运行单个测试
python -m pytest tests/test_auto_retry.py -v
```

## 环境配置

创建`.env`文件（参考配置）：
```
LLM_PROVIDER=zhipu
ZHIPU_API_KEY=your_key_here
MODEL_NAME=glm-4
TEMPERATURE=0.7
```

## 架构概述

### 两大阶段

1. **离线构建阶段 (The Creator)** - 读取小说，生成世界数据
2. **在线运行阶段 (The Runtime)** - 游戏世界模拟与玩家交互

### Agent层次结构

```
agents/
├── offline/                    # 离线构建
│   ├── architect.py           # 旧版架构师入口
│   └── creatorGod/            # 新版三子客体架构 (v0.3.0)
│       ├── creator_god.py     # CreatorGod主控制器
│       ├── character_filter_agent.py  # 角色过滤
│       ├── world_setting_agent.py     # 世界设定提取
│       └── character_detail_agent.py  # 角色档案生成
│
└── online/                     # 在线运行
    ├── layer1/                # 安检与中枢
    │   ├── os_agent.py       # 信息中枢：消息路由、状态管理
    │   └── logic_agent.py    # 逻辑审查：输入验证、幻觉检测
    ├── layer2/                # 光明会（逻辑大脑）
    │   ├── ws_agent.py       # 世界状态运行者：时间、NPC状态
    │   ├── plot_agent.py     # 命运编织者：剧情走向
    │   └── vibe_agent.py     # 氛围感受者：环境描写
    └── layer3/                # 演员组
        └── npc_agent.py      # NPC动态生成与演绎
```

### 核心模块

- `utils/llm_factory.py` - LLM抽象工厂，支持智谱清言、OpenAI
- `utils/custom_zhipuai.py` - 修复原始SDK 60秒硬编码超时问题
- `utils/logger.py` - 彩色日志系统
- `config/settings.py` - 环境配置管理
- `game_engine.py` - 游戏引擎主控
- `agents/message_protocol.py` - Agent间JSON通信协议

## 用户流程与数据流转

### 阶段一：离线构建（run_architect.py）

```
用户提供小说.txt
       │
       ▼
┌──────────────────────────────────────────────────────┐
│              CreatorGod 三阶段处理                     │
├──────────────────────────────────────────────────────┤
│                                                       │
│  [1] CharacterFilterAgent (角色过滤)                  │
│      小说文本 → LLM → 角色列表 + 重要性评分            │
│                  │                                    │
│                  ▼                                    │
│  [2] WorldSettingAgent (世界设定)                     │
│      小说文本 → LLM → 物理法则/社会规则/地点           │
│                  │                                    │
│                  ▼                                    │
│  [3] CharacterDetailAgent (角色档案) ←── 支持失败重试  │
│      小说+角色列表 → LLM → 每个角色的详细档案          │
│                                                       │
└──────────────────────────────────────────────────────┘
       │
       ▼
data/worlds/<世界名>/
├── world_setting.json      # 世界观、法则、地点
├── characters_list.json    # 角色ID、名称、重要性
└── characters/
    ├── character_xxx.json  # 性格、行为规则、关系、语言样本
    └── ...
```

### 阶段二：在线运行（play_game.py）

**启动流程：**

```
加载世界数据
     │
     ▼
┌─────────────────────────────────────┐
│  OS初始化                            │
│  - 加载world_setting + characters   │
│  - 创建消息队列                      │
└─────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────┐
│  光明会初始化（并行）                 │
│  ├─ WS: 初始化NPC状态/位置/时间      │
│  ├─ Vibe: 初始化环境氛围             │
│  └─ Plot: 分析剧情线索库             │
└─────────────────────────────────────┘
     │
     ▼
Plot动态生成开场场景 → 展示给玩家
```

**游戏回合流程：**

```
玩家输入文字
     │
     ▼
┌──────────────────────────────────────────────────────────────┐
│ Layer1: 安检与中枢                                            │
│                                                               │
│   OS接收 ──→ Logic审查 ──→ 通过？──┬─→ 拒绝理由返回玩家       │
│                                   │                          │
│                                   ▼ 通过                      │
└──────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────┐
│ Layer2: 光明会协作                                            │
│                                                               │
│   Plot ←──拉取状态──→ WS (世界状态)                           │
│    │   ←──拉取氛围──→ Vibe (环境)                             │
│    │                                                          │
│    ▼                                                          │
│   Plot编写新剧本                                              │
│    │                                                          │
│    ├──→ WS更新: NPC位置/状态/时间/离屏事件                    │
│    └──→ Vibe更新: 环境变化/氛围                               │
│                                                               │
└──────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────┐
│ Layer3: 演员演绎                                              │
│                                                               │
│   OS拆解剧本 → 分发给相关NPC Agents                           │
│                    │                                          │
│         ┌─────────┼─────────┐                                │
│         ▼         ▼         ▼                                │
│      NPC-A     NPC-B     NPC-C   (并行演绎)                  │
│         │         │         │                                │
│         └─────────┴─────────┘                                │
│                   │                                          │
│                   ▼                                          │
│   OS整合所有NPC输出 → 按时间线拼接                            │
│                                                               │
└──────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                            展示给玩家
                                    │
                                    ▼
                            等待下一轮输入
```

### Agent间消息协议

所有Agent通信通过OS中转，使用JSON格式：

```json
{
  "from": "plot",
  "to": "ws",
  "type": "state_query",
  "payload": { "query": "current_npc_positions" },
  "timestamp": "2024-11-28T12:00:00"
}
```

## 上下文管理策略（如何省Token）

系统通过以下策略控制LLM上下文大小：

### 1. 拆分式数据加载

```
data/worlds/<世界名>/
├── world_setting.json      # 只在初始化时加载一次
├── characters_list.json    # 轻量级索引
└── characters/
    └── character_xxx.json  # 按需加载特定角色
```

- 不是一次性加载所有数据到内存
- OS按需获取：`get_character_data(id)` / `get_location_data(id)`

### 2. 滑动窗口历史（核心策略）

| 组件 | 窗口大小 | 代码位置 |
|------|---------|----------|
| OS.recent_events | 最近5条 | `os_agent.py:232-234` |
| NPC.dialogue_history | 最近10条(5轮) | `npc_agent.py:181-182` |
| Plot.available_plots | 前10个节点 | `plot_agent.py:166` |

```python
# 示例：NPC对话历史滑动窗口
if len(self.dialogue_history) > 10:
    self.dialogue_history = self.dialogue_history[-10:]
```

### 3. 每个Agent只接收必要信息

```
┌─────────────────────────────────────────────────────────────┐
│ Plot 接收:                                                   │
│ - world_name, genre (静态，几个字)                           │
│ - available_plots (最多10个节点摘要)                         │
│ - player_action (当前输入)                                   │
│ - present_characters (在场角色名，非完整档案)                │
│ - world_context (WS状态摘要)                                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ NPC 接收:                                                    │
│ - 自己的角色卡 (traits, behavior_rules, voice_samples)       │
│ - scene_context (位置、时间、氛围，几行文字)                 │
│ - director_instruction (Plot给的简短指令)                   │
│ - dialogue_history (最近3轮对话)                            │
│ - player_input (当前一句话)                                 │
└─────────────────────────────────────────────────────────────┘
```

### 4. 角色重要性过滤

```python
# plot_agent.py - 根据importance决定谁出场
importance_thresholds = {
    "high": 80.0,    # 高潮场景：只让权重80+的主要角色出现
    "normal": 50.0,  # 常规场景：权重50+
    "low": 0.0       # 过渡场景：任意角色
}
```

- 减少同时在场的NPC数量 → 减少并行LLM调用 → 减少总Token

### 5. 状态快照 vs 完整历史

```
每回合存储的是"快照"，不是"累积历史"：

┌──────────────────────────────────────┐
│ Turn 5 快照                          │
│ - current_time: "下午3点"            │
│ - npc_positions: {npc_001: "办公室"} │
│ - tension_level: 7                   │
│ - active_plot_nodes: ["hint_003"]   │
└──────────────────────────────────────┘

SQLite/JSON存档用于：
- 游戏存档/读档
- 调试审计
- 不用于构建LLM Prompt
```

### 6. Prompt模板分离

```
prompts/online/npc_system.txt  ← 静态模板（加载一次）
                │
                ▼
        运行时只填充动态占位符：
        {character_name}, {traits}, {current_mood}...
```

- 系统Prompt从文件加载，不重复生成
- 动态信息通过`{placeholder}`填充

## 关键设计原则

1. **LLM超时处理** - 切换LLM提供商时必须配置足够的超时时间（默认600秒），参考`utils/custom_zhipuai.py`
2. **Prompt工程** - 所有Prompt统一存放于`prompts/`目录
3. **日志系统** - 运行日志保存于`logs/`，Agent状态变更使用JSONL格式追踪
4. **拆分式数据存储** - 世界数据采用多文件结构，便于按需加载

## 目录结构

```
├── agents/          # Agent实现
├── prompts/         # Prompt模板
│   ├── offline/    # 架构师Prompt
│   └── online/     # 运行时Agent Prompt
├── data/
│   ├── novels/     # 输入小说
│   ├── worlds/     # 生成的世界数据
│   └── runtime/    # 运行时数据
├── utils/          # 工具模块
├── config/         # 配置管理
├── initial/        # 初始化模块
├── logs/           # 运行日志
├── tests/          # 测试文件
└── docs/reports/   # 工作报告与问题修复记录
```
