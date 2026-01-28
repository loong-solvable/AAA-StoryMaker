"""
角色过滤子客体：负责角色普查
"""
from typing import Any, Dict, List, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from utils.llm_factory import get_llm
from utils.logger import setup_logger
from .utils import load_prompt, parse_json_response, escape_braces


class CharacterFilterAgent:
    """角色过滤 Agent：扫描小说并输出角色列表"""

    def __init__(
        self,
        llm=None,
        prompt_filename: str = "character_filter.txt",
        logger=None,
    ):
        self.logger = logger or setup_logger("大中正", "genesis_group.log")
        self.llm = llm or get_llm()
        self.prompt_text = escape_braces(load_prompt(prompt_filename))

    def run(self, novel_text: str) -> List[Dict[str, Any]]:
        """执行角色普查"""
        self.logger.info("=" * 60)
        self.logger.info("📍 阶段1：角色过滤（角色普查）")
        self.logger.info("=" * 60)

        # 估算 Token 数 (简单按字符数/1.5估算)
        estimated_tokens = len(novel_text) / 1.5
        MAX_TOKENS = 10000000  # 设置安全阈值（支持长上下文模型）
        
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

        self.logger.info("🤖 正在调用角色过滤 LLM...")
        try:
            response = chain.invoke({"novel_text": novel_text}, config={"timeout": 18000})
            characters_list = parse_json_response(response)
            
            if isinstance(characters_list, dict):
                self.logger.warning("⚠️  LLM返回了单个对象，已自动包装为列表")
                characters_list = [characters_list]
                
            self.logger.info(f"✅ 角色普查完成，发现 {len(characters_list)} 个角色")
            return characters_list
            
        except Exception as e:
            self.logger.error(f"❌ 角色普查失败: {e}")
            raise e

    def _run_chunked(self, novel_text: str) -> List[Dict[str, Any]]:
        """分块处理长小说"""
        CHUNK_SIZE = 50000  # 每次处理约 5万字符
        OVERLAP = 2000      # 重叠 2000 字符
        
        chunks = []
        start = 0
        while start < len(novel_text):
            end = min(start + CHUNK_SIZE, len(novel_text))
            chunks.append(novel_text[start:end])
            if end == len(novel_text):
                break
            start = end - OVERLAP
            
        self.logger.info(f"📚 将小说切分为 {len(chunks)} 个片段进行处理")
        
        all_characters = {}
        
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
                response = chain.invoke({"novel_text": chunk}, config={"timeout": 18000})
                chunk_chars = parse_json_response(response)
                
                if isinstance(chunk_chars, dict):
                    chunk_chars = [chunk_chars]
                
                if not isinstance(chunk_chars, list):
                    self.logger.warning(f"⚠️ 片段 {i} 返回格式错误，跳过")
                    continue
                    
                # 合并结果
                for char in chunk_chars:
                    name = char.get("name")
                    if name:
                        if name not in all_characters:
                            all_characters[name] = char
                        else:
                            # 如果已存在，可以根据需要合并信息（这里简单保留第一次出现的）
                            pass
                            
                self.logger.info(f"   ✅ 片段 {i} 提取了 {len(chunk_chars)} 个角色")
                
            except Exception as e:
                self.logger.error(f"❌ 片段 {i} 处理失败: {e}")
        
        result_list = list(all_characters.values())
        self.logger.info(f"✅ 分块普查完成，共发现 {len(result_list)} 个不重复角色")
        return result_list
