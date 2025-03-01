from clock import LamportClock
import random
from typing import Optional, Dict
import time
import logger
import socket
import json
from queue import Queue
import os


class VM:
    def __init__(
        self,
        vm_id: int,
        tick_rate: Optional[int] = None,
        sockets: Optional[Dict] = None,
    ):
        self.clock = LamportClock(str(vm_id))
        if not tick_rate:
            tick_rate = random.randint(1, 6)
        self.tick_rate = tick_rate
        self.vm_id = vm_id
        self.logger = logger.setup_logger(self.vm_id, self.clock)
        self.sockets = sockets
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


if __name__ == "__main__":
    # Read configuration from environment variables.
    vm_id = int(os.environ.get("VM_ID", "1"))
    port = int(os.environ.get("PORT", "5001"))
    # The PEERS environment variable should be a JSON string.
    peers_str = os.environ.get("PEERS", "{}")
    peers = json.loads(peers_str)

    vm = VirtualMachine(vm_id, port, peers)
    try:
        vm.run()
    except KeyboardInterrupt:
        vm.running = False
        time.sleep(1)
