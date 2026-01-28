"""
checkpoint.py

Implements a simple checkpointing and recovery mechanism that works with the
`RAM` class defined in `memory.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from memory import RAM


@dataclass
class Checkpoint:
    """Represents either a full or incremental checkpoint."""

    timestamp: datetime
    is_full: bool
    # For a full checkpoint we store a full copy of RAM state.
    full_state: Optional[List[str]] = None
    # For an incremental checkpoint we only store changed pages.
    changed_pages: Optional[Dict[int, str]] = None


class CheckpointManager:
    """
    Manages full and incremental checkpoints for a given RAM instance.

    Policy:
    - A FULL checkpoint stores the entire list of pages.
    - An INCREMENTAL checkpoint stores only dirty pages since the last checkpoint.
    - Recovery:
        1. Locate the most recent FULL checkpoint.
        2. Start from that state.
        3. Apply each subsequent INCREMENTAL checkpoint in order.
        4. Load the reconstructed pages into RAM.
    """

    def __init__(self, ram: RAM) -> None:
        self.ram = ram
        self._checkpoints: List[Checkpoint] = []

    # -----------------------------
    # Checkpoint creation
    # -----------------------------
    def create_checkpoint(self, is_full: bool = True) -> None:
        """Create a full or incremental checkpoint."""
        ts = datetime.now()

        if is_full or not self._has_full_checkpoint():
            # Either explicit full checkpoint or we need an initial base.
            state = self.ram.get_state()
            ckpt = Checkpoint(
                timestamp=ts,
                is_full=True,
                full_state=state,
                changed_pages=None,
            )
            ckpt_type = "FULL"
        else:
            dirty = self.ram.get_dirty_pages()
            ckpt = Checkpoint(
                timestamp=ts,
                is_full=False,
                full_state=None,
                changed_pages=dirty if dirty else {},
            )
            ckpt_type = "INCREMENTAL"

        self._checkpoints.append(ckpt)
        # Once stored, we can clear dirty flags.
        self.ram.clear_dirty()

        print(f"[CKPT] Created {ckpt_type} checkpoint at {ts.strftime('%H:%M:%S')}")
        self._debug_print_checkpoint(ckpt)

    def _has_full_checkpoint(self) -> bool:
        return any(c.is_full for c in self._checkpoints)

    # -----------------------------
    # Recovery
    # -----------------------------
    def recover(self) -> None:
        """Recover RAM to the latest consistent state from checkpoints."""
        if not self._checkpoints:
            print("[CKPT] No checkpoints available to recover from.")
            return

        # 1. Find the latest full checkpoint.
        full_index = None
        for i in range(len(self._checkpoints) - 1, -1, -1):
            if self._checkpoints[i].is_full:
                full_index = i
                break

        if full_index is None:
            print("[CKPT] No FULL checkpoint found; cannot recover.")
            return

        full_ckpt = self._checkpoints[full_index]
        assert full_ckpt.full_state is not None
        pages = list(full_ckpt.full_state)

        # 2. Apply all incremental checkpoints after the full one.
        for ckpt in self._checkpoints[full_index + 1 :]:
            if not ckpt.is_full and ckpt.changed_pages:
                for idx, value in ckpt.changed_pages.items():
                    if 0 <= idx < len(pages):
                        pages[idx] = value

        # 3. Load reconstructed state into RAM.
        self.ram.load_state(pages)
        print("[CKPT] Recovery complete.")

    # -----------------------------
    # Debug helpers
    # -----------------------------
    def _debug_print_checkpoint(self, ckpt: Checkpoint) -> None:
        if ckpt.is_full:
            print(f"       FULL state: {ckpt.full_state}")
        else:
            print(f"       DIRTY pages: {ckpt.changed_pages}")


