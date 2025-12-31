"""
角色档案子客体：为单个角色生成详细档案
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from utils.llm_factory import get_llm
from utils.logger import setup_logger
from .utils import load_prompt, parse_json_response, escape_braces


class CharacterDetailAgent:
    """角色档案 Agent（许劭）"""

    def __init__(
        self,
        llm=None,
        prompt_filename: str = "character_detail.txt",
        logger=None,
    ):
        self.logger = logger or setup_logger("许劭", "genesis_group.log")
        self.llm = llm or get_llm()
        self.prompt_template = load_prompt(prompt_filename)

    def _build_prompt(
        self, 
        char_name: str, 
        char_id: str, 
        characters_list: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        构建提示词，包含角色列表信息以保持ID一致性
        
        Args:
            char_name: 目标角色名
            char_id: 目标角色ID
            characters_list: 阶段1生成的角色列表，用于ID同步
        """
        prompt = self.prompt_template.replace("{target_name}", char_name)
        prompt = prompt.replace("{target_id}", char_id)
        
        # 构建角色列表信息（用于relationship_matrix中的ID引用）
        if characters_list:
            characters_list_str = json.dumps(characters_list, ensure_ascii=False, indent=2)
            prompt = prompt.replace("{characters_list}", characters_list_str)
        else:
            prompt = prompt.replace("{characters_list}", "[]")
        
        return escape_braces(prompt)

    def create_one(
        self, 
        novel_text: str, 
        char_info: Dict[str, Any],
        characters_list: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        为单个角色生成档案
        
        Args:
            novel_text: 小说文本
            char_info: 当前角色信息
            characters_list: 阶段1生成的角色列表，用于ID同步
        """
        char_id = char_info.get("id")
        char_name = char_info.get("name")
        importance = char_info.get("importance")

        # 估算 Token 数
        estimated_tokens = len(novel_text) / 1.5
        MAX_TOKENS = 10000000  # 支持长上下文模型
        
        if estimated_tokens > MAX_TOKENS:
            self.logger.warning(f"⚠️ 小说过长 (约 {int(estimated_tokens)} tokens)，将进行分块处理...")
            return self._create_one_chunked(novel_text, char_info, characters_list)

        prompt_text = self._build_prompt(char_name, char_id, characters_list)
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", prompt_text),
                ("human", "{novel_text}"),
            ]
        )
        chain = prompt | self.llm | StrOutputParser()

        response = chain.invoke({"novel_text": novel_text}, config={"timeout": 600})
        char_data = parse_json_response(response)
        char_data["importance"] = importance
        return char_data

    def _create_one_chunked(
        self,
        novel_text: str,
        char_info: Dict[str, Any],
        characters_list: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """分块生成角色档案"""
        CHUNK_SIZE = 50000
        OVERLAP = 2000
        
        chunks = []
        start = 0
        while start < len(novel_text):
            end = min(start + CHUNK_SIZE, len(novel_text))
            chunks.append(novel_text[start:end])
            if end == len(novel_text):
                break
            start = end - OVERLAP
            
        self.logger.info(f"📚 将小说切分为 {len(chunks)} 个片段进行处理")
        
        merged_data = {
            "id": char_info.get("id"),
            "name": char_info.get("name"),
            "importance": char_info.get("importance"),
            "age": "",
            "gender": "",
            "appearance": "",
            "personality": "",
            "background": "",
            "relationships": []
        }
        
        prompt_text = self._build_prompt(char_info.get("name"), char_info.get("id"), characters_list)
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", prompt_text),
                ("human", "{novel_text}"),
            ]
        )
        chain = prompt | self.llm | StrOutputParser()
        
        for i, chunk in enumerate(chunks, 1):
            # 简单过滤：如果片段中不包含角色名，大概率可以跳过（优化速度）
            if char_info.get("name") not in chunk:
                continue
                
            self.logger.info(f"🤖 处理片段 {i}/{len(chunks)}...")
            try:
                response = chain.invoke({"novel_text": chunk}, config={"timeout": 600})
                chunk_data = parse_json_response(response)
                
                # 合并逻辑
                if not merged_data["age"] and chunk_data.get("age"):
                    merged_data["age"] = chunk_data["age"]
                if not merged_data["gender"] and chunk_data.get("gender"):
                    merged_data["gender"] = chunk_data["gender"]
                    
                if chunk_data.get("appearance"):
                    merged_data["appearance"] += f"\n{chunk_data['appearance']}"
                if chunk_data.get("personality"):
                    merged_data["personality"] += f"\n{chunk_data['personality']}"
                if chunk_data.get("background"):
                    merged_data["background"] += f"\n{chunk_data['background']}"
                    
                if chunk_data.get("relationships"):
                    # 合并关系（简单追加，后续可能需要去重或LLM整理，这里先保留所有线索）
                    existing_rels = {(r.get("target_id"), r.get("relationship")) for r in merged_data["relationships"]}
                    for rel in chunk_data["relationships"]:
                        key = (rel.get("target_id"), rel.get("relationship"))
                        if key not in existing_rels:
                            merged_data["relationships"].append(rel)
                            existing_rels.add(key)
                            
            except Exception as e:
                self.logger.warning(f"⚠️ 片段 {i} 处理失败: {e}")
        
        return merged_data

    def _save_character(
        self, 
        world_dir: Path, 
        char_id: str, 
        char_data: Dict[str, Any]
    ) -> None:
        """保存单个角色档案"""
        characters_dir = world_dir / "characters"
        characters_dir.mkdir(exist_ok=True)
        char_file = characters_dir / f"character_{char_id}.json"
        with char_file.open("w", encoding="utf-8") as f:
            json.dump(char_data, f, ensure_ascii=False, indent=2)
        self.logger.info(f"   💾 已保存角色档案: {char_file.name}")

    def run(
        self,
        novel_text: str,
        characters_list: List[Dict[str, Any]],
        world_dir: Optional[Path] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        批量为角色生成档案
        
        Args:
            novel_text: 小说文本
            characters_list: 阶段1生成的角色列表（包含ID信息）
            world_dir: 世界目录，若提供则每个角色创建后即时保存
        """
        self.logger.info("=" * 60)
        self.logger.info("📍 阶段3：创建角色详细档案")
        self.logger.info("=" * 60)

        characters_details: Dict[str, Dict[str, Any]] = {}
        total = len(characters_list)

        for idx, char_info in enumerate(characters_list, 1):
            char_id = char_info.get("id")
            char_name = char_info.get("name")
            importance = char_info.get("importance")
            self.logger.info(
                f"[{idx}/{total}] 处理角色: {char_name} (重要性 {importance})"
            )
            try:
                # 传入characters_list以保持ID一致性
                char_data = self.create_one(novel_text, char_info, characters_list)
                characters_details[char_id] = char_data
                self.logger.info(f"   ✅ {char_name} 档案创建完成")
                
                # 即时保存
                if world_dir:
                    self._save_character(world_dir, char_id, char_data)
            except Exception as e:
                self.logger.warning(f"   ⚠️  {char_name} 档案创建失败: {e}")
                error_data = {
                    "id": char_id,
                    "name": char_name,
                    "importance": importance,
                    "error": str(e),
                }
                characters_details[char_id] = error_data
                # 即使失败也保存错误信息
                if world_dir:
                    self._save_character(world_dir, char_id, error_data)

        self.logger.info(f"✅ 角色档案生成完成: {len(characters_details)}/{total}")
        return characters_details
