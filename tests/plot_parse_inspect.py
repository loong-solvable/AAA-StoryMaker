"""
临时调试脚本：检查 Plot 输出是否包含可解析的角色 ID。

用法示例（在项目根目录）:
  python tests/plot_parse_inspect.py --runtime "data/runtime/白鹿原_20251219_112721"

脚本会读取 runtime/plot/current_script.json 的 content 字段，使用与初始化阶段相同的正则规则尝试解析
入场/在场/离场角色，并打印结果（包含是否匹配到 npc_xxx）。
"""

import argparse
import json
import re
from pathlib import Path


def parse_characters_from_plot(content: str):
    entry_pattern = r"\*\*入场\*\*:\s*(\S+)\s*\((\w+)\)\s*\[First Appearance:\s*(True|False)\]"
    present_pattern = r"\*\*在场\*\*:\s*(\S+)\s*\((\w+)\)"
    exit_pattern = r"\*\*离场\*\*:\s*(\S+)\s*\((\w+)\)"
    chars = []
    for match in re.finditer(entry_pattern, content, re.IGNORECASE):
        name, cid, first_app = match.groups()
        chars.append({"id": cid, "name": name, "first_appearance": first_app.lower() == "true", "source": "入场"})
    for match in re.finditer(present_pattern, content, re.IGNORECASE):
        name, cid = match.groups()
        if cid not in [c["id"] for c in chars]:
            chars.append({"id": cid, "name": name, "first_appearance": False, "source": "在场"})
    for match in re.finditer(exit_pattern, content, re.IGNORECASE):
        name, cid = match.groups()
        if cid not in [c["id"] for c in chars]:
            chars.append({"id": cid, "name": name, "first_appearance": False, "source": "离场"})
    return chars


def main():
    ap = argparse.ArgumentParser(description="检查 Plot 剧本中的角色解析情况")
    ap.add_argument("--runtime", required=True, type=Path, help="运行时目录，例如 data/runtime/白鹿原_20251219_112721")
    args = ap.parse_args()

    script_path = args.runtime / "plot" / "current_script.json"
    if not script_path.exists():
        print(f"[ERROR] 找不到 {script_path}")
        return

    data = json.load(open(script_path, "r", encoding="utf-8"))
    content = data.get("content") or ""

    print(f"=== 检查 {script_path} ===")
    print(f"内容前 500 字符:\n{content[:500]}\n")

    chars = parse_characters_from_plot(content)
    print(f"匹配到的角色数: {len(chars)}")
    for c in chars:
        print(f" - {c['name']} ({c['id']}), 来源: {c['source']}, 首次: {c['first_appearance']}")

    # 兜底检测 npc_xxx ID 是否出现过
    id_hits = re.findall(r"npc_\\d+", content)
    print(f"\n全文出现的 npc_* ID: {set(id_hits)}")


if __name__ == "__main__":
    main()
