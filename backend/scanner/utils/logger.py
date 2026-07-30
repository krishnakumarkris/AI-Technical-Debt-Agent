"""
Centralized logger for the scanner module using loguru.
Import `logger` from this file anywhere you need to log.
"""

import sys
from loguru import logger

logger.remove()

logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <7}</level> | <level>{message}</level>",
    level="INFO",
)

logger.add(
    "scanner/output/scan.log",
    rotation="1 MB",
    retention=3,
    level="DEBUG",
)
