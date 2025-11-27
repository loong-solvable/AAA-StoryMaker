# 📦 样本数据

本目录存放角色卡JSON样本和其他示例数据。

---

## 📋 文件说明

### 角色卡样本

- **NPC角色卡样本.json** - NPC角色卡设计规范
  - 完整的字段说明
  - importance权重系统
  - relationship_matrix社交矩阵
  - behavior_rules行为准则
  - voice_samples语言样本

- **用户角色卡样本.json** - 玩家角色卡设计规范
  - 轻量化设计
  - 只保留必要字段
  - 重点在社交关系

---

## 🎯 使用方式

### 创建新角色

参考样本文件的格式，创建你自己的角色：

```json
{
  "id": "npc_001",
  "name": "角色名称",
  "importance": 85.0,
  "traits": ["标签1", "标签2"],
  "behavior_rules": ["规则1", "规则2"],
  "relationship_matrix": {
    "user": {
      "address_as": "称呼",
      "attitude": "态度描述"
    }
  },
  "voice_samples": ["台词1", "台词2"]
}
```

### 示例世界

完整的示例世界数据在：`../worlds/`（拆分式结构）

查看新的世界数据格式：`../worlds/README.md`

---

## 📚 相关文档

- 数据模型实现：`../../utils/character_data.py`
- NPC Agent使用：`../../agents/online/layer3/npc_agent.py`

