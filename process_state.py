"""
Defines the state of the simulated process, including its memory and registers.
"""
import random
from config import GRID_WIDTH, GRID_HEIGHT

class PageFrame:
    """Represents a single page in the process's virtual memory."""
    def __init__(self, page_id, data=None):
        self.id = page_id
        self.data = data if data is not None else bytearray([0])
        self.is_dirty = False

    def write(self, new_data):
        """Writes data to the page and marks it as dirty."""
        if self.data != new_data:
            self.data = new_data
            self.is_dirty = True

    def reset_dirty_bit(self):
        self.is_dirty = False

    def __repr__(self):
        return f"Page(id={self.id}, dirty={self.is_dirty}, data={self.data.hex()})"


class Process:
    """Encapsulates the entire state of the simulated process."""
    def __init__(self, width=GRID_WIDTH, height=GRID_HEIGHT):
        self.width = width
        self.height = height
        # CPU Registers
        self.registers = {"AX": 0, "BX": 0, "CX": 0}
        # Program Counter
        self.program_counter = 0
        # Volatile Memory
        self.memory = {i: PageFrame(i) for i in range(width * height)}

    def get_page_id(self, x, y):
        return y * self.width + x

    def write_memory(self, x, y, value):
        """Simulates a write to memory, marking the page as dirty."""
        page_id = self.get_page_id(x, y)
        if page_id in self.memory:
            self.memory[page_id].write(bytearray([value]))

    def read_memory(self, x, y):
        """Reads a value from a memory page."""
        page_id = self.get_page_id(x, y)
        return self.memory[page_id].data[0] if self.memory[page_id].data else 0

    def step(self):
        """Advances the process by one logic step (e.g., agent moves)."""
        self.program_counter += 1

        # Simple random walk
        move = random.choice([-1, 1])
        if random.choice(['x', 'y']) == 'x':
            self.registers['AX'] = max(0, min(self.width - 1, self.registers['AX'] + move))
        else:
            self.registers['BX'] = max(0, min(self.height - 1, self.registers['BX'] + move))

        # Agent "collects" a coin
        agent_x, agent_y = self.registers['AX'], self.registers['BX']
        if self.read_memory(agent_x, agent_y) > 0:
            self.registers['CX'] += self.read_memory(agent_x, agent_y)
            self.write_memory(agent_x, agent_y, 0)  # Clear the coin

        # Occasionally, a new "coin" appears
        if random.random() < 0.05:
            cx, cy = random.randint(0, self.width - 1), random.randint(0, self.height - 1)
            if self.read_memory(cx, cy) == 0:
                self.write_memory(cx, cy, random.randint(1, 5))
