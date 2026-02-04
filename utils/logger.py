"""
JARVIS 日志系统
使用 loguru 提供美观的日志输出

Author: gngdingghuan
"""

import sys
from pathlib import Path
from loguru import logger

from config import get_config


def setup_logger():
    """配置日志系统"""
    config = get_config()
    
    # 移除默认处理器
    logger.remove()
    
    # 控制台输出（带颜色）
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level=config.log_level,
        colorize=True,
    )
    
    # 文件输出
    log_path = Path(config.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    logger.add(
        config.log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation="10 MB",
        retention="7 days",
        compression="zip",
    )
    
    return logger


# 初始化日志
log = setup_logger()
