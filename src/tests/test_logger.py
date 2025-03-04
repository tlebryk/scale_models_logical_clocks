import pytest
import logging
import os
import time
from unittest.mock import patch, MagicMock
import tempfile
import shutil

# Import the module to be tested
import logger


# Mock LamportClock for testing
class MockLamportClock:
    def __init__(self, name):
        self.value = 0
        self.name = name

    def __str__(self):
        return f"{self.name}:{self.value}"


# Fixtures
@pytest.fixture
def mock_clock():
    """Create a mock LamportClock for testing."""
    return MockLamportClock("test")


@pytest.fixture
def temp_log_dir():
    """Create a temporary directory for log files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Clean up after the test
    shutil.rmtree(temp_dir)


# Tests for LogicalClockFilter
def test_logical_clock_filter(mock_clock):
    """Test that LogicalClockFilter adds logical clock information to log records."""
    # Create a filter
    filter = logger.LogicalClockFilter(mock_clock)

    # Create a log record
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Test message",
        args=(),
        exc_info=None,
    )

    # Apply the filter
    filter.filter(record)

    # Check that logical_clock was added to the record
    assert hasattr(record, "logical_clock")
    assert record.logical_clock == str(mock_clock)

    # Create a formatter that uses logical_clock
    formatter = logging.Formatter("%(message)s [LogicalClock: %(logical_clock)s]")

    # Format the record
    formatted = formatter.format(record)

    # Check that the formatted string contains the logical_clock
    assert "Test message [LogicalClock: test:0]" == formatted


# Tests for setup_logger
def test_setup_logger_name(mock_clock):
    """Test that setup_logger creates a logger with the correct name."""
    with patch("logging.getLogger") as mock_get_logger:
        with patch("logging.FileHandler"):
            logger.setup_logger(1, mock_clock)
            mock_get_logger.assert_called_once_with("VM_1")


def test_setup_logger_level(mock_clock):
    """Test that setup_logger sets the correct log level."""
    with patch("logging.getLogger") as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        with patch("logging.FileHandler"):
            logger.setup_logger(1, mock_clock, log_level=logging.DEBUG)
            mock_logger.setLevel.assert_called_once_with(logging.DEBUG)


def test_setup_logger_adds_filter(mock_clock):
    """Test that setup_logger adds LogicalClockFilter."""
    with patch("logging.getLogger") as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        with patch("logging.FileHandler"):
            logger.setup_logger(1, mock_clock)
            # Check that addFilter was called with an instance of LogicalClockFilter
            mock_logger.addFilter.assert_called_once()
            filter_arg = mock_logger.addFilter.call_args[0][0]
            assert isinstance(filter_arg, logger.LogicalClockFilter)
            assert filter_arg.clock == mock_clock


def test_setup_logger_creates_log_dir(mock_clock, temp_log_dir):
    """Test that setup_logger creates the log directory if it doesn't exist."""
    log_dir = os.path.join(temp_log_dir, "test_logs")

    # Ensure the directory doesn't exist before the test
    if os.path.exists(log_dir):
        shutil.rmtree(log_dir)

    with patch("logging.getLogger"):
        with patch("logging.FileHandler"):
            with patch("os.makedirs") as mock_makedirs:
                logger.setup_logger(1, mock_clock, log_dir=log_dir)
                mock_makedirs.assert_called_once_with(log_dir, exist_ok=True)


def test_setup_logger_creates_file_handler(mock_clock, temp_log_dir):
    """Test that setup_logger creates a file handler with the correct log file name."""
    with patch("logging.getLogger"):
        with patch("logging.FileHandler") as mock_handler:
            with patch("time.strftime", return_value="2023-01-01_12-00"):
                logger.setup_logger(1, mock_clock, log_dir=temp_log_dir, file_mode="a")

                # Check that FileHandler was created with the correct arguments
                mock_handler.assert_called_once()
                file_name = mock_handler.call_args[0][0]

                # Verify the file name format
                assert file_name == os.path.join(
                    temp_log_dir, "vm_log_2023-01-01_12-00_1.txt"
                )

                # Verify the file mode
                assert mock_handler.call_args[1]["mode"] == "a"


def test_setup_logger_sets_formatter(mock_clock):
    """Test that setup_logger sets the correct formatter."""
    with patch("logging.getLogger"):
        with patch("logging.FileHandler") as mock_handler:
            mock_file_handler = MagicMock()
            mock_handler.return_value = mock_file_handler

            logger.setup_logger(1, mock_clock)

            # Check that setFormatter was called
            mock_file_handler.setFormatter.assert_called_once()

            # Check that the formatter includes logical_clock
            formatter = mock_file_handler.setFormatter.call_args[0][0]
            assert "%(logical_clock)s" in formatter._fmt


def test_setup_logger_returns_logger(mock_clock):
    """Test that setup_logger returns a logger."""
    with patch("logging.getLogger") as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        with patch("logging.FileHandler"):
            result = logger.setup_logger(1, mock_clock)
            assert result == mock_logger


def test_setup_logger_clears_existing_handlers(mock_clock):
    """Test that setup_logger clears any existing handlers."""
    with patch("logging.getLogger") as mock_get_logger:
        mock_logger = MagicMock()
        # Add a mock handler to the logger
        mock_handler = MagicMock()
        mock_logger.handlers = [mock_handler]
        mock_get_logger.return_value = mock_logger

        with patch("logging.FileHandler"):
            logger.setup_logger(1, mock_clock)

            # Check that removeHandler was called for the existing handler
            mock_logger.removeHandler.assert_called_once_with(mock_handler)


def test_setup_logger_handler_level(mock_clock):
    """Test that setup_logger sets the correct log level on the file handler."""
    with patch("logging.getLogger"):
        with patch("logging.FileHandler") as mock_handler:
            mock_file_handler = MagicMock()
            mock_handler.return_value = mock_file_handler

            custom_level = logging.WARNING
            logger.setup_logger(1, mock_clock, log_level=custom_level)

            # Check that the handler level was set
            mock_file_handler.setLevel.assert_called_once_with(custom_level)
