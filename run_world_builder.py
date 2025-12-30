#!/usr/bin/env python3
"""
⚠️ 此入口已弃用，请使用 dev.py 替代。
将在 v1.0.0 版本移除。

旧功能已移动到:
- dev.py --stage genesis: 创世组
- dev.py --continue-build: 断点续传

参数映射:
- --novel → dev.py --stage genesis --novel
- --resume <世界名> → dev.py --stage genesis --continue-build <世界名>
- --list → dev.py --list-worlds

原始实现已备份到 run_world_builder_old.py
"""
import sys

def main():
    # 直接输出到 stderr 确保用户可见
    print(
        "\n"
        "=" * 60 + "\n"
        "⚠️  run_world_builder.py 已弃用\n"
        "   请使用 python dev.py --stage genesis 替代\n"
        "   此入口将在 v1.0.0 版本移除\n"
        "=" * 60 + "\n",
        file=sys.stderr
    )
    
    # 转换参数并调用 dev.py
    args = sys.argv[1:]
    new_args = []
    
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--novel":
            new_args.extend(["--stage", "genesis", "--novel"])
            if i + 1 < len(args):
                new_args.append(args[i + 1])
                i += 1
        elif arg == "--resume":
            new_args.extend(["--stage", "genesis", "--continue-build"])
            if i + 1 < len(args):
                new_args.append(args[i + 1])
                i += 1
        elif arg == "--list":
            new_args.append("--list-worlds")
        else:
            new_args.append(arg)
        i += 1
    
    # 如果没有参数，默认添加 --stage genesis
    if not new_args:
        new_args = ["--stage", "genesis"]
    
    from dev import main as dev_main
    dev_main(new_args)


if __name__ == "__main__":
    main()
