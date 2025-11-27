"""
运行架构师Agent的入口脚本
三阶段世界构建流程
"""
from agents.offline.architect import create_world
from config.settings import settings
from utils.logger import default_logger as logger


def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("🎭 欢迎使用 Infinite Story - 无限故事机")
    print("=" * 70)
    print()
    print("📌 三阶段构建流程:")
    print("   1️⃣ 角色过滤 - 识别所有角色并评估重要性")
    print("   2️⃣ 世界设定 - 提取物理法则、社会规则、地点")
    print("   3️⃣ 角色档案 - 为每个角色创建详细档案")
    print()
    print("=" * 70)
    print()
    
    # 验证配置
    try:
        logger.info("🔍 正在验证配置...")
        settings.validate()
        logger.info("✅ 配置验证通过")
    except ValueError as e:
        logger.error(str(e))
        print("\n" + "=" * 70)
        print("❌ 配置验证失败！")
        print("=" * 70)
        print()
        print("请按以下步骤配置：")
        print("1. 复制 .env.example 为 .env")
        print("2. 编辑 .env 文件，填入你的智谱清言API密钥")
        print("3. 保存后重新运行本脚本")
        print()
        return
    
    # 确保目录存在
    settings.ensure_directories()
    
    # 运行架构师
    try:
        world_dir = create_world("example_novel.txt")
        
        print("\n" + "=" * 70)
        print("🎉 世界构建成功！")
        print("=" * 70)
        print()
        print(f"📁 世界数据已生成: {world_dir}")
        print()
        print("📖 生成的文件：")
        print(f"   - world_setting.json      # 世界观设定")
        print(f"   - characters_list.json    # 角色列表")
        print(f"   - characters/             # 角色详细档案")
        print()
        print(f"📋 运行日志: {settings.LOGS_DIR}/architect.log")
        print()
        print("=" * 70)
        
    except FileNotFoundError as e:
        logger.error(f"❌ 文件未找到: {e}")
        print("\n" + "=" * 70)
        print("❌ 运行失败：找不到示例小说文件")
        print("=" * 70)
        print()
        print(f"请确保文件存在: {settings.NOVELS_DIR}/example_novel.txt")
        print()
        
    except Exception as e:
        logger.error(f"❌ 运行过程中发生错误: {e}", exc_info=True)
        print("\n" + "=" * 70)
        print("❌ 运行失败")
        print("=" * 70)
        print()
        print(f"错误信息: {e}")
        print()
        print("请查看日志文件获取详细信息:")
        print(f"   {settings.LOGS_DIR}/architect.log")
        print()


if __name__ == "__main__":
    main()

