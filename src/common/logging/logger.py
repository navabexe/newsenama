# File: common/logging/logger.py

import logging
import sys
from typing import Optional

logger = logging.getLogger("marketplace")
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(
    '[%(asctime)s] %(levelname)s | %(message)s | context=%(context)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)


def _extra_context(extra: Optional[dict] = None):
    return {"context": extra or {}}


def log_info(message: str, extra: Optional[dict] = None):
    logger.info(message, extra=_extra_context(extra))


def log_warning(message: str, extra: Optional[dict] = None):
    logger.warning(message, extra=_extra_context(extra))


def log_error(message: str, extra: Optional[dict] = None, exc_info: bool = False):
    logger.error(message, extra=_extra_context(extra), exc_info=exc_info)


def log_debug(message: str, extra: Optional[dict] = None):
    logger.debug(message, extra=_extra_context(extra))
