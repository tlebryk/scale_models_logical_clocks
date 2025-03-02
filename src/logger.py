# logger.py
import logging
from clock import LamportClock


class LogicalClockAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        # Assume extra contains 'logical_clock'
        clock = kwargs.pop("logical_clock", None)
        if clock is not None:
            msg = f"[LogicalClock: {clock}] {msg}"
        return msg, kwargs


def setup_logger(vm_id, logical_clock: LamportClock, log_level=logging.INFO):
    logger = logging.getLogger(f"VM_{vm_id}")
    logger.setLevel(log_level)

    if not logger.handlers:
        file_handler = logging.FileHandler(f"vm_{vm_id}_log.txt")
        file_handler.setLevel(log_level)
        formatter = logging.Formatter(
            "%(asctime)s | VM %(name)s | %(levelname)s | %(message)s"
        ) # look how to add line number of the log 
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return LogicalClockAdapter(logger, {"logical_clock": logical_clock})
