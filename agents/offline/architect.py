"""
架构师 (The Architect)
离线构建者，负责将小说转化为Genesis.json数据包
"""
import json
from pathlib import Path
from typing import Dict, Any
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser
from utils.llm_factory import get_llm
from utils.logger import setup_logger
from config.settings import settings

logger = setup_logger("Architect", "architect.log")


class ArchitectAgent:
    """架构师Agent - ETL引擎"""
    
    def __init__(self):
        """初始化架构师Agent"""
        logger.info("🏗️  初始化架构师Agent...")
        
        # 创建LLM实例
        self.llm = get_llm()
        
        # 加载系统提示词
        self.system_prompt = self._load_system_prompt()
        
        # 创建处理链
        self.chain = self._build_chain()
        
        logger.info("✅ 架构师Agent初始化完成")
    
    def _load_system_prompt(self) -> str:
        """加载系统提示词"""
        prompt_file = settings.PROMPTS_DIR / "offline" / "architect_system.txt"
        
        if not prompt_file.exists():
            logger.error(f"❌ 未找到提示词文件: {prompt_file}")
            raise FileNotFoundError(f"提示词文件不存在: {prompt_file}")
        
        with open(prompt_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        logger.info(f"✅ 成功加载提示词: {prompt_file.name}")
        return content
    
    def _build_chain(self):
        """构建LangChain处理链"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human", "请阅读以下小说并生成Genesis数据包：\n\n{novel_text}")
        ])
        
        chain = prompt | self.llm | StrOutputParser()
        return chain
    
    def process_novel(self, novel_path: Path) -> Dict[str, Any]:
        """
        处理小说文件，生成Genesis数据包
        
        Args:
            novel_path: 小说文件路径
        
        Returns:
            Genesis数据字典
        """
        logger.info(f"📖 开始处理小说: {novel_path.name}")
        
        # 读取小说
        novel_text = self._read_novel(novel_path)
        
        # 调用LLM生成数据
        logger.info("🤖 正在调用LLM进行世界观解析...")
        logger.info("⏳ 这可能需要1-2分钟，请耐心等待...")
        
        try:
            response = self.chain.invoke({"novel_text": novel_text})
            logger.info("✅ LLM解析完成")
        except Exception as e:
            logger.error(f"❌ LLM调用失败: {e}")
            raise
        
        # 解析JSON
        genesis_data = self._parse_response(response)
        
        logger.info("✅ 小说处理完成")
        return genesis_data
    
    def _read_novel(self, novel_path: Path) -> str:
        """读取小说文件"""
        if not novel_path.exists():
            logger.error(f"❌ 小说文件不存在: {novel_path}")
            raise FileNotFoundError(f"小说文件不存在: {novel_path}")
        
        with open(novel_path, "r", encoding="utf-8") as f:
            text = f.read()
        
        word_count = len(text)
        logger.info(f"✅ 成功读取小说: {novel_path.name} ({word_count}字)")
        
        if word_count < 1000:
            logger.warning("⚠️  小说字数较少，可能影响解析质量")
        
        return text
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """解析LLM返回的JSON响应"""
        logger.info("🔍 正在解析LLM响应...")
        
        # 提取JSON部分（去除可能的markdown代码块）
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        
        try:
            data = json.loads(response)
            logger.info("✅ JSON解析成功")
            
            # 验证数据结构
            self._validate_genesis(data)
            
            return data
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON解析失败: {e}")
            logger.error(f"原始响应: {response[:500]}...")
            raise ValueError("LLM返回的数据格式不正确")
    
    def _validate_genesis(self, data: Dict[str, Any]):
        """验证Genesis数据包的结构"""
        required_keys = ["world", "characters", "locations", "plot_hints", "initial_scene"]
        
        for key in required_keys:
            if key not in data:
                logger.error(f"❌ Genesis数据包缺少必要字段: {key}")
                raise ValueError(f"Genesis数据包缺少必要字段: {key}")
        
        logger.info(f"✅ Genesis数据验证通过:")
        logger.info(f"   - 角色数量: {len(data['characters'])}")
        logger.info(f"   - 地点数量: {len(data['locations'])}")
        logger.info(f"   - 剧情线索: {len(data['plot_hints'])}")
    
    def save_genesis(self, genesis_data: Dict[str, Any], output_path: Path):
        """
        保存Genesis数据包到文件
        
        Args:
            genesis_data: Genesis数据字典
            output_path: 输出文件路径
        """
        logger.info(f"💾 保存Genesis数据包到: {output_path}")
        
        # 确保目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 保存JSON文件
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(genesis_data, f, ensure_ascii=False, indent=2)
        
        file_size = output_path.stat().st_size / 1024  # KB
        logger.info(f"✅ Genesis.json已保存 ({file_size:.2f} KB)")
    
    def run(self, novel_filename: str = "example_novel.txt") -> Path:
        """
        完整的运行流程
        
        Args:
            novel_filename: 小说文件名（在data/novels/目录下）
        
        Returns:
            生成的Genesis.json文件路径
        """
        logger.info("=" * 60)
        logger.info("🚀 启动架构师Agent - 世界构建流程")
        logger.info("=" * 60)
        
        # 输入输出路径
        novel_path = settings.NOVELS_DIR / novel_filename
        genesis_path = settings.GENESIS_DIR / "genesis.json"
        
        # 处理流程
        genesis_data = self.process_novel(novel_path)
        self.save_genesis(genesis_data, genesis_path)
        
        logger.info("=" * 60)
        logger.info("🎉 世界构建完成！")
        logger.info(f"📄 Genesis.json路径: {genesis_path}")
        logger.info("=" * 60)
        
        return genesis_path


# 便捷函数
def create_genesis(novel_filename: str = "example_novel.txt") -> Path:
    """创建Genesis数据包的便捷函数"""
    architect = ArchitectAgent()
    return architect.run(novel_filename)

