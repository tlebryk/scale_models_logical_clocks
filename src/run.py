# run.py
from clock import LamportClock
import random
from typing import Optional, Dict
import time
import logger
import socket
import json
from queue import Queue
import os
import threading

# Add this at the top of your run.py file with the other imports
# Environment detection
ENVIRONMENT = os.environ.get("ENVIRONMENT", "local").lower()
# Add these constants at the top of your file
TOTAL_VMS = int(os.environ.get("TOTAL_VMS", "3"))  # Default to 3 VMs in the system
STARTUP_TIMEOUT = int(
    os.environ.get("STARTUP_TIMEOUT", "30")
)  # Seconds to wait for all VMs


# Function to get the appropriate host for a VM ID
def get_vm_host(vm_id):
    """
    Returns the appropriate hostname for a VM based on the environment.
    In Docker, returns the container name, in local mode returns localhost.
    """
    if ENVIRONMENT == "docker":
        return f"lamport-vm{vm_id}"
    else:
        return "localhost"


class VM:
    def __init__(
        self, vm_id: int, port: int, peers: Optional[Dict] = None, logmode="w"
    ):
        self.clock = LamportClock(str(vm_id))
        self.tick_rate = random.randint(1, 6)
        self.vm_id = vm_id
        self.port = port
        # TODO: use new log file every time we run
        self.logger = logger.setup_logger(self.vm_id, self.clock, file_mode=logmode)
        self.logger.info(f"Tick rate: {self.tick_rate}")
        # Store peers configuration (dict of {peer_id: port})
        self.peers = peers if peers is not None else {}
        # store outgoing connections to peers.
        self.peer_sockets = {}
        self.message_queue = Queue()

    # NOTE: Pls check and see if this logic is correct based on the instructions,
    #  may need to edit when logical clocks are incremented

    # Add this to the VM class
    def wait_for_all_vms(self):
        """
        Wait until all expected VM connections are established before starting the event loop.
        """
        self.logger.info(f"Waiting for all {TOTAL_VMS} VMs to come online...")

        # Track which VMs we're expecting to connect with
        expected_vm_ids = set(range(1, TOTAL_VMS + 1))
        expected_vm_ids.discard(self.vm_id)  # Remove self from expected connections

        # Create an event to signal when all VMs are connected
        self.all_vms_connected = threading.Event()

        # If there are no expected peers, set the event immediately
        if not expected_vm_ids:
            self.all_vms_connected.set()
            return

        # Function to check if all expected VMs are connected
        def check_connections():
            connected_vms = set(self.peer_sockets.keys())
            if connected_vms.issuperset(expected_vm_ids):
                self.logger.info(f"All expected VMs are now connected!")
                self.all_vms_connected.set()

        # Register the check function to be called whenever a new connection is established
        self.on_peer_connected = check_connections

        # Initial check in case connections were already established
        check_connections()

        # Wait for the event with timeout
        startup_complete = self.all_vms_connected.wait(timeout=STARTUP_TIMEOUT)

        if not startup_complete:
            self.logger.warning(
                f"Timeout waiting for all VMs to connect. "
                f"Connected to {len(self.peer_sockets)}/{len(expected_vm_ids)} expected peers. "
                f"Proceeding anyway."
            )

    def internal_action(self):
        action = random.randint(1, 10)

        message = json.dumps({"sender": self.vm_id, "clock": self.clock.value}).encode(
            "utf-8"
        )
        peer_ids = sorted(self.peer_sockets.keys())
        self.clock.increment()
        if action == 1:
            if peer_ids:
                # send message to A
                self.send_message(message, peer_ids[0])
                self.log_event(f"Sent message to VM {peer_ids[0]}")
            else:
                self.log_event("Internal event (no peers available)")

        elif action == 2:
            if len(peer_ids) >= 2:
                # send message to second available peer
                self.send_message(message, peer_ids[1])
                self.log_event(f"Sent message to VM {peer_ids[1]}")
            else:
                self.log_event("Internal event (not enough peers for action 2)")
        elif action == 3:
            if len(peer_ids) >= 2:
                # send message to A & B (first 2 available peers)
                self.send_message(message, peer_ids[0])
                self.send_message(message, peer_ids[1])
                self.log_event(f"Sent messages to VM {peer_ids[0]}, {peer_ids[1]}")
            else:
                self.log_event("Internal event (not enough peers for action 3)")
        else:
            # just perform an internal event
            self.log_event(f"Internal event")

    def recv_message(self):
        # TODO: socket logic to use message queue instead
        message = self.socket.recv(1024)
        msg_decoded = json.loads(message.decode("utf-8"))
        self.log_event(f"Received message from VM {self.vm_id}")  # update logical clock
        sender = msg_decoded["sender"]
        clock_value = int(msg_decoded["clock"])
        self.clock.compare(clock_value)
        event = f"Received message from VM {sender}; length message queue: {self.message_queue.qsize()}"
        self.log_event(event)

    def send_message(self, message: bytearray, destination_vm_id: int):
        # Ensure the connection is established
        if destination_vm_id not in self.peer_sockets:
            self.setup_peer_connection(destination_vm_id)
        # Append newline if it's not already there, to ensure proper delimiting
        if not message.endswith(b"\n"):
            message += b"\n"
        sock = self.peer_sockets.get(destination_vm_id)
        if sock:
            try:
                sock.sendall(message)
                # self.log_event(f"Sent message to VM {destination_vm_id}")
            except Exception as e:
                self.logger.error(
                    f"Error sending message to VM {destination_vm_id}: {e}"
                )
        else:
            self.logger.error(f"No connection available for VM {destination_vm_id}")

    def event_loop(self):
        # continuous event loop to simulate clock ticks
        while True:
            start_time = time.time()
            if not self.message_queue.empty():
                # process one message from the queue
                message = self.message_queue.get()
                msg_decoded = json.loads(message.decode("utf-8"))
                sender = msg_decoded.get("sender")
                clock_val = int(msg_decoded.get("clock"))
                self.clock.compare(clock_val)
                event = f"Received message from VM {sender}; queue size: {self.message_queue.qsize()}"
                self.log_event(event)
            else:
                # no incoming messages, perform an internal action
                self.internal_action()
            elapsed_time = time.time() - start_time
            sleep_time = max(0, (1 / self.tick_rate) - elapsed_time)
            time.sleep(sleep_time)

    def log_event(self, event: str):
        """Log an event using the dedicated VM logger."""
        self.logger.info(f"Event: {event}")  # No extra parameter needed

    # Modify the run method to wait for all VMs
    def run(self):
        self.logger.info(f"Starting VM {self.vm_id} with tick rate {self.tick_rate}")
        self.start_server()
        time.sleep(1)
        self.setup_peer_connections()

        # Wait for all VMs to be connected
        self.wait_for_all_vms()

        # Now that we have all expected connections, send a ping to confirm
        ping_message = (
            json.dumps(
                {"sender": self.vm_id, "clock": self.clock.value, "type": "ping"}
            ).encode("utf-8")
            + b"\n"
        )

        for peer_id in self.peer_sockets:
            try:
                self.peer_sockets[peer_id].sendall(ping_message)
                self.log_event(f"Sent ping to VM {peer_id}")
            except Exception as e:
                self.logger.error(f"Error sending ping to VM {peer_id}: {e}")

        # Start the event loop
        self.event_loop()

    # Update the start_server method
    def start_server(self):
        # Start a server to listen for incoming connections
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Bind to appropriate interface based on environment
        if ENVIRONMENT == "docker":
            # In Docker, bind to all interfaces to allow cross-container communication
            self.server_socket.bind(("0.0.0.0", self.port))
        else:
            # In local mode, bind to localhost
            self.server_socket.bind(("localhost", self.port))

        self.server_socket.listen(5)
        self.logger.info(f"Server listening on port {self.port} in {ENVIRONMENT} mode")

        # start new thread to accept incoming connections
        threading.Thread(target=self.accept_connections, daemon=True).start()

    # Update the setup_peer_connection method to call the callback on successful connection
    def setup_peer_connection(self, destination_vm_id: int):
        """Establish a persistent outgoing connection to a single peer with handshake using newline delimiter."""
        if str(destination_vm_id) not in self.peers:
            self.logger.error(
                f"VM {destination_vm_id} not found in peer configuration."
            )
            return
        peer_port = self.peers[str(destination_vm_id)]
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            # Use the appropriate hostname based on environment
            target_host = get_vm_host(destination_vm_id)
            self.logger.info(f"Attempting to connect to {target_host}:{peer_port}")

            sock.connect((target_host, peer_port))
            handshake_message = (
                json.dumps(
                    {
                        "sender": self.vm_id,
                        "clock": self.clock.value,
                        "type": "handshake",
                    }
                ).encode("utf-8")
                + b"\n"  # Append newline as message delimiter
            )
            sock.sendall(handshake_message)
            self.peer_sockets[destination_vm_id] = sock
            self.logger.info(
                f"Connected persistently to peer VM {destination_vm_id} on port {peer_port}"
            )

            # Call the callback if it exists
            if hasattr(self, "on_peer_connected") and callable(self.on_peer_connected):
                self.on_peer_connected()

            # Start a thread to handle incoming messages on this socket
            threading.Thread(
                target=self.handle_client,
                args=(sock,),
                daemon=True,
            ).start()

        except Exception as e:
            self.logger.error(
                f"Error connecting to peer VM {destination_vm_id} on port {peer_port}: {e}"
            )

    def setup_peer_connections(self):
        """Establish outgoing connections to all configured peers by calling setup_peer_connection for each."""
        for peer_id_str, peer_port in self.peers.items():
            peer_id = int(peer_id_str)
            if peer_id == self.vm_id:
                continue  # Skip self
            if peer_id in self.peer_sockets:
                continue  # Already connected
            self.setup_peer_connection(peer_id)

    def accept_connections(self):
        # continuously accept incoming connections from other VMs
        while True:
            client_socket, addr = self.server_socket.accept()
            self.logger.info(f"Accepted connection from {addr}")
            threading.Thread(
                target=self.register_incoming_peer,
                args=(client_socket,),
                daemon=True,
            ).start()

    # Modify the register_incoming_peer method to call the callback when a new peer connects
    def register_incoming_peer(self, client_socket):
        """
        Receive the handshake using newline as the message delimiter.
        Reads from the socket until a newline is found, then decodes the JSON handshake.
        """
        buffer = ""
        while "\n" not in buffer:
            data = client_socket.recv(1024)
            if not data:
                self.logger.error("No handshake received; closing connection.")
                client_socket.close()
                return
            buffer += data.decode("utf-8")
        # Split the buffer at the first newline character
        handshake_str, _, remaining = buffer.partition("\n")
        try:
            handshake_data = json.loads(handshake_str)
        except json.JSONDecodeError as e:
            self.logger.error(f"Error during handshake: {e}")
            client_socket.close()
            return
        if handshake_data.get("type") != "handshake":
            self.logger.error("Expected handshake type, got something else")
            client_socket.close()
            return
        peer_id = handshake_data.get("sender")
        if peer_id is None:
            self.logger.error("Handshake message missing 'sender' field")
            client_socket.close()
            return
        peer_id = int(peer_id)
        if peer_id not in self.peer_sockets:
            self.peer_sockets[peer_id] = client_socket
            self.logger.info(f"Registered incoming connection from VM {peer_id}")

            # Call the callback if it exists
            if hasattr(self, "on_peer_connected") and callable(self.on_peer_connected):
                self.on_peer_connected()
        else:
            self.logger.info(f"VM {peer_id} already connected via another socket")
        # If any extra data remains after the handshake, add it to the message queue.
        if remaining.strip():
            self.message_queue.put(remaining.encode("utf-8"))
        self.handle_client(client_socket)

    def handle_client(self, client_socket):
        """
        Reads messages from the client socket using newline as a delimiter.
        Accumulates data in a buffer and splits out complete messages to add them to the message queue.
        """
        buffer = ""
        while True:
            try:
                data = client_socket.recv(1024)
                if not data:
                    break
                buffer += data.decode("utf-8")
                while "\n" in buffer:
                    message_str, _, buffer = buffer.partition("\n")
                    if message_str.strip():
                        self.message_queue.put(message_str.encode("utf-8"))
            except Exception as e:
                self.logger.error(f"Error handling client message: {e}")
                break
        client_socket.close()


if __name__ == "__main__":
    # Read configuration from environment variables.
    vm_id = int(os.environ.get("VM_ID", "1"))
    port = int(os.environ.get("PORT", "5001"))
    # The PEERS environment variable should be a JSON string.
    # note for setup: VM1 has no peers, VM2 connects to VM1, VM3 connects to VM1 and VM2, etc.
    peers_str = os.environ.get("PEERS", "{}")
    peers = json.loads(peers_str)

    vm = VM(vm_id, port, peers)
    try:
        vm.run()
    except KeyboardInterrupt:
        time.sleep(1)
