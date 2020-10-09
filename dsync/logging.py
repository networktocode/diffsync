"""Helpful APIs for setting up DSync logging."""

import logging

import structlog  # type: ignore


def enable_console_logging(verbosity=0):
    """Enable formatted logging to console with the specified verbosity.

    See https://www.structlog.org/en/stable/development.html as a reference

    Args:
        verbosity (int): 0 for WARNING logs, 1 for INFO logs, 2 for DEBUG logs
    """
    if verbosity == 0:
        logging.basicConfig(format="%(message)s", level=logging.WARNING)
    elif verbosity == 1:
        logging.basicConfig(format="%(message)s", level=logging.INFO)
    else:
        logging.basicConfig(format="%(message)s", level=logging.DEBUG)

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,  # <-- added
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M.%S"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
