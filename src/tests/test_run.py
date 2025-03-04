import pytest
import socket
import json
import threading
import time
import os
from unittest.mock import MagicMock, patch, Mock
import queue

# Import the module to be tested
from run import VM, get_vm_host, ENVIRONMENT, TOTAL_VMS, STARTUP_TIMEOUT, LamportClock


# Fixtures
@pytest.fixture
def mock_logger():
    """Create a mock logger for testing."""
    logger = MagicMock()
    return logger


@pytest.fixture
def mock_socket():
    """Create a mock socket for testing."""
    mock_sock = MagicMock(spec=socket.socket)
    return mock_sock


@pytest.fixture
def vm_config():
    """Basic VM configuration for tests."""
    return {
        "vm_id": 1,
        "port": 5001,
        "peers": {"2": 5002, "3": 5003},
        "tick_rate": 2,
        "log_dir": "./test_logs",
        "run_time": 10,
        "max_action": 5,
    }


# Tests for utility functions
def test_get_vm_host():
    """Test get_vm_host function."""
    # Test with Docker environment
    with patch("run.ENVIRONMENT", "docker"):
        assert get_vm_host(1) == "lamport-vm1"
        assert get_vm_host(2) == "lamport-vm2"

    # Test with local environment
    with patch("run.ENVIRONMENT", "local"):
        assert get_vm_host(1) == "localhost"
        assert get_vm_host(2) == "localhost"


# Tests for VM class
@patch("run.logger.setup_logger")
@patch("run.LamportClock", LamportClock)
def test_vm_initialization(mock_setup_logger, vm_config, mock_logger):
    """Test VM initialization with various configurations."""
    mock_setup_logger.return_value = mock_logger

    # Create a VM instance
    vm = VM(**vm_config)

    # Verify correct initialization
    assert vm.vm_id == vm_config["vm_id"]
    assert vm.port == vm_config["port"]
    assert vm.peers == vm_config["peers"]
    assert vm.tick_rate == vm_config["tick_rate"]
    assert vm.max_action == vm_config["max_action"]
    assert vm.run_time == vm_config["run_time"]
    assert isinstance(vm.message_queue, queue.Queue)
    assert vm.clock.name == str(vm_config["vm_id"])
    assert vm.clock.value == 0

    # Verify logger was set up correctly
    mock_setup_logger.assert_called_once_with(
        vm_config["vm_id"], vm.clock, file_mode="w", log_dir=vm_config["log_dir"]
    )


@patch("run.logger.setup_logger")
@patch("run.LamportClock", LamportClock)
@patch("socket.socket")
def test_start_server(mock_socket, mock_setup_logger, vm_config, mock_logger):
    """Test the start_server method."""
    mock_setup_logger.return_value = mock_logger
    mock_socket_instance = MagicMock()
    mock_socket.return_value = mock_socket_instance

    vm = VM(**vm_config)

    # Mock threading to avoid actually creating a thread
    with patch("threading.Thread") as mock_thread:
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance

        # Call the method being tested
        vm.start_server()

        # Verify socket was created and configured correctly
        mock_socket.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM)

        # Verify binding depends on environment
        if ENVIRONMENT == "docker":
            mock_socket_instance.bind.assert_called_once_with(
                ("0.0.0.0", vm_config["port"])
            )
        else:
            mock_socket_instance.bind.assert_called_once_with(
                ("localhost", vm_config["port"])
            )

        # Verify socket is listening
        mock_socket_instance.listen.assert_called_once_with(5)

        # Verify thread was started for accept_connections
        mock_thread.assert_called_once()
        mock_thread_instance.start.assert_called_once()


@patch("run.logger.setup_logger")
@patch("run.LamportClock", LamportClock)
def test_log_event(mock_setup_logger, vm_config, mock_logger):
    """Test the log_event method."""
    mock_setup_logger.return_value = mock_logger

    vm = VM(**vm_config)
    test_event = "Test event"
    mock_logger.reset_mock()

    # Call the method being tested
    vm.log_event(test_event)

    # Verify log was created correctly
    mock_logger.info.assert_called_once_with(f"Event: {test_event}")


