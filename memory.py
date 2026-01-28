"""
memory.py

Simple RAM abstraction used by the checkpointing demo.
"""

from __future__ import annotations

from typing import Dict, List


class RAM:
    """
    Very small in‑memory "RAM" model backed by a Python list.

    - Each index is a page.
    - Pages store arbitrary string content.
    - We track which pages were modified (dirty pages) so that
    the checkpoint manager can create incremental checkpoints.
    """

    def __init__(self, num_pages: int) -> None:
        if num_pages <= 0:
            raise ValueError("num_pages must be positive")

        self.num_pages: int = num_pages
        self.pages: List[str] = ["" for _ in range(num_pages)]
        self._dirty_pages: set[int] = set()

    # -----------------------------
    # Basic read / write operations
    # -----------------------------
    def _validate_index(self, page_index: int) -> None:
        if not 0 <= page_index < self.num_pages:
            raise IndexError(
                f"Page index {page_index} out of bounds (0..{self.num_pages - 1})"
            )

    def write_to_page(self, page_index: int, data: str) -> None:
        """Write data to a page and mark it as dirty."""
        self._validate_index(page_index)
        self.pages[page_index] = data
        self._dirty_pages.add(page_index)
        print(f"[RAM] Wrote to page {page_index}: '{data}'")

    def read_page(self, page_index: int) -> str:
        """Read the content of a page."""
        self._validate_index(page_index)
        return self.pages[page_index]

    # -----------------------------
    # State helpers for checkpointing
    # -----------------------------
    def get_state(self) -> List[str]:
        """Return a copy of the full RAM state."""
        return list(self.pages)

    def load_state(self, new_pages: List[str]) -> None:
        """Replace the current RAM contents with `new_pages`."""
        if len(new_pages) != self.num_pages:
            raise ValueError(
                f"Expected {self.num_pages} pages, got {len(new_pages)} instead"
            )
        self.pages = list(new_pages)
        self._dirty_pages.clear()
        print("[RAM] State loaded into RAM.")

    def get_dirty_pages(self) -> Dict[int, str]:
        """Return a mapping (page_index -> data) for all dirty pages."""
        return {i: self.pages[i] for i in self._dirty_pages}

    def clear_dirty(self) -> None:
        """Clear the dirty page set after a checkpoint."""
        self._dirty_pages.clear()


