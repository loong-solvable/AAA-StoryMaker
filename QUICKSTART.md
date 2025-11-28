# 🚀 快速开始指南

## 📋 前置要求

- Python 3.9 或更高版本
- 智谱清言API密钥（推荐）或其他LLM API密钥

---

## ⚡ 5分钟快速上手

### 步骤1: 创建虚拟环境

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 步骤2: 安装依赖

```bash
pip install -r requirements.txt
```

### 步骤3: 配置API密钥

1. 复制配置模板：
```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

2. 编辑 `.env` 文件，填入你的API密钥：
```env
# 使用智谱清言（推荐）
ZHIPU_API_KEY=your_zhipu_api_key_here
LLM_PROVIDER=zhipu
MODEL_NAME=glm-4

# 或使用OpenAI
# OPENAI_API_KEY=your_openai_api_key_here
# LLM_PROVIDER=openai
# MODEL_NAME=gpt-4
```

### 步骤4: 开始游玩！

**第一次运行 - 生成世界:**
```bash
python run_architect.py
```

**开始游戏:**
```bash
python play_game.py
```

---

## 🎯 运行结果

成功运行后，你将看到：

```
======================================================================
🎭 欢迎使用 Infinite Story - 无限故事机
======================================================================

📌 创世组三阶段构建流程:
   1️⃣ 大中正 - 角色普查，识别所有角色并评估重要性
   2️⃣ Demiurge - 提取世界观设定（物理法则、社会规则、地点）
   3️⃣ 藻鉴 - 为每个角色创建详细档案（角色卡）

======================================================================

[2024-11-26] [GenesisGroup] [INFO] 🏗️  初始化创世组...
[2024-11-26] [LLMFactory] [INFO] 🤖 正在创建LLM实例...
[2024-11-26] [GenesisGroup] [INFO] ✅ 创世组初始化完成
[2024-11-26] [大中正] [INFO] 📍 阶段1：角色普查
[2024-11-26] [大中正] [INFO] ✅ 角色普查完成，发现 15 个角色
[2024-11-26] [Demiurge] [INFO] 📍 阶段2：提取世界观设定
[2024-11-26] [Demiurge] [INFO] ✅ 世界观设定提取完成
[2024-11-26] [藻鉴] [INFO] 📍 阶段3：创建角色详细档案
...
[2024-11-26] [GenesisGroup] [INFO] ✅ 世界数据已保存

======================================================================
🎉 世界构建成功！
======================================================================

📁 世界数据已生成: data\worlds\都市迷局\
   - world_setting.json      # 世界观设定
   - characters_list.json    # 角色列表
   - characters/             # 角色详细档案
```

---

## 📂 查看结果

### 生成的文件结构

```
data/worlds/都市迷局/
├── world_setting.json      # 世界观设定
├── characters_list.json    # 角色列表
└── characters/             # 角色档案
    ├── character_linchen.json
    ├── character_suqingyu.json
    └── ...
```

### 1. world_setting.json - 世界观设定

```json
{
  "meta": {
    "title": "都市迷局",
    "genre": "现代都市悬疑",
    "time_period": "2024年"
  },
  "laws_of_physics": [
    "现代都市，无超自然元素",
    "符合现实世界物理规律"
  ],
  "social_rules": [
    {
      "rule": "职场等级制度",
      "condition": "下属与上司互动",
      "result": "需保持尊重"
    }
  ],
  "locations": [
    {
      "id": "loc_001",
      "name": "启明科技公司",
      "description": "高科技办公楼..."
    }
  ]
}
```

### 2. characters_list.json - 角色列表

```json
[
  {
    "id": "linchen",
    "name": "林晨",
    "importance": 1.0
  },
  {
    "id": "suqingyu",
    "name": "苏晴雨",
    "importance": 0.8
  }
]
```

### 3. character_linchen.json - 角色详细档案

```json
{
  "id": "linchen",
  "name": "林晨",
  "gender": "男",
  "age": "25岁",
  "importance": 1.0,
  "traits": ["AI工程师", "技术宅", "正义感强"],
  "behavior_rules": [
    "遇到技术问题会专注研究",
    "对不公正的事情会站出来"
  ],
  "voice_samples": [
    "这个算法还有优化空间。",
    "我们必须找出真相。"
  ]
}
```

### 运行日志

- **位置**: `logs/architect.log`
- **包含**: 创世组（大中正+Demiurge+藻鉴）完整的三阶段处理流程和调试信息

---

## 🔧 常见问题

### Q1: API密钥在哪里获取？

**智谱清言（推荐）:**
1. 访问 [智谱AI开放平台](https://open.bigmodel.cn/)
2. 注册账号
3. 创建API密钥

**OpenAI:**
1. 访问 [OpenAI Platform](https://platform.openai.com/)
2. 创建API密钥

### Q2: 运行失败怎么办？

检查以下几点：
1. ✅ 虚拟环境已激活
2. ✅ 依赖已正确安装 (`pip list` 查看)
3. ✅ `.env` 文件已创建且API密钥正确
4. ✅ 网络连接正常
5. ✅ 查看 `logs/architect.log` 了解详细错误

### Q3: 如何使用自己的小说？

1. 将你的小说文本文件（`.txt`格式）放入 `data/novels/` 目录
2. 修改 `run_architect.py` 中的文件名，或直接运行：

```python
from agents.offline.architect import create_world

# 使用你的小说文件
world_dir = create_world("your_novel.txt")
print(f"世界数据已生成: {world_dir}")
```

### Q4: 小说有什么要求？

- **格式**: 纯文本 `.txt` 文件（UTF-8编码）
- **长度**: 建议 5000-20000 字
- **类型**: 现代都市、修仙玄幻、悬疑、言情等各类型均可
- **结构**: 有完整的角色、场景和剧情

### Q5: 为什么推荐智谱清言？

1. ✅ 国内访问稳定，无需VPN
2. ✅ 中文理解能力强
3. ✅ 价格实惠（新用户有免费额度）
4. ✅ API调用简单

---

## 🎓 下一步

完成第一阶段后，你可以：

1. **查看代码实现**
   - 阅读 `agents/offline/creatorGod/` 目录了解创世组的三阶段处理流程
   - 查看 `prompts/offline/creatorGod/` 目录了解创世组三成员的Prompt

2. **修改Prompt**
   - 编辑 `world_setting.txt` 优化Demiurge的世界设定提取
   - 编辑 `character_detail.txt` 优化藻鉴的角色档案生成
   - 编辑 `character_filter.txt` 调整大中正的角色重要性评估

3. **等待第二阶段**
   - 在线运行系统（信息中枢、光明会、NPC）
   - 真正可玩的互动游戏

4. **阅读架构文档**
   - 查看 [ARCHITECTURE.md](./ARCHITECTURE.md) 了解完整设计

---

## 💡 提示

- 📖 **首次运行**: 使用自带的 `example_novel.txt` 熟悉流程
- ⏰ **处理时间**: LLM解析需要1-2分钟，请耐心等待
- 📝 **查看日志**: 遇到问题先查看 `logs/` 目录下的日志文件
- 🔄 **多次尝试**: LLM输出有随机性，可多次运行比较结果

---

## 📞 获取帮助

- 查看详细文档: [README.md](./README.md)
- 查看架构设计: [ARCHITECTURE.md](./ARCHITECTURE.md)
- 查看工作报告: [工作报告-第1次-2024年11月24日.md](./工作报告-第1次-2024年11月24日.md)

---

**祝你使用愉快！🎉**

