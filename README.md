# Fault-Tolerant Process Checkpointing Simulation

This project is a terminal-based simulation that demonstrates the concept of fault tolerance in a simple game-like environment. A process (represented by a moving agent) navigates a grid, and its state is periodically saved to stable storage. In the event of a simulated crash, the process can be recovered to its last known good state, preventing a complete loss of progress.

The user interface is built using the `rich` library to provide a more engaging and readable terminal experience.

## Features

- **Interactive Terminal UI:** A visually appealing and responsive grid-based display built with `rich`.
- **Process Simulation:** An agent moves around a grid, representing a running process with its own state (position, score, etc.).
- **Automatic Checkpointing:** The system automatically saves the process's state at regular intervals (both full and incremental checkpoints).
- **Manual Checkpointing:** Users can manually trigger a checkpoint save at any time.
- **Simulated Crashes:** Users can simulate a system crash to test the recovery mechanism.
- **State Recovery:** The simulation can be restarted from the most recent valid checkpoint, restoring the agent's position and all other state variables.
- **Stable Storage:** Checkpoints are saved as JSON files in a `stable_storage` directory, mimicking persistent storage.

## How to Run

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/DCIT-301-Group-31/Checkpointing-and-Recovery.git
    cd Checkpointing-and-Recovery
    ```

2.  **Set up a virtual environment (recommended):**

    ```bash
    python -m venv .venv
    # On Windows
    .venv\Scripts\activate
    # On macOS/Linux
    source .venv/bin/activate
    ```

3.  **Install the dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Start a new simulation:**

    ```bash
    python main.py --start
    ```

5.  **To recover from a crash:**
    If the simulation has crashed, run the following command to restore from the last checkpoint:
    ```bash
    python main.py --recover
    ```

## Controls

- **[S]**: Manually save an incremental checkpoint.
- **[K]**: Simulate a system crash. The application will terminate.
- **[Q]**: Gracefully quit the simulation, saving a final checkpoint before exiting.

## Checkpointing and Recovery Mechanism

The core of this simulation is its ability to withstand failures. This is achieved through a robust checkpointing system:

- **Process State (`process_state.py`):** This module defines the `Process` class, which encapsulates all the critical data that needs to be saved. This includes:
  - `registers`: A dictionary holding process variables like agent position (`AX`, `BX`) and score (`CX`).
  - `program_counter`: Tracks the number of steps or operations the process has executed.
  - `memory`: A representation of the process's memory, in this case, the game grid.

- **Checkpoint Manager (`checkpoint_manager.py`):** This is the engine that handles saving and loading checkpoints.
  - **Full vs. Incremental Checkpoints:**
    - A **full checkpoint** saves the entire state of the process. The first checkpoint created is always a full one.
    - An **incremental checkpoint** only saves the _changes_ that have occurred since the last checkpoint. This is more efficient than repeatedly saving the full state.
  - **Recovery Process:** When `main.py --recover` is run, the `CheckpointManager` finds the most recent full checkpoint and applies all subsequent incremental checkpoints in chronological order to reconstruct the final valid state.

- **Stable Storage:** All checkpoints are serialized into JSON files and stored in the `stable_storage/` directory. This separation ensures that even if the main application crashes, the saved states remain safe.
