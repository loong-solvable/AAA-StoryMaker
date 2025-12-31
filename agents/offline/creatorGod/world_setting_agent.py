"""
世界观设定子客体：负责抽取世界规则与地理
"""
from typing import Any, Dict, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from utils.llm_factory import get_llm
from utils.logger import setup_logger
from .utils import load_prompt, parse_json_response, escape_braces


class WorldSettingAgent:
    """世界观设定 Agent"""

    def __init__(
        self,
        llm=None,
        prompt_filename: str = "world_setting.txt",
        logger=None,
    ):
        self.logger = logger or setup_logger("Demiurge", "genesis_group.log")
        self.llm = llm or get_llm()
        self.prompt_text = escape_braces(load_prompt(prompt_filename))

    def run(self, novel_text: str) -> Dict[str, Any]:
        """抽取世界设定"""
        self.logger.info("=" * 60)
        self.logger.info("📍 阶段2：提取世界观设定")
        self.logger.info("=" * 60)

        # 估算 Token 数
        estimated_tokens = len(novel_text) / 1.5
        MAX_TOKENS = 10000000  # 支持长上下文模型
        
        if estimated_tokens > MAX_TOKENS:
            self.logger.warning(f"⚠️ 小说过长 (约 {int(estimated_tokens)} tokens)，将进行分块处理...")
            return self._run_chunked(novel_text)

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self.prompt_text),
                ("human", "{novel_text}"),
            ]
        )
        chain = prompt | self.llm | StrOutputParser()

        self.logger.info("🤖 正在调用世界观 LLM...")
        try:
            response = chain.invoke({"novel_text": novel_text}, config={"timeout": 600})
            world_setting = parse_json_response(response)
            return world_setting
        except Exception as e:
            self.logger.error(f"❌ 世界观提取失败: {e}")
            raise e

    def _run_chunked(self, novel_text: str) -> Dict[str, Any]:
        """分块处理长小说"""
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
        
        merged_setting = {
            "world_name": "",
            "world_view": "",
            "rules": [],
            "locations": []
        }
        
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self.prompt_text),
                ("human", "{novel_text}"),
            ]
        )
        chain = prompt | self.llm | StrOutputParser()
        
        for i, chunk in enumerate(chunks, 1):
            self.logger.info(f"🤖 处理片段 {i}/{len(chunks)}...")
            try:
                response = chain.invoke({"novel_text": chunk}, config={"timeout": 600})
                chunk_setting = parse_json_response(response)
                
                # 合并逻辑
                if not merged_setting["world_name"] and chunk_setting.get("world_name"):
                    merged_setting["world_name"] = chunk_setting["world_name"]
                    
                if chunk_setting.get("world_view"):
                    merged_setting["world_view"] += f"\n\n[片段{i}补充]: " + chunk_setting["world_view"]
                    
                if chunk_setting.get("rules"):
                    if isinstance(chunk_setting["rules"], list):
                        merged_setting["rules"].extend(chunk_setting["rules"])
                    elif isinstance(chunk_setting["rules"], str):
                        merged_setting["rules"].append(chunk_setting["rules"])
                        
                if chunk_setting.get("locations"):
                    if isinstance(chunk_setting["locations"], list):
                        # 简单去重（按名称）
                        existing_names = {loc.get("name") for loc in merged_setting["locations"] if loc.get("name")}
                        for loc in chunk_setting["locations"]:
                            if loc.get("name") and loc.get("name") not in existing_names:
                                merged_setting["locations"].append(loc)
                                existing_names.add(loc.get("name"))
                                
                self.logger.info(f"   ✅ 片段 {i} 处理完成")
                
            except Exception as e:
                self.logger.error(f"❌ 片段 {i} 处理失败: {e}")
        
        # 清理 rules (去重)
        merged_setting["rules"] = list(set(merged_setting["rules"]))
        
        return merged_setting
