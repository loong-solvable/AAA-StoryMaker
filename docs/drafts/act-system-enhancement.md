# Draft: 幕目标系统增强方案

## 需求总结 (来自用户)

1. **NPC扮演质量**: 需要测试和优化，确保NPC能很好地进行角色扮演
2. **Plot剧本质量**: 需要测试和优化，确保剧本按计划产出
3. **每幕主要目标**: 确保每幕都有明确的主要目标
4. **NPC幕内小目标**: 每个NPC在每幕都应有自己的小目标
5. **NPC主动推进**: NPC应该主动向自己的目标推进，而不仅是被动响应
6. **玩家目标显示**: 为玩家在每幕增加可见的"目标"，提供导向性
7. **目标达成判断**: 当相关Agent判断目标达成时，结束此幕进入下一幕

---

## 现有系统分析

### 1. Conductor (中枢指挥家) - `agents/online/layer1/conductor.py`

**现有能力:**
- 管理 `ActObjective` (目标描述、完成条件、max_turns)
- `_create_default_act()` 生成默认幕配置
- `evaluate_progress()` 检查条件达成度
- `advance_to_next_act()` 执行幕转换
- 支持多种完成条件: `npc_interaction_count`, `location_visited`, `event_occurred`, `turns_elapsed`, `flag`

**关键结构:**
```python
@dataclass
class ActObjective:
    objective_id: str
    description: str           # 目标描述（给玩家看）
    internal_goal: str         # 内部目标（给Plot用）
    completion_conditions: List[Dict]
    failure_conditions: List[Dict]
    max_turns: int = 15
    urgency_curve: str = "linear"
    plot_guidance: str = ""
```

**默认幕配置 (line 618-636):**
```python
def _create_default_act(self) -> Dict[str, Any]:
    return {
        "act_number": 1,
        "act_name": "自由探索",
        "objective": {
            "objective_id": "default_explore",
            "description": "自由探索这个世界，与周围的人和事互动",
            "internal_goal": "让玩家熟悉世界和角色",
            "completion_conditions": [
                {"type": "turns_elapsed", "min_turns": 8},
                {"type": "npc_interaction_count", "threshold": 3}
            ],
            "max_turns": 25,
            "urgency_curve": "linear",
            "plot_guidance": "保持开放，响应玩家的探索行为..."
        }
    }
```

**问题:**
- 默认幕只有一个，缺少多幕配置
- genesis_data 中通常没有 `act_definitions`

### 2. NPCAgent - `agents/online/layer3/npc_agent.py`

**现有能力:**
- `react()` / `async_react()` 生成NPC响应
- 情感状态追踪: `emotional_state` 包含 `current_mood`, `attitude_toward_player`, `trust_level`
- 滑动窗口对话历史 (30条)
- `decide_behavior()` 决定行为模式 (respond/observe/autonomous/initiate)
- `take_initiative()` 主动发起行为

**Prompt模板 (`prompts/online/npc_system.txt`):**
- 支持 `{objective}` 占位符 - NPC的核心目标
- 支持 `{role_in_scene}` - 角色定位
- 支持 `{emotional_arc}` - 情绪曲线
- **问题**: 当前 `objective` 字段很少被填充，多为默认值

**NPC幕级指令 (Conductor中):**
```python
@dataclass
class NPCActBriefing:
    npc_id: str
    npc_name: str
    role_in_act: str = "参与者"  # 引导者/阻碍者/旁观者/参与者
    knowledge_scope: List[str]
    forbidden_knowledge: List[str]
    emotional_journey: str  # "从冷漠到好奇"
    key_lines: List[str]
```

### 3. PlotDirector - `agents/online/layer2/plot_agent.py`

**现有能力:**
- `generate_scene_script()` 生成场景剧本
- 接收 `act_context` (目标、紧迫度、剩余回合)
- 紧迫度响应策略已实现 (0.3/0.6/0.8阈值)
- 输出【剧情】【角色调度】【幕进度评估】结构
- 支持 `READY_TO_END`/`FORCE_END`/`CONTINUE` 信号

**幕完成信号解析 (line 446-463):**
```python
# 解析幕完成信号
signal_match = re.search(r'\*\*幕完成信号\*\*:\s*(CONTINUE|READY_TO_END|FORCE_END)', ...)
if signal_match:
    result["act_completion"]["signal"] = signal_match.group(1).upper()
```

### 4. GameEngine - `game_engine.py`

**输出渲染:**
- `_format_opening()` - 开场文本格式化 (line 1250-1273)
- `_render_output()` - 回合输出渲染 (line 1275-1326)

**当前开场格式:**
```
======================================================================
  🎭 {世界标题}
======================================================================

{氛围描写}

💭 {导演笔记}

你的故事开始了...

======================================================================
```

**问题:** 没有显示当前幕目标给玩家

### 5. 幕转换逻辑 (GameEngine line 925-944)

```python
# 检查 Plot Agent 返回的幕完成信号
act_completion = script.get("act_completion", {})
act_signal = act_completion.get("signal", "CONTINUE")

if act_signal in ("READY_TO_END", "FORCE_END"):
    outcome = "success" if act_signal == "READY_TO_END" else "timeout"
    self.conductor.advance_to_next_act(outcome)
```

---

## 技术决策

### 决策1: 默认幕配置方案
**选择**: 扩展 `_create_default_act()` 为 `_create_default_acts()` 返回多幕配置列表
- 第一幕: 探索与熟悉
- 第二幕: 发现问题
- 第三幕: 解决与行动
- 后续幕: 开放式发展

### 决策2: 玩家目标显示位置
**选择**: 在 `_format_opening()` 和 `_render_output()` 中添加目标显示区块
- 格式: `🎯 当前目标: {objective_description}`

### 决策3: NPC目标推进机制
**选择**: 增强 `npc_system.txt` 提示词，添加"主动推进"指令段落

### 决策4: 测试策略
**选择**: 手动验证 (项目无自动化测试基础设施)

---

## 开放问题

1. ~~默认幕数量~~: 已决定 3-4 个默认幕
2. ~~目标显示格式~~: 已决定使用 🎯 图标
3. ~~测试方案~~: 已决定手动验证
