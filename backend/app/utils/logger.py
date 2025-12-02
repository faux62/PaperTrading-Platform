"""
PaperTrading Platform - Logger Configuration
Centralized logging with loguru
"""
import sys
from pathlib import Path
from loguru import logger

from app.config import settings


# Remove default handler
logger.remove()

# Console handler with custom format
logger.add(
    sys.stdout,
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="DEBUG" if settings.DEBUG else "INFO",
)

# File handler for all logs
log_path = Path("logs")
log_path.mkdir(exist_ok=True)

logger.add(
    log_path / "app.log",
    rotation="10 MB",
    retention="30 days",
    compression="gz",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
)

# File handler for errors only
logger.add(
    log_path / "error.log",
    rotation="10 MB",
    retention="30 days",
    compression="gz",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="ERROR",
)


def get_logger(name: str = __name__):
    """
    Get a logger instance with the specified name.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance
    """
    return logger.bind(name=name)


# Export configured logger
__all__ = ["logger", "get_logger"]
