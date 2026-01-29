"""
Manages the simulation, UI, and user input.
"""
import os
import sys
import time
import msvcrt
from config import GRID_WIDTH, GRID_HEIGHT, STABLE_STORAGE_PATH, CHECKPOINT_INTERVAL
from process_state import Process
from checkpoint_manager import CheckpointManager

class Simulation:
    """Manages the simulation, UI, and user input."""
    def __init__(self, stdscr=None):
        self.process = Process(GRID_WIDTH, GRID_HEIGHT)
        self.manager = CheckpointManager(STABLE_STORAGE_PATH)
        self.status_message = "Simulation starting..."
        self.frame_count = 0

    def setup(self):
        """Initializes the simulation environment."""
        # Clear terminal and hide cursor
        os.system('cls')
        
        # Create an initial full checkpoint if the storage is empty
        if not self.manager.get_all_checkpoints():
            self.status_message = self.manager.save_checkpoint(self.process, is_full=True)

    def run_loop(self):
        """The main event loop for the simulation."""
        while True:
            self.frame_count += 1
            self.draw_grid()
            self.status_message = "Running..."

            # --- Process Logic ---
            self.process.step()

            # --- Checkpoint Daemon Simulation ---
            if self.process.program_counter % CHECKPOINT_INTERVAL == 0:
                self.status_message = self.manager.save_checkpoint(self.process, is_full=False)

            # --- Handle User Input (non-blocking) ---
            if msvcrt.kbhit():
                key = msvcrt.getch().decode('utf-8', errors='ignore').lower()
                if key == 'q':
                    self.status_message = self.manager.save_checkpoint(self.process, is_full=False)
                    self.draw_grid("Finalizing and saving state...")
                    time.sleep(0.5)
                    break
                elif key == 's':
                    self.status_message = self.manager.save_checkpoint(self.process, is_full=False)
                    self.draw_grid("SAVING...")
                    time.sleep(0.5)
                elif key == 'k':
                    print("\n\n*** SIMULATED CRASH (K pressed)! ***")
                    print("Run 'python main.py --recover' to restore from checkpoint.")
                    sys.exit(1)

            time.sleep(0.15)  # Control game speed

    def draw_grid(self, status_override=None):
        """Draws the grid, agent, and status info."""
        # Move cursor to top-left instead of clearing (reduces flicker)
        print("\033[H", end="")
        
        agent_x, agent_y = self.process.registers['AX'], self.process.registers['BX']
        
        # Build the display as a single string for smoother output
        lines = []
        
        # Game title
        lines.append("\033[95m" + "=" * 40 + "\033[0m")
        lines.append("\033[95m   CHECKPOINT RECOVERY GAME   \033[0m")
        lines.append("\033[95m" + "=" * 40 + "\033[0m")
        lines.append("")
        
        # Top border
        lines.append("\033[36m+" + "-" * (GRID_WIDTH * 2) + "+\033[0m")
        
        # Grid
        for y in range(self.process.height):
            row = "\033[36m|\033[0m"
            for x in range(self.process.width):
                cell_value = self.process.read_memory(x, y)
                
                if x == agent_x and y == agent_y:
                    # Player - animated
                    player_chars = ["@", "*", "@", "O"]
                    char = player_chars[(self.frame_count // 2) % len(player_chars)]
                    row += f"\033[92;1m{char}\033[0m "
                elif cell_value > 0:
                    # Coin - animated
                    coin_chars = ["o", "O", "0", "O"]
                    char = coin_chars[(self.frame_count + x + y) % len(coin_chars)]
                    row += f"\033[93;1m{char}\033[0m "
                else:
                    row += ". "
            row += "\033[36m|\033[0m"
            lines.append(row)
        
        # Bottom border
        lines.append("\033[36m+" + "-" * (GRID_WIDTH * 2) + "+\033[0m")
        lines.append("")
        
        # Status
        status = status_override if status_override else self.status_message
        if "SAVING" in status or "Checkpoint" in status:
            lines.append(f"Status: \033[91;1m{status}\033[0m")
        else:
            lines.append(f"Status: \033[97m{status}\033[0m")
        
        lines.append("")
        
        # Player stats
        lines.append(f"\033[92mPlayer Position: ({agent_x}, {agent_y})\033[0m")
        lines.append(f"\033[93;1mCoins Collected: {self.process.registers['CX']}\033[0m")
        lines.append(f"Steps Taken: {self.process.program_counter}")
        lines.append("")
        
        # Controls
        lines.append("\033[36m------------ CONTROLS ------------\033[0m")
        lines.append("[S] Save Checkpoint  [K] Crash  [Q] Quit")
        lines.append("")
        
        # Print all at once
        print("\n".join(lines))
