"""
架构师 (The Architect)
离线构建者，负责将小说转化为三份JSON数据包
- world_setting.json: 世界观设定
- characters_list.json: 角色列表（含重要性评分）
- characters/character_<id>.json: 每个角色的详细档案
"""
import json
import re
from pathlib import Path
from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from utils.llm_factory import get_llm
from utils.logger import setup_logger
from config.settings import settings

logger = setup_logger("Architect", "architect.log")


class ArchitectAgent:
    """架构师Agent - ETL引擎（三阶段处理）"""
    
    def __init__(self):
        """初始化架构师Agent"""
        logger.info("🏗️  初始化架构师Agent...")
        
        # 创建LLM实例
        self.llm = get_llm()
        
        # 加载三个提示词
        self.world_prompt = self._load_prompt("世界观架构师.txt")
        self.char_filter_prompt = self._load_prompt("角色过滤架构师.txt")
        self.char_detail_prompt = self._load_prompt("角色制作架构师")  # 无扩展名
        
        logger.info("✅ 架构师Agent初始化完成")
    
    def _load_prompt(self, filename: str) -> str:
        """加载提示词文件"""
        prompt_file = settings.PROMPTS_DIR / "offline" / filename
        
        if not prompt_file.exists():
            logger.error(f"❌ 未找到提示词文件: {prompt_file}")
            raise FileNotFoundError(f"提示词文件不存在: {prompt_file}")
        
        with open(prompt_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        logger.info(f"✅ 成功加载提示词: {filename}")
        return content
    
    def _read_novel(self, novel_path: Path) -> str:
        """读取小说文件"""
        if not novel_path.exists():
            logger.error(f"❌ 小说文件不存在: {novel_path}")
            raise FileNotFoundError(f"小说文件不存在: {novel_path}")
        
        with open(novel_path, "r", encoding="utf-8") as f:
            text = f.read()
        
        word_count = len(text)
        logger.info(f"✅ 成功读取小说: {novel_path.name} ({word_count}字)")
             
        return text
    
    def _parse_json_response(self, response: str) -> Any:
        """解析LLM返回的JSON响应"""
        # 提取JSON部分（去除可能的markdown代码块）
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        
        # 移除JSON中的注释（LLM可能返回带注释的JSON）
        # 处理单行注释：// ...
        response = re.sub(r'//.*?(?=\n|$)', '', response)
        # 处理多行注释：/* ... */
        response = re.sub(r'/\*.*?\*/', '', response, flags=re.DOTALL)
        # 移除空行和多余空白
        response = '\n'.join(line for line in response.split('\n') if line.strip())
        
        try:
            data = json.loads(response)
            return data
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON解析失败: {e}")
            logger.error(f"原始响应前500字: {response[:500]}...")
            logger.error(f"清理后响应前500字: {response[:500]}...")
            raise ValueError("LLM返回的数据格式不正确")
    
    def stage1_filter_characters(self, novel_text: str) -> List[Dict[str, Any]]:
        """
        阶段1：角色过滤
        快速扫描小说，列出所有角色并评估重要性
        
        Returns:
            [{"id": "npc_001", "name": "韩立", "importance": 0.9}, ...]
        """
        logger.info("=" * 60)
        logger.info("📍 阶段1：角色过滤（角色普查）")
        logger.info("=" * 60)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.char_filter_prompt),
            ("human", "{novel_text}")
        ])
        
        chain = prompt | self.llm | StrOutputParser()
        
        logger.info("🤖 正在调用LLM进行角色普查...")
        try:
            # 设置超时配置：10分钟
            response = chain.invoke(
                {"novel_text": novel_text},
                config={"timeout": 600}
            )
            characters_list = self._parse_json_response(response)
            
            logger.info(f"✅ 角色普查完成，发现 {len(characters_list)} 个角色")
            for char in characters_list[:5]:  # 显示前5个
                logger.info(f"   - {char.get('name')} (重要性: {char.get('importance')})")
            if len(characters_list) > 5:
                logger.info(f"   ... 还有 {len(characters_list) - 5} 个角色")
            
            return characters_list
        
        except Exception as e:
            logger.error(f"❌ 角色过滤失败: {e}")
            raise
    
    def stage2_extract_world_setting(self, novel_text: str) -> Dict[str, Any]:
        """
        阶段2：提取世界观设定
        
        Returns:
            world_setting.json 数据
        """
        logger.info("=" * 60)
        logger.info("📍 阶段2：提取世界观设定")
        logger.info("=" * 60)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.world_prompt),
            ("human", "{novel_text}")
        ])
        
        chain = prompt | self.llm | StrOutputParser()
        
        logger.info("🤖 正在调用LLM进行世界观解析...")
        try:
            # 设置超时配置：10分钟
            response = chain.invoke(
                {"novel_text": novel_text},
                config={"timeout": 600}
            )
            world_setting = self._parse_json_response(response)
            
            logger.info("✅ 世界观设定提取完成")
            logger.info(f"   - 世界标题: {world_setting.get('meta', {}).get('title', '未知')}")
            logger.info(f"   - 物理法则: {len(world_setting.get('laws_of_physics', []))}条")
            logger.info(f"   - 社会规则: {len(world_setting.get('social_rules', []))}条")
            logger.info(f"   - 地点数量: {len(world_setting.get('locations', []))}个")
            
            return world_setting
        
        except Exception as e:
            logger.error(f"❌ 世界观提取失败: {e}")
            raise
    
    def stage3_create_character_details(
        self, 
        novel_text: str, 
        characters_list: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        阶段3：创建角色详细档案
        为每个角色生成完整的角色卡
        
        Returns:
            {character_id: character_data, ...}
        """
        logger.info("=" * 60)
        logger.info("📍 阶段3：创建角色详细档案")
        logger.info("=" * 60)
        
        characters_details = {}
        total = len(characters_list)
        
        for idx, char_info in enumerate(characters_list, 1):
            char_id = char_info.get("id")
            char_name = char_info.get("name")
            importance = char_info.get("importance")
            
            logger.info(f"[{idx}/{total}] 正在处理角色: {char_name} (重要性: {importance})")
            
            # 动态填充提示词模板
            char_prompt = self.char_detail_prompt.replace("{target_name}", char_name)
            char_prompt = char_prompt.replace("{target_id}", char_id)
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", char_prompt),
                ("human", "{novel_text}")
            ])
            
            chain = prompt | self.llm | StrOutputParser()
            
            try:
                # 设置超时配置：10分钟
                response = chain.invoke(
                    {"novel_text": novel_text},
                    config={"timeout": 600}
                )
                char_data = self._parse_json_response(response)
                
                # 确保importance字段被保留
                char_data["importance"] = importance
                
                characters_details[char_id] = char_data
                logger.info(f"   ✅ {char_name} 档案创建完成")
            
            except Exception as e:
                logger.warning(f"   ⚠️  {char_name} 档案创建失败: {e}")
                # 创建一个基础档案，避免完全失败
                characters_details[char_id] = {
                    "id": char_id,
                    "name": char_name,
                    "importance": importance,
                    "error": str(e)
                }
        
        logger.info(f"✅ 角色档案创建完成: {len(characters_details)}/{total}")
        return characters_details
    
    def save_world_data(
        self,
        world_name: str,
        world_setting: Dict[str, Any],
        characters_list: List[Dict[str, Any]],
        characters_details: Dict[str, Dict[str, Any]]
    ) -> Path:
        """
        保存世界数据到目录结构
        
        Args:
            world_name: 世界名称（用作文件夹名）
            world_setting: 世界设定数据
            characters_list: 角色列表
            characters_details: 角色详细数据
        
        Returns:
            世界文件夹路径
        """
        logger.info("=" * 60)
        logger.info("💾 保存世界数据")
        logger.info("=" * 60)
        
        # 创建世界文件夹
        world_dir = settings.DATA_DIR / "worlds" / world_name
        world_dir.mkdir(parents=True, exist_ok=True)
        
        characters_dir = world_dir / "characters"
        characters_dir.mkdir(exist_ok=True)
        
        # 1. 保存世界设定
        world_setting_path = world_dir / "world_setting.json"
        with open(world_setting_path, "w", encoding="utf-8") as f:
            json.dump(world_setting, f, ensure_ascii=False, indent=2)
        logger.info(f"✅ 已保存: world_setting.json")
        
        # 2. 保存角色列表
        characters_list_path = world_dir / "characters_list.json"
        with open(characters_list_path, "w", encoding="utf-8") as f:
            json.dump(characters_list, f, ensure_ascii=False, indent=2)
        logger.info(f"✅ 已保存: characters_list.json ({len(characters_list)}个角色)")
        
        # 3. 保存每个角色的详细档案
        for char_id, char_data in characters_details.items():
            char_file = characters_dir / f"character_{char_id}.json"
            with open(char_file, "w", encoding="utf-8") as f:
                json.dump(char_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ 已保存: {len(characters_details)}个角色档案到 characters/")
        
        logger.info(f"📁 世界数据已保存到: {world_dir}")
        return world_dir
    
    def _auto_retry_failed_characters(
        self,
        world_dir: Path,
        world_name: str,
        novel_text: str,
        characters_list: List[Dict[str, Any]],
        retry_delay: int = 10,
        max_retries: int = 3
    ):
        """
        自动检查并重试失败的角色创建
        
        Args:
            world_dir: 世界文件夹路径
            world_name: 世界名称
            novel_text: 原始小说文本
            characters_list: 角色列表
            retry_delay: 重试延迟（秒）
            max_retries: 最大重试次数
        """
        import time
        
        logger.info("=" * 80)
        logger.info("🔍 检查角色创建状态...")
        logger.info("=" * 80)
        
        characters_dir = world_dir / "characters"
        failed_characters = []
        
        # 扫描失败的角色
        for char_info in characters_list:
            char_id = char_info["id"]
            char_name = char_info["name"]
            importance = char_info["importance"]
            char_file = characters_dir / f"character_{char_id}.json"
            
            # 情况1: 文件不存在
            if not char_file.exists():
                logger.warning(f"⚠️  {char_name} (ID: {char_id}): 文件不存在")
                failed_characters.append((char_id, char_name, importance))
                continue
            
            # 情况2: 文件存在但包含error字段
            try:
                with open(char_file, "r", encoding="utf-8") as f:
                    char_data = json.load(f)
                
                if "error" in char_data:
                    logger.warning(f"⚠️  {char_name} (ID: {char_id}): 创建失败")
                    failed_characters.append((char_id, char_name, importance))
                else:
                    logger.info(f"✅ {char_name} (ID: {char_id}): 状态正常")
            except json.JSONDecodeError:
                logger.warning(f"⚠️  {char_name} (ID: {char_id}): JSON解析失败")
                failed_characters.append((char_id, char_name, importance))
        
        # 如果没有失败的角色，直接返回
        if not failed_characters:
            logger.info("=" * 80)
            logger.info("✅ 太棒了！所有角色都创建成功，无需重试")
            logger.info("=" * 80)
            return
        
        # 发现失败的角色，开始重试
        logger.info("=" * 80)
        logger.info(f"⚠️  发现 {len(failed_characters)} 个角色创建失败，自动开始重试...")
        for char_id, char_name, importance in failed_characters:
            logger.info(f"   - {char_name} (ID: {char_id}, 重要性: {importance})")
        logger.info("=" * 80)
        
        success_count = 0
        still_failed = []
        
        # 逐个重试失败的角色
        for char_id, char_name, importance in failed_characters:
            retry_count = 0
            success = False
            
            while retry_count < max_retries and not success:
                retry_count += 1
                logger.info(f"🔄 [{retry_count}/{max_retries}] 重试: {char_name} (ID: {char_id})")
                
                # 延迟避免API限流
                if retry_count > 1 or failed_characters.index((char_id, char_name, importance)) > 0:
                    logger.info(f"⏰ 等待 {retry_delay} 秒以避免API限流...")
                    time.sleep(retry_delay)
                
                try:
                    # 动态填充提示词模板
                    char_prompt = self.char_detail_prompt.replace("{target_name}", char_name)
                    char_prompt = char_prompt.replace("{target_id}", char_id)
                    
                    prompt = ChatPromptTemplate.from_messages([
                        ("system", char_prompt),
                        ("human", "{novel_text}")
                    ])
                    
                    chain = prompt | self.llm | StrOutputParser()
                    
                    # 调用LLM
                    response = chain.invoke(
                        {"novel_text": novel_text},
                        config={"timeout": 600}
                    )
                    
                    # 解析JSON响应
                    char_data = self._parse_json_response(response)
                    char_data["importance"] = importance
                    
                    # 保存到文件
                    char_file = characters_dir / f"character_{char_id}.json"
                    with open(char_file, "w", encoding="utf-8") as f:
                        json.dump(char_data, f, ensure_ascii=False, indent=2)
                    
                    logger.info(f"✅ {char_name} 重试成功！")
                    success = True
                    success_count += 1
                
                except Exception as e:
                    logger.warning(f"❌ {char_name} 第{retry_count}次重试失败: {e}")
                    if retry_count < max_retries:
                        # 失败后等待更长时间
                        wait_time = retry_delay * 2
                        logger.info(f"⏰ 将在 {wait_time} 秒后再次尝试...")
                        time.sleep(wait_time)
            
            if not success:
                still_failed.append((char_id, char_name, importance))
        
        # 最终报告
        logger.info("=" * 80)
        logger.info("📊 自动重试完成！")
        logger.info(f"   ✅ 成功修复: {success_count} 个角色")
        logger.info(f"   ❌ 仍然失败: {len(still_failed)} 个角色")
        
        if still_failed:
            logger.warning("⚠️  以下角色仍未创建成功：")
            for char_id, char_name, importance in still_failed:
                logger.warning(f"   - {char_name} (ID: {char_id})")
            logger.warning("💡 建议：")
            logger.warning("   1. 稍后手动运行: python temp/retry_failed_characters.py {world_name}")
            logger.warning("   2. 检查API配额是否充足")
            logger.warning("   3. 增加retry_delay参数以降低请求频率")
        else:
            logger.info("🎉 所有角色现已创建完成！")
        
        logger.info("=" * 80)
    
    def run(self, novel_filename: str = "example_novel.txt") -> Path:
        """
        完整的三阶段运行流程
        
        Args:
            novel_filename: 小说文件名（在data/novels/目录下）
        
        Returns:
            生成的世界文件夹路径
        """
        logger.info("=" * 80)
        logger.info("🚀 启动架构师Agent - 三阶段世界构建流程")
        logger.info("=" * 80)
        
        # 读取小说
        novel_path = settings.NOVELS_DIR / novel_filename
        novel_text = self._read_novel(novel_path)
        
        # 阶段1：角色过滤
        characters_list = self.stage1_filter_characters(novel_text)
        
        # 阶段2：提取世界观
        world_setting = self.stage2_extract_world_setting(novel_text)
        
        # 阶段3：创建角色档案
        characters_details = self.stage3_create_character_details(novel_text, characters_list)
        
        # 确定世界名称
        world_name = world_setting.get("meta", {}).get("title", "未知世界")
        
        # 保存数据
        world_dir = self.save_world_data(
            world_name=world_name,
            world_setting=world_setting,
            characters_list=characters_list,
            characters_details=characters_details
        )
        
        logger.info("=" * 80)
        logger.info("🎉 世界构建完成！")
        logger.info(f"📁 世界数据路径: {world_dir}")
        logger.info(f"   - world_setting.json")
        logger.info(f"   - characters_list.json ({len(characters_list)}个角色)")
        logger.info(f"   - characters/ ({len(characters_details)}个档案)")
        logger.info("=" * 80)
        
        # 自动检查并重试失败的角色
        self._auto_retry_failed_characters(world_dir, world_name, novel_text, characters_list)
        
        return world_dir


# 便捷函数
def create_world(novel_filename: str = "example_novel.txt") -> Path:
    """创建世界数据的便捷函数"""
    architect = ArchitectAgent()
    return architect.run(novel_filename)
