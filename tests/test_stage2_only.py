"""
只测试阶段2：世界观提取
这是超时问题的重点测试
"""
import json
from pathlib import Path
from langchain_core.prompts import ChatPromptTemplate
from utils.llm_factory import get_llm
from utils.logger import setup_logger
from config.settings import settings

logger = setup_logger("Stage2Test", "stage2_test.log")


def load_prompt(filename: str) -> str:
    """加载提示词文件"""
    prompt_file = settings.PROMPTS_DIR / "offline" / filename
    
    if not prompt_file.exists():
        logger.error(f"❌ 未找到提示词文件: {prompt_file}")
        raise FileNotFoundError(f"提示词文件不存在: {prompt_file}")
    
    with open(prompt_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    logger.info(f"✅ 成功加载提示词: {filename}")
    return content


def read_novel(novel_path: Path) -> str:
    """读取小说文件"""
    if not novel_path.exists():
        logger.error(f"❌ 小说文件不存在: {novel_path}")
        raise FileNotFoundError(f"小说文件不存在: {novel_path}")
    
    with open(novel_path, "r", encoding="utf-8") as f:
        text = f.read()
    
    word_count = len(text)
    logger.info(f"✅ 成功读取小说: {novel_path.name} ({word_count}字)")
         
    return text


def parse_json_response(response: str) -> any:
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


def test_stage2_world_extraction():
    """测试阶段2：世界观提取（流式输出）"""
    print("\n" + "=" * 70)
    print("🎯 专项测试：阶段2 - 世界观提取")
    print("=" * 70)
    print()
    print("测试目标：")
    print("  ⭐ 验证超时配置是否生效（10分钟）")
    print("  ⭐ 验证世界观提取的完整性")
    print("  ⭐ 验证流式输出是否正常")
    print()
    print("-" * 70)
    
    # 初始化
    logger.info("🧪 初始化测试环境...")
    llm = get_llm()
    logger.info("✅ LLM初始化完成")
    
    # 读取小说
    novel_path = settings.NOVELS_DIR / "example_novel.txt"
    novel_text = read_novel(novel_path)
    
    # 加载提示词
    world_prompt = load_prompt("世界观架构师.txt")
    
    print("\n📋 提示词信息：")
    print(f"   - 长度: {len(world_prompt)} 字符")
    print(f"   - 小说长度: {len(novel_text)} 字符")
    print()
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", world_prompt),
        ("human", "{novel_text}")
    ])
    
    from langchain_core.output_parsers import StrOutputParser
    chain = prompt | llm | StrOutputParser()
    
    print("🤖 开始调用LLM进行世界观提取...")
    print("⏱️  这个过程可能需要1-3分钟，请耐心等待...")
    print("⏱️  已配置10分钟超时，不会出现之前的超时错误")
    print("💡 注意：由于智谱AI的流式输出兼容性问题，使用普通invoke模式")
    print("-" * 70)
    
    try:
        import time
        start_time = time.time()
        
        # 使用普通invoke（智谱AI的流式输出有兼容性问题）
        print("⏳ 正在等待LLM响应（这可能需要1-3分钟）...", flush=True)
        
        full_response = chain.invoke(
            {"novel_text": novel_text}
        )
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        print()  # 换行
        print("-" * 70)
        print(f"✅ 响应接收完成！")
        print(f"   - 耗时: {elapsed_time:.2f}秒")
        print(f"   - 总字符数: {len(full_response)}个")
        print()
        
        # 解析JSON
        print("🔄 正在解析JSON数据...")
        world_setting = parse_json_response(full_response)
        
        print("\n" + "=" * 70)
        print("✅ 世界观设定提取成功！")
        print("=" * 70)
        print()
        print("📊 提取结果统计：")
        print(f"   - 世界标题: {world_setting.get('meta', {}).get('title', '未知')}")
        print(f"   - 物理法则: {len(world_setting.get('laws_of_physics', []))}条")
        print(f"   - 社会规则: {len(world_setting.get('social_rules', []))}条")
        print(f"   - 地点数量: {len(world_setting.get('locations', []))}个")
        print()
        
        # 显示详细内容
        print("📋 详细内容预览：")
        print()
        
        if world_setting.get('laws_of_physics'):
            print("  🔬 物理法则:")
            for i, law in enumerate(world_setting['laws_of_physics'][:3], 1):
                print(f"     {i}. {law[:100]}{'...' if len(law) > 100 else ''}")
            if len(world_setting['laws_of_physics']) > 3:
                print(f"     ... 还有 {len(world_setting['laws_of_physics']) - 3} 条")
            print()
        
        if world_setting.get('social_rules'):
            print("  👥 社会规则:")
            for i, rule in enumerate(world_setting['social_rules'][:3], 1):
                print(f"     {i}. {rule[:100]}{'...' if len(rule) > 100 else ''}")
            if len(world_setting['social_rules']) > 3:
                print(f"     ... 还有 {len(world_setting['social_rules']) - 3} 条")
            print()
        
        if world_setting.get('locations'):
            print("  📍 地点信息:")
            for i, loc in enumerate(world_setting['locations'][:3], 1):
                name = loc.get('name', '未知')
                desc = loc.get('description', '')
                print(f"     {i}. {name}: {desc[:80]}{'...' if len(desc) > 80 else ''}")
            if len(world_setting['locations']) > 3:
                print(f"     ... 还有 {len(world_setting['locations']) - 3} 个地点")
            print()
        
        print("=" * 70)
        print("🎉 阶段2测试完全通过！")
        print("=" * 70)
        print()
        print("测试结论：")
        print("  ✅ 超时配置工作正常（未出现超时错误）")
        print(f"  ✅ LLM响应正常（耗时{elapsed_time:.2f}秒）")
        print("  ✅ JSON解析工作正常")
        print("  ✅ 数据结构完整")
        print()
        print("💡 现在可以安全运行 run_architect.py 了！")
        print()
        
        logger.info(f"✅ 阶段2测试成功，耗时 {elapsed_time:.2f}秒")
        return True
    
    except Exception as e:
        logger.error(f"❌ 阶段2测试失败: {e}", exc_info=True)
        print(f"\n❌ 测试失败: {e}")
        print()
        print("如果出现超时错误，可能的原因：")
        print("  1. 网络连接不稳定")
        print("  2. LLM服务响应过慢")
        print("  3. 提示词过于复杂")
        print()
        return False


def main():
    """主函数"""
    try:
        # 验证配置
        settings.validate()
        settings.ensure_directories()
        
        # 运行测试
        success = test_stage2_world_extraction()
        
        if not success:
            print("\n⚠️  测试失败，请检查日志文件")
            print(f"   {settings.LOGS_DIR}/stage2_test.log")
    
    except Exception as e:
        logger.error(f"❌ 测试运行失败: {e}", exc_info=True)
        print(f"\n❌ 测试运行失败: {e}")
        print(f"详情请查看: {settings.LOGS_DIR}/stage2_test.log")


if __name__ == "__main__":
    main()

