# Draft: Fix Act Never Ends Issue

## Requirements (confirmed)

### Problem Statement
幕（Act）永远不会自然结束。玩家必须使用显式触发词（如"结束"、"告辞"）才能推进幕转换。

### Root Cause Analysis (from user input)

1. **默认幕定义太宽松**:
   - `max_turns: 999` -> 永远不会超时
   - `completion_conditions: []` -> 永远无法完成
   - 结果：`progress` 永远接近 0%，`urgency` 永远接近 0

2. **Plot Prompt 有策略但无执行力**:
   - Prompt 中确实写了紧迫度响应策略（0.3/0.6/0.8 阈值）
   - 但由于 `urgency` 始终为 0，这些策略**永远不会触发**

3. **缺少幕完成信号**:
   - 没有机制让 Plot Agent 告诉系统"这幕可以结束了"
   - 只能等玩家说"结束/告辞/再见"等显式触发词

## Technical Decisions

### Decision 1: Default max_turns
- **选择**: 将默认 `max_turns` 从 999 改为 15
- **理由**: 
  - 15 回合是一个合理的场景长度
  - 与项目中其他地方使用的值一致（os_agent.py 和 osagent_session.py 都使用 15）
  - 紧迫度曲线可以正常工作（0 -> 1 在 15 回合内）

### Decision 2: Default completion_conditions
- **选择**: 添加基于回合的默认完成条件
- **理由**:
  - 即使没有明确目标，回合数也可以作为自然的节奏标记
  - 保持灵活性，不强制严格的完成条件

### Decision 3: Plot Agent Completion Signal
- **选择**: 添加【幕完成建议】板块到 Plot Prompt，并在 PlotDirector 中解析
- **理由**:
  - 让 Plot 根据剧情自然走向给出完成建议
  - 不破坏现有数据结构（向后兼容）
  - 信号是建议性的，不是强制性的

## Research Findings

### From conductor.py
- `_create_default_act()` 第618-633行：创建默认幕定义
- `advance_to_next_act()` 第889-939行：创建后续幕定义
- `_calculate_urgency()` 第683-707行：紧迫度计算逻辑
- `_layer0_rule_check()` 第319-384行：幕转换触发条件

### From plot_system.txt
- 紧迫度响应策略定义在第46-52行
- 输出格式使用【】标题（第79-95行）
- 现有板块：【剧情】【世界与物理事件】【角色登场与调度】

### From plot_agent.py
- `_parse_text_script()` 第339-436行：解析文本格式剧本
- 使用正则表达式解析【】板块
- 返回的 script 字典被 GameEngine 使用

### From game_engine.py
- 第454-461行：检查幕转换条件
- 使用 `act_evaluation.get("should_advance")` 判断是否推进

## Scope Boundaries

### INCLUDE:
1. 修改 conductor.py 的 `_create_default_act()` 方法
2. 修改 conductor.py 的 `advance_to_next_act()` 方法
3. 修改 plot_system.txt 添加幕完成建议板块
4. 修改 plot_agent.py 解析幕完成信号

### EXCLUDE:
- 不修改现有数据结构（TurnDecision, ActContext）
- 不修改 genesis 数据格式
- 不修改 game_engine.py 的幕转换逻辑（仅使用现有接口）
- 不添加新的依赖

## Open Questions
- [RESOLVED] 测试策略：项目有 pytest 测试文件（test_three_scenes_flow.py 等），可以手动验证

## Constraints from User
1. 每个修改都要经过严格审核和测试
2. 严禁引入 bug
3. 修改要有良好的兼容性
4. 现有数据结构必须保持向后兼容
