"""
LLM 并发控制模块

用法：
    from utils.concurrency import llm_concurrency
    
    async with llm_concurrency.get_semaphore():
        result = await llm.ainvoke(...)
"""

import asyncio
import os
import weakref
from typing import Optional


class LLMConcurrencyManager:
    """线程安全的 LLM 并发控制器"""
    
    def __init__(self, max_concurrency: Optional[int] = None):
        self._concurrency = max_concurrency or int(os.getenv("LLM_CONCURRENCY", "5"))
        self._semaphores: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()
    
    def get_semaphore(self) -> asyncio.Semaphore:
        """获取与当前事件循环绑定的 Semaphore（公开 API）"""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        
        if loop:
            sem = self._semaphores.get(loop)
            if sem is None:
                sem = asyncio.Semaphore(self._concurrency)
                self._semaphores[loop] = sem
            return sem
        return asyncio.Semaphore(self._concurrency)
    
    def set_concurrency(self, value: int):
        """动态调整并发数"""
        self._concurrency = value
    
    @property
    def concurrency(self) -> int:
        return self._concurrency


# 全局单例
llm_concurrency = LLMConcurrencyManager()

