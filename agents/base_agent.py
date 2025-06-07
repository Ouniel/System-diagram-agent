"""
基础Agent抽象类
定义所有Agent的公共接口和功能
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from utils.logger import LoggerMixin
from api.deepseek_client import DeepSeekClient


class BaseAgent(ABC, LoggerMixin):
    """基础Agent抽象类"""
    
    def __init__(self, client: Optional[DeepSeekClient] = None):
        """
        初始化基础Agent
        
        Args:
            client: DeepSeek API客户端，如果不提供则创建新实例
        """
        self.client = client or DeepSeekClient()
        self.context = {}  # 上下文存储
        
    @abstractmethod
    def process(self, input_data: Any, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        处理输入数据的抽象方法
        
        Args:
            input_data: 输入数据
            context: 上下文信息
        
        Returns:
            处理结果字典
        """
        pass
    
    def update_context(self, key: str, value: Any) -> None:
        """
        更新上下文信息
        
        Args:
            key: 上下文键
            value: 上下文值
        """
        self.context[key] = value
        self.logger.debug(f"更新上下文: {key}")
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """
        获取上下文信息
        
        Args:
            key: 上下文键
            default: 默认值
        
        Returns:
            上下文值
        """
        return self.context.get(key, default)
    
    def clear_context(self) -> None:
        """清空上下文"""
        self.context.clear()
        self.logger.debug("清空上下文")
    
    def _make_api_call(
        self, 
        prompt: str, 
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        统一的API调用方法
        
        Args:
            prompt: 提示词
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大token数
        
        Returns:
            API响应文本
        """
        try:
            self.logger.debug(f"发送API请求，prompt长度: {len(prompt)}")
            
            messages = [{"role": "user", "content": prompt}]
            
            response = self.client.chat_completion(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            self.logger.debug(f"收到API响应，长度: {len(response) if response else 0}")
            return response
            
        except Exception as e:
            self.logger.error(f"API调用失败: {e}")
            raise
    
    def _retry_api_call(
        self,
        prompt: str,
        max_retries: int = 3,
        **kwargs
    ) -> str:
        """
        带重试的API调用
        
        Args:
            prompt: 提示词
            max_retries: 最大重试次数
            **kwargs: 其他API参数
        
        Returns:
            API响应文本
        """
        return self.client.retry_request(
            self._make_api_call,
            max_retries=max_retries,
            prompt=prompt,
            **kwargs
        )
    
    def validate_input(self, input_data: Any) -> bool:
        """
        验证输入数据的基础方法
        
        Args:
            input_data: 输入数据
        
        Returns:
            是否有效
        """
        if input_data is None:
            self.logger.warning("输入数据为空")
            return False
        
        if isinstance(input_data, str) and not input_data.strip():
            self.logger.warning("输入字符串为空")
            return False
        
        return True
    
    def format_output(self, result: Any) -> Dict[str, Any]:
        """
        格式化输出结果的基础方法
        
        Args:
            result: 处理结果
        
        Returns:
            格式化后的结果字典
        """
        return {
            "success": True,
            "data": result,
            "agent": self.__class__.__name__,
            "context": self.context.copy()
        }
    
    def handle_error(self, error: Exception) -> Dict[str, Any]:
        """
        统一的错误处理方法
        
        Args:
            error: 异常对象
        
        Returns:
            错误信息字典
        """
        self.logger.error(f"{self.__class__.__name__} 处理失败: {error}")
        
        return {
            "success": False,
            "error": str(error),
            "agent": self.__class__.__name__,
            "context": self.context.copy()
        }
    
    def get_agent_info(self) -> Dict[str, Any]:
        """
        获取Agent信息
        
        Returns:
            Agent信息字典
        """
        return {
            "name": self.__class__.__name__,
            "description": self.__doc__ or "无描述",
            "context_keys": list(self.context.keys()),
            "client_info": self.client.get_model_info()
        } 