"""
运行时文件清理工具

用于清理之前运行时生成的世界、剧本和角色文件。
支持清理指定世界或所有世界的运行时数据。
"""

import shutil
from pathlib import Path
from typing import List, Optional, Dict
from config.settings import Settings, PROJECT_ROOT


class RuntimeCleaner:
    """运行时文件清理器"""
    
    def __init__(self):
        self.data_dir = Settings.DATA_DIR
        self.runtime_dir = self.data_dir / "runtime"
        self.worlds_dir = self.data_dir / "worlds"
        self.npc_prompt_dir = Settings.PROMPTS_DIR / "online" / "npc_prompt"
        self.npc_agent_dir = PROJECT_ROOT / "agents" / "online" / "layer3"
    
    def list_runtime_worlds(self) -> List[str]:
        """
        列出所有运行时世界名称
        
        Returns:
            世界名称列表（去重）
        """
        if not self.runtime_dir.exists():
            return []
        
        worlds = set()
        for runtime_folder in self.runtime_dir.iterdir():
            if runtime_folder.is_dir():
                # 运行时目录格式: {world_name}_{timestamp}
                # 提取世界名称（去掉时间戳部分）
                name_parts = runtime_folder.name.rsplit("_", 2)
                if len(name_parts) >= 2:
                    # 尝试提取世界名称（去掉最后两部分，即日期和时间戳）
                    # 但有些世界名可能包含下划线，所以需要更智能的解析
                    # 简单方法：找到最后一个符合日期格式的部分
                    world_name = None
                    for i in range(len(name_parts) - 1, 0, -1):
                        # 检查是否是日期格式 YYYYMMDD
                        if len(name_parts[i]) == 8 and name_parts[i].isdigit():
                            world_name = "_".join(name_parts[:i])
                            break
                    
                    if world_name:
                        worlds.add(world_name)
        
        return sorted(list(worlds))
    
    def list_saved_worlds(self) -> List[str]:
        """
        列出所有已保存的世界名称
        
        Returns:
            世界名称列表
        """
        if not self.worlds_dir.exists():
            return []
        
        worlds = []
        for world_folder in self.worlds_dir.iterdir():
            if world_folder.is_dir() and (world_folder / "world_setting.json").exists():
                worlds.append(world_folder.name)
        
        return sorted(worlds)
    
    def get_world_characters(self, world_name: str) -> List[Dict[str, str]]:
        """
        获取指定世界的角色列表
        
        Args:
            world_name: 世界名称
            
        Returns:
            角色信息列表，每个元素包含 id 和 name
        """
        world_dir = self.worlds_dir / world_name
        characters_dir = world_dir / "characters"
        
        if not characters_dir.exists():
            return []
        
        characters = []
        for char_file in characters_dir.glob("character_*.json"):
            try:
                import json
                with open(char_file, "r", encoding="utf-8") as f:
                    char_data = json.load(f)
                    char_id = char_data.get("id", "")
                    char_name = char_data.get("name", "")
                    if char_id and char_name:
                        characters.append({"id": char_id, "name": char_name})
            except Exception:
                continue
        
        return characters
    
    def cleanup_runtime_dirs(self, world_name: Optional[str] = None) -> int:
        """
        清理运行时目录
        
        Args:
            world_name: 世界名称，如果为None则清理所有运行时目录
            
        Returns:
            清理的目录数量
        """
        if not self.runtime_dir.exists():
            return 0
        
        cleaned_count = 0
        
        if world_name:
            # 清理指定世界的所有运行时目录
            for runtime_folder in self.runtime_dir.iterdir():
                if runtime_folder.is_dir() and runtime_folder.name.startswith(f"{world_name}_"):
                    shutil.rmtree(runtime_folder)
                    cleaned_count += 1
        else:
            # 清理所有运行时目录
            for runtime_folder in self.runtime_dir.iterdir():
                if runtime_folder.is_dir():
                    shutil.rmtree(runtime_folder)
                    cleaned_count += 1
        
        return cleaned_count
    
    def cleanup_world_dir(self, world_name: str) -> bool:
        """
        清理世界目录
        
        Args:
            world_name: 世界名称
            
        Returns:
            是否成功清理
        """
        world_dir = self.worlds_dir / world_name
        if world_dir.exists():
            shutil.rmtree(world_dir)
            return True
        return False
    
    def cleanup_character_files(self, world_name: str) -> int:
        """
        清理指定世界的角色相关文件（提示词和agent文件）
        
        Args:
            world_name: 世界名称
            
        Returns:
            清理的文件数量
        """
        characters = self.get_world_characters(world_name)
        cleaned_count = 0
        
        for char in characters:
            char_id = char["id"]
            char_name = char["name"]
            
            # 清理提示词文件
            prompt_file = self.npc_prompt_dir / f"{char_id}_{char_name}_prompt.txt"
            if prompt_file.exists():
                prompt_file.unlink()
                cleaned_count += 1
            
            # 清理agent文件
            agent_file = self.npc_agent_dir / f"{char_id}_{char_name}.py"
            if agent_file.exists():
                agent_file.unlink()
                cleaned_count += 1
        
        return cleaned_count
    
    def cleanup_all_character_files(self) -> int:
        """
        清理所有动态生成的角色文件
        
        Returns:
            清理的文件数量
        """
        cleaned_count = 0
        
        # 清理所有提示词文件
        if self.npc_prompt_dir.exists():
            for prompt_file in self.npc_prompt_dir.glob("npc_*_prompt.txt"):
                prompt_file.unlink()
                cleaned_count += 1
        
        # 清理所有agent文件（排除基础文件）
        if self.npc_agent_dir.exists():
            for agent_file in self.npc_agent_dir.glob("npc_*.py"):
                # 排除基础模板文件（如果有的话）
                agent_file.unlink()
                cleaned_count += 1
        
        return cleaned_count
    
    def cleanup_world(
        self,
        world_name: str,
        include_runtime: bool = True,
        include_world_data: bool = False,
        include_character_files: bool = True
    ) -> Dict[str, int]:
        """
        清理指定世界的所有相关文件
        
        Args:
            world_name: 世界名称
            include_runtime: 是否清理运行时目录
            include_world_data: 是否清理世界数据目录
            include_character_files: 是否清理角色相关文件
            
        Returns:
            清理结果统计
        """
        result = {
            "runtime_dirs": 0,
            "world_dirs": 0,
            "character_files": 0
        }
        
        if include_runtime:
            result["runtime_dirs"] = self.cleanup_runtime_dirs(world_name)
        
        if include_world_data:
            if self.cleanup_world_dir(world_name):
                result["world_dirs"] = 1
        
        if include_character_files:
            result["character_files"] = self.cleanup_character_files(world_name)
        
        return result
    
    def cleanup_all(
        self,
        include_runtime: bool = True,
        include_world_data: bool = False,
        include_character_files: bool = True
    ) -> Dict[str, int]:
        """
        清理所有运行时文件
        
        Args:
            include_runtime: 是否清理运行时目录
            include_world_data: 是否清理世界数据目录
            include_character_files: 是否清理角色相关文件
            
        Returns:
            清理结果统计
        """
        result = {
            "runtime_dirs": 0,
            "world_dirs": 0,
            "character_files": 0
        }
        
        if include_runtime:
            result["runtime_dirs"] = self.cleanup_runtime_dirs()
        
        if include_world_data:
            worlds = self.list_saved_worlds()
            for world_name in worlds:
                if self.cleanup_world_dir(world_name):
                    result["world_dirs"] += 1
        
        if include_character_files:
            result["character_files"] = self.cleanup_all_character_files()
        
        return result


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="清理运行时生成的世界、剧本和角色文件",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 列出所有运行时世界
  python -m utils.cleanup_runtime --list
  
  # 清理指定世界的运行时数据（保留世界数据）
  python -m utils.cleanup_runtime --world "白垩纪往事"
  
  # 清理指定世界的所有数据（包括世界数据）
  python -m utils.cleanup_runtime --world "白垩纪往事" --include-world-data
  
  # 清理所有运行时数据
  python -m utils.cleanup_runtime --all
  
  # 清理所有数据（包括世界数据）
  python -m utils.cleanup_runtime --all --include-world-data
        """
    )
    
    parser.add_argument(
        "--list",
        action="store_true",
        help="列出所有运行时世界和已保存的世界"
    )
    
    parser.add_argument(
        "--world",
        type=str,
        help="指定要清理的世界名称"
    )
    
    parser.add_argument(
        "--all",
        action="store_true",
        help="清理所有运行时数据"
    )
    
    parser.add_argument(
        "--include-world-data",
        action="store_true",
        help="同时清理世界数据目录（谨慎使用）"
    )
    
    parser.add_argument(
        "--no-runtime",
        action="store_true",
        help="不清理运行时目录"
    )
    
    parser.add_argument(
        "--no-character-files",
        action="store_true",
        help="不清理角色相关文件"
    )
    
    parser.add_argument(
        "--yes",
        action="store_true",
        help="跳过确认提示"
    )
    
    args = parser.parse_args()
    
    cleaner = RuntimeCleaner()
    
    # 列出所有世界
    if args.list:
        runtime_worlds = cleaner.list_runtime_worlds()
        saved_worlds = cleaner.list_saved_worlds()
        
        print("\n📋 运行时世界列表:")
        if runtime_worlds:
            for world in runtime_worlds:
                print(f"  - {world}")
        else:
            print("  （无）")
        
        print("\n📋 已保存的世界列表:")
        if saved_worlds:
            for world in saved_worlds:
                print(f"  - {world}")
        else:
            print("  （无）")
        
        return
    
    # 确认操作
    if not args.yes:
        if args.world:
            print(f"\n⚠️  即将清理世界 '{args.world}' 的相关文件")
        elif args.all:
            print("\n⚠️  即将清理所有运行时数据")
        else:
            print("\n❌ 请指定 --world <世界名> 或 --all")
            parser.print_help()
            return
        
        if args.include_world_data:
            print("⚠️  警告：将同时清理世界数据目录！")
        
        confirm = input("\n确认继续？(yes/no): ")
        if confirm.lower() not in ["yes", "y"]:
            print("❌ 操作已取消")
            return
    
    # 执行清理
    try:
        if args.world:
            result = cleaner.cleanup_world(
                world_name=args.world,
                include_runtime=not args.no_runtime,
                include_world_data=args.include_world_data,
                include_character_files=not args.no_character_files
            )
            print(f"\n✅ 清理完成:")
            print(f"  - 运行时目录: {result['runtime_dirs']} 个")
            print(f"  - 世界数据目录: {result['world_dirs']} 个")
            print(f"  - 角色相关文件: {result['character_files']} 个")
        
        elif args.all:
            result = cleaner.cleanup_all(
                include_runtime=not args.no_runtime,
                include_world_data=args.include_world_data,
                include_character_files=not args.no_character_files
            )
            print(f"\n✅ 清理完成:")
            print(f"  - 运行时目录: {result['runtime_dirs']} 个")
            print(f"  - 世界数据目录: {result['world_dirs']} 个")
            print(f"  - 角色相关文件: {result['character_files']} 个")
        
        else:
            print("\n❌ 请指定 --world <世界名> 或 --all")
            parser.print_help()
    
    except Exception as e:
        print(f"\n❌ 清理过程中出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

