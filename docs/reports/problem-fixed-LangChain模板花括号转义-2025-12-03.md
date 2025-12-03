# 问题修复报告：LangChain 模板花括号转义问题

**日期**: 2025-12-03  
**问题类型**: 提示词模板格式错误  
**严重程度**: 高（导致游戏无法启动）

---

## 问题描述

在运行游戏时遇到以下错误：

```
ValueError: Invalid variable name 'world_setting.json' in f-string template. 
Variable names cannot contain attribute access (.) or indexing ([]).
```

**错误位置**: `agents/online/layer2/ws_agent.py` 第71行  
**根本原因**: LangChain 的 `ChatPromptTemplate.from_messages()` 会将提示词中的所有 `{变量名}` 格式解析为变量占位符。如果提示词中包含字面量的花括号（如 `{world_setting.json}`），会被误识别为变量名，导致解析错误。

---

## 问题分析

### 1. 错误发生的文件

- **`prompts/online/ws_system.txt`** 第74行：`{world_setting.json}` 
- **`prompts/online/ws_system.txt`** 第77行：`{}`（在反引号内）

### 2. 其他潜在问题文件

检查了所有提示词文件，发现以下情况：

#### ✅ 需要修复的文件
- **`prompts/online/ws_system.txt`**: 包含字面量花括号 `{world_setting.json}` 和 `{}`
- **`prompts/online/plot_system.txt`**: 包含未使用的变量占位符（`{characters_list}`, `{world_setting}` 等），这些变量在代码中未被实际使用，但会被 LangChain 解析

#### ✅ 不需要修复的文件（变量会被代码替换后统一转义）
- **`prompts/online/ws_update_system.txt`**: 变量 `{current_world_state}`, `{scene_memory}`, `{world_setting}` 会被 `os_agent.py` 替换后转义
- **`prompts/online/script_divider.txt`**: 变量 `{current_scene}`, `{current_script}`, `{world_state}` 会被 `os_agent.py` 替换后转义
- **`prompts/online/npc_system.txt`**: 变量会被替换，JSON示例中的花括号已经是转义格式（`{{` 和 `}}`）
- **`prompts/online/os_system.txt`**: 变量会被替换，JSON示例中的花括号已经是转义格式

---

## 修复方案

### LangChain 模板转义规则

在 LangChain 的 `ChatPromptTemplate` 中：
- **变量占位符**: `{变量名}` - 会被解析为变量
- **字面量花括号**: `{{` 和 `}}` - 会被转义为单个 `{` 和 `}`

### 修复内容

#### 1. `prompts/online/ws_system.txt`

**修复前**:
```
- 设置初始场景可以参考{world_setting.json}里的场景也可以自己设定一个新场景。
- **relationship_matrix 初始化时留空 `{}`**（因为还没有角色正式登场互动）
```

**修复后**:
```
- 设置初始场景可以参考{{world_setting.json}}里的场景也可以自己设定一个新场景。
- **relationship_matrix 初始化时留空 `{{}}`**（因为还没有角色正式登场互动）
```

#### 2. `prompts/online/plot_system.txt`

**修复前**:
```
## 1. 花名册 (characters_list.json)
{characters_list}

## 2. 世界设定 (world_setting.json)
{world_setting}
...
```

**修复后**:
```
## 1. 花名册 (characters_list.json)
{{characters_list}}

## 2. 世界设定 (world_setting.json)
{{world_setting}}
...
```

**说明**: 虽然这些变量在代码中未被实际使用，但为了避免 LangChain 解析错误，统一转义为字面量。

---

## 修复效果

修复后，LangChain 可以正确解析提示词模板，不再将字面量花括号误识别为变量占位符。

---

## 相关文件

- `prompts/online/ws_system.txt` - 已修复
- `prompts/online/plot_system.txt` - 已修复
- `agents/online/layer2/ws_agent.py` - 使用修复后的提示词
- `agents/online/layer2/plot_agent.py` - 使用修复后的提示词

---

## 经验总结

1. **提示词模板中的字面量花括号必须转义**: 使用 `{{` 和 `}}` 表示单个 `{` 和 `}`
2. **区分真正的变量占位符和字面量**: 
   - 如果变量会被代码替换，保留为 `{变量名}` 格式
   - 如果是字面量文本，必须转义为 `{{文本}}` 格式
3. **检查所有提示词文件**: 确保没有遗漏的字面量花括号

---

## 测试建议

运行以下命令测试修复效果：

```bash
python main.py
```

如果游戏能正常启动，说明修复成功。

