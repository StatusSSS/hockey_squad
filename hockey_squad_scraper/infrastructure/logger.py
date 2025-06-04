from __future__ import annotations

import sys

from loguru import logger


logger.remove()

logger.add(
    sys.stderr,
    level="INFO",
    backtrace=True,
    diagnose=True,
    colorize=True,
    enqueue=True
)


logger.disable("urllib3")

__all__ : list[str] = ["logger"]

