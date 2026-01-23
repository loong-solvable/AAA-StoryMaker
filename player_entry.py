#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
玩家入口（新）
只展示必要信息，保证沉浸与简洁。
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from cli.entry_flow import run_entry


def main() -> None:
    run_entry("player")


if __name__ == "__main__":
    main()
