
import shutil
from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).parent.parent

def cleanup():
    print("🧹 开始彻底清理临时文件和生成数据...")
    
    # 1. 清理 runtime 目录下的所有测试数据
    runtime_dir = PROJECT_ROOT / "data" / "runtime"
    if runtime_dir.exists():
        for item in runtime_dir.iterdir():
            if item.is_dir():
                print(f"   🗑️ 删除运行时目录: {item.name}")
                shutil.rmtree(item)
    
    # 2. 清理 data/worlds 下的所有世界数据
    worlds_dir = PROJECT_ROOT / "data" / "worlds"
    if worlds_dir.exists():
        for item in worlds_dir.iterdir():
            if item.is_dir():
                print(f"   🗑️ 删除世界数据: {item.name}")
                shutil.rmtree(item)

    # 3. 清理生成的 NPC Agent 文件
    layer3_dir = PROJECT_ROOT / "agents" / "online" / "layer3"
    for item in layer3_dir.glob("npc_*_*.py"): # 匹配 npc_001_林晨.py 这种格式
        print(f"   🗑️ 删除 Agent 文件: {item.name}")
        item.unlink()
        
    # 4. 清理生成的 Prompt 文件
    prompt_dir = PROJECT_ROOT / "prompts" / "online" / "npc_prompt"
    if prompt_dir.exists():
        for item in prompt_dir.glob("*.txt"):
            print(f"   🗑️ 删除 Prompt 文件: {item.name}")
            item.unlink()

    print("✅ 彻底清理完成")

if __name__ == "__main__":
    cleanup()

