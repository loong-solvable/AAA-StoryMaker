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

### 运行Demo

**第一阶段：创世组（离线构建）**
```bash
python run_genesis.py
```
该脚本会执行创世组的三阶段处理：
1. **大中正** - 角色普查，识别所有角色并评估重要性
2. **Demiurge** - 提取世界观设定（物理法则、社会规则、地点）
3. **许劭** - 为每个角色创建详细档案（角色卡）

生成结果保存在 `data/worlds/<世界名>/` 目录：
- `world_setting.json` - 世界观设定
- `characters_list.json` - 角色列表
- `characters/` - 每个角色的详细档案

**第二阶段：OS与Logic（在线系统基础）**
```bash
python test_phase2_demo.py
```
该脚本会：
1. 初始化信息中枢OS
2. 初始化逻辑审查官Logic
3. 演示消息路由和验证功能
4. 测试世界上下文管理

**完整游戏：互动叙事体验**
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

