# -*- mode: python ; coding: utf-8 -*-

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
