import logging
import sys
from loguru import logger


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging(log_level: str = "INFO"):
    # Set Loguru's log level to INFO
    logger.remove()
    logger.add(sys.stderr, level=log_level)

    # Attach the intercept handler to the stdlib root logger
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # Let uvicorn's logs propagate so they go through Loguru too
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True