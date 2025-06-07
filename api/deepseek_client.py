"""
DeepSeek API客户端
封装DeepSeek API的调用逻辑
"""

import asyncio
import time
from typing import Dict, List, Optional, Union, AsyncGenerator
from openai import OpenAI, AsyncOpenAI
from openai.types.chat import ChatCompletion

from config import DeepSeekConfig
from utils.logger import LoggerMixin
from utils.validators import validate_api_response, sanitize_user_input


class DeepSeekClient(LoggerMixin):
    """DeepSeek API客户端"""
    
    def __init__(self, config: Optional[DeepSeekConfig] = None, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        初始化客户端
        
        Args:
            config: DeepSeek配置对象
            api_key: API密钥，如果不提供则使用配置中的密钥
            base_url: API基础URL，如果不提供则使用配置中的URL
        """
        self.config = config or DeepSeekConfig()
        self.api_key = api_key or self.config.api_key
        self.base_url = base_url or self.config.base_url
        
        # 初始化同步和异步客户端
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.config.timeout
        )
        
        self.async_client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.config.timeout
        )
        
        self.logger.info(f"DeepSeek客户端初始化完成，基础URL: {self.base_url}")
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs
    ) -> Union[ChatCompletion, str]:
        """
        发送聊天完成请求
        
        Args:
            messages: 消息列表
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大token数
            stream: 是否使用流式响应
            **kwargs: 其他参数
        
        Returns:
            API响应或生成的文本
        """
        # 清理输入
        cleaned_messages = []
        for msg in messages:
            cleaned_msg = {
                "role": msg["role"],
                "content": sanitize_user_input(msg["content"])
            }
            cleaned_messages.append(cleaned_msg)
        
        # 设置默认参数
        model = model or self.config.model
        temperature = temperature if temperature is not None else 0.7
        max_tokens = max_tokens or 4000
        
        try:
            self.logger.debug(f"发送聊天请求，模型: {model}, 消息数: {len(cleaned_messages)}")
            
            response = self.client.chat.completions.create(
                model=model,
                messages=cleaned_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream,
                **kwargs
            )
            
            if stream:
                return self._handle_stream_response(response)
            else:
                content = response.choices[0].message.content
                self.logger.debug(f"收到响应，长度: {len(content) if content else 0}")
                return content
                
        except Exception as e:
            self.logger.error(f"聊天请求失败: {e}")
            raise
    
    def reasoning_completion(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        发送推理完成请求
        
        Args:
            prompt: 推理提示
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大token数
            **kwargs: 其他参数
        
        Returns:
            生成的文本
        """
        model = model or self.config.model
        
        messages = [
            {"role": "user", "content": sanitize_user_input(prompt)}
        ]
        
        return self.chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
    
    async def async_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        异步发送聊天完成请求
        
        Args:
            messages: 消息列表
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大token数
            **kwargs: 其他参数
        
        Returns:
            生成的文本
        """
        # 清理输入
        cleaned_messages = []
        for msg in messages:
            cleaned_msg = {
                "role": msg["role"],
                "content": sanitize_user_input(msg["content"])
            }
            cleaned_messages.append(cleaned_msg)
        
        # 设置默认参数
        model = model or self.config.model
        temperature = temperature if temperature is not None else 0.7
        max_tokens = max_tokens or 4000
        
        try:
            self.logger.debug(f"发送异步聊天请求，模型: {model}")
            
            response = await self.async_client.chat.completions.create(
                model=model,
                messages=cleaned_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            content = response.choices[0].message.content
            self.logger.debug(f"收到异步响应，长度: {len(content) if content else 0}")
            return content
            
        except Exception as e:
            self.logger.error(f"异步聊天请求失败: {e}")
            raise
    
    def _handle_stream_response(self, response) -> str:
        """
        处理流式响应
        
        Args:
            response: 流式响应对象
        
        Returns:
            完整的响应文本
        """
        full_content = ""
        try:
            for chunk in response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_content += content
                    print(content, end='', flush=True)
            print()  # 换行
            return full_content
        except Exception as e:
            self.logger.error(f"处理流式响应失败: {e}")
            return full_content
    
    def retry_request(
        self,
        request_func,
        max_retries: Optional[int] = None,
        delay: float = 1.0,
        backoff_factor: float = 2.0,
        *args,
        **kwargs
    ):
        """
        带重试的请求
        
        Args:
            request_func: 请求函数
            max_retries: 最大重试次数
            delay: 初始延迟时间
            backoff_factor: 退避因子
            *args: 请求函数参数
            **kwargs: 请求函数关键字参数
        
        Returns:
            请求结果
        """
        max_retries = max_retries or self.config.max_retries
        current_delay = delay
        
        for attempt in range(max_retries + 1):
            try:
                return request_func(*args, **kwargs)
            except Exception as e:
                if attempt == max_retries:
                    self.logger.error(f"请求失败，已达到最大重试次数 {max_retries}: {e}")
                    raise
                
                self.logger.warning(f"请求失败，{current_delay}秒后重试 (第{attempt + 1}次): {e}")
                time.sleep(current_delay)
                current_delay *= backoff_factor
    
    def test_connection(self) -> bool:
        """
        测试API连接
        
        Returns:
            连接是否成功
        """
        try:
            response = self.chat_completion(
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            self.logger.info("API连接测试成功")
            return True
        except Exception as e:
            self.logger.error(f"API连接测试失败: {e}")
            return False
    
    def get_model_info(self) -> Dict[str, str]:
        """
        获取模型信息
        
        Returns:
            模型信息字典
        """
        return {
            "chat_model": self.config.model,
            "reasoner_model": self.config.model,
            "base_url": self.base_url,
            "api_key_set": bool(self.api_key)
        } 