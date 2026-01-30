"""
Handles the logic for saving and recovering process state from disk.
"""
import os
import json
import time
import base64
from process_state import Process

class CheckpointManager:
    """Handles saving and recovering process state from disk."""
    def __init__(self, storage_path):
        self.storage_path = storage_path
        if not os.path.exists(self.storage_path):
            os.makedirs(self.storage_path)

    def get_all_checkpoints(self):
        """Scans storage and returns sorted checkpoint data."""
        files = [f for f in os.listdir(self.storage_path) if f.endswith('.json')]
        if not files:
            return []

        checkpoints = []
        for f in files:
            try:
                with open(os.path.join(self.storage_path, f), 'r') as fp:
                    data = json.load(fp)
                    checkpoints.append(data)
            except (json.JSONDecodeError, IOError):
                continue  # Ignore corrupted files

        checkpoints.sort(key=lambda c: c['timestamp'])
        return checkpoints

    def save_checkpoint(self, process: Process, is_full=False):
        """Saves the process state to disk (Full or Incremental)."""
        all_checkpoints = self.get_all_checkpoints()
        last_id = all_checkpoints[-1]['checkpoint_id'] if all_checkpoints else 0
        new_checkpoint_id = last_id + 1

        payload = {}
        checkpoint_type = "FULL" if is_full else "INCREMENTAL"

        if not is_full:
            # Incremental: save only dirty pages
            for page_id, page in process.memory.items():
                if page.is_dirty:
                    payload[page_id] = base64.b64encode(page.data).decode('utf-8')
        else:
            # Full: save all pages
            for page_id, page in process.memory.items():
                payload[page_id] = base64.b64encode(page.data).decode('utf-8')

        if not is_full and not payload:
            return "No changes to save."

        last_full_cp = next((cp for cp in reversed(all_checkpoints) if cp['type'] == 'FULL'), None)

        manifest = {
            "checkpoint_id": new_checkpoint_id,
            "timestamp": time.time(),
            "type": checkpoint_type,
            "parent_checkpoint_id": last_full_cp['checkpoint_id'] if last_full_cp and not is_full else None,
            "process_context": {
                "program_counter": process.program_counter,
                "registers": process.registers
            },
            "memory_payload": payload
        }

        file_path = os.path.join(self.storage_path, f"checkpoint_{new_checkpoint_id}.json")
        with open(file_path, 'w') as f:
            json.dump(manifest, f, indent=2)

        # CRUCIAL STEP: Reset dirty bits after saving an incremental checkpoint
        if not is_full:
            for page in process.memory.values():
                page.reset_dirty_bit()

        return f"Saved {checkpoint_type} Checkpoint {new_checkpoint_id}."

    def recover(self, process: Process):
        """Restores the system state by replaying logs into the process object."""
        all_checkpoints = self.get_all_checkpoints()
        if not all_checkpoints:
            return "No checkpoints found. Starting fresh."

        last_full_cp = next((cp for cp in reversed(all_checkpoints) if cp['type'] == 'FULL'), None)
        if not last_full_cp:
            return "No full checkpoint found. Cannot recover."

        # 1. Load the base full checkpoint state
        for page_id_str, b64_data in last_full_cp['memory_payload'].items():
            process.memory[int(page_id_str)].data = base64.b64decode(b64_data)

        # 2. Find and apply all subsequent incremental checkpoints in order
        for cp in all_checkpoints:
            if cp['type'] == 'INCREMENTAL' and cp['timestamp'] > last_full_cp['timestamp']:
                for page_id_str, b64_data in cp['memory_payload'].items():
                    process.memory[int(page_id_str)].data = base64.b64decode(b64_data)

        # 3. The final register/PC state is from the very last checkpoint
        final_cp = all_checkpoints[-1]
        process.registers = final_cp['process_context']['registers']
        process.program_counter = final_cp['process_context']['program_counter']

        return f"Recovery complete. Restored to state from Checkpoint {final_cp['checkpoint_id']}."
# done