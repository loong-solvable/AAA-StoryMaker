#!/usr/bin/env python3
"""
⚠️ 此入口已弃用，请使用新架构入口替代。
将在 v1.0.0 版本移除。

推荐入口:
- player_entry.py: 玩家入口（使用 GameEngine + Conductor）
- developer_entry.py: 开发者入口（使用 GameEngine + Conductor）
- api_server.py: API 服务器（支持多用户会话）

新架构优势:
- Conductor 幕管理系统（动态幕转换、紧迫度驱动）
- 三模式分流优化
- NPC 幕级指令支持
"""
import sys

def main():
    print(
        "\n"
        "=" * 60 + "\n"
        "⚠️  play_game.py 已弃用\n"
        "   请使用 python player_entry.py 替代\n"
        "   此入口将在 v1.0.0 版本移除\n"
        "=" * 60 + "\n",
        file=sys.stderr
    )
    
    # 转发到新入口
    from player_entry import main as player_main
    player_main()


if __name__ == "__main__":
    main()
