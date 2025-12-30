#!/usr/bin/env python3
"""
⚠️ 此入口已弃用，请使用 dev.py 替代。
将在 v1.0.0 版本移除。

旧功能已移动到:
- dev.py --stage genesis: 创世组

原始实现已备份到 run_creator_god_old.py
"""
import sys

def main():
    # 直接输出到 stderr 确保用户可见
    print(
        "\n"
        "=" * 60 + "\n"
        "⚠️  run_creator_god.py 已弃用\n"
        "   请使用 python dev.py --stage genesis 替代\n"
        "   此入口将在 v1.0.0 版本移除\n"
        "=" * 60 + "\n",
        file=sys.stderr
    )
    
    # 转换参数并调用 dev.py
    args = ["--stage", "genesis"] + sys.argv[1:]
    
    from dev import main as dev_main
    dev_main(args)


if __name__ == "__main__":
    main()
