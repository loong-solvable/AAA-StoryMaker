# problem-fixed-在线LLM连接超时-2026-01-21

## 问题概述
在线运行时遇到 OpenRouter 连接异常，调用耗时过长，导致玩家等待时间过久。

## 影响范围
- 在线 NPC 角色演绎
- 在线对话路由
- 逻辑审查官验证

## 修复方案
- 为在线交互设置独立超时与重试参数，避免长时间阻塞。
- 在线路由使用专用 LLM，缩短失败等待时间。

## 修改内容
- `config/settings.py` 增加 `ONLINE_LLM_TIMEOUT` 与 `ONLINE_LLM_MAX_RETRIES`
- `utils/llm_factory.py` 支持为 LLM 指定超时与重试
- `agents/online/layer3/npc_001_林晨.py` / `npc_002_苏晴雨.py` 使用在线超时与重试
- `agents/online/layer1/logic_agent.py` 使用在线超时与重试
- `agents/online/layer1/os_agent.py` 路由使用专用 LLM

## 结果验证
- 在线调用失败时可更快返回并走降级逻辑，不再长时间阻塞。
