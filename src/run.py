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
    def __init__(self, 
                 vm_id: int, 
                 port: int, 
                 peers: Optional[Dict] = None):
        # Initialize the logical clock for this VM.
        self.clock = LamportClock(str(vm_id))
        # Set up a random tick rate between 1 and 6 ticks per second.
        self.tick_rate = random.randint(1, 6)
        self.vm_id = vm_id
        self.port = port  # Port on which this VM will listen for incoming connections.
        self.logger = logger.setup_logger(self.vm_id, self.clock)
        # Store peers configuration (expected to be a dict of {peer_id: port})
        self.peers = peers if peers is not None else {}
        # Dictionary to store persistent outgoing connections to peers.
        self.peer_sockets = {}
        self.message_queue = Queue()


    def internal_action(self):
        action = random.randint(1, 10)
        message = json.dumps(
            {"sender": self.vm_id, "clock": self.logical_clock}
        ).encode("utf-8")

        if action == 1:
            # send message to A
            # figure out how connection ids work later
            self.send_message(message, 0)
        if action == 2:
            # send message to B
            self.send_message(message, 1)

        if action == 3:
            # send message to A & B
            self.send_message(message, 0)
            self.send_message(message, 1)
        else:
            self.logical_clock.increment()
            self.log_event(f"Internal event, Logical Clock: {self.logical_clock}")



    def setup_peer_connection(self, peer_id, port):
        """Establish persistent outgoing connections to each peer."""
        for peer_id, port in self.peers.items():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(("localhost", port))
                self.peer_sockets[peer_id] = sock
                self.logger.info(
                    f"Connected persistently to peer VM {peer_id} on port {port}"
                )
            except Exception as e:
                self.logger.error(
                    f"Error connecting to peer VM {peer_id} on port {port}: {e}"
                )


    def recv_message(self):
        # TODO: socket logic to use message queue instead.
        message = self.socket.recv(1024)
        msg_decoded = json.loads(message.decode("utf-8"))
        self.logger.info(
            f"Received message from VM {self.vm_id}"
        )  # updat logical clock
        sender = msg_decoded["sender"]
        clock_value = int(msg_decoded["clock"])
        self.clock.compare(clock_value)
        event = f"Received message from VM {sender}; length message queue: {self.message_queue.qsize()}"
        self.log_event(event)

    def send_message(self, message: bytearray, destination_vm_id: int):
        if destination_vm_id in self.sockets:
            # open up connection with that vm
            self.setup_peer_connection(destination_vm_id)

        socket = self.sockets[destination_vm_id]
        socket.sendall(message)
        self.logger.info(f"Sent message to VM {destination_vm_id}")

    def event_loop(self):
        start_time = time.time()
        # do stuff here
        elapsed_time = time.time() - start_time
        # if elapsed time more than threshold, don't sleep
        # otherwise sleep the remaining threshold time
        sleep_time = max(0, (1 / self.tick_rate) - elapsed_time)
        time.sleep(sleep_time)

    def log_event(self, event: str):
        """Log an event using the dedicated VM logger."""
        self.logger.info(f"Event: {event}", extra={"logical_clock": self.clock})


    def run(self):
        self.start_server()
        # Pause briefly to let the server start.
        time.sleep(1)
        self.setup_peer_connections()
        # setting up server for first vm, check if the server id is 1, 
        # if it is then send ping to other 2 servers
        if self.vm_id == 1:
                ping_message = json.dumps({"sender": self.vm_id, "clock": self.clock.value, "type": "ping"}).encode("utf-8")
                for peer_id in self.peer_sockets:
                    try:
                        self.peer_sockets[peer_id].sendall(ping_message)
                        self.logger.info(f"Sent ping to VM {peer_id}")
                    except Exception as e:
                        self.logger.error(f"Error sending ping to VM {peer_id}: {e}")
        self.event_loop()


        self.event_loop()

    def setup_peer_connections(self):
        # Establish persistent outgoing connections to all peers.
        for peer_id_str, peer_port in self.peers.items():
            if int(peer_id_str) == self.vm_id:
                continue
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(("localhost", peer_port))
                self.peer_sockets[int(peer_id_str)] = sock
                self.logger.info(f"Connected persistently to peer VM {peer_id_str} on port {peer_port}")
            except Exception as e:
                self.logger.error(f"Error connecting to peer VM {peer_id_str} on port {peer_port}: {e}")

    

    def start_server(self):
            # Start a server to listen for incoming connections.
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.bind(("localhost", self.port))
            self.server_socket.listen(5)
            self.logger.info(f"Server listening on port {self.port}")
            # Start a new thread to accept incoming connections.
            threading.Thread(target=self.accept_connections, daemon=True).start()

    def accept_connections(self):
        # Continuously accept incoming connections.
        while True:
            client_socket, addr = self.server_socket.accept()
            self.logger.info(f"Accepted connection from {addr}")
            # Start a new thread to handle the client's messages.
            threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True).start()

    
    def handle_client(self, client_socket):
        """
        function to set up message queue
        """
        # Handle incoming messages from a connected client.
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
    peers_str = os.environ.get("PEERS", "{}")
    peers = json.loads(peers_str)

    vm = VM(vm_id, port, peers)
    try:
        vm.run()
    except KeyboardInterrupt:
        vm.running = False
        time.sleep(1)
