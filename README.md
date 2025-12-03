# 🎭 Infinite Story - 无限故事机

> 一个基于LangChain的生成式互动叙事游戏引擎

## 📖 项目简介

**Infinite Story** 是一个创新的AI驱动叙事游戏系统。用户可以上传一本小说，AI会自动解析并重构整个世界观，然后用户可以作为一个新角色进入该世界，通过自然语言与世界互动。

### 核心特性

- ✨ **纯AI驱动**: 无数值战斗、无RPG属性，专注于逻辑严谨的剧情模拟
- 🌍 **动态世界**: AI实时模拟世界状态、NPC行为和剧情发展
- 🎨 **高度沉浸**: 生成式环境描写和社会互动
- 🔧 **模块化设计**: 基于LangChain的多Agent协作系统

## 🏗️ 系统架构

### 离线构建阶段（The Creator）
- **创世组 (Genesis Group)**: 由三位专职Agent组成，协同完成世界数据的提取与构建：
  - **大中正 (The Censor)**: 负责角色普查，评估角色重要性并生成角色列表
  - **Demiurge（造物主）**: 负责提取世界规则、物理法则、社会背景等世界观设定
  - **许劭（角色雕刻师）**: 负责提取角色详细信息，制作角色卡档案

### 在线运行系统（The Runtime）

**第一层 - 安检与中枢**
- **逻辑审查官 (Logic)**: 审核输入输出的逻辑一致性
- **信息中枢 (OS)**: 剧本拆分、消息分发与状态管理

**第二层 - 光明会（逻辑大脑）**
- **世界状态运行者 (WS)**: 模拟时间流逝、事件触发
- **命运编织者 (Plot)**: 掌控剧情走向和高潮节奏
- **氛围感受者 (Vibe)**: 生成沉浸式环境描写

**第三层 - 演员组（表现层）**
- **NPC Agents**: 扮演小说中的角色，生成台词和行为

## 🚀 快速开始

### 环境准备

1. **克隆项目**
```bash
cd D:\code\AAA-StoryMaker
```

2. **创建虚拟环境**
```bash
python -m venv venv
venv\Scripts\activate  # Windows
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **配置API密钥**
```bash
# 复制配置模板
copy .env.example .env

# 编辑 .env 文件，填入你的智谱清言API密钥
# ZHIPU_API_KEY=your_api_key_here
```

### 完整运行流程

按照以下顺序运行，可以体验从世界构建到剧情演绎的完整流程：

#### 第一阶段：创世组（离线构建世界数据）

```bash
python run_creator_god.py
```

**功能说明：**
该脚本执行创世组的三阶段处理，从小说文本中提取并构建完整的世界数据：

1. **大中正 (The Censor)** - 角色普查阶段
   - 识别小说中的所有角色
   - 评估每个角色的重要性
   - 生成角色列表（`characters_list.json`）

2. **Demiurge（造物主）** - 世界观提取阶段
   - 提取物理法则和世界规则
   - 提取社会背景和规则
   - 提取地点信息和感官描述
   - 生成世界观设定（`world_setting.json`）

3. **许劭（角色雕刻师）** - 角色档案制作阶段
   - 为每个重要角色创建详细档案
   - 提取角色特征、行为规则、关系网络
   - 生成角色卡（`characters/character_*.json`）

**输出结果：**
生成的世界数据保存在 `data/worlds/<世界名>/` 目录：
```
data/worlds/<世界名>/
├── world_setting.json      # Demiurge生成的世界观设定
├── characters_list.json    # 大中正生成的角色列表
└── characters/            # 许劭生成的角色详细档案
    ├── character_npc_001.json
    ├── character_npc_002.json
    └── ...
