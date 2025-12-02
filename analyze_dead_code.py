"""
分析项目中的死文件和死代码
找出从未被导入使用的Python文件
"""
import ast
import os
from pathlib import Path
from collections import defaultdict
from typing import Dict, Set, List, Tuple

# 项目根目录
PROJECT_ROOT = Path(__file__).parent

# 排除的目录和文件
EXCLUDED_DIRS = {
    '__pycache__',
    'venv',
    '.git',
    'logs',
    'data/runtime',  # 运行时数据，不是代码
    'data/genesis',  # 生成的数据
    'data/worlds',   # 世界数据
    'data/novels',   # 小说数据
    'data/samples',  # 样本数据
}

EXCLUDED_FILES = {
    'analyze_dead_code.py',  # 本脚本自身
}

# 入口文件（这些文件可能被直接运行，即使不被导入）
ENTRY_POINTS = {
    'main.py',
    'play_game.py',
    'run_game.py',
    'run_creator_god.py',
    'initial_Illuminati.py',
    'test_phase2_demo.py',
    'temp/retry_failed_characters.py',
}

# 测试文件（这些文件可能被测试框架运行）
TEST_FILES = {
    'tests/run_all_tests.py',
    'tests/cleanup_full.py',
    'tests/cleanup_temp_files.py',
    'tests/setup_test_data.py',
}


def get_all_python_files() -> Set[Path]:
    """获取所有Python文件"""
    files = set()
    for root, dirs, filenames in os.walk(PROJECT_ROOT):
        # 排除不需要的目录
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        
        for filename in filenames:
            if filename.endswith('.py'):
                filepath = Path(root) / filename
                rel_path = filepath.relative_to(PROJECT_ROOT)
                
                # 检查是否在排除的目录中
                if any(excluded in str(rel_path) for excluded in EXCLUDED_DIRS):
                    continue
                
                # 检查是否在排除的文件列表中
                if str(rel_path) in EXCLUDED_FILES:
                    continue
                
                files.add(rel_path)
    
    return files


def extract_imports(filepath: Path) -> Set[str]:
    """提取文件中的所有导入"""
    imports = set()
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content, filename=str(filepath))
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split('.')[0])
    
    except Exception as e:
        print(f"⚠️  解析文件失败 {filepath}: {e}")
    
    return imports


def module_to_file(module_name: str, files: Set[Path]) -> List[Path]:
    """将模块名转换为可能的文件路径"""
    candidates = []
    
    # 直接匹配
    for f in files:
        if f.stem == module_name or f.stem == module_name.replace('.', '_'):
            candidates.append(f)
    
    # 路径匹配
    module_parts = module_name.split('.')
    for f in files:
        parts = f.parts[:-1]  # 排除文件名
        if len(parts) >= len(module_parts):
            if list(parts[-len(module_parts):]) == module_parts:
                candidates.append(f)
    
    return candidates


def analyze_imports():
    """分析导入关系"""
    all_files = get_all_python_files()
    
    print(f"📊 找到 {len(all_files)} 个Python文件")
    print()
    
    # 提取所有文件的导入
    file_imports: Dict[Path, Set[str]] = {}
    for filepath in all_files:
        imports = extract_imports(PROJECT_ROOT / filepath)
        file_imports[filepath] = imports
    
    # 构建导入关系图
    imported_by: Dict[Path, Set[Path]] = defaultdict(set)
    
    for importer_file, imports in file_imports.items():
        for module_name in imports:
            # 跳过标准库
            if module_name in ['sys', 'os', 'json', 'pathlib', 'typing', 'datetime', 
                              'dataclasses', 'uuid', 'argparse', 'shutil', 'time',
                              're', 'importlib', 'tempfile', 'ast', 'collections']:
                continue
            
            # 查找被导入的文件
            candidates = module_to_file(module_name, all_files)
            for candidate in candidates:
                imported_by[candidate].add(importer_file)
    
    # 找出从未被导入的文件
    never_imported = []
    for filepath in all_files:
        # 跳过入口文件和测试文件
        if str(filepath) in ENTRY_POINTS or str(filepath) in TEST_FILES:
            continue
        
        # 检查是否被导入
        if filepath not in imported_by:
            never_imported.append(filepath)
    
    # 输出结果
    print("=" * 80)
    print("🔍 死文件分析结果")
    print("=" * 80)
    print()
    
    if never_imported:
        print(f"❌ 发现 {len(never_imported)} 个从未被导入的文件：")
        print()
        for filepath in sorted(never_imported):
            print(f"   - {filepath}")
    else:
        print("✅ 未发现明显的死文件")
    
    print()
    print("=" * 80)
    print("📋 导入关系统计")
    print("=" * 80)
    print()
    
    # 统计被导入次数
    import_counts = [(f, len(importers)) for f, importers in imported_by.items()]
    import_counts.sort(key=lambda x: x[1], reverse=True)
    
    print("被导入最多的文件（前10个）：")
    for filepath, count in import_counts[:10]:
        print(f"   {count:3d} 次 - {filepath}")
    
    print()
    print("=" * 80)
    print("⚠️  特殊文件检查")
    print("=" * 80)
    print()
    
    # 检查入口文件
    print("入口文件（可能被直接运行）：")
    for entry in sorted(ENTRY_POINTS):
        filepath = Path(entry)
        if filepath in all_files:
            print(f"   ✅ {entry}")
        else:
            print(f"   ❌ {entry} (不存在)")
    
    print()
    print("测试文件（可能被测试框架运行）：")
    for test_file in sorted(TEST_FILES):
        filepath = Path(test_file)
        if filepath in all_files:
            print(f"   ✅ {test_file}")
        else:
            print(f"   ❌ {test_file} (不存在)")
    
    return never_imported, imported_by


if __name__ == "__main__":
    never_imported, imported_by = analyze_imports()

