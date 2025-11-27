"""
临时工具：重试失败的角色创建
用于修复architect运行时因429错误导致的角色创建失败问题

使用方法：
    python temp/retry_failed_characters.py <世界名称>
    例如：python temp/retry_failed_characters.py 未知世界
"""
import json
import time
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agents.offline.architect import ArchitectAgent
from utils.logger import setup_logger

logger = setup_logger("CharacterRetry", "character_retry.log")


class CharacterRetryTool:
    """角色重试工具"""
    
    def __init__(self, world_name: str):
        """
        初始化重试工具
        
        Args:
            world_name: 世界名称（文件夹名）
        """
        self.world_name = world_name
        self.world_path = project_root / "data" / "worlds" / world_name
        self.characters_dir = self.world_path / "characters"
        self.characters_list_path = self.world_path / "characters_list.json"
        
        # 初始化architect（复用其LLM和prompt）
        self.architect = ArchitectAgent()
        
        logger.info(f"🔧 初始化角色重试工具")
        logger.info(f"📁 世界路径: {self.world_path}")
    
    def check_world_exists(self) -> bool:
        """检查世界文件夹是否存在"""
        if not self.world_path.exists():
            logger.error(f"❌ 世界文件夹不存在: {self.world_path}")
            return False
        
        if not self.characters_list_path.exists():
            logger.error(f"❌ 角色列表文件不存在: {self.characters_list_path}")
            return False
        
        if not self.characters_dir.exists():
            logger.error(f"❌ 角色文件夹不存在: {self.characters_dir}")
            return False
        
        return True
    
    def scan_failed_characters(self) -> List[Tuple[str, str, str, float]]:
        """
        扫描失败的角色
        
        Returns:
            List of (char_id, char_name, error_msg, importance)
        """
        logger.info("=" * 80)
        logger.info("🔍 开始扫描失败的角色...")
        logger.info("=" * 80)
        
        failed_characters = []
        
        # 读取角色列表
        with open(self.characters_list_path, "r", encoding="utf-8") as f:
            characters_list = json.load(f)
        
        logger.info(f"📋 角色列表中共有 {len(characters_list)} 个角色")
        
        # 检查每个角色的文件
        for char_info in characters_list:
            char_id = char_info["id"]
            char_name = char_info["name"]
            importance = char_info["importance"]
            
            char_file = self.characters_dir / f"character_{char_id}.json"
            
            # 情况1: 文件不存在
            if not char_file.exists():
                logger.warning(f"⚠️  {char_name} (ID: {char_id}): 文件不存在")
                failed_characters.append((char_id, char_name, "文件不存在", importance))
                continue
            
            # 情况2: 文件存在但包含error字段
            try:
                with open(char_file, "r", encoding="utf-8") as f:
                    char_data = json.load(f)
                
                if "error" in char_data:
                    error_msg = char_data["error"]
                    logger.warning(f"⚠️  {char_name} (ID: {char_id}): 创建失败 - {error_msg[:100]}")
                    failed_characters.append((char_id, char_name, error_msg, importance))
                else:
                    logger.info(f"✅ {char_name} (ID: {char_id}): 状态正常")
            
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️  {char_name} (ID: {char_id}): JSON解析失败 - {e}")
                failed_characters.append((char_id, char_name, f"JSON解析失败: {e}", importance))
        
        logger.info("=" * 80)
        logger.info(f"📊 扫描结果: 发现 {len(failed_characters)} 个失败的角色")
        if failed_characters:
            for char_id, char_name, error, importance in failed_characters:
                logger.info(f"   - {char_name} (ID: {char_id}, 重要性: {importance})")
        logger.info("=" * 80)
        
        return failed_characters
    
    def retry_character(
        self, 
        char_id: str, 
        char_name: str, 
        importance: float,
        novel_text: str,
        retry_delay: int = 5
    ) -> bool:
        """
        重试创建单个角色
        
        Args:
            char_id: 角色ID
            char_name: 角色名称
            importance: 重要性
            novel_text: 小说原文
            retry_delay: 重试前的延迟秒数（避免429）
        
        Returns:
            是否成功
        """
        logger.info(f"🔄 开始重试角色: {char_name} (ID: {char_id})")
        logger.info(f"⏰ 等待 {retry_delay} 秒以避免API限流...")
        time.sleep(retry_delay)
        
        try:
            # 动态填充提示词模板
            char_prompt = self.architect.char_detail_prompt.replace("{target_name}", char_name)
            char_prompt = char_prompt.replace("{target_id}", char_id)
            
            from langchain_core.prompts import ChatPromptTemplate
            from langchain_core.output_parsers import StrOutputParser
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", char_prompt),
                ("human", "{novel_text}")
            ])
            
            chain = prompt | self.architect.llm | StrOutputParser()
            
            logger.info(f"🤖 正在调用LLM创建角色档案...")
            
            # 设置超时配置：10分钟
            response = chain.invoke(
                {"novel_text": novel_text},
                config={"timeout": 600}
            )
            
            # 解析JSON响应
            char_data = self.architect._parse_json_response(response)
            
            # 确保importance字段被保留
            char_data["importance"] = importance
            
            # 保存到文件
            char_file = self.characters_dir / f"character_{char_id}.json"
            with open(char_file, "w", encoding="utf-8") as f:
                json.dump(char_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ {char_name} 档案重新创建成功！")
            return True
        
        except Exception as e:
            logger.error(f"❌ {char_name} 重试失败: {e}")
            return False
    
    def run_retry(
        self, 
        novel_path: str = None,
        retry_delay: int = 10,
        max_retries: int = 3
    ):
        """
        运行重试流程
        
        Args:
            novel_path: 小说文件路径（如果为None，会提示用户输入）
            retry_delay: 每次重试之间的延迟秒数
            max_retries: 最大重试次数
        """
        logger.info("=" * 80)
        logger.info("🚀 启动角色重试工具")
        logger.info("=" * 80)
        
        # 检查世界是否存在
        if not self.check_world_exists():
            logger.error("❌ 世界数据不完整，无法继续")
            return
        
        # 扫描失败的角色
        failed_characters = self.scan_failed_characters()
        
        if not failed_characters:
            logger.info("🎉 太棒了！没有发现失败的角色，一切正常！")
            return
        
        # 获取小说原文
        if novel_path is None:
            logger.info("=" * 80)
            logger.info("📖 请提供原始小说文件路径")
            logger.info("   示例: data/novels/example_novel.txt")
            novel_path = input("小说路径: ").strip()
        
        novel_file = Path(novel_path)
        if not novel_file.exists():
            logger.error(f"❌ 小说文件不存在: {novel_file}")
            return
        
        with open(novel_file, "r", encoding="utf-8") as f:
            novel_text = f.read()
        
        logger.info(f"✅ 已加载小说文件 ({len(novel_text)} 字符)")
        
        # 开始重试
        logger.info("=" * 80)
        logger.info("🔄 开始重试失败的角色")
        logger.info(f"   - 重试延迟: {retry_delay} 秒")
        logger.info(f"   - 最大重试次数: {max_retries}")
        logger.info("=" * 80)
        
        success_count = 0
        failed_count = 0
        
        for char_id, char_name, error, importance in failed_characters:
            retry_count = 0
            success = False
            
            while retry_count < max_retries and not success:
                retry_count += 1
                logger.info(f"📍 [{retry_count}/{max_retries}] 尝试重试: {char_name}")
                
                success = self.retry_character(
                    char_id=char_id,
                    char_name=char_name,
                    importance=importance,
                    novel_text=novel_text,
                    retry_delay=retry_delay
                )
                
                if not success and retry_count < max_retries:
                    logger.warning(f"⚠️  第 {retry_count} 次尝试失败，将在 {retry_delay * 2} 秒后重试...")
                    time.sleep(retry_delay * 2)  # 失败后等待更长时间
            
            if success:
                success_count += 1
            else:
                failed_count += 1
        
        # 最终报告
        logger.info("=" * 80)
        logger.info("📊 重试完成！最终结果：")
        logger.info(f"   ✅ 成功: {success_count} 个角色")
        logger.info(f"   ❌ 失败: {failed_count} 个角色")
        logger.info("=" * 80)
        
        if failed_count > 0:
            logger.warning("⚠️  仍有角色创建失败，可能需要：")
            logger.warning("   1. 增加retry_delay参数（减少API调用频率）")
            logger.warning("   2. 稍后再次运行此工具")
            logger.warning("   3. 检查API配额是否充足")


def main():
    """主函数"""
    print("=" * 80)
    print("🔧 角色重试工具 (临时工具)")
    print("   用于修复architect因API限流导致的角色创建失败问题")
    print("=" * 80)
    
    # 获取命令行参数
    if len(sys.argv) < 2:
        print("❌ 用法: python temp/retry_failed_characters.py <世界名称> [小说路径]")
        print("   示例: python temp/retry_failed_characters.py 未知世界 data/novels/example_novel.txt")
        sys.exit(1)
    
    world_name = sys.argv[1]
    novel_path = sys.argv[2] if len(sys.argv) >= 3 else None
    
    # 创建工具实例
    tool = CharacterRetryTool(world_name)
    
    # 运行重试
    tool.run_retry(
        novel_path=novel_path,
        retry_delay=10,  # 每次重试等待10秒
        max_retries=3    # 最多重试3次
    )
    
    print("=" * 80)
    print("✅ 工具执行完成！")
    print("=" * 80)


if __name__ == "__main__":
    main()