@patch("run.logger.setup_logger")
@patch("run.LamportClock", LamportClock)
def test_wait_for_all_vms(mock_setup_logger, vm_config, mock_logger):
    """Test the wait_for_all_vms method."""
    mock_setup_logger.return_value = mock_logger

    vm = VM(**vm_config)
    vm.peer_sockets = {2: MagicMock(), 3: MagicMock()}

    # Mock threading.Event
    with patch("threading.Event") as mock_event:
        mock_event_instance = MagicMock()
        mock_event.return_value = mock_event_instance

        # Set the event to trigger immediately
        mock_event_instance.wait.return_value = True

        # Call the method being tested
        vm.wait_for_all_vms()

        # Verify event was created and waited on
        mock_event.assert_called_once()
        mock_event_instance.wait.assert_called_once_with(timeout=STARTUP_TIMEOUT)

        # Since all peers are already connected, event should be set immediately
        mock_event_instance.set.assert_called_once()


@patch("run.logger.setup_logger")
@patch("run.LamportClock", LamportClock)
def test_setup_peer_connection(mock_setup_logger, vm_config, mock_logger):
    """Test setup_peer_connection method."""
    mock_setup_logger.return_value = mock_logger

    vm = VM(**vm_config)

    # Mock socket creation and connection
    with patch("socket.socket") as mock_socket:
        mock_socket_instance = MagicMock()
        mock_socket.return_value = mock_socket_instance

        # Mock threading
        with patch("threading.Thread") as mock_thread:
            mock_thread_instance = MagicMock()
            mock_thread.return_value = mock_thread_instance

            # Mock callback
            vm.on_peer_connected = MagicMock()

            # Call the method being tested
            vm.setup_peer_connection(2)

            # Verify socket was created
            mock_socket.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM)

            # Verify connection was attempted with correct host/port
            expected_host = get_vm_host(2)
            mock_socket_instance.connect.assert_called_once_with((expected_host, 5002))

            # Verify handshake message was sent
            mock_socket_instance.sendall.assert_called_once()

            # Verify socket was stored
            assert vm.peer_sockets[2] == mock_socket_instance

            # Verify callback was called
            vm.on_peer_connected.assert_called_once()

            # Verify thread was started to handle client
            mock_thread.assert_called_once()
            mock_thread_instance.start.assert_called_once()


@patch("run.logger.setup_logger")
@patch("run.LamportClock", LamportClock)
def test_setup_peer_connections(mock_setup_logger, vm_config, mock_logger):
    """Test setup_peer_connections method."""
    mock_setup_logger.return_value = mock_logger

    vm = VM(**vm_config)

    # Mock the setup_peer_connection method
    with patch.object(vm, "setup_peer_connection") as mock_setup:
        # Call the method being tested
        vm.setup_peer_connections()

        # Verify setup_peer_connection was called for each peer
        assert mock_setup.call_count == 2
        mock_setup.assert_any_call(2)
        mock_setup.assert_any_call(3)


@patch("run.logger.setup_logger")
@patch("run.LamportClock", LamportClock)
def test_send_message(mock_setup_logger, vm_config, mock_logger):
    """Test send_message method."""
    mock_setup_logger.return_value = mock_logger

    vm = VM(**vm_config)

    # Create a mock socket and add it to peer_sockets
    mock_socket = MagicMock()
    vm.peer_sockets = {2: mock_socket}

    # Test message
    test_message = b'{"test": "message"}'

    # Call the method being tested
    vm.send_message(test_message, 2)

    # Verify message was sent with newline appended
    mock_socket.sendall.assert_called_once_with(test_message + b"\n")

    # Test with missing peer - should try to establish connection
    with patch.object(vm, "setup_peer_connection") as mock_setup_conn:
        vm.send_message(test_message, 3)
        mock_setup_conn.assert_called_once_with(3)


@patch("run.logger.setup_logger")
@patch("run.LamportClock", LamportClock)
def test_internal_action(mock_setup_logger, vm_config, mock_logger):
    """Test internal_action method."""
    mock_setup_logger.return_value = mock_logger

    vm = VM(**vm_config)

    # Mock the send_message method
    with patch.object(vm, "send_message") as mock_send:
        # Mock the log_event method
        with patch.object(vm, "log_event") as mock_log:
            # Force a specific random action
            with patch("random.randint", return_value=1):
                # Add some mock peer sockets
                vm.peer_sockets = {2: MagicMock(), 3: MagicMock()}

                # Call the method being tested
                vm.internal_action()

                # Verify the clock was incremented
                assert vm.clock.value == 1

                # Verify a message was sent to the first peer
                mock_send.assert_called_once()
                assert mock_send.call_args[0][1] == 2  # Second peer ID

                # Verify event was logged
                mock_log.assert_called_once()


