#!/usr/bin/env python3
"""
AAA-StoryMaker EXE 打包脚本

使用方法:
    pip install pyinstaller
    python build_exe.py

输出:
    dist/InfiniteStory/
        ├── InfiniteStory.exe    # 主程序
        ├── data/                 # 数据目录
        ├── prompts/              # 提示词目录
        ├── logs/                 # 日志目录
        └── template.env          # 配置模板
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent

def check_pyinstaller():
    """检查 PyInstaller 是否安装"""
    try:
        import PyInstaller
        print(f"[OK] PyInstaller {PyInstaller.__version__} installed")
        return True
    except ImportError:
        print("[!] PyInstaller not installed, installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
        return True

def create_spec_file():
    """创建 PyInstaller spec 文件"""
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

block_cipher = None

# 项目根目录
PROJECT_ROOT = Path(SPECPATH)

# 需要包含的数据文件
datas = [
    # 提示词文件
    (str(PROJECT_ROOT / 'prompts'), 'prompts'),
    # 配置模板
    (str(PROJECT_ROOT / 'template.env'), '.'),
]

# 需要包含的隐式导入
hiddenimports = [
    'langchain',
    'langchain_core',
    'langchain_community',
    'langchain_openai',
    'zhipuai',
    'openai',
    'httpx',
    'pydantic',
    'colorlog',
    'dotenv',
    'uvicorn',
    'fastapi',
    'starlette',
    'anyio',
]

a = Analysis(
    ['play.py'],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'cv2',
        'torch',
        'tensorflow',
        'tkinter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='InfiniteStory',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # 控制台程序
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 可以添加图标: icon='icon.ico'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='InfiniteStory',
)
'''
    
    spec_path = PROJECT_ROOT / "InfiniteStory.spec"
    with open(spec_path, "w", encoding="utf-8") as f:
        f.write(spec_content)
    
    print(f"[OK] Created {spec_path}")
    return spec_path

def build_exe():
    """执行打包"""
    print("\n" + "=" * 50)
    print("Building EXE...")
    print("=" * 50 + "\n")
    
    spec_path = PROJECT_ROOT / "InfiniteStory.spec"
    
    # 运行 PyInstaller
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--clean", str(spec_path)],
        cwd=str(PROJECT_ROOT)
    )
    
    if result.returncode != 0:
        print("\n[FAILED] Build failed!")
        return False
    
    return True

def copy_additional_files():
    """复制额外需要的文件"""
    dist_dir = PROJECT_ROOT / "dist" / "InfiniteStory"
    
    if not dist_dir.exists():
        print("[FAILED] Dist directory not found")
        return False
    
    print("\nCopying additional files...")
    
    # 1. 创建空的 data 目录结构
    data_dirs = [
        "data/novels",
        "data/worlds", 
        "data/runtime",
        "data/saves",
        "logs",
    ]
    
    for dir_path in data_dirs:
        target = dist_dir / dir_path
        target.mkdir(parents=True, exist_ok=True)
        print(f"   [OK] Created {dir_path}/")
    
    # 2. 复制示例小说（如果存在）
    novels_src = PROJECT_ROOT / "data" / "novels"
    if novels_src.exists():
        novels_dst = dist_dir / "data" / "novels"
        for novel in novels_src.glob("*.txt"):
            shutil.copy2(novel, novels_dst)
            print(f"   [OK] Copied novel: {novel.name}")
    
    # 3. 复制已有的世界数据（可选）
    worlds_src = PROJECT_ROOT / "data" / "worlds"
    if worlds_src.exists():
        worlds_dst = dist_dir / "data" / "worlds"
        for world_dir in worlds_src.iterdir():
            if world_dir.is_dir():
                shutil.copytree(world_dir, worlds_dst / world_dir.name, dirs_exist_ok=True)
                print(f"   [OK] Copied world: {world_dir.name}")
    
    # 4. 创建启动说明
    readme_content = """# Infinite Story

## Quick Start

1. Configure API Key
   - Copy template.env to .env
   - Edit .env, fill in your API key

2. Run Game
   - Double-click InfiniteStory.exe

## Directory Structure

- data/novels/   - Put novel files (.txt) here
- data/worlds/   - Parsed world data
- data/runtime/  - Game saves
- prompts/       - AI prompts (do not delete)
- logs/          - Runtime logs

## Get API Key

Recommended: OpenRouter (free quota)
1. Visit https://openrouter.ai/
2. Register
3. Create API Key in settings
4. Fill in .env OPENROUTER_API_KEY

Enjoy your infinite story!
"""
    
    readme_path = dist_dir / "README.txt"
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)
    print(f"   [OK] Created README.txt")
    
    return True

def main():
    # 设置控制台编码
    if sys.platform == "win32":
        os.system("chcp 65001 >nul 2>&1")
    
    print("=" * 50)
    print("AAA-StoryMaker EXE Build Tool")
    print("=" * 50)
    print()
    
    # 1. 检查 PyInstaller
    if not check_pyinstaller():
        return 1
    
    # 2. 创建 spec 文件
    create_spec_file()
    
    # 3. 执行打包
    if not build_exe():
        return 1
    
    # 4. 复制额外文件
    if not copy_additional_files():
        return 1
    
    # 5. 完成
    dist_dir = PROJECT_ROOT / "dist" / "InfiniteStory"
    print("\n" + "=" * 50)
    print("[SUCCESS] Build completed!")
    print("=" * 50)
    print(f"\nOutput: {dist_dir}")
    print("\nUsage:")
    print("   1. Copy InfiniteStory folder to your friend")
    print("   2. Configure .env file (fill in API key)")
    print("   3. Double-click InfiniteStory.exe")
    print()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
