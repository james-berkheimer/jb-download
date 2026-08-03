"""Console logging setup for jb-download."""

import logging

import colorlog

LOGGER_NAME = "jb-download"

_LEVEL_COLORS = {
    "DEBUG": "cyan",
    "INFO": "white",
    "WARNING": "yellow",
    "ERROR": "red",
    "CRITICAL": "red,bg_white",
}


def get_logger(name: str = LOGGER_NAME) -> logging.Logger:
    """Return the named jb-download logger without configuring it.

    Args:
        name: Logger name. Defaults to the application logger.

    Returns:
        The requested logger instance.
    """
    return logging.getLogger(name)


def setup_logger(level: int | str = logging.INFO, name: str = LOGGER_NAME) -> logging.Logger:
    """Configure and return the application logger with colored console output.

    INFO records are printed bare so normal progress output stays readable;
    every other level is prefixed with its level name.

    Args:
        level: Logging level, either a ``logging`` constant or its name.
        name: Logger name to configure.

    Returns:
        The configured logger instance.
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        logger.setLevel(level)
        return logger

    info_handler = logging.StreamHandler()
    info_handler.setFormatter(
        colorlog.ColoredFormatter("%(log_color)s%(message)s", log_colors=_LEVEL_COLORS)
    )
    info_handler.addFilter(lambda record: record.levelno == logging.INFO)

    other_handler = logging.StreamHandler()
    other_handler.setFormatter(
        colorlog.ColoredFormatter(
            "%(log_color)s%(levelname)s:%(reset)s %(message)s", log_colors=_LEVEL_COLORS
        )
    )
    other_handler.addFilter(lambda record: record.levelno != logging.INFO)

    logger.addHandler(info_handler)
    logger.addHandler(other_handler)
    logger.setLevel(level)
    logger.propagate = False

    return logger