```

**日志文件：** `logs/genesis_group.log`

---

#### 第二阶段：三幕完整流程测试（在线运行系统）

```bash
python tests/test_three_scenes_flow.py
```

**功能说明：**
该脚本演示完整的游戏运行流程，包括光明会初始化和三幕剧情演绎：

**阶段0：光明会初始化**
- **WS（世界状态运行者）**：读取世界数据，初始化世界状态
  - 生成初始场景、天气、在场角色
  - 保存到 `data/runtime/<世界名>_<时间戳>/ws/world_state.json`
- **Plot（命运编织者）**：生成起始场景和第一幕剧本
  - 基于世界数据和角色卡生成开场场景
  - 生成第一幕剧本（约500字）
  - 保存到 `data/runtime/.../plot/current_scene.json` 和 `current_script.json`
- **Vibe（氛围感受者）**：生成初始氛围描写
  - 基于场景和剧本生成沉浸式环境描写
  - 保存到 `data/runtime/.../vibe/initial_atmosphere.json`

**第1幕演绎流程：**
1. **剧本拆分**：OS Agent 将剧本拆分为各角色的任务卡
2. **角色初始化**：初始化首次出场的角色
3. **对话循环**：运行最多12轮对话，NPC根据任务卡生成台词和行为
4. **幕间处理**：归档第1幕剧本，更新世界状态，生成第2幕剧本

**第2幕演绎流程：**
1. 剧本拆分 → 角色初始化 → 对话循环（最多12轮）
2. 幕间处理：归档第2幕，更新世界状态，生成第3幕剧本

**第3幕演绎流程：**
1. 剧本拆分 → 角色初始化 → 对话循环（最多12轮）
2. 结束：三幕完整流程测试完成

**输出结果：**
运行时数据保存在 `data/runtime/<世界名>_<时间戳>/` 目录：
```
data/runtime/<世界名>_<时间戳>/
├── ws/
│   └── world_state.json           # WS世界状态
├── plot/
│   ├── current_scene.json         # 当前场景
│   ├── current_script.json        # 当前剧本
│   └── archive/                   # 历史剧本存档
│       ├── scene_1_script.json
│       └── scene_2_script.json
├── vibe/
│   └── initial_atmosphere.json    # 初始氛围
└── test_report.json                # 测试报告
```

**测试报告：**
脚本会在运行时目录生成 `test_report.json`，包含：
- 每幕的演绎结果（成功状态、轮数、对话数）
- 归档文件列表
- 发现的问题（如有）

**日志文件：** 各Agent的日志保存在 `logs/` 目录

---

#### 其他运行选项

**OS与Logic基础测试：**
```bash
python test_phase2_demo.py
```
演示信息中枢OS和逻辑审查官Logic的基础功能。

**完整游戏体验：**
```bash
python play_game.py
```
这是完整可玩的游戏！你将：
1. 进入由小说生成的世界
2. 与NPC自然对话互动
3. 体验动态剧情发展
4. 沉浸式的环境描写

## 📁 项目结构

```
AAA-StoryMaker/
├── agents/               # Agent实现
│   ├── offline/         # 离线构建（创世组：大中正+Demiurge+许劭）
│   └── online/          # 在线运行（游戏Agent）
├── prompts/             # Prompt工程
├── data/                # 数据存储
│   ├── novels/         # 输入：小说文本
│   ├── worlds/         # 输出：世界数据（拆分式结构）⭐
│   └── runtime/        # 运行时数据
├── initial/             # 初始化模块
├── logs/                # 运行日志
├── utils/               # 工具模块
└── config/              # 配置管理
```

## 🛠️ 技术栈

- **语言**: Python 3.9+
- **AI框架**: LangChain
- **LLM提供商**: 智谱清言（GLM-4）、OpenAI（可选）
- **配置管理**: python-dotenv
- **日志**: colorlog

## 📝 开发状态

### ✅ 第一阶段（已完成）
- [x] 项目架构设计
- [x] 创世组Agent实现（大中正+Demiurge+许劭三阶段处理）
- [x] LLM工厂模式
- [x] 日志系统
- [x] 世界数据生成（拆分式结构）

### ✅ 第二阶段（已完成 - v0.2.0）
- [x] Agent消息协议定义
- [x] 信息中枢OS实现
- [x] 逻辑审查官Logic实现
- [x] 消息路由系统
- [x] 世界上下文管理
- [x] 基础测试Demo

### ✅ 第三&四阶段（当前 - v1.0.0）
- [x] 光明会三大Agent（WS/Plot/Vibe）
- [x] NPC动态生成系统
- [x] 完整的游戏回合逻辑
- [x] CLI交互界面
- [x] 游戏引擎整合
- [x] 可玩的完整游戏

### 🔜 未来优化
- [ ] 游戏存档/读档系统
- [ ] 多结局分支系统
- [ ] 性能优化
- [ ] Web界面

## 📄 许可证

本项目为学习和研究目的开发。

## 👨‍💻 开发团队

项目版本: v0.1.0 - 架构师Demo阶段

