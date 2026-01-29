
"""
Main entry point for the Fault-Tolerant Process Checkpointing Simulation.

This script parses command-line arguments and launches the simulation
in one of two modes:
- --start: Begins a new simulation.
- --recover: Restores the simulation from the last saved state.
"""
import argparse
import time
import os
from process_state import Process
from checkpoint_manager import CheckpointManager
from simulation import Simulation
from config import STABLE_STORAGE_PATH, GRID_WIDTH, GRID_HEIGHT

def main(recover=False):
    """
    Main function to run the simulation.
    Initializes and runs the simulation.
    """
    sim = Simulation()
    if recover:
        # Apply the recovered state to the simulation's process object
        sim.manager.recover(sim.process)
    
    sim.setup()
    sim.run_loop()

if __name__ == "__main__":
    # Enable ANSI colors on Windows
    os.system('')
    
    parser = argparse.ArgumentParser(description="Fault-Tolerant Process Checkpointing Simulation")
    parser.add_argument('--start', action='store_true', help="Start a new simulation.")
    parser.add_argument('--recover', action='store_true', help="Recover from the last checkpoint.")
    args = parser.parse_args()

    if args.start:
        main()
    elif args.recover:
        # First, perform recovery to print status to the console
        temp_process = Process(GRID_WIDTH, GRID_HEIGHT)
        manager = CheckpointManager(STABLE_STORAGE_PATH)
        
        print("Attempting recovery...")
        recovery_status = manager.recover(temp_process)
        print(recovery_status)
        
        # If recovery is possible, restart the simulation in the recovered state
        if "Cannot recover" not in recovery_status and "No checkpoints" not in recovery_status:
            print("Restarting simulation from recovered state...")
            time.sleep(2)
            main(recover=True)
    else:
        print("Usage: python main.py --start OR python main.py --recover")

