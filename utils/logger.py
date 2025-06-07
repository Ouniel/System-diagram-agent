"""
日志工具模块
提供统一的日志管理功能
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from rich.logging import RichHandler
from rich.console import Console

from config import AppConfig


def setup_logger(
    name: str = "system_diagram_agent",
    level: Optional[str] = None,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    设置日志记录器
    
    Args:
        name: 日志记录器名称
        level: 日志级别
        log_file: 日志文件路径
    
    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger(name)
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 设置日志级别
    app_config = AppConfig()
    log_level = level or app_config.log_level
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # 创建控制台处理器（使用Rich美化输出）
    console_handler = RichHandler(
        console=Console(stderr=True),
        show_time=True,
        show_path=False,
        markup=True
    )
    console_handler.setLevel(logging.INFO)
    
    # 创建文件处理器
    log_file_path = log_file or "system_diagram_agent.log"
    if log_file_path:
        # 确保日志目录存在
        Path(log_file_path).parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # 设置文件日志格式
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    # 设置控制台日志格式
    console_formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    return logger


def get_logger(name: str = "system_diagram_agent") -> logging.Logger:
    """
    获取日志记录器
    
    Args:
        name: 日志记录器名称
    
    Returns:
        日志记录器实例
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        return setup_logger(name)
    return logger


class LoggerMixin:
    """日志记录器混入类"""
    
    @property
    def logger(self) -> logging.Logger:
        """获取当前类的日志记录器"""
        return get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")


# 默认日志记录器
default_logger = setup_logger() 