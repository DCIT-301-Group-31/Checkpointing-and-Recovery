import time

from memory import RAM
from checkpoint import CheckpointManager


def run_simulation() -> None:
    # 1. Initialize System
    my_ram = RAM(num_pages=5)
    ckpt_sys = CheckpointManager(my_ram)

    # 2. Simulate Work (Phase A)
    print("--- SIMULATION START ---")
    my_ram.write_to_page(0, "Hello World")  # Changes Page 0
    my_ram.write_to_page(1, "Operating Systems")  # Changes Page 1

    # 3. Trigger FULL Checkpoint
    ckpt_sys.create_checkpoint(is_full=True)

    # 4. Simulate More Work (Phase B)
    time.sleep(1)
    my_ram.write_to_page(0, "Hello Python")  # Updates Page 0 only
    # Page 1 is NOT changed, so it won't be in the next save

    # 5. Trigger INCREMENTAL Checkpoint
    ckpt_sys.create_checkpoint(is_full=False)

    # 6. Simulate a "Crash" (Clear all memory)
    print("\n!!! SYSTEM CRASH!!! Clearing RAM...")
    my_ram = RAM(num_pages=5)  # New empty RAM
    print(f"Page 0 content after crash: '{my_ram.read_page(0)}' (Should be empty)")

    # 7. Recover
    # We cheat slightly by passing the old ckpt_sys to the new RAM for the demo
    ckpt_sys.ram = my_ram
    ckpt_sys.recover()

    # 8. Verify
    print(f"Page 0 content after recovery: '{my_ram.read_page(0)}'")
    print(f"Page 1 content after recovery: '{my_ram.read_page(1)}'")


if __name__ == "__main__":
    run_simulation()