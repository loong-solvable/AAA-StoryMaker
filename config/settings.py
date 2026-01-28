"""
配置管理模块
负责加载环境变量和项目配置
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Determine if running in a frozen state (PyInstaller)
if getattr(sys, 'frozen', False):
    # Bundled resources (code, prompts) are in _MEIPASS
    RESOURCE_ROOT = Path(sys._MEIPASS)
    # User data (logs, .env, saves) should be next to the executable
    USER_DATA_ROOT = Path(sys.executable).parent
else:
    # Normal development mode
    RESOURCE_ROOT = Path(__file__).parent.parent
    USER_DATA_ROOT = RESOURCE_ROOT

# 项目根目录 (保持兼容性，指向资源目录)
PROJECT_ROOT = RESOURCE_ROOT

# 加载环境变量 (从用户数据目录加载)
load_dotenv(USER_DATA_ROOT / ".env")


class Settings:
    """项目配置类"""
    
    # LLM配置
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "zhipu")
    
    # 智谱清言配置
    ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY", "")
    
    # OpenAI配置（备用）
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    
    # OpenRouter配置
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-3-flash-preview")
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    
    # 讯飞星火配置（备用）
    IFLYTEK_APP_ID = os.getenv("IFLYTEK_APP_ID", "")
    IFLYTEK_API_KEY = os.getenv("IFLYTEK_API_KEY", "")
    IFLYTEK_API_SECRET = os.getenv("IFLYTEK_API_SECRET", "")
    
    # 模型参数（OpenRouter使用时会优先读取OPENROUTER_MODEL）
    MODEL_NAME = os.getenv("MODEL_NAME", "glm-4")
    TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))
    MAX_TOKENS = None  # 不限制，让模型自己决定需要多少tokens

    # 在线交互超时与重试（面向玩家的实时体验）
    ONLINE_LLM_TIMEOUT = float(os.getenv("ONLINE_LLM_TIMEOUT", "180"))
    ONLINE_LLM_MAX_RETRIES = int(os.getenv("ONLINE_LLM_MAX_RETRIES", "1"))

    # LangSmith 追踪配置
    LANGCHAIN_TRACING = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
    LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "AAA-StoryMaker")
    LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY", "")
    
    # 项目路径
    # 项目路径
    DATA_DIR = USER_DATA_ROOT / "data"
    NOVELS_DIR = DATA_DIR / "novels"
    GENESIS_DIR = DATA_DIR / "genesis"
    LOGS_DIR = USER_DATA_ROOT / "logs"
    PROMPTS_DIR = RESOURCE_ROOT / "prompts"

    # 长期记忆存储（可选）
    MEMORY_MONGO_URI = os.getenv("MEMORY_MONGO_URI", "")
    MEMORY_MONGO_DB = os.getenv("MEMORY_MONGO_DB", "aaa_story")
    MEMORY_MONGO_COLLECTION = os.getenv("MEMORY_MONGO_COLLECTION", "long_term_memory")
    
    @classmethod
    def validate(cls):
        """验证配置是否完整"""
        errors = []
        
        if cls.LLM_PROVIDER == "zhipu" and not cls.ZHIPU_API_KEY:
            errors.append("❌ 未配置ZHIPU_API_KEY")
        elif cls.LLM_PROVIDER == "openai" and not cls.OPENAI_API_KEY:
            errors.append("❌ 未配置OPENAI_API_KEY")
        elif cls.LLM_PROVIDER == "openrouter" and not cls.OPENROUTER_API_KEY:
            errors.append("❌ 未配置OPENROUTER_API_KEY")
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
