"""
[已弃用] 运行架构师的入口脚本 - 已更名为 run_genesis.py

请使用新的入口脚本：
    python run_genesis.py

创世组三阶段构建流程：
1. 大中正 - 角色普查
2. Demiurge - 世界设定提取
3. 许劭 - 角色档案制作
"""
import warnings

warnings.warn(
    "run_architect.py已弃用，请使用run_genesis.py",
    DeprecationWarning,
    stacklevel=2
)

# 向后兼容：运行新的入口
from run_genesis import main

if __name__ == "__main__":
    main()
