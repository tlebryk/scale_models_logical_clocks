import pytest
from clock import LamportClock


def test_init():
    """Test that a new LamportClock initializes with the correct name and a zero value."""
    clock = LamportClock("process1")
    assert clock.name == "process1"
    assert clock.value == 0


def test_increment():
    """Test that the increment method increases the clock value by 1."""
    clock = LamportClock("process1")
    assert clock.value == 0

    clock.increment()
    assert clock.value == 1

    clock.increment()
    assert clock.value == 2


def test_compare_with_smaller_value():
    """Test that compare sets the clock value to max(self.value, clock_value) + 1
    when the current value is larger."""
    clock = LamportClock("process1")
    clock.value = 5

    clock.compare(3)
    assert clock.value == 6  # max(5, 3) + 1 = 6


def test_compare_with_larger_value():
    """Test that compare sets the clock value to max(self.value, clock_value) + 1
    when the received value is larger."""
    clock = LamportClock("process1")
    clock.value = 5

    clock.compare(10)
    assert clock.value == 11  # max(5, 10) + 1 = 11


def test_compare_with_equal_value():
    """Test that compare sets the clock value to max(self.value, clock_value) + 1
    when the values are equal."""
    clock = LamportClock("process1")
    clock.value = 5

    clock.compare(5)
    assert clock.value == 6  # max(5, 5) + 1 = 6


def test_str_representation():
    """Test that the string representation is formatted correctly."""
    clock = LamportClock("process1")
    clock.value = 42

    assert str(clock) == "process1: 42"


def test_multiple_operations():
    """Test a sequence of operations to ensure correct behavior."""
    clock1 = LamportClock("process1")
    clock2 = LamportClock("process2")

    # Initial state
    assert clock1.value == 0
    assert clock2.value == 0

    # Process 1 does some work
    clock1.increment()
    assert clock1.value == 1

    # Process 2 does some work
    clock2.increment()
    clock2.increment()
    assert clock2.value == 2

    # Process 1 receives a message from Process 2 with clock value 2
    clock1.compare(clock2.value)
    assert clock1.value == 3  # max(1, 2) + 1 = 3

    # Process 2 does more work
    clock2.increment()
    assert clock2.value == 3

    # Process 2 receives a message from Process 1 with clock value 3
    clock2.compare(clock1.value)
    assert clock2.value == 4  # max(3, 3) + 1 = 4
