
# Distributed VM Simulation with Lamport Clocks

This project simulates a small asynchronous distributed system using multiple virtual machines (VMs) running on a single host. Each VM maintains its own Lamport clock to order events, communicates with its peers via sockets, and logs its internal state and events. The system integrates some of the key concepts we learned in class such as message passing, logical clocks, and coordinated startup.

## Overview

- **Distributed System Model:**  
  The simulation models a distributed system where each VM operates at its own tick rate (instructions per second). VMs send messages to each other based on random actions, update their logical clocks using our Lamport Clock, and log event

- **Lamport Clock:**  
  Each VM maintains a simple Lamport clock to assign a logical timestamp to every event. This helps determine a consistent order of events without relying on synchronized physical clocks.

- **Networking:**  
  VMs communicate using TCP sockets. The project supports two modes: running locally (with each VM started in its own terminal) or via Docker using a Docker Compose file.

- **Configuration via Environment Variables:**  
  All parameters, such as VM ID, port, peer configuration, tick rate, log directory, and run time, are configurable via environment variables. This makes it easy to adjust experiments and run tests in different environments.

## How It Works

1. **Startup and Connection:**  
   - The first VM starts without any peers.
   - The second VM connects to the first.
   - The third VM connects to both the first and the second.  
   This pattern is designed to make it easy to add more VMs in the future.

2. **Event Loop and Message Processing:**  
   Each VM runs a continuous event loop where:
   - If the message queue has messages, it processes one message per tick (updating the clock and logging the event).
   - Otherwise, the VM performs an internal action, which might involve sending messages to peers.
   - The clock is incremented on every event, and messages carry the current clock value for proper synchronization.

3. **Handshake and Logging:**  
   VMs perform a handshake when establishing a connection. Logging is structured to include the current clock value for every event, helping analyze drift and the message queue state.

4. **Project Structure**
    - run.py: Main entry point for the distributed system simulation. Sets up servers, peer connections, and the event loop.
    - clock.py: Contains the LamportClock class, which implements the logical clock mechanism.
    - logger.py: Sets up logging for each VM, logging events along with the current state of the logical clock.
    - tests/: Contains unit and integration tests for the project.

## Running the Project

### Via Docker

In the project’s `src` directory, run:

```bash
docker compose up --build
```

To shut down the servers:

```bash
docker compose down
```

### Running Locally

Open separate terminal windows for each VM and run the following commands:

#### VM 1
```bash
export VM_ID=1
export PORT=5001
export PEERS='{}'
python run.py
```

#### VM 2
```bash
export VM_ID=2
export PORT=5002
export PEERS='{"1": 5001}'
python run.py
```

#### VM 3
```bash
export VM_ID=3
export PORT=5003
export PEERS='{"1": 5001, "2": 5002}'
python run.py
```

## Running Tests
To run tests locally, use one of the following command:

- **Running Unit tests (from src directory):**

  ```bash
  python -m pytest
  ```

