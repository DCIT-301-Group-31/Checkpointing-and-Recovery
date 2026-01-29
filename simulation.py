"""
Manages the simulation, UI, and user input.
"""
import os
import sys
import time
import msvcrt
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich.console import Console

from config import GRID_WIDTH, GRID_HEIGHT, STABLE_STORAGE_PATH, CHECKPOINT_INTERVAL
from process_state import Process
from checkpoint_manager import CheckpointManager

console = Console()


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
        with Live(self.draw_grid(), screen=True, redirect_stderr=False) as live:
            while True:
                self.frame_count += 1
                
                # --- Process Logic ---
                self.process.step()

                # --- Checkpoint Daemon Simulation ---
                if self.process.program_counter % CHECKPOINT_INTERVAL == 0:
                    self.status_message = self.manager.save_checkpoint(self.process, is_full=False)
                    live.update(self.draw_grid("Checkpoint auto-saved..."))
                    time.sleep(0.5)

                # --- Handle User Input (non-blocking) ---
                if msvcrt.kbhit():
                    key = msvcrt.getch().decode('utf-8', errors='ignore').lower()
                    if key == 'q':
                        self.status_message = self.manager.save_checkpoint(self.process, is_full=False)
                        live.update(self.draw_grid("Finalizing and saving state..."))
                        time.sleep(0.5)
                        break
                    elif key == 's':
                        self.status_message = self.manager.save_checkpoint(self.process, is_full=False)
                        live.update(self.draw_grid("SAVING CHECKPOINT..."))
                        time.sleep(0.5)
                    elif key == 'k':
                        # We need to exit the live display before printing the crash message
                        break  # Exit the loop first

                live.update(self.draw_grid())
                time.sleep(0.15)  # Control game speed

        # This part runs after the loop breaks (e.g., on 'k' or 'q')
        if msvcrt.kbhit() and msvcrt.getch().decode('utf-8', errors='ignore').lower() == 'k':
            console.print("\n\n[bold red]*** SIMULATED CRASH (K pressed)! ***[/bold red]")
            console.print("[yellow]Run 'python main.py --recover' to restore from the last checkpoint.[/yellow]")
            sys.exit(1)

    def draw_grid(self, status_override=None):
        """Draws the grid, agent, and status info using Rich."""
        agent_x, agent_y = self.process.registers['AX'], self.process.registers['BX']

        # --- Create the Grid Table ---
        grid_table = Table.grid(expand=True)
        for _ in range(self.process.width):
            grid_table.add_column()

        for y in range(self.process.height):
            row_cells = []
            for x in range(self.process.width):
                cell_value = self.process.read_memory(x, y)
                if x == agent_x and y == agent_y:
                    player_chars = ["@", "*", "@", "O"]
                    char = player_chars[(self.frame_count // 2) % len(player_chars)]
                    cell_content = Text(char, style="bold green")
                elif cell_value > 0:
                    coin_chars = ["o", "O", "0", "O"]
                    char = coin_chars[(self.frame_count + x + y) % len(coin_chars)]
                    cell_content = Text(char, style="bold yellow")
                else:
                    cell_content = Text(". ", style="dim white")
                row_cells.append(cell_content)
            grid_table.add_row(*row_cells)
        
        grid_panel = Panel(grid_table, title="[cyan]Game World[/cyan]", border_style="cyan")

        # --- Create Status and Stats Panels ---
        status = status_override if status_override else self.status_message
        status_style = "bold red" if "SAVING" in status or "Checkpoint" in status else "white"
        status_panel = Panel(Text(status, justify="center", style=status_style), title="[white]Status[/white]", border_style="red")

        stats_text = Text()
        stats_text.append(f"Player Position: ({agent_x}, {agent_y})\n", style="green")
        stats_text.append(f"Coins Collected: {self.process.registers['CX']}\n", style="bold yellow")
        stats_text.append(f"Steps Taken: {self.process.program_counter}")
        stats_panel = Panel(stats_text, title="[green]Player Stats[/green]", border_style="green")

        # --- Create Controls Panel ---
        controls_text = Text("[S] Save Checkpoint  [K] Crash  [Q] Quit", justify="center")
        controls_panel = Panel(controls_text, title="[cyan]Controls[/cyan]", border_style="cyan")

        # --- Assemble Layout ---
        left_column = Columns([stats_panel, status_panel])
        main_layout = Table.grid(expand=True)
        main_layout.add_column()
        main_layout.add_row(Text("CHECKPOINT RECOVERY GAME", style="bold magenta", justify="center"))
        main_layout.add_row(grid_panel)
        main_layout.add_row(left_column)
        main_layout.add_row(controls_panel)

        return main_layout
