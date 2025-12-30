#!/usr/bin/env python3
"""
⚠️ 此入口已弃用，请使用 play.py 替代。
将在 v1.0.0 版本移除。

旧功能已移动到:
- play.py: 玩家入口（推荐）
- dev.py: 开发者入口

原始实现已备份到 main_old.py
"""
import sys

def main():
    # 直接输出到 stderr 确保用户可见
    print(
        "\n"
        "=" * 60 + "\n"
        "⚠️  main.py 已弃用\n"
        "   请使用 python play.py 替代\n"
        "   此入口将在 v1.0.0 版本移除\n"
        "=" * 60 + "\n",
        file=sys.stderr
    )
    
    # 透传命令行参数
    from play import main as play_main
    play_main(sys.argv[1:])


if __name__ == "__main__":
    main()
