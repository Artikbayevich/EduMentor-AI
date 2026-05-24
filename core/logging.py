from loguru import logger
import sys


def setup_logging() -> None:
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="DEBUG",
        colorize=True,
    )
    logger.add(
        "logs/edumentor.log",
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        level="INFO",
    )
