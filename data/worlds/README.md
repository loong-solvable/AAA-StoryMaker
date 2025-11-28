# 🌍 Worlds - 世界数据目录

> 存放创世组生成的世界数据（新格式：拆分式结构）
>
> **创世组成员**：大中正（角色普查）+ Demiurge（世界观设定）+ Minos（角色档案）

## 📁 目录结构

```
worlds/
├── 修仙世界/                      # 世界名称（自动从小说标题提取）
│   ├── world_setting.json        # 世界观设定
│   ├── characters_list.json      # 角色列表（含重要性评分）
│   └── characters/               # 角色详细档案
│       ├── character_hanli.json
│       ├── character_yunmeng.json
│       └── ...
│
├── 都市职场/                      # 另一个世界
│   ├── world_setting.json
│   ├── characters_list.json
│   └── characters/
│
└── example/                       # 示例世界（供参考）
    ├── world_setting.json
    ├── characters_list.json
    └── characters/
```

## 📄 文件说明

### 1. world_setting.json - 世界观设定

由 **Demiurge（造物主）** 生成，包含：

```json
{
  "meta": {
    "title": "世界标题",
    "genre": "世界类型",
    "time_period": "时代背景"
  },
  "laws_of_physics": [
    "物理法则1",
    "物理法则2"
  ],
  "social_rules": [
    {
      "rule": "社会规则描述",
      "condition": "触发条件",
      "result": "违反后果"
    }
  ],
  "locations": [
    {
      "id": "loc_001",
      "name": "地点名称",
      "description": "地点描述"
    }
  ]
}
```

### 2. characters_list.json - 角色列表

由 **大中正（The Censor）** 生成，快速列出所有角色及其重要性评分：

```json
[
  {
    "id": "hanli",
    "name": "韩立",
    "importance": 1.0
  },
  {
    "id": "yunmeng",
    "name": "云梦",
    "importance": 0.7
  }
]
```

**importance 说明：**
- `1.0` - 主角/核心反派
- `0.5` - 关键配角
- `0.1` - 背景板/路人

### 3. characters/character_<id>.json - 角色详细档案

由 **Minos（角色雕刻师）** 为每个角色生成独立档案：

```json
{
  "id": "hanli",
  "name": "韩立",
  "gender": "男",
  "age": "25岁",
  "importance": 1.0,
  "traits": [
    "剑修",
    "谨慎多疑",
    "实力强大"
  ],
  "behavior_rules": [
    "绝不轻信他人",
    "做事必留后手",
    "遇到危险优先逃跑"
  ],
  "relationship_matrix": {
    "yunmeng": {
      "address_as": "云师姐",
      "attitude": "表面恭敬，内心防备"
    }
  },
  "possessions": [
    "紫霄剑",
    "储物袋"
  ],
  "current_appearance": "身穿青衫，腰挂长剑...",
  "voice_samples": [
    "在下韩立，见过云师姐。",
    "此事蹊跷，需从长计议。"
  ]
}
```

## 🚀 使用方法

### 生成新世界

```bash
# 运行创世组，自动生成世界数据
python run_architect.py
```

### 加载世界数据（Python）

```python
from pathlib import Path
from initial import load_world_data, load_world_setting

# 方式1：加载完整世界数据
world_dir = Path("data/worlds/修仙世界")
world_data = load_world_data(world_dir)

# 访问数据
world_setting = world_data["world_setting"]
characters_list = world_data["characters_list"]
characters = world_data["characters"]

# 方式2：只加载世界设定
world_setting = load_world_setting(world_dir)

# 方式3：只加载特定角色
from initial.init_world import load_character_details
hanli_data = load_character_details(world_dir, "hanli")
```

### 列出所有可用世界

```python
from initial.init_world import list_available_worlds

worlds = list_available_worlds()
print(worlds)  # ['修仙世界', '都市职场', 'example']
```

## 🔄 与旧格式对比

### 旧格式（Genesis.json）

```
data/
└── genesis/
    └── genesis.json  # 所有数据在一个大文件里
```

**缺点：**
- ❌ 文件庞大，难以维护
- ❌ 修改一个角色需要重新解析整个文件
- ❌ LLM无法针对性地读取某部分数据

### 新格式（Worlds拆分式）

```
data/
└── worlds/
    └── 世界名/
        ├── world_setting.json      # 世界观独立
        ├── characters_list.json    # 角色索引独立
        └── characters/             # 每个角色独立
```

**优点：**
- ✅ 模块化清晰，职责单一
- ✅ 按需加载，性能更好
- ✅ 易于修改和维护
- ✅ 便于LLM针对性读取

## 📝 注意事项

1. **世界名称：** 自动从小说的 `world.title` 提取，确保唯一性
2. **字符编码：** 所有JSON文件使用UTF-8编码
3. **向后兼容：** 旧的Genesis格式仍保留在 `data/genesis/`，新旧格式可共存
4. **角色ID：** 建议使用拼音或英文，避免特殊字符

## 🔗 相关文档

- [创世组使用说明](../../README.md)
- [角色卡样本](../samples/README.md)
- [初始化模块文档](../../initial/README.md)

---

**创建日期：** 2024-11-26  
**更新记录：** 从单文件Genesis迁移到拆分式结构

