"""
手动调试 Plot Agent 的小工具，便于查看提示词与输出。

用法示例（在项目根目录执行）:
  python tests/plot_agent_harness.py ^
      --genesis data/runtime/白鹿原_20251219_112721/genesis.json ^
      --world-state data/runtime/白鹿原_20251219_112721/ws/world_state.json ^
      --story-history data/runtime/白鹿原_20251219_112721/all_scene_memory.json ^
      --scene-dialogues data/runtime/白鹿原_20251219_112721/npc/memory/scene_memory.json ^
      --present npc_001 npc_009 npc_010 ^
      --player-action "保持沉默观察"

说明：
- 该脚本不会被测试框架自动运行，主要用于人工查看 Plot Agent 的“思考输入”和“模型输出”。
- 需要联网调用 LLM（与正式运行一致），请在有凭据时使用。
"""

import argparse
import json
import sys
from pathlib import Path

# 确保可以导入项目模块
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.online.layer2.plot_agent import PlotDirector  # noqa: E402


HUMAN_PROMPT_TEMPLATE = """请为当前场景生成剧本指令：

【世界背景】
世界：{world_name}
类型：{genre}

【剧情节点信息】
可用剧情节点：
{available_plots}

已完成节点：{completed_nodes}
当前激活节点：{active_nodes}

【当前情况】
场景编号：第{scene_number}幕
玩家行动：{player_action}
玩家位置：{player_location}
在场角色：{present_characters}

【世界状态摘要】
{world_context}

请按照系统提示词中的格式要求生成场景剧本。"""


def load_json(path: Path):
    if not path:
        return {}
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_args():
    parser = argparse.ArgumentParser(description="Plot Agent 调试脚本（打印提示词与输出）")
    parser.add_argument("--genesis", type=Path, required=True, help="genesis.json 路径")
    parser.add_argument("--world-state", type=Path, help="world_state.json 路径，可选")
    parser.add_argument("--story-history", type=Path, help="all_scene_memory.json 路径，可选")
    parser.add_argument("--scene-dialogues", type=Path, help="scene_memory.json 路径，可选")
    parser.add_argument("--present", nargs="*", help="在场角色 ID 列表，默认取 genesis 中全部角色")
    parser.add_argument("--player-action", default="保持沉默，观察四周", help="玩家最近的行动描述")
    parser.add_argument("--player-location", default="未知地点", help="玩家所在位置")
    return parser.parse_args()


def main():
    args = build_args()

    genesis_data = load_json(args.genesis)
    world_state = load_json(args.world_state) if args.world_state else {}
    story_history = load_json(args.story_history) if args.story_history else {}
    scene_dialogues = load_json(args.scene_dialogues) if args.scene_dialogues else {}

    director = PlotDirector(genesis_data)

    present_chars = args.present or [c.get("id") for c in genesis_data.get("characters", []) if c.get("id")]

    # 构造用于打印的人类提示词文本（便于查看“思考输入”）
    formatted_human_prompt = HUMAN_PROMPT_TEMPLATE.format(
        world_name=genesis_data.get("world", {}).get("title", "未知世界"),
        genre=genesis_data.get("world", {}).get("genre", "未知类型"),
        available_plots="(由 Plot Agent 内部格式化)",
        completed_nodes=", ".join(director.completed_nodes) if director.completed_nodes else "无",
        active_nodes=", ".join(director.active_nodes) if director.active_nodes else "无",
        scene_number=director.scene_count + 1,
        player_action=args.player_action,
        player_location=args.player_location,
        present_characters=", ".join(present_chars) if present_chars else "无",
        world_context=json.dumps(world_state, ensure_ascii=False, indent=2) if world_state else "（未提供）",
    )

    print("====== System Prompt (片段) ======")
    print(director.system_prompt[:800] + ("..." if len(director.system_prompt) > 800 else ""))
    print("\n====== Human Prompt (格式化后) ======")
    print(formatted_human_prompt)

    # 构造 world_context 输入（直接传 world_state）
    world_context_input = world_state if world_state else {"note": "未提供 world_state，使用占位"}

    script = director.generate_scene_script(
        player_action=args.player_action,
        player_location=args.player_location,
        present_characters=present_chars,
        world_context=world_context_input,
    )

    print("\n====== Plot Agent 输出（解析后的剧本字典） ======")
    print(json.dumps(script, ensure_ascii=False, indent=2))

    # 可选：打印 story_history / scene_dialogues 概要，帮助复现上下文
    if story_history:
        print("\n[调试] 已载入 all_scene_memory.json (仅摘要显示)：")
        print(json.dumps(story_history.get("meta", {}), ensure_ascii=False, indent=2))
    if scene_dialogues:
        print("\n[调试] 已载入 scene_memory.json 最近对话：")
        log = scene_dialogues.get("dialogue_log", [])
        for entry in log[-5:]:
            speaker = entry.get("speaker_name", entry.get("speaker_id", "?"))
            content = entry.get("content", "")
            print(f" - {speaker}: {content[:80]}")


if __name__ == "__main__":
    main()

