"""
修复的配置管理模块
处理环境变量和应用配置
"""

import os
from typing import Optional
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import Field

# 加载环境变量
load_dotenv()


class DeepSeekConfig(BaseSettings):
    """DeepSeek API配置"""
    
    api_key: str = Field(default="sk-test-key", description="DeepSeek API密钥")
    base_url: str = Field(default="https://api.deepseek.com/v1", description="API基础URL")
    model: str = Field(default="deepseek-chat", description="使用的模型名称")
    timeout: int = Field(default=60, description="请求超时时间（秒）")
    max_retries: int = Field(default=3, description="最大重试次数")
    retry_delay: float = Field(default=1.0, description="重试间隔（秒）")
    
    model_config = {
        "env_prefix": "DEEPSEEK_",
        "extra": "ignore",
        "case_sensitive": False
    }


class ControllerConfig(BaseSettings):
    """控制器配置"""
    
    max_concurrent_sessions: int = Field(default=10, description="最大并发会话数")
    session_timeout: int = Field(default=3600, description="会话超时时间（秒）")
    enable_caching: bool = Field(default=True, description="启用缓存")
    cache_ttl: int = Field(default=300, description="缓存TTL（秒）")
    
    model_config = {
        "extra": "ignore",
        "case_sensitive": False
    }


class AppConfig(BaseSettings):
    """应用配置"""
    
    # 日志配置
    log_level: str = Field(default="INFO", description="日志级别")
    log_file_enabled: bool = Field(default=True, description="启用文件日志")
    log_max_bytes: int = Field(default=10485760, description="日志文件最大大小")
    log_backup_count: int = Field(default=3, description="日志备份数量")
    
    # 应用信息
    app_name: str = Field(default="system-diagram-agent", description="应用名称")
    app_version: str = Field(default="1.0.0", description="应用版本")
    app_debug: bool = Field(default=False, description="调试模式")
    
    # Web配置
    web_host: str = Field(default="localhost", description="Web服务地址")
    web_port: int = Field(default=5000, description="Web服务端口")
    web_debug: bool = Field(default=False, description="Web调试模式")
    
    model_config = {
        "extra": "ignore",
        "case_sensitive": False
    }


def validate_config() -> bool:
    """验证配置是否完整"""
    try:
        config = DeepSeekConfig()
        if not config.api_key or config.api_key == "sk-test-key":
            print("警告：使用测试API密钥，请设置真实的DEEPSEEK_API_KEY")
        
        return True
    except Exception as e:
        print(f"配置验证失败：{e}")
        return False


def get_config_info() -> dict:
    """获取配置信息（隐藏敏感信息）"""
    try:
        deepseek_config = DeepSeekConfig()
        app_config = AppConfig()
        controller_config = ControllerConfig()
        
        return {
            "deepseek": {
                "base_url": deepseek_config.base_url,
                "model": deepseek_config.model,
                "timeout": deepseek_config.timeout,
                "api_key_set": bool(deepseek_config.api_key and deepseek_config.api_key != "sk-test-key")
            },
            "app": {
                "name": app_config.app_name,
                "version": app_config.app_version,
                "log_level": app_config.log_level,
                "web_port": app_config.web_port
            },
            "controller": {
                "max_sessions": controller_config.max_concurrent_sessions,
                "cache_enabled": controller_config.enable_caching
            }
        }
    except Exception as e:
        return {"error": str(e)} 