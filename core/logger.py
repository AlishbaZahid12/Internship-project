"""
Centralized logging configuration. Import get_logger(__name__) in every
module instead of using print() statements.
"""

import logging
import os
from datetime import datetime

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, f"app_{datetime.now().strftime('%Y%m%d')}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),  # also prints to console
    ],
)


def get_logger(name: str) -> logging.Logger:
    """Usage: logger = get_logger(__name__)"""
    return logging.getLogger(name)