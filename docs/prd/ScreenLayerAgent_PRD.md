# 荧幕层 Agent (Screen Layer Agent) 产品需求文档 (PRD)

**版本**: v1.0
**日期**: 2025-12-18
**状态**: 规划中

---

## 1. Agent 架构与定位

### 1.1 定义
**荧幕层 Agent (Screen Agent)** 是 Infinite Story 系统中的"渲染引擎"和"视觉翻译官"。它是连接"文本逻辑层"（Plot/WS/NPC）与"视听表现层"（用户终端/生图生视频AI）的桥梁。

### 1.2 核心职责
1.  **数据清洗**：过滤中间件日志，提取纯净的剧情内容。
2.  **视觉翻译**：将抽象的文学描述转化为具体的视觉 Prompt。
3.  **双流输出**：
    *   **人流 (Human-Readable)**：面向开发者的实时、干净的终端剧本流。
    *   **机流 (Machine-Readable)**：面向媒体生成 AI 的结构化 JSON 数据流。

### 1.3 文件目录规范
*   **Prompt 存放位置**: `prompts/online/screen_system.txt`
*   **代码实现位置**: `agents/online/layer3/screen_agent.py` (位于表现层，与 NPC Agents 同级或略高一级)
*   **数据输出位置**: `data/runtime/<world_name>_<timestamp>/screen/` (用于存放每一幕的渲染数据)

---

## 2. 输入数据接口 (Inputs)

Screen Agent 接收来自 OS 的聚合数据包，包含以下字段：

```python
class ScreenInput(BaseModel):
    # 基础元数据
    scene_id: int              # 当前幕次
    timestamp: str             # 游戏内时间
    
    # 剧情数据 (来自 NPC & Plot)
    dialogue_log: List[Dict]   # 本轮对话记录
        # 包含: speaker, content, action, emotion, target
    
    # 世界状态 (来自 WS)
    world_state: Dict
        # 包含: location (name, description), time_of_day, weather
    
    # 氛围数据 (来自 Vibe - 预留接口)
    vibe_data: Optional[Dict] = None
        # 预留字段: atmosphere_tags, color_grading, music_style
```

---

## 3. 功能模块一：开发者终端实时显示 (Human-Readable Output)

### 3.1 目标
解决目前终端输出混乱（夹杂路由日志、OS 思考过程）的问题，提供沉浸式的阅读体验。

### 3.2 渲染规则
1.  **屏蔽噪音**：完全屏蔽 OS 的路由决策日志、LLM 思考过程 (`thought`)、JSON 解析错误等系统信息。
2.  **剧本格式**：采用标准剧本格式打印。
3.  **颜色编码**：
    *   **场景头**：使用醒目颜色（如青色）打印场景切换和环境描述。
    *   **旁白**：使用斜体或灰色。
    *   **角色台词**：`[角色名]` 高亮，台词标准色。
    *   **动作**：使用括号包裹并弱化显示 `(动作描述)`。

### 3.3 示例输出
```text
=== 第 3 幕：雨夜街道 ===
[环境] 霓虹灯管映照的湿润地面，蓝紫色调。暴雨如注。

[李默]: (举起枪，手微微颤抖) 别过来！
[神秘人]: (冷笑，从阴影中走出) 你以为那把破枪能伤得了我？
```

---

## 4. 功能模块二：媒体生成数据流 (Machine-Readable JSON)

### 4.1 目标
将文学文本转化为 AI 可理解的视觉语言，为生图 (SD/Midjourney) 和视频生成 (Sora/Runway) 提供"即插即用"的结构化数据。

### 4.2 核心逻辑 (Visual Translation)
Screen Agent 需要内置一个轻量级 LLM 调用或高效的 Prompt 模板，执行以下转化：
*   **情绪 -> 表情 Tag**：`愤怒` -> `furious expression, knitted eyebrows`
*   **环境 -> 氛围 Tag**：`压抑` -> `dim lighting, claustrophobic composition, volumetric fog`
*   **动作 -> 动态描述**：`开枪` -> `muzzle flash, dynamic pose, motion blur`

### 4.3 持久化要求
*   **文件路径**: `data/runtime/<world_name>_<timestamp>/screen/scene_<id>.json`
*   **更新频率**: 每当一轮对话结束或场景发生变化时追加/更新。

### 4.4 JSON 数据结构标准

```json
{
  "meta": {
    "world_name": "Cyberpunk 2077",
    "scene_id": 3,
    "turn_id": 5,
    "timestamp": "2025-12-18 12:00:00"
  },
  "visual_render_data": {
    "summary": "李默在雨夜街头与神秘人对峙",
    
    "environment": {
      "location": "Cyberpunk street at night",
      "lighting": "Neon purple and blue, cinematic lighting, wet ground reflections",
      "weather": "Heavy rain, storm",
      "composition": "Wide shot, low angle"
    },
    
    "characters_in_shot": [
      {
        "name": "李默",
        "is_focus": true,  // 当前镜头焦点
        "visual_tags": "Asian male, 25 years old, black techwear hoodie, messy hair",
        "pose": "aiming a handgun with both hands, dynamic pose",
        "expression": "nervous, sweating, determined eyes, shouting",
        "screen_position": "center"
      },
      {
        "name": "神秘人",
        "is_focus": false,
        "visual_tags": "Tall figure, trench coat, face obscured by shadow",
        "pose": "walking forward calmly, hands in pockets",
        "expression": "smirking visible",
        "screen_position": "background left"
      }
    ],
    
    "media_prompts": {
      "image_gen_prompt": "Cinematic shot of Li Mo aiming a gun in a cyberpunk rainy street, neon purple lighting, heavy rain, 8k, photorealistic, highly detailed, dramatic atmosphere...",
      "video_gen_script": "Camera tracks Li Mo's shaking hands holding the gun, then pans to the mysterious figure approaching from the shadows.",
      "negative_prompt": "low quality, blurry, bad anatomy, deformed hands"
    }
  }
}
```

---

## 5. 交互流程图 (伪代码)

```python
class ScreenAgent:
    def render(self, input_data: ScreenInput):
        # 1. 终端渲染 (实时)
        self._render_to_terminal(input_data)
        
        # 2. 视觉翻译 (异步/批处理)
        visual_data = self._translate_to_visual(input_data)
        
        # 3. 数据持久化
        self._save_json(visual_data)

    def _render_to_terminal(self, data):
        # 清洗并打印格式化文本
        print(f"[{data.speaker}]: {data.content} ({data.action})")

    def _translate_to_visual(self, data):
        # 调用 LLM 将文本转化为 Visual Tags
        prompt = load_prompt("prompts/online/screen_system.txt")
        return llm.invoke(prompt, data)
```

---

## 6. 后续规划 (Roadmap)

1.  **v1.0**: 实现终端清洗和基础 JSON 输出。
2.  **v1.1**: 接入 Vibe 数据，增强环境氛围的描述准确度。
3.  **v2.0**: 开发独立的前端页面，读取 `screen_layer_output.json` 并实时展示生成的图片。

