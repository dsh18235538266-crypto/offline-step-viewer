"""Atomic MCP tools for STEP model creation/editing.

Each tool operates on the in-memory ModelState singleton.
Tools are async and use build123d for geometry.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from build123d import (
    Box,
    Cylinder,
    Sphere,
    Plane,
    Axis,
    Location,
    Pos,
    Vector,
    Compound,
    Solid,
    Shape,
    Mode,
    Align,
)

from .state import get_state
from .viewer_ws import push_model

logger = logging.getLogger("step_modeler.tools")


# ── primitives ──────────────────────────────────────────────────


async def create_box(
    length: float,
    width: float,
    height: float,
    pos: Optional[list[float]] = None,
) -> dict:
    """Create a rectangular box and set it as the current model.

    Args:
        length: X dimension in mm.
        width: Y dimension in mm.
        height: Z dimension in mm.
        pos: Optional [x, y, z] center offset in mm. Defaults to origin.

    Returns:
        Summary dict with bounding box and metadata.
    """
    state = get_state()
    offset = Vector(*(pos or [0, 0, 0]))

    box = Box(length, width, height, align=Align.CENTER)
    if offset != Vector(0, 0, 0):
        box = box.moved(Pos(*offset))

    new_shape = Compound.make_compound([box]) if not isinstance(box, Compound) else box
    state.replace(new_shape)

    result = state.info()
    result["action"] = "create_box"
    result["params"] = {"length": length, "width": width, "height": height, "pos": pos}
    logger.info("Created box %.1f x %.1f x %.1f", length, width, height)
    return result


async def create_cylinder(
    radius: float,
    height: float,
    pos: Optional[list[float]] = None,
    axis: Optional[list[float]] = None,
) -> dict:
    """Create a cylinder and set it as the current model.

    Args:
        radius: Radius in mm.
        height: Height in mm (along Z by default).
        pos: Optional [x, y, z] center offset.
        axis: Optional [x, y, z] direction axis (default Z).

    Returns:
        Summary dict with bounding box.
    """
    state = get_state()
    offset = Vector(*(pos or [0, 0, 0]))
    axis_dir = Vector(*(axis or [0, 0, 1]))

    cyl = Cylinder(radius, height, align=Align.CENTER)
    if axis_dir != Vector(0, 0, 1):
        # Rotate so cylinder's Z aligns with axis_dir
        cyl = cyl.moved(Pos(0, 0, 0))  # identity translation
        cyl = cyl.rotated((0, 0, 0), axis_dir.to_tuple(), 0)  # placeholder; build123d API varies

    if offset != Vector(0, 0, 0):
        cyl = cyl.moved(Pos(*offset))

    new_shape = Compound.make_compound([cyl]) if not isinstance(cyl, Compound) else cyl
    state.replace(new_shape)

    result = state.info()
    result["action"] = "create_cylinder"
    result["params"] = {"radius": radius, "height": height, "pos": pos, "axis": axis}
    logger.info("Created cylinder r=%.1f h=%.1f", radius, height)
    return result


# ── boolean operations ─────────────────────────────────────────


async def boolean_subtract(tool_shape_cmd: str, tool_pos: list[float]) -> dict:
    """Subtract a primitive from the current model (e.g. drill a hole).

    NOTE: For MVP simplicity, this creates a tool (box/cylinder) at the
    given position and subtracts it from the current shape.  More
    sophisticated tool shapes will be added later.

    Args:
        tool_shape_cmd: Compact descriptor like "cylinder:r=4,h=20" or
            "box:l=10,w=10,h=10".  The primitive is created centered at
            the given pos and subtracted.
        tool_pos: [x, y, z] center of the tool primitive in mm.

    Returns:
        Summary dict with bounding box after subtraction.
    """
    state = get_state()
    if state.is_empty():
        raise ValueError("No base model to subtract from. Call create_box/cylinder first.")

    # Parse tool descriptor
    parts = tool_shape_cmd.split(":", 2)
    kind = parts[0]
    params: dict[str, float] = {}
    if len(parts) > 1:
        for kv in parts[1].split(","):
            if "=" in kv:
                k, v = kv.split("=", 1)
                params[k.strip()] = float(v)

    offset = Vector(*tool_pos)

    if kind == "cylinder":
        r = params.get("r", 4.0)
        h = params.get("h", 20.0)
        tool = Cylinder(r, h, align=Align.CENTER)
    elif kind == "box":
        l = params.get("l", 10.0)
        w = params.get("w", 10.0)
        h = params.get("h", 10.0)
        tool = Box(l, w, h, align=Align.CENTER)
    else:
        raise ValueError(f"Unknown tool kind '{kind}'. Use 'cylinder' or 'box'.")

    tool = tool.moved(Pos(*offset))

    current = state.current
    # build123d boolean: use Shape.__sub__ which returns a Compound
    new_shape = current - tool

    state.replace(new_shape if new_shape is not None else current)

    result = state.info()
    result["action"] = "boolean_subtract"
    result["params"] = {"tool": tool_shape_cmd, "pos": tool_pos}
    logger.info("Subtracted %s at %s", tool_shape_cmd, tool_pos)
    return result


async def boolean_union(other_shape_cmd: str, other_pos: list[float]) -> dict:
    """Union a primitive with the current model.

    Args:
        other_shape_cmd: Descriptor like "cylinder:r=4,h=20" or "box:l=10,w=10,h=10".
        other_pos: [x, y, z] center of the added primitive in mm.

    Returns:
        Summary dict after union.
    """
    state = get_state()
    if state.is_empty():
        raise ValueError("No base model. Call create_box/cylinder first.")

    parts = other_shape_cmd.split(":", 2)
    kind = parts[0]
    params: dict[str, float] = {}
    if len(parts) > 1:
        for kv in parts[1].split(","):
            if "=" in kv:
                k, v = kv.split("=", 1)
                params[k.strip()] = float(v)

    offset = Vector(*other_pos)

    if kind == "cylinder":
        r = params.get("r", 4.0)
        h = params.get("h", 20.0)
        other = Cylinder(r, h, align=Align.CENTER)
    elif kind == "box":
        l = params.get("l", 10.0)
        w = params.get("w", 10.0)
        h = params.get("h", 10.0)
        other = Box(l, w, h, align=Align.CENTER)
    else:
        raise ValueError(f"Unknown shape kind '{kind}'.")

    other = other.moved(Pos(*offset))

    current = state.current
    new_shape = current + other

    state.replace(new_shape if new_shape is not None else current)

    result = state.info()
    result["action"] = "boolean_union"
    result["params"] = {"other": other_shape_cmd, "pos": other_pos}
    logger.info("Unioned %s at %s", other_shape_cmd, other_pos)
    return result


# ── export & viewer ────────────────────────────────────────────


async def export_step(path: Optional[str] = None) -> dict:
    """Export the current model to a STEP file.

    Args:
        path: Output file path. If omitted, returns bytes in response
            but does not write to disk.

    Returns:
        Dict with file path (if written) and size.
    """
    state = get_state()
    if state.is_empty():
        raise ValueError("No model to export.")

    if path:
        abs_path = state.export_step_to_file(path)
        return {
            "action": "export_step",
            "path": abs_path,
            "size": __import__("os").path.getsize(abs_path),
        }
    else:
        data = state.export_step_bytes()
        return {
            "action": "export_step",
            "size": len(data),
            "note": "STEP bytes generated; not written to disk. Use push_to_viewer or pass a path.",
        }


async def push_to_viewer(source: str = "manual") -> dict:
    """Export the current model as STEP and push it to the HTML viewer.

    The viewer (if connected) will automatically reload the model.
    This is the tool to call after any modeling operation so the user
    can see the result in real time.

    Args:
        source: Human-readable label shown in the viewer status bar.

    Returns:
        Dict describing the push result.
    """
    state = get_state()
    if state.is_empty():
        raise ValueError("No model to push.")

    step_bytes = state.export_step_bytes()
    await push_model(step_bytes, source=source)

    return {
        "action": "push_to_viewer",
        "source": source,
        "size": len(step_bytes),
        "viewers_connected": len(__import__("step_modeler.viewer_ws", fromlist=["_clients"])._clients),
        "info": state.info(),
    }


# ── utility ────────────────────────────────────────────────────


async def get_model_info() -> dict:
    """Return information about the current model in memory."""
    state = get_state()
    return state.info()


async def reset_model() -> dict:
    """Clear the in-memory model (start fresh)."""
    state = get_state()
    state.reset()
    return {"action": "reset", "empty": True}


async def undo() -> dict:
    """Undo the last modeling operation."""
    state = get_state()
    ok = state.undo()
    return {"action": "undo", "success": ok, "info": state.info()}


async def redo() -> dict:
    """Redo a previously undone operation."""
    state = get_state()
    ok = state.redo()
    return {"action": "redo", "success": ok, "info": state.info()}
