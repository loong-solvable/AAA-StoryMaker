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

📌 当前阶段: 第一阶段 - 离线构建者 (The Architect)
🎯 目标: 将小说转化为可游戏化的Genesis世界数据包

======================================================================

[2024-11-24 12:00:00] [Architect] [INFO] 🏗️  初始化架构师Agent...
[2024-11-24 12:00:01] [LLMFactory] [INFO] 🤖 正在创建LLM实例...
[2024-11-24 12:00:02] [Architect] [INFO] ✅ 架构师Agent初始化完成
[2024-11-24 12:00:03] [Architect] [INFO] 📖 开始处理小说: example_novel.txt
[2024-11-24 12:00:04] [Architect] [INFO] 🤖 正在调用LLM进行世界观解析...
[2024-11-24 12:00:05] [Architect] [INFO] ⏳ 这可能需要1-2分钟，请耐心等待...
...
[2024-11-24 12:01:30] [Architect] [INFO] ✅ Genesis.json已保存

======================================================================
🎉 恭喜！第一阶段Demo运行成功！
======================================================================

📁 Genesis数据包已生成: data\genesis\genesis.json
```

---

## 📂 查看结果

### 生成的文件

1. **Genesis.json** - 世界数据包
   - 位置: `data/genesis/genesis.json`
   - 包含: 世界观、角色、地点、剧情节点

2. **运行日志** - 详细执行记录
   - 位置: `logs/architect.log`
   - 包含: 完整的处理流程和调试信息

### Genesis.json 示例结构

```json
{
  "world": {
    "title": "都市迷局",
    "genre": "现代都市悬疑",
    "time_period": "2024年",
    "location": "江城市",
    "world_rules": [
      "现代都市，无超自然元素",
      "以科技和商业为背景",
      "符合现实世界逻辑"
    ]
  },
  "characters": [
    {
      "id": "char_001",
      "name": "林晨",
      "age": "25",
      "gender": "男",
      "occupation": "AI算法工程师",
      "personality": ["内向", "技术宅", "正义感"],
      "background": "名校毕业，技术能力出众..."
    }
  ],
  ...
}
```

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
from agents.offline.architect import create_genesis

# 使用你的小说文件
genesis_path = create_genesis("your_novel.txt")
```

### Q4: 小说有什么要求？

- **格式**: 纯文本 `.txt` 文件（UTF-8编码）
- **长度**: 建议 5000-20000 字
- **类型**: 现代都市、悬疑、言情等（暂不支持玄幻、仙侠）
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
   - 阅读 `agents/offline/architect.py` 了解Agent如何工作
   - 查看 `prompts/offline/architect_system.txt` 了解Prompt工程

2. **修改Prompt**
   - 编辑提示词文件，优化提取效果
   - 添加更多的数据字段

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

