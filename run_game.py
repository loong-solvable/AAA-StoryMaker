#!/usr/bin/env python3
"""
⚠️ 此入口已弃用，请使用 dev.py 替代。
将在 v1.0.0 版本移除。

旧功能已移动到:
- dev.py: 开发者入口（推荐）
- play.py: 玩家入口

参数映射:
- --skip-genesis → dev.py --stage game
- --world → dev.py --world
- --novel → dev.py --novel
- --auto → dev.py --auto-test

原始实现已备份到 run_game_old.py
"""
import sys

def main():
    # 直接输出到 stderr 确保用户可见
    print(
        "\n"
        "=" * 60 + "\n"
        "⚠️  run_game.py 已弃用\n"
        "   请使用 python dev.py 替代\n"
        "   此入口将在 v1.0.0 版本移除\n"
        "=" * 60 + "\n",
        file=sys.stderr
    )
    
    # 透传命令行参数
    from dev import main as dev_main
    dev_main(sys.argv[1:])


if __name__ == "__main__":
    main()
