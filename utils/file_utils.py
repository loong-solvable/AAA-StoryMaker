import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Union

from utils.logger import setup_logger

logger = setup_logger("FileUtils", "file_utils.log")


def safe_read_json(file_path: Union[str, Path], default: Any = None) -> Any:
    """
    安全读取 JSON 文件，自动处理编码问题
    
    Args:
        file_path: 文件路径
        default: 读取失败时返回的默认值
        
    Returns:
        解析后的 JSON 数据，或 default
    """
    path = Path(file_path)
    
    if not path.exists():
        logger.warning(f"⚠️ 文件不存在: {path}")
        return default
    
    # 尝试多种编码
    encodings = ["utf-8", "utf-8-sig", "gbk", "gb2312", "gb18030", "latin-1"]
    
    for encoding in encodings:
        try:
            with open(path, "r", encoding=encoding) as f:
                data = json.load(f)
                
            if encoding != "utf-8":
                logger.info(f"📄 使用 {encoding} 编码成功读取: {path.name}")
                
            return data
            
        except UnicodeDecodeError:
            continue
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ JSON 解析失败 ({encoding}): {path.name} - {e}")
            continue
        except Exception as e:
            logger.error(f"❌ 读取文件失败: {path} - {e}")
            return default
    
    logger.error(f"❌ 无法使用任何已知编码读取文件: {path}")
    return default


def safe_read_text(file_path: Union[str, Path], default: str = "") -> str:
    """
    安全读取文本文件，自动处理编码问题
    
    Args:
        file_path: 文件路径
        default: 读取失败时返回的默认值
        
    Returns:
        文件内容，或 default
    """
    path = Path(file_path)
    
    if not path.exists():
        logger.warning(f"⚠️ 文件不存在: {path}")
        return default
    
    # 尝试多种编码
    encodings = ["utf-8", "utf-8-sig", "gbk", "gb2312", "gb18030", "latin-1"]
    
    for encoding in encodings:
        try:
            with open(path, "r", encoding=encoding) as f:
                content = f.read()
                
            if encoding != "utf-8":
                logger.info(f"📄 使用 {encoding} 编码成功读取: {path.name}")
                
            return content
            
        except UnicodeDecodeError:
            continue
        except Exception as e:
            logger.error(f"❌ 读取文件失败: {path} - {e}")
            return default
    
    logger.error(f"❌ 无法使用任何已知编码读取文件: {path}")
    return default


def atomic_write_json(file_path: Union[str, Path], data: Any, indent: int = 2, ensure_ascii: bool = False):
    """
    Atomically write JSON data to a file.
    
    This function writes data to a temporary file first, then renames it to the target file.
    This ensures that the target file is never in a corrupted or partial state if the
    process is interrupted.
    
    Args:
        file_path: Target file path.
        data: JSON serializable data.
        indent: JSON indentation.
        ensure_ascii: JSON ensure_ascii flag.
    """
    path = Path(file_path)
    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create a temporary file in the same directory to ensure atomic rename works across filesystems
    tmp_path = path.with_suffix(f"{path.suffix}.tmp.{os.getpid()}")
    
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)
            f.flush()
            os.fsync(f.fileno())
            
        # Atomic rename
        shutil.move(str(tmp_path), str(path))
        
    except Exception as e:
        # Clean up temp file if something goes wrong
        if tmp_path.exists():
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        raise e


def safe_write_json(file_path: Union[str, Path], data: Any, indent: int = 2) -> bool:
    """
    安全写入 JSON 文件（使用原子写入，带错误处理）
    
    Args:
        file_path: 目标文件路径
        data: 要写入的数据
        indent: 缩进
        
    Returns:
        是否成功
    """
    try:
        atomic_write_json(file_path, data, indent=indent)
        return True
    except Exception as e:
        logger.error(f"❌ 写入 JSON 失败: {file_path} - {e}")
        return False


def safe_write_text(file_path: Union[str, Path], content: str) -> bool:
    """
    安全写入文本文件
    
    Args:
        file_path: 目标文件路径
        content: 要写入的内容
        
    Returns:
        是否成功
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    tmp_path = path.with_suffix(f"{path.suffix}.tmp.{os.getpid()}")
    
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
            
        shutil.move(str(tmp_path), str(path))
        return True
        
    except Exception as e:
        logger.error(f"❌ 写入文本失败: {file_path} - {e}")
        if tmp_path.exists():
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        return False

