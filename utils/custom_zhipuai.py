"""
自定义ChatZhipuAI类
修复langchain_community.chat_models.ChatZhipuAI的超时问题
原始类在_generate和_stream方法中硬编码了60秒超时
"""
from typing import Any, Iterator, List, Optional
import httpx
from langchain_core.messages import BaseMessage
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.outputs import ChatResult, ChatGenerationChunk
from langchain_core.language_models.chat_models import generate_from_stream
from langchain_community.chat_models import ChatZhipuAI
from langchain_community.chat_models.zhipuai import _get_jwt_token, _truncate_params, connect_sse
from utils.logger import setup_logger

logger = setup_logger("CustomZhipuAI")


class CustomChatZhipuAI(ChatZhipuAI):
    """
    自定义ChatZhipuAI类，修复超时问题
    
    原始ChatZhipuAI类在_generate方法中硬编码了60秒超时：
    with httpx.Client(headers=headers, timeout=60) as client:
    
    本类覆盖_generate和_stream方法，使用自定义的超时配置
    """
    
    # 新增字段：自定义超时配置（秒）
    request_timeout: float = 600.0  # 默认10分钟
    
    def __init__(self, *args, request_timeout: float = 600.0, **kwargs):
        """
        初始化自定义ChatZhipuAI
        
        Args:
            request_timeout: HTTP请求超时时间（秒），默认600秒（10分钟）
            *args, **kwargs: 传递给父类ChatZhipuAI的其他参数
        """
        super().__init__(*args, **kwargs)
        self.request_timeout = request_timeout
        logger.info(f"⏱️  自定义ChatZhipuAI已初始化，超时配置: {request_timeout}秒")
    
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        stream: Optional[bool] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """
        生成聊天响应（覆盖父类方法以修复超时问题）
        """
        should_stream = stream if stream is not None else self.streaming
        if should_stream:
            stream_iter = self._stream(
                messages, stop=stop, run_manager=run_manager, **kwargs
            )
            return generate_from_stream(stream_iter)

        if self.zhipuai_api_key is None:
            raise ValueError("Did not find zhipuai_api_key.")
        
        message_dicts, params = self._create_message_dicts(messages, stop)
        payload = {
            **params,
            **kwargs,
            "messages": message_dicts,
            "stream": False,
        }
        _truncate_params(payload)
        headers = {
            "Authorization": _get_jwt_token(self.zhipuai_api_key),
            "Accept": "application/json",
        }
        
        # ⚠️  关键修改：使用自定义超时配置，而不是硬编码的60秒
        timeout_config = httpx.Timeout(
            connect=60.0,                    # 连接超时：60秒
            read=self.request_timeout,       # 读取超时：使用自定义配置
            write=60.0,                      # 写入超时：60秒
            pool=60.0                        # 连接池超时：60秒
        )
        
        logger.debug(f"发起HTTP请求，超时配置: {self.request_timeout}秒")
        
        with httpx.Client(headers=headers, timeout=timeout_config) as client:
            response = client.post(self.zhipuai_api_base, json=payload)
            response.raise_for_status()
        
        return self._create_chat_result(response.json())

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        """
        流式生成聊天响应（覆盖父类方法以修复超时问题）
        """
        if self.zhipuai_api_key is None:
            raise ValueError("Did not find zhipuai_api_key.")
        
        message_dicts, params = self._create_message_dicts(messages, stop)
        payload = {
            **params,
            **kwargs,
            "messages": message_dicts,
            "stream": True,
        }
        _truncate_params(payload)
        headers = {
            "Authorization": _get_jwt_token(self.zhipuai_api_key),
            "Accept": "text/event-stream",
        }
        
        # ⚠️  关键修改：使用自定义超时配置
        timeout_config = httpx.Timeout(
            connect=60.0,
            read=self.request_timeout,
            write=60.0,
            pool=60.0
        )
        
        logger.debug(f"发起流式HTTP请求，超时配置: {self.request_timeout}秒")
        
        with httpx.Client(headers=headers, timeout=timeout_config) as client:
            with connect_sse(client, "POST", self.zhipuai_api_base, json=payload) as event_source:
                for sse in event_source.iter_sse():
                    if sse.data:
                        chunk = self._create_chat_chunk(sse.data, run_manager)
                        if chunk:
                            yield chunk

    def _create_chat_chunk(
        self, data: str, run_manager: Optional[CallbackManagerForLLMRun] = None
    ) -> Optional[ChatGenerationChunk]:
        """从SSE数据创建聊天块"""
        import json as json_lib
        from langchain_core.messages import AIMessageChunk
        
        if data == "[DONE]":
            return None
        
        try:
            response_dict = json_lib.loads(data)
            choices = response_dict.get("choices", [])
            if not choices:
                return None
            
            choice = choices[0]
            delta = choice.get("delta", {})
            content = delta.get("content", "")
            
            if not content:
                return None
            
            message_chunk = AIMessageChunk(content=content)
            generation_info = dict(finish_reason=choice.get("finish_reason"))
            
            chunk = ChatGenerationChunk(
                message=message_chunk,
                generation_info=generation_info
            )
            
            if run_manager:
                run_manager.on_llm_new_token(content, chunk=chunk)
            
            return chunk
        except Exception as e:
            logger.error(f"解析流式数据失败: {e}")
            return None



