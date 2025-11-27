# 临时工具文件夹 (Temporary Tools)

这个文件夹包含临时的辅助工具脚本，用于解决开发阶段的特定问题。

⚠️ **注意**：这些工具都是临时性的，在项目成熟后将被移除或集成到主系统中。

## 工具列表

### 1. retry_failed_characters.py
**功能**：重试失败的角色创建

**使用场景**：
当architect运行时因为API限流（429 Too Many Requests）导致某些角色创建失败时使用。

**使用方法**：
```bash
# 激活虚拟环境
.\venv\Scripts\activate

# 运行工具
python temp/retry_failed_characters.py <世界名称> [小说路径]

# 示例
python temp/retry_failed_characters.py 未知世界 data/novels/example_novel.txt
```

**工作流程**：
1. 扫描指定世界的所有角色文件
2. 识别包含`error`字段或不存在的角色
3. 自动重试创建这些失败的角色
4. 添加延迟机制避免再次触发API限流

**参数说明**：
- `世界名称`：必填，对应`data/worlds/`下的世界文件夹名称
- `小说路径`：可选，原始小说文件路径。如不提供，程序会提示输入

**配置选项**（可在代码中调整）：
- `retry_delay`: 每次重试之间的延迟秒数（默认10秒）
- `max_retries`: 最大重试次数（默认3次）

**日志文件**：
- 运行日志保存在：`logs/character_retry.log`

---

## 开发计划

将来项目成熟后，这些临时工具将被以下功能替代：

1. **多LLM负载均衡**：在architect中自动切换不同的LLM API，避免单一API限流
2. **智能重试机制**：在architect中内置指数退避重试逻辑
3. **断点续传**：architect支持从中断点继续执行
4. **并发控制**：限制同时发送的API请求数量

届时，`temp/`文件夹将被删除。