@patch("run.logger.setup_logger")
@patch("run.LamportClock", LamportClock)
def test_internal_action_with_different_actions(
    mock_setup_logger, vm_config, mock_logger
):
    """Test internal_action method with different random actions."""
    mock_setup_logger.return_value = mock_logger

    vm = VM(**vm_config)

    # Add peer sockets
    vm.peer_sockets = {2: MagicMock(), 3: MagicMock(), 4: MagicMock()}

    # Mock send_message and log_event
    with patch.object(vm, "send_message") as mock_send:
        with patch.object(vm, "log_event") as mock_log:
            # Test with different actions
            test_actions = [1, 2, 3, 4, 5, 6, 7, 8]
            for action in test_actions:
                # Reset mocks
                mock_send.reset_mock()
                mock_log.reset_mock()

                # Force specific action
                with patch("random.randint", return_value=action):
                    vm.internal_action()

                    # Verify log_event was called for all actions
                    mock_log.assert_called_once()

                    # Verify send_message was called for specific actions
                    if action == 1:
                        mock_send.assert_called_once()
                        assert mock_send.call_args[0][1] == 2
                    elif action == 2:
                        mock_send.assert_called_once()
                        assert mock_send.call_args[0][1] == 3
                    elif action == 3:
                        assert mock_send.call_count == 2
                        assert sorted([c[0][1] for c in mock_send.call_args_list]) == [
                            2,
                            3,
                        ]
                    else:
                        mock_send.assert_not_called()


@patch("run.logger.setup_logger")
@patch("run.LamportClock", LamportClock)
def test_event_loop(mock_setup_logger, vm_config, mock_logger):
    """Test event_loop method."""
    mock_setup_logger.return_value = mock_logger

    # Reduce run_time for faster test
    vm_config["run_time"] = 0.1
    vm = VM(**vm_config)

    # Mock the internal_action method
    with patch.object(vm, "internal_action") as mock_internal:
        # Mock the time.sleep method to avoid actually sleeping
        with patch("time.sleep") as mock_sleep:
            # Call the method being tested
            vm.event_loop()

            # Verify internal_action was called at least once
            mock_internal.assert_called()

            # Verify sleep was called at least once
            mock_sleep.assert_called()


@patch("run.logger.setup_logger")
@patch("run.LamportClock", LamportClock)
def test_process_message_from_queue(mock_setup_logger, vm_config, mock_logger):
    """Test processing a message from the queue in the event loop."""
    mock_setup_logger.return_value = mock_logger

    # Short run time for faster test
    vm_config["run_time"] = 0.1
    vm = VM(**vm_config)

    # Add a message to the queue
    test_message = json.dumps({"sender": 2, "clock": 5}).encode("utf-8")
    vm.message_queue.put(test_message)

    # Mock the log_event method
    with patch.object(vm, "log_event") as mock_log:
        # Mock time.sleep to avoid actually sleeping
        with patch("time.sleep") as mock_sleep:
            # Mock internal_action to avoid actually running it
            with patch.object(vm, "internal_action"):
                # Call the event loop
                vm.event_loop()

                # Verify the message was processed
                assert vm.message_queue.empty()
                assert vm.clock.value == 6  # Clock should be updated
                mock_log.assert_called()  # Event should be logged


@patch("run.logger.setup_logger")
@patch("run.LamportClock", LamportClock)
def test_run(mock_setup_logger, vm_config, mock_logger):
    """Test run method."""
    mock_setup_logger.return_value = mock_logger

    vm = VM(**vm_config)

    # Mock all the methods called by run
    with patch.object(vm, "start_server") as mock_start:
        with patch.object(vm, "setup_peer_connections") as mock_setup_peers:
            with patch.object(vm, "wait_for_all_vms") as mock_wait:
                with patch.object(vm, "event_loop") as mock_event_loop:
                    with patch("time.sleep") as mock_sleep:
                        # Mock peer sockets
                        vm.peer_sockets = {2: MagicMock(), 3: MagicMock()}

                        # Call the method being tested
                        vm.run()

                        # Verify methods were called in the correct order
                        mock_start.assert_called_once()
                        mock_sleep.assert_called_once_with(1)
                        mock_setup_peers.assert_called_once()
                        mock_wait.assert_called_once()
                        mock_event_loop.assert_called_once()

                        # Verify ping messages were sent to peers
                        assert vm.peer_sockets[2].sendall.call_count == 1
                        assert vm.peer_sockets[3].sendall.call_count == 1


