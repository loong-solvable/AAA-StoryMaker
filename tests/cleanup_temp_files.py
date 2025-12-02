
import shutil
from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).parent.parent

def cleanup():
    print("🧹 开始清理临时文件...")
    
    # 1. 清理 runtime 目录下的测试数据
    runtime_dir = PROJECT_ROOT / "data" / "runtime"
    if runtime_dir.exists():
        for item in runtime_dir.iterdir():
            if item.is_dir() and item.name.startswith("江城市_"):
                print(f"   🗑️ 删除运行时目录: {item.name}")
                shutil.rmtree(item)
    
    # 2. 清理生成的 NPC Agent 文件
    layer3_dir = PROJECT_ROOT / "agents" / "online" / "layer3"
    for item in layer3_dir.glob("npc_*.py"):
        if item.name != "npc_agent.py":  # 保留基类文件（如果有的话，或者确认只有生成的）
             # 确认一下是否有基类文件，通常是 npc_agent.py 但在 layer3 目录下吗？
             # 根据之前的 ls，layer3 下有 __init__.py 和 npc_001_林晨.py
             # 真正的 NPCManager 在 npc_agent.py 中，但我不确定它是否在 layer3 根目录
             # 让我们先只删除 npc_*.py，且排除可能的基础文件
             pass

    # 更安全的做法是只删除我们在测试中生成的特定格式的文件
    # 刚才测试生成的有：npc_001_林晨.py, npc_002_苏晴雨.py, npc_006_神秘电话男子.py
    
    for item in layer3_dir.glob("npc_*_*.py"): # 匹配 npc_001_林晨.py 这种格式
        print(f"   🗑️ 删除 Agent 文件: {item.name}")
        item.unlink()
        
    # 3. 清理生成的 Prompt 文件
    prompt_dir = PROJECT_ROOT / "prompts" / "online" / "npc_prompt"
    if prompt_dir.exists():
        for item in prompt_dir.glob("*.txt"):
            print(f"   🗑️ 删除 Prompt 文件: {item.name}")
            item.unlink()

    print("✅ 清理完成")

if __name__ == "__main__":
    cleanup()

