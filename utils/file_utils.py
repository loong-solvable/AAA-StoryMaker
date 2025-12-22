import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, Union

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
