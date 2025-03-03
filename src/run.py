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


class VM:
    def __init__(self, vm_id: int, port: int, peers: Optional[Dict] = None):
        self.clock = LamportClock(str(vm_id))
        self.tick_rate = random.randint(1, 6)
        self.vm_id = vm_id
        self.port = port
        self.logger = logger.setup_logger(self.vm_id, self.clock)
        # Store peers configuration (dict of {peer_id: port})
        self.peers = peers if peers is not None else {}
        # store outgoing connections to peers.
        self.peer_sockets = {}
        self.message_queue = Queue()

    # NOTE: Pls check and see if this logic is correct based on the instructions,
    #  may need to edit when logical clocks are incremented

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
            else:
                self.log_event("Internal event (no peers available)")
        elif action == 2:
            if len(peer_ids) >= 2:
                # send message to second available peer
                self.send_message(message, peer_ids[1])
            else:
                self.log_event("Internal event (not enough peers for action 2)")
        elif action == 3:
            if len(peer_ids) >= 2:
                # send message to A & B (first 2 available peers)
                self.send_message(message, peer_ids[0])
                self.send_message(message, peer_ids[1])
            else:
                self.log_event("Internal event (not enough peers for action 3)")
        else:
            # just perform an internal event
            self.log_event(f"Internal event, Logical Clock: {self.clock}")

    def recv_message(self):
        # TODO: socket logic to use message queue instead
        message = self.socket.recv(1024)
        msg_decoded = json.loads(message.decode("utf-8"))
        self.logger.info(
            f"Received message from VM {self.vm_id}"
        )  # update logical clock
        sender = msg_decoded["sender"]
        clock_value = int(msg_decoded["clock"])
        self.clock.compare(clock_value)
        event = f"Received message from VM {sender}; length message queue: {self.message_queue.qsize()}"
        self.log_event(event)

    def send_message(self, message: bytearray, destination_vm_id: int):
        # if connection does not exist, try to set it up
        if destination_vm_id not in self.peer_sockets:
            self.setup_peer_connection(destination_vm_id)
        # us the persistent connection to send the message
        sock = self.peer_sockets.get(destination_vm_id)
        if sock:
            try:
                sock.sendall(message)
                self.logger.info(f"Sent message to VM {destination_vm_id}")
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
        self.logger.info(f"Event: {event}", extra={"logical_clock": self.clock})

    def run(self):
        self.start_server()
        time.sleep(1)
        self.setup_peer_connections()
        # For VM1, we assume no peers are configured, so nothing to ping
        # for other VMs, have them send a ping to the other VMs to confirm connection
        if self.vm_id != 1:
            ping_message = json.dumps(
                {"sender": self.vm_id, "clock": self.clock.value, "type": "ping"}
            ).encode("utf-8")
            for peer_id in self.peer_sockets:
                try:
                    self.peer_sockets[peer_id].sendall(ping_message)
                    self.logger.info(f"Sent ping to VM {peer_id}")
                except Exception as e:
                    self.logger.error(f"Error sending ping to VM {peer_id}: {e}")
        self.event_loop()

    def start_server(self):
        # Start a server to listen for incoming connections
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind(("localhost", self.port))
        self.server_socket.listen(5)
        self.logger.info(f"Server listening on port {self.port}")
        # start new thread to accept incoming connections
        threading.Thread(target=self.accept_connections, daemon=True).start()

    def setup_peer_connection(self, destination_vm_id: int):
        """Establish a persistent outgoing connection to a single peer with handshake."""
        if str(destination_vm_id) in self.peers:
            peer_port = self.peers[str(destination_vm_id)]
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(("localhost", peer_port))
                # Immediately send a handshake message
                handshake_message = json.dumps(
                    {
                        "sender": self.vm_id,
                        "clock": self.clock.value,
                        "type": "handshake",
                    }
                ).encode("utf-8")
                sock.sendall(handshake_message)
                self.peer_sockets[destination_vm_id] = sock
                self.logger.info(
                    f"Connected persistently to peer VM {destination_vm_id} on port {peer_port}"
                )
            except Exception as e:
                self.logger.error(
                    f"Error connecting to peer VM {destination_vm_id} on port {peer_port}: {e}"
                )

    def setup_peer_connections(self):
        # Start outgoing connections to all configured peers
        for peer_id_str, peer_port in self.peers.items():
            if int(peer_id_str) == self.vm_id:
                continue
            # Only create an outgoing connection if one doesn't already exist
            if int(peer_id_str) in self.peer_sockets:
                continue
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(("localhost", peer_port))
                handshake_message = json.dumps(
                    {
                        "sender": self.vm_id,
                        "clock": self.clock.value,
                        "type": "handshake",
                    }
                ).encode("utf-8")
                sock.sendall(handshake_message)
                self.peer_sockets[int(peer_id_str)] = sock
                self.logger.info(
                    f"Connected persistently to peer VM {peer_id_str} on port {peer_port}"
                )
            except Exception as e:
                self.logger.error(
                    f"Error connecting to peer VM {peer_id_str} on port {peer_port}: {e}"
                )

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

    def register_incoming_peer(self, client_socket):
        try:
            # Wait for the handshake message
            handshake = client_socket.recv(1024)
            if not handshake:
                self.logger.error("No handshake received; closing connection.")
                client_socket.close()
                return
            handshake_data = json.loads(handshake.decode("utf-8"))
            if handshake_data.get("type") != "handshake":
                self.logger.error("Expected handshake type, got something else")
                client_socket.close()
                return
            peer_id = handshake_data.get("sender")
            if peer_id is None:
                self.logger.error("Handshake message missing 'sender' field")
                client_socket.close()
                return
            # Ensure consistent key type (integer)
            peer_id = int(peer_id)
            if peer_id not in self.peer_sockets:
                self.peer_sockets[peer_id] = client_socket
                self.logger.info(f"Registered incoming connection from VM {peer_id}")
            else:
                self.logger.info(f"VM {peer_id} already connected via another socket")
            # Now process further messages from this connection
            self.handle_client(client_socket)
        except Exception as e:
            self.logger.error(f"Error during handshake: {e}")
            client_socket.close()

    def handle_client(self, client_socket):
        """
        Function to add incoming messages to the message queue.
        """
        while True:
            try:
                message = client_socket.recv(1024)
                if not message:
                    break
                # Instead of processing immediately, add the message to the queue.
                self.message_queue.put(message)
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
