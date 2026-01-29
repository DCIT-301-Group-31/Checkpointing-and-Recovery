
import curses
import json
import os
import sys
import time
import random
import argparse
import base64

# --- Configuration ---
GRID_WIDTH = 10
GRID_HEIGHT = 10
PAGE_SIZE = 1 # Each cell is a page for simplicity
STABLE_STORAGE_PATH = './stable_storage/'
CHECKPOINT_INTERVAL = 150 # Number of game loops between auto-checkpoints

# --- Data Structures ---

class PageFrame:
    """Represents a page in memory."""
    def __init__(self, page_id, data=None):
        self.id = page_id
        self.data = data if data is not None else bytearray()
        self.is_dirty = False

    def write(self, new_data):
        """Writes data to the page and marks it as dirty."""
        self.data = new_data
        self.is_dirty = True

    def __repr__(self):
        return f"Page(id={self.id}, dirty={self.is_dirty}, data={self.data.hex()})"

# --- Global State (Simulated Hardware) ---

# Volatile Memory
memory_map = {i: PageFrame(i, data=bytearray([0])) for i in range(GRID_WIDTH * GRID_HEIGHT)}
dirty_vector = {i: False for i in range(GRID_WIDTH * GRID_HEIGHT)} # Simplified dirty bit tracking

# CPU Registers
cpu_registers = {
    "AX": 0, # Agent X position
    "BX": 0, # Agent Y position
    "CX": 0  # Coins collected
}

# Program Counter
program_counter = 0 # Represents the current step/instruction in the simulation loop

# --- Core Checkpointing & Recovery Logic ---

def get_last_checkpoint_info():
    """Scans storage to find the latest full and incremental checkpoint IDs."""
    if not os.path.exists(STABLE_STORAGE_PATH):
        os.makedirs(STABLE_STORAGE_PATH)
        return None, 0

    files = [f for f in os.listdir(STABLE_STORAGE_PATH) if f.endswith('.json')]
    if not files:
        return None, 0

    checkpoints = []
    for f in files:
        try:
            with open(os.path.join(STABLE_STORAGE_PATH, f), 'r') as fp:
                data = json.load(fp)
                checkpoints.append(data)
        except (json.JSONDecodeError, IOError):
            continue # Ignore corrupted files

    checkpoints.sort(key=lambda c: c['timestamp'])

    last_full = None
    for cp in reversed(checkpoints):
        if cp['type'] == 'FULL':
            last_full = cp
            break
    
    last_checkpoint_id = checkpoints[-1]['checkpoint_id'] if checkpoints else 0
    
    return last_full, last_checkpoint_id


def save_checkpoint(is_full=False):
    """Saves the process state to disk (Full or Incremental)."""
    global dirty_vector

    last_full, last_id = get_last_checkpoint_info()
    new_checkpoint_id = last_id + 1

    payload = {}
    checkpoint_type = "FULL" if is_full else "INCREMENTAL"

    # For incremental, only save dirty pages
    if not is_full:
        for page_id, is_dirty in dirty_vector.items():
            if is_dirty:
                payload[page_id] = base64.b64encode(memory_map[page_id].data).decode('utf-8')
    else: # For full, save all pages
        for page_id, page in memory_map.items():
            payload[page_id] = base64.b64encode(page.data).decode('utf-8')

    # If it's an incremental checkpoint with nothing to save, abort.
    if not is_full and not payload:
        return "No changes to save."

    manifest = {
        "checkpoint_id": new_checkpoint_id,
        "timestamp": time.time(),
        "type": checkpoint_type,
        "parent_checkpoint_id": last_full['checkpoint_id'] if last_full and not is_full else None,
        "process_context": {
            "program_counter": program_counter,
            "registers": cpu_registers
        },
        "memory_payload": payload
    }

    file_path = os.path.join(STABLE_STORAGE_PATH, f"checkpoint_{new_checkpoint_id}.json")
    with open(file_path, 'w') as f:
        json.dump(manifest, f, indent=2)

    # CRUCIAL STEP: Reset dirty bits after an incremental checkpoint
    if not is_full:
        dirty_vector = {i: False for i in range(GRID_WIDTH * GRID_HEIGHT)}

    return f"Saved {checkpoint_type} Checkpoint {new_checkpoint_id}."


def recover_from_checkpoints():
    """Restores the system state by replaying logs."""
    global cpu_registers, program_counter, memory_map

    last_full, _ = get_last_checkpoint_info()
    if not last_full:
        return "No full checkpoint found. Starting fresh."

    # 1. Load the base full checkpoint
    base_file = os.path.join(STABLE_STORAGE_PATH, f"checkpoint_{last_full['checkpoint_id']}.json")
    with open(base_file, 'r') as f:
        base_cp = json.load(f)

    for page_id_str, b64_data in base_cp['memory_payload'].items():
        page_id = int(page_id_str)
        memory_map[page_id].data = base64.b64decode(b64_data)

    # 2. Find and apply all subsequent incremental checkpoints
    all_files = sorted(os.listdir(STABLE_STORAGE_PATH), key=lambda x: int(x.split('_')[1].split('.')[0]))
    
    incremental_checkpoints_to_apply = []
    for filename in all_files:
        if not filename.endswith('.json'): continue
        
        with open(os.path.join(STABLE_STORAGE_PATH, filename), 'r') as f:
            cp_data = json.load(f)
            if cp_data['type'] == 'INCREMENTAL' and cp_data['timestamp'] > base_cp['timestamp']:
                incremental_checkpoints_to_apply.append(cp_data)

    # 3. Apply incremental checkpoints in order
    for inc_cp in incremental_checkpoints_to_apply:
        for page_id_str, b64_data in inc_cp['memory_payload'].items():
            page_id = int(page_id_str)
            memory_map[page_id].data = base64.b64decode(b64_data)
    
    # 4. The final state is from the very last checkpoint (full or incremental)
    last_checkpoint_file = os.path.join(STABLE_STORAGE_PATH, all_files[-1])
    with open(last_checkpoint_file, 'r') as f:
        final_cp_data = json.load(f)

    cpu_registers = final_cp_data['process_context']['registers']
    program_counter = final_cp_data['process_context']['program_counter']

    return f"Recovery complete. Restored to state from Checkpoint {final_cp_data['checkpoint_id']}."


