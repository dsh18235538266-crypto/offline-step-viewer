"""In-memory model state with history stack.

Build123d Shape lives in memory; every mutation pushes the previous
shape onto an undo stack.  Export helpers produce STEP bytes.
"""

from __future__ import annotations

import io
import os
import tempfile
from dataclasses import dataclass, field
from typing import Optional

from build123d import Compound, export_step, Shape


@dataclass
class ModelState:
    """Mutable singleton holding the current build123d shape + history."""

    current: Optional[Shape] = None
    _undo_stack: list[Shape] = field(default_factory=list)
    _redo_stack: list[Shape] = field(default_factory=list)

    # ── mutation ────────────────────────────────────────────────

    def replace(self, new_shape: Shape) -> None:
        """Replace the current shape, pushing old one onto undo stack.

        Note: build123d boolean ops return new shapes, so we just keep
        the reference — no copy needed.
        """
        if self.current is not None:
            self._undo_stack.append(self.current)
        self._redo_stack.clear()
        self.current = new_shape

    def mutate(self, fn) -> None:
        """Apply fn(current) -> new shape; fn receives None for empty state."""
        old = self.current
        new = fn(old)
        if old is not None:
            self._undo_stack.append(old)
        self._redo_stack.clear()
        self.current = new

    # ── history ─────────────────────────────────────────────────

    def undo(self) -> bool:
        if not self._undo_stack:
            return False
        if self.current is not None:
            self._redo_stack.append(self.current)
        self.current = self._undo_stack.pop()
        return True

    def redo(self) -> bool:
        if not self._redo_stack:
            return False
        if self.current is not None:
            self._undo_stack.append(self.current)
        self.current = self._redo_stack.pop()
        return True

    def reset(self) -> None:
        """Clear everything (fresh session)."""
        self.current = None
        self._undo_stack.clear()
        self._redo_stack.clear()

    # ── queries ────────────────────────────────────────────────

    def is_empty(self) -> bool:
        return self.current is None

    def info(self) -> dict:
        """Return a summary dict for tool responses."""
        if self.current is None:
            return {"empty": True, "shape_count": 0}
        try:
            bbox = self.current.bounding_box()
            return {
                "empty": False,
                "shape_count": len(list(self.current.get_shape_entities())) if hasattr(self.current, "get_shape_entities") else 1,
                "bbox": {
                    "min": [round(bbox.min.X, 3), round(bbox.min.Y, 3), round(bbox.min.Z, 3)],
                    "max": [round(bbox.max.X, 3), round(bbox.max.Y, 3), round(bbox.max.Z, 3)],
                    "size": [round(bbox.size.X, 3), round(bbox.size.Y, 3), round(bbox.size.Z, 3)],
                },
                "volume": round(self.current.volume, 3) if hasattr(self.current, "volume") else None,
            }
        except Exception:
            return {"empty": False, "shape_count": 1, "bbox": None}

    # ── export ─────────────────────────────────────────────────

    def export_step_bytes(self) -> bytes:
        """Export current shape as STEP file bytes."""
        if self.current is None:
            raise ValueError("No model in memory. Create one first (e.g. create_box).")

        # build123d export_step writes to a file; use temp file then read
        tmp = tempfile.NamedTemporaryFile(suffix=".step", delete=False)
        tmp.close()
        try:
            export_step(self.current, tmp.name)
            with open(tmp.name, "rb") as f:
                return f.read()
        finally:
            os.unlink(tmp.name)

    def export_step_to_file(self, path: str) -> str:
        """Export current shape to a STEP file on disk."""
        if self.current is None:
            raise ValueError("No model in memory.")
        export_step(self.current, path)
        return os.path.abspath(path)


# ── module-level singleton ──────────────────────────────────────

_state = ModelState()


def get_state() -> ModelState:
    """Get the global model state singleton."""
    return _state
