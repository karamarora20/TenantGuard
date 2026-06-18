import logging
from pathlib import Path
from typing import Optional, Union

from src.config.settings import settings


def get_logger(
    name: str = "app",
    log_file: Optional[Union[str, Path]] = None,
    level: int = settings.LOG_LEVEL,
) -> logging.Logger:
    """Create and return a configured logger.

    Args:
        name: Logger name.
        log_file: Optional path to a file to write logs.
        level: Logging level.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(level)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    if log_file:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
