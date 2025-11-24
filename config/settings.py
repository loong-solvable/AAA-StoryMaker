"""
配置管理模块
负责加载环境变量和项目配置
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 加载环境变量
load_dotenv(PROJECT_ROOT / ".env")


class Settings:
    """项目配置类"""
    
    # LLM配置
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "zhipu")
    
    # 智谱清言配置
    ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY", "")
    
    # OpenAI配置（备用）
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    
    # 讯飞星火配置（备用）
    IFLYTEK_APP_ID = os.getenv("IFLYTEK_APP_ID", "")
    IFLYTEK_API_KEY = os.getenv("IFLYTEK_API_KEY", "")
    IFLYTEK_API_SECRET = os.getenv("IFLYTEK_API_SECRET", "")
    
    # 模型参数
    MODEL_NAME = os.getenv("MODEL_NAME", "glm-4")
    TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4000"))
    
    # 项目路径
    DATA_DIR = PROJECT_ROOT / "data"
    NOVELS_DIR = DATA_DIR / "novels"
    GENESIS_DIR = DATA_DIR / "genesis"
    LOGS_DIR = PROJECT_ROOT / "logs"
    PROMPTS_DIR = PROJECT_ROOT / "prompts"
    
    @classmethod
    def validate(cls):
        """验证配置是否完整"""
        errors = []
        
        if cls.LLM_PROVIDER == "zhipu" and not cls.ZHIPU_API_KEY:
            errors.append("❌ 未配置ZHIPU_API_KEY")
        elif cls.LLM_PROVIDER == "openai" and not cls.OPENAI_API_KEY:
            errors.append("❌ 未配置OPENAI_API_KEY")
        elif cls.LLM_PROVIDER == "iflytek" and not cls.IFLYTEK_API_KEY:
            errors.append("❌ 未配置讯飞星火API密钥")
        
        if errors:
            error_msg = "\n".join(errors)
            raise ValueError(f"配置验证失败:\n{error_msg}\n\n请检查.env文件配置")
        
        return True
    
    @classmethod
    def ensure_directories(cls):
        """确保必要的目录存在"""
        cls.NOVELS_DIR.mkdir(parents=True, exist_ok=True)
        cls.GENESIS_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOGS_DIR.mkdir(parents=True, exist_ok=True)


# 全局配置实例
settings = Settings()

