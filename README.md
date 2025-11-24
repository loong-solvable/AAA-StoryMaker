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
- **架构师 (The Architect)**: 读取小说，提取世界观、人物、剧情，生成`Genesis.json`

### 在线运行系统（The Runtime）

**第一层 - 安检与中枢**
- **逻辑审查官 (Logic)**: 审核输入输出的逻辑一致性
- **信息中枢 (OS)**: 消息路由与状态管理

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

**第一阶段：架构师（离线构建）**
```bash
python run_architect.py
```
该脚本会：
1. 读取 `data/novels/example_novel.txt` 中的示例小说
2. 调用架构师Agent进行世界观解析
3. 生成 `data/genesis/genesis.json` 数据包

**第二阶段：OS与Logic（在线系统基础）**
```bash
python test_phase2_demo.py
```
该脚本会：
1. 初始化信息中枢OS
2. 初始化逻辑审查官Logic
3. 演示消息路由和验证功能
4. 测试世界上下文管理

## 📁 项目结构

```
AAA-StoryMaker/
├── agents/               # Agent实现
│   ├── offline/         # 离线构建（本阶段）
│   └── online/          # 在线运行（未来）
├── prompts/             # Prompt工程
├── data/                # 数据存储
│   ├── novels/         # 输入小说
│   └── genesis/        # 输出世界数据
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
- [x] 架构师Agent实现
- [x] LLM工厂模式
- [x] 日志系统
- [x] Genesis.json生成

### ✅ 第二阶段（当前 - v0.2.0）
- [x] Agent消息协议定义
- [x] 信息中枢OS实现
- [x] 逻辑审查官Logic实现
- [x] 消息路由系统
- [x] 世界上下文管理
- [x] 基础测试Demo

### 🔜 第三阶段（未来）
- [ ] 光明会三大Agent（WS/Plot/Vibe）
- [ ] NPC动态生成系统
- [ ] 完整的游戏回合逻辑
- [ ] CLI交互界面

## 📄 许可证

本项目为学习和研究目的开发。

## 👨‍💻 开发团队

项目版本: v0.1.0 - 架构师Demo阶段

