"""
运行架构师Agent的入口脚本
这是第一阶段Demo的主程序
"""
from agents.offline.architect import create_genesis
from config.settings import settings
from utils.logger import default_logger as logger


def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("🎭 欢迎使用 Infinite Story - 无限故事机")
    print("=" * 70)
    print()
    print("📌 当前阶段: 第一阶段 - 离线构建者 (The Architect)")
    print("🎯 目标: 将小说转化为可游戏化的Genesis世界数据包")
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
        genesis_path = create_genesis("example_novel.txt")
        
        print("\n" + "=" * 70)
        print("🎉 恭喜！第一阶段Demo运行成功！")
        print("=" * 70)
        print()
        print(f"📁 Genesis数据包已生成: {genesis_path}")
        print()
        print("📖 你可以打开以下文件查看结果：")
        print(f"   - Genesis.json: {genesis_path}")
        print(f"   - 运行日志: {settings.LOGS_DIR}/architect.log")
        print()
        print("=" * 70)
        print()
        print("🔜 下一步:")
        print("   第二阶段将实现在线运行系统（信息中枢、光明会、NPC等）")
        print("   敬请期待！")
        print()
        
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

