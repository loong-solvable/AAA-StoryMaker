import subprocess
import sys
import shutil
import os
from pathlib import Path

def install_requirements():
    print("Checking requirements...")
    try:
        import PyInstaller
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

def build():
    # Clean dist/build
    print("Cleaning previous builds...")
    shutil.rmtree("dist", ignore_errors=True)
    shutil.rmtree("build", ignore_errors=True)

    # Common arguments
    # Note: On Windows, use ; for separator, on Linux/Mac use :
    sep = ";" if os.name == 'nt' else ":"
    
    common_args = [
        "--noconfirm",
        "--onefile",
        "--console",
        f"--add-data", f"prompts{sep}prompts",
        f"--add-data", f"agents{sep}agents",  # For dynamic loading in play.py
        f"--add-data", f"run_world_builder_old.py{sep}.",  # World building module
        "--hidden-import", "initial_Illuminati",
        "--hidden-import", "run_world_builder_old",  # World builder
        "--hidden-import", "agents.offline.stage1_character_census",
        "--hidden-import", "agents.offline.stage2_world_extractor", 
        "--hidden-import", "agents.offline.stage3_character_architect",
        "--hidden-import", "tiktoken_ext.openai_public", # Common missing hidden import for langchain
        "--hidden-import", "tiktoken_ext",
    ]

    # Build Play (Infinite Story)
    print("Building Infinite Story (play.py)...")
    subprocess.check_call([
        "pyinstaller",
        *common_args,
        "--name", "InfiniteStory",
        "play.py"
    ])

    # Build Main (Legacy wrapper)
    print("Building Legacy Launcher (main.py)...")
    subprocess.check_call([
        "pyinstaller",
        *common_args,
        "--name", "StoryMaker_Legacy",
        "main.py"
    ])
    
    print("\nBuild Complete!")
    print(f"Executables are in: {Path('dist').absolute()}")

if __name__ == "__main__":
    install_requirements()
    build()