@patch("run.logger.setup_logger")
@patch("run.LamportClock", LamportClock)
def test_handle_client(mock_setup_logger, vm_config, mock_logger):
    """Test handle_client method."""
    mock_setup_logger.return_value = mock_logger

    vm = VM(**vm_config)

    # Create a mock socket
    mock_socket = MagicMock()

    # Test with normal message
    mock_socket.recv.side_effect = [
        b'{"sender": 2, "clock": 5}\n',  # Complete message
        b"",  # Connection closed
    ]

    # Call the method being tested
    vm.handle_client(mock_socket)

    # Verify message was added to queue
    assert vm.message_queue.qsize() == 1

    # Verify socket was closed
    mock_socket.close.assert_called_once()


@patch("run.logger.setup_logger")
@patch("run.LamportClock", LamportClock)
def test_handle_client_multiple_messages(mock_setup_logger, vm_config, mock_logger):
    """Test handle_client method with multiple messages."""
    mock_setup_logger.return_value = mock_logger

    vm = VM(**vm_config)

    # Create a mock socket
    mock_socket = MagicMock()

    # Test with multiple messages
    mock_socket.recv.side_effect = [
        b'{"sender": 2, "clock": 5}\n{"sender": 3, "clock": 7}\n',  # Two complete messages
        b'{"sender": 4, "clock": 10}\n',  # One more message
        b"",  # Connection closed
    ]

    # Call the method being tested
    vm.handle_client(mock_socket)

    # Verify all messages were added to queue
    assert vm.message_queue.qsize() == 3

    # Verify socket was closed
    mock_socket.close.assert_called_once()


@patch("run.logger.setup_logger")
@patch("run.LamportClock", LamportClock)
def test_register_incoming_peer(mock_setup_logger, vm_config, mock_logger):
    """Test register_incoming_peer method."""
    mock_setup_logger.return_value = mock_logger

    vm = VM(**vm_config)

    # Create a mock socket
    mock_socket = MagicMock()

    # Mock handle_client to avoid actually processing
    with patch.object(vm, "handle_client") as mock_handle:
        # Prepare a valid handshake message
        handshake = json.dumps({"sender": 2, "clock": 0, "type": "handshake"}) + "\n"

        mock_socket.recv.return_value = handshake.encode("utf-8")

        # Mock the callback
        vm.on_peer_connected = MagicMock()

        # Call the method being tested
        vm.register_incoming_peer(mock_socket)

        # Verify peer was registered
        assert 2 in vm.peer_sockets
        assert vm.peer_sockets[2] == mock_socket

        # Verify callback was called
        vm.on_peer_connected.assert_called_once()

        # Verify handle_client was called
        mock_handle.assert_called_once_with(mock_socket)


@patch("run.logger.setup_logger")
@patch("run.LamportClock", LamportClock)
def test_register_incoming_peer_invalid_handshake(
    mock_setup_logger, vm_config, mock_logger
):
    """Test register_incoming_peer method with invalid handshake."""
    mock_setup_logger.return_value = mock_logger

    vm = VM(**vm_config)

    # Create a mock socket
    mock_socket = MagicMock()

    # Prepare an invalid handshake message (missing type)
    handshake = json.dumps({"sender": 2, "clock": 0}) + "\n"

    mock_socket.recv.return_value = handshake.encode("utf-8")

    # Call the method being tested
    vm.register_incoming_peer(mock_socket)

    # Verify peer was not registered
    assert 2 not in vm.peer_sockets

    # Verify socket was closed
    mock_socket.close.assert_called_once()


@patch("run.logger.setup_logger")
@patch("run.LamportClock", LamportClock)
def test_accept_connections(mock_setup_logger, vm_config, mock_logger):
    """Test accept_connections method."""
    mock_setup_logger.return_value = mock_logger

    vm = VM(**vm_config)

    # Create mock server socket
    vm.server_socket = MagicMock()

    # Mock register_incoming_peer to avoid actually processing
    with patch.object(vm, "register_incoming_peer") as mock_register:
        # Mock threading to avoid actually creating threads
        with patch("threading.Thread") as mock_thread:
            mock_thread_instance = MagicMock()
            mock_thread.return_value = mock_thread_instance

            # Mock server_socket.accept to return once then raise an exception to exit the loop
            client_socket = MagicMock()
            addr = ("127.0.0.1", 12345)
            vm.server_socket.accept.side_effect = [
                (client_socket, addr),
                Exception("Test exception to exit loop"),
            ]

            # Call the method being tested - this should raise the exception
            with pytest.raises(Exception, match="Test exception to exit loop"):
                vm.accept_connections()

            # Verify thread was started to register the peer
            mock_thread.assert_called_once()
            mock_thread_instance.start.assert_called_once()
