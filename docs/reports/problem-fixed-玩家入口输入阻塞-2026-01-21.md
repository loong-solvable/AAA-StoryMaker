# problem-fixed-玩家入口输入阻塞-2026-01-21

## 问题概述
玩家入口在轮到玩家说话时无法获得输入机会，导致交互卡住。

## 影响范围
- 新玩家入口 `player_entry.py`
- 统一入口流程 `cli/entry_flow.py`

## 诊断过程
1. 对比 `play.py` 的原生 OS Agent 交互流程。
2. 检查新入口使用的 `SessionFactory` 与 `OSAgentSession`，发现输入回调与 OS Agent 交互时序不一致。
3. 结论：需要将新入口的 OS Agent 流程改为“按需回调输入”的原生模式。

## 修复方案
- 在 `cli/entry_flow.py` 增加原生 OS Agent 运行循环，复用 `play.py` 的输入回调模式。
- 对玩家/开发者模式输出密度做区分，但执行流程一致。
- 修复 `run_scene_loop()` 的暂停机制，确保回调返回空时能正确返回并记录下一位发言者。

## 修改内容
- 新增 `run_osagent_loop()` 并在 `run_game_session()` 中优先使用。
- 玩家模式：提示最少信息，仅在需要时交互。
- 开发者模式：额外输出运行细节与状态信息。
- `agents/online/layer1/os_agent.py` 增加 `start_speaker_id`，支持断点续演与暂停返回。
- `cli/osagent_session.py` 记录并传递 `next_speaker_id`，避免话筒顺序重置。

## 结果验证
- 入口流程中玩家输入回调已与 OS Agent 的输入时机对齐。
- 若需要完整验证，可在本地运行 `python player_entry.py` 进行交互测试。
