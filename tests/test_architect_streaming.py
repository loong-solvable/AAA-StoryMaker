"""
创世组测试脚本 - 流式输出版本
用于测试超时修复效果，并通过流式输出监控LLM响应进度
"""
import json
from pathlib import Path
from langchain_core.prompts import ChatPromptTemplate
from utils.llm_factory import get_llm
from utils.logger import setup_logger
from config.settings import settings

logger = setup_logger("GenesisGroupTest", "genesis_group_test.log")


class GenesisGroupTester:
    """创世组测试类 - 使用流式输出"""
    
    def __init__(self):
        """初始化测试器"""
        logger.info("🧪 初始化创世组测试器...")
        self.llm = get_llm()
        logger.info("✅ LLM初始化完成")
    
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
    
    def _parse_json_response(self, response: str) -> any:
        """解析JSON响应"""
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
            return data
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON解析失败: {e}")
            logger.error(f"原始响应前500字: {response[:500]}...")
            raise ValueError("LLM返回的数据格式不正确")
    
    def test_stage1_with_streaming(self, novel_text: str):
        """测试阶段1：角色过滤（流式输出）"""
        print("\n" + "=" * 70)
        print("📍 测试阶段1：角色过滤（流式输出）")
        print("=" * 70)
        
        logger.info("📍 开始测试阶段1 - 角色过滤")
        
        # 加载提示词
        char_filter_prompt = self._load_prompt("角色过滤架构师.txt")
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", char_filter_prompt),
            ("human", "{novel_text}")
        ])
        
        chain = prompt | self.llm
        
        print("🤖 正在调用LLM (流式输出)...")
        print("-" * 70)
        
        try:
            # 使用流式输出
            full_response = ""
            chunk_count = 0
            
            for chunk in chain.stream({"novel_text": novel_text}):
                chunk_count += 1
                content = chunk.content if hasattr(chunk, 'content') else str(chunk)
                full_response += content
                
                # 实时打印，每收到一个chunk就打印一个点
                print(".", end="", flush=True)
                
                # 每50个chunk打印一次统计信息
                if chunk_count % 50 == 0:
                    print(f" [{chunk_count} chunks, {len(full_response)} chars]", flush=True)
            
            print()  # 换行
            print("-" * 70)
            print(f"✅ 流式接收完成！共收到 {chunk_count} 个chunks, {len(full_response)} 个字符")
            
            # 解析JSON
            characters_list = self._parse_json_response(full_response)
            
            print(f"✅ 角色普查完成，发现 {len(characters_list)} 个角色")
            for char in characters_list[:5]:
                print(f"   - {char.get('name')} (重要性: {char.get('importance')})")
            if len(characters_list) > 5:
                print(f"   ... 还有 {len(characters_list) - 5} 个角色")
            
            logger.info(f"✅ 阶段1测试成功，发现 {len(characters_list)} 个角色")
            return characters_list
        
        except Exception as e:
            logger.error(f"❌ 阶段1测试失败: {e}", exc_info=True)
            print(f"\n❌ 测试失败: {e}")
            raise
    
    def test_stage2_with_streaming(self, novel_text: str):
        """测试阶段2：世界观提取（流式输出） - 重点测试"""
        print("\n" + "=" * 70)
        print("📍 测试阶段2：世界观提取（流式输出） ⭐ 重点测试")
        print("=" * 70)
        
        logger.info("📍 开始测试阶段2 - 世界观提取（重点测试）")
        
        # 加载提示词
        world_prompt = self._load_prompt("世界观架构师.txt")
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", world_prompt),
            ("human", "{novel_text}")
        ])
        
        chain = prompt | self.llm
        
        print("🤖 正在调用LLM (流式输出)...")
        print("⏱️  这是最耗时的阶段，预计需要1-3分钟...")
        print("-" * 70)
        
        try:
            # 使用流式输出
            full_response = ""
            chunk_count = 0
            
            for chunk in chain.stream({"novel_text": novel_text}):
                chunk_count += 1
                content = chunk.content if hasattr(chunk, 'content') else str(chunk)
                full_response += content
                
                # 实时打印
                print(".", end="", flush=True)
                
                # 每50个chunk打印一次统计信息
                if chunk_count % 50 == 0:
                    print(f" [{chunk_count} chunks, {len(full_response)} chars]", flush=True)
            
            print()  # 换行
            print("-" * 70)
            print(f"✅ 流式接收完成！共收到 {chunk_count} 个chunks, {len(full_response)} 个字符")
            
            # 解析JSON
            world_setting = self._parse_json_response(full_response)
            
            print(f"\n✅ 世界观设定提取完成")
            print(f"   - 世界标题: {world_setting.get('meta', {}).get('title', '未知')}")
            print(f"   - 物理法则: {len(world_setting.get('laws_of_physics', []))}条")
            print(f"   - 社会规则: {len(world_setting.get('social_rules', []))}条")
            print(f"   - 地点数量: {len(world_setting.get('locations', []))}个")
            
            # 显示部分详细内容
            print(f"\n📋 世界观详情预览：")
            if world_setting.get('laws_of_physics'):
                print(f"   物理法则示例: {world_setting['laws_of_physics'][0][:100]}...")
            if world_setting.get('social_rules'):
                print(f"   社会规则示例: {world_setting['social_rules'][0][:100]}...")
            if world_setting.get('locations'):
                loc = world_setting['locations'][0]
                print(f"   地点示例: {loc.get('name')} - {loc.get('description', '')[:80]}...")
            
            logger.info(f"✅ 阶段2测试成功")
            return world_setting
        
        except Exception as e:
            logger.error(f"❌ 阶段2测试失败: {e}", exc_info=True)
            print(f"\n❌ 测试失败: {e}")
            raise
    
    def run_full_test(self, novel_filename: str = "example_novel.txt"):
        """运行完整测试"""
        print("\n" + "=" * 70)
        print("🧪 架构师Agent完整测试 - 流式输出版")
        print("=" * 70)
        print()
        print("本测试将验证：")
        print("  ✅ 超时配置是否生效（10分钟超时）")
        print("  ✅ 流式输出是否正常工作")
        print("  ✅ 各阶段是否能正确处理数据")
        print("  ⭐ 重点测试阶段2的世界观提取功能")
        print()
        
        # 读取小说
        novel_path = settings.NOVELS_DIR / novel_filename
        novel_text = self._read_novel(novel_path)
        
        # 测试阶段1
        print("\n🔄 开始测试阶段1...")
        try:
            characters_list = self.test_stage1_with_streaming(novel_text)
        except Exception as e:
            print(f"\n❌ 阶段1测试失败，停止后续测试")
            return False
        
        # 测试阶段2（重点）
        print("\n🔄 开始测试阶段2（重点）...")
        try:
            world_setting = self.test_stage2_with_streaming(novel_text)
        except Exception as e:
            print(f"\n❌ 阶段2测试失败")
            print("\n⚠️  如果出现超时错误，说明：")
            print("   1. 网络连接不稳定")
            print("   2. LLM服务响应过慢")
            print("   3. 提示词过于复杂，需要优化")
            return False
        
        print("\n" + "=" * 70)
        print("🎉 所有测试通过！")
        print("=" * 70)
        print()
        print("测试结果汇总：")
        print(f"  ✅ 阶段1 - 角色过滤: 发现 {len(characters_list)} 个角色")
        print(f"  ✅ 阶段2 - 世界观提取: 提取完成")
        print(f"     - 物理法则: {len(world_setting.get('laws_of_physics', []))}条")
        print(f"     - 社会规则: {len(world_setting.get('social_rules', []))}条")
        print(f"     - 地点: {len(world_setting.get('locations', []))}个")
        print()
        print("✅ 超时配置正常工作")
        print("✅ 流式输出正常工作")
        print("✅ 数据解析正常工作")
        print()
        print("现在可以安全使用 run_genesis.py 运行完整流程了！")
        print()
        
        logger.info("✅ 全部测试通过！")
        return True


def main():
    """主函数"""
    try:
        # 验证配置
        settings.validate()
        settings.ensure_directories()
        
        # 运行测试
        tester = GenesisGroupTester()
        success = tester.run_full_test("example_novel.txt")
        
        if not success:
            print("\n⚠️  测试未完全通过，请检查日志文件")
            print(f"   {settings.LOGS_DIR}/genesis_group_test.log")
    
    except Exception as e:
        logger.error(f"❌ 测试运行失败: {e}", exc_info=True)
        print(f"\n❌ 测试运行失败: {e}")
        print(f"详情请查看: {settings.LOGS_DIR}/genesis_group_test.log")


if __name__ == "__main__":
    main()
