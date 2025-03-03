import pytest
import logging
import os
import re
from unittest.mock import patch, MagicMock
from logger import LogicalClockAdapter, setup_logger
from clock import LamportClock


@pytest.fixture
def logical_clock():
    return LamportClock("test_process")


@pytest.fixture
def cleanup_log_files():
    # Setup - nothing to do
    yield
    # Teardown - remove any log files created during tests
    for filename in os.listdir("."):
        if filename.startswith("vm_") and filename.endswith("_log.txt"):
            os.remove(filename)


class TestLogicalClockAdapter:
    def test_process_with_logical_clock(self):
        """Test that process correctly formats messages when logical_clock is provided."""
        logger = logging.getLogger("test")
        adapter = LogicalClockAdapter(logger, {})

        clock = LamportClock("test")
        clock.value = 42

        msg, kwargs = adapter.process("Test message", {"logical_clock": clock})

        assert msg == "[LogicalClock: test: 42] Test message"
        assert "logical_clock" not in kwargs

    def test_process_without_logical_clock(self):
        """Test that process leaves messages unchanged when no logical_clock is provided."""
        logger = logging.getLogger("test")
        adapter = LogicalClockAdapter(logger, {})

        msg, kwargs = adapter.process("Test message", {})

        assert msg == "Test message"
        assert kwargs == {}


class TestSetupLogger:
    def test_setup_logger_creates_handler(self, logical_clock, cleanup_log_files):
        """Test that setup_logger creates a file handler if none exists."""
        vm_id = "test1"
        logger = setup_logger(vm_id, logical_clock)

        # Verify the logger is correctly configured
        assert logger.logger.name == f"VM_{vm_id}"
        assert logger.logger.level == logging.INFO
        assert len(logger.logger.handlers) == 1
        assert isinstance(logger.logger.handlers[0], logging.FileHandler)
        assert logger.logger.handlers[0].baseFilename.endswith(f"vm_{vm_id}_log.txt")

    def test_setup_logger_reuses_existing_handlers(
        self, logical_clock, cleanup_log_files
    ):
        """Test that setup_logger doesn't add duplicate handlers."""
        vm_id = "test2"

        # Call setup_logger twice with the same vm_id
        logger1 = setup_logger(vm_id, logical_clock)
        logger2 = setup_logger(vm_id, logical_clock)

        # Verify no duplicate handlers were created
        assert len(logger2.logger.handlers) == 1

    def test_setup_logger_with_custom_log_level(self, logical_clock, cleanup_log_files):
        """Test setup_logger with a custom log level."""
        vm_id = "test3"
        custom_level = logging.DEBUG

        logger = setup_logger(vm_id, logical_clock, log_level=custom_level)

        assert logger.logger.level == custom_level
        assert logger.logger.handlers[0].level == custom_level

    def test_logger_writes_to_file(self, logical_clock, cleanup_log_files):
        """Test that logs are correctly written to file with timestamp and logical clock."""
        vm_id = "test4"
        logger = setup_logger(vm_id, logical_clock)

        # Log a test message
        test_message = "This is a test log message"
        logger.info(test_message)

        # Verify the message was written to the log file
        log_file_path = f"vm_{vm_id}_log.txt"
        assert os.path.exists(log_file_path)

        with open(log_file_path, "r") as f:
            log_content = f.read()

        # Check log format
        assert f"VM VM_{vm_id}" in log_content
        assert "INFO" in log_content
        assert f"[LogicalClock: {logical_clock}]" in log_content
        assert test_message in log_content

        # Check timestamp format (should match "YYYY-MM-DD HH:MM:SS,mmm" format)
        timestamp_pattern = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}"
        assert re.search(timestamp_pattern, log_content) is not None

    @patch("logging.FileHandler")
    def test_log_formatter(self, mock_file_handler, logical_clock):
        """Test that the correct formatter is applied to the logger."""
        mock_handler_instance = MagicMock()
        mock_file_handler.return_value = mock_handler_instance

        setup_logger("test5", logical_clock)

        # Verify the formatter was set
        mock_handler_instance.setFormatter.assert_called_once()
        formatter = mock_handler_instance.setFormatter.call_args[0][0]

        # Check formatter format string
        expected_format = "%(asctime)s | VM %(name)s | %(levelname)s | %(message)s"
        assert formatter._fmt == expected_format
