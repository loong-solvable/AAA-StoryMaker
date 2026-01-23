#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
开发者入口（新）
输出更多上下文与状态信息，方便定位问题。
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from cli.entry_flow import run_entry


def main() -> None:
    run_entry("dev")


if __name__ == "__main__":
    main()
