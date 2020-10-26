"""Helpful APIs for setting up DiffSync logging.

Copyright (c) 2020 Network To Code, LLC <info@networktocode.com>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

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