# --- Simulation (Grid World) ---

def update_memory(x, y, value):
    """Simulates a write to memory, marking the page as dirty."""
    page_id = y * GRID_WIDTH + x
    if page_id in memory_map:
        memory_map[page_id].write(bytearray([value]))
        dirty_vector[page_id] = True

def read_memory(x, y):
    """Reads a value from a memory page."""
    page_id = y * GRID_WIDTH + x
    return memory_map[page_id].data[0] if memory_map[page_id].data else 0

def draw_grid(win, status="Running..."):
    """Draws the grid, agent, and status info."""
    win.clear()
    agent_x, agent_y = cpu_registers['AX'], cpu_registers['BX']
    
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            char = "."
            cell_value = read_memory(x, y)
            if cell_value > 0:
                char = str(cell_value) # Represents a "coin"
            
            if x == agent_x and y == agent_y:
                char = "A"
            
            win.addch(y, x * 2, char)

    # Display status and info
    win.addstr(GRID_HEIGHT + 1, 0, f"Status: {status}")
    win.addstr(GRID_HEIGHT + 2, 0, f"Agent (X,Y): ({agent_x}, {agent_y}) | Coins: {cpu_registers['CX']} | Step: {program_counter}")
    win.addstr(GRID_HEIGHT + 3, 0, "Controls: [S]ave Checkpoint | [K]ill (Crash) | [Q]uit")
    win.refresh()

def main_loop(stdscr):
    """The main event loop for the simulation."""
    global program_counter, cpu_registers

    curses.curs_set(0) # Hide cursor
    stdscr.nodelay(1) # Non-blocking input
    stdscr.timeout(200) # Refresh every 200ms

    status_message = "Simulation started."
    
    # Initial full checkpoint if none exists
    last_full, _ = get_last_checkpoint_info()
    if not last_full:
        status_message = save_checkpoint(is_full=True)

    while True:
        draw_grid(stdscr, status_message)
        status_message = "Running..." # Reset status after drawing

        # --- Process Logic (Agent Movement) ---
        program_counter += 1
        
        # Simple random walk
        move = random.choice([-1, 1])
        if random.choice(['x', 'y']) == 'x':
            cpu_registers['AX'] = max(0, min(GRID_WIDTH - 1, cpu_registers['AX'] + move))
        else:
            cpu_registers['BX'] = max(0, min(GRID_HEIGHT - 1, cpu_registers['BX'] + move))

        # Agent "collects" a coin
        if read_memory(cpu_registers['AX'], cpu_registers['BX']) > 0:
            cpu_registers['CX'] += read_memory(cpu_registers['AX'], cpu_registers['BX'])
            update_memory(cpu_registers['AX'], cpu_registers['BX'], 0) # Clear the coin

        # Occasionally, a new "coin" appears
        if random.random() < 0.05:
            cx, cy = random.randint(0, GRID_WIDTH-1), random.randint(0, GRID_HEIGHT-1)
            if read_memory(cx, cy) == 0:
                update_memory(cx, cy, random.randint(1, 5))

        # --- Checkpoint Daemon Simulation ---
        if program_counter % CHECKPOINT_INTERVAL == 0:
            status_message = save_checkpoint(is_full=False)

        # --- Handle User Input ---
        key = stdscr.getch()
        if key == ord('q'):
            break
        elif key == ord('s'):
            status_message = save_checkpoint(is_full=False)
            draw_grid(stdscr, "SAVING...")
            time.sleep(0.5)
        elif key == ord('k'):
            # Simulate a crash
            raise SystemExit("Simulated kernel panic (K pressed)!")

# --- Entry Point ---

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fault-Tolerant Process Checkpointing Simulation")
    parser.add_argument('--start', action='store_true', help="Start a new simulation.")
    parser.add_argument('--recover', action='store_true', help="Recover from the last checkpoint.")
    args = parser.parse_args()

    if args.start:
        curses.wrapper(main_loop)
    elif args.recover:
        print("Attempting recovery...")
        recovery_status = recover_from_checkpoints()
        print(recovery_status)
        if "No full checkpoint" not in recovery_status:
            print("Restarting simulation from recovered state...")
            time.sleep(2)
            curses.wrapper(main_loop)
    else:
        print("Usage: python main.py --start OR python main.py --recover")

