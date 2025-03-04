# logger.py
import logging
from clock import LamportClock
import threading
import time
import os


class LogicalClockFilter(logging.Filter):
    """A filter that adds logical clock information to log records"""

    def __init__(self, clock):
        super().__init__()
        self.clock = clock

    def filter(self, record):
        record.logical_clock = str(self.clock)
        return True


def setup_logger(
    vm_id,
    logical_clock,
    log_level=logging.INFO,
    file_mode="w",
    log_dir="./logs/logs_trials",
):
    os.makedirs(log_dir, exist_ok=True)
    logger = logging.getLogger(f"VM_{vm_id}")
    logger.setLevel(log_level)

    # Clear any existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Add our filter that injects the logical clock into each record
    logger.addFilter(LogicalClockFilter(logical_clock))

    # Create file handler
    # Create log file name with timestamp to the minute
    log_file_name = os.path.join(
        log_dir, f"vm_log_{time.strftime('%Y-%m-%d_%H-%M')}_{vm_id}.txt"
    )
    file_handler = logging.FileHandler(log_file_name, mode=file_mode)
    file_handler.setLevel(log_level)

    # Update formatter to include logical clock
    formatter = logging.Formatter(
        " %(message)s | %(asctime)s | %(levelname)s | [LogicalClock: %(logical_clock)s]"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger  # Return the regular logger, not an adapter
