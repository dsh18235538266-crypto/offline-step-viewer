"""MCP server entry point (mcp 2.x / MCPServer API).

Registers all tools via the @mcp.tool() decorator — schemas are
auto-derived from function type annotations.  Starts the viewer
WebSocket server in the background.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from typing import Optional

from mcp.server.mcpserver import MCPServer

from . import tools as _tools
from . import templates as _templates
from .state import get_state
from .viewer_ws import start_server, push_model

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("step_modeler.server")

mcp = MCPServer("step-modeler-mcp")


# ── primitives ──────────────────────────────────────────────────

@mcp.tool()
async def create_box(
    length: float,
    width: float,
    height: float,
    pos: Optional[list[float]] = None,
) -> str:
    """Create a rectangular box and set it as the current model in memory.

    Args:
        length: X dimension in mm.
        width: Y dimension in mm.
        height: Z dimension in mm.
        pos: Optional [x, y, z] center offset in mm. Defaults to origin.

    Returns:
        JSON summary with bounding box and metadata.
    """
    result = await _tools.create_box(length, width, height, pos)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def create_cylinder(
    radius: float,
    height: float,
    pos: Optional[list[float]] = None,
    axis: Optional[list[float]] = None,
) -> str:
    """Create a cylinder and set it as the current model. Default axis is Z.

    Args:
        radius: Radius in mm.
        height: Height in mm (along axis).
        pos: Optional [x, y, z] center offset in mm.
        axis: Optional [x, y, z] direction axis. Default [0, 0, 1].

    Returns:
        JSON summary with bounding box.
    """
    result = await _tools.create_cylinder(radius, height, pos, axis)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


# ── boolean operations ─────────────────────────────────────────

@mcp.tool()
async def boolean_subtract(tool_shape_cmd: str, tool_pos: list[float]) -> str:
    """Subtract a primitive tool from the current model (e.g. drill a hole).

    The tool is described compactly:
    - 'cylinder:r=4,h=20' → cylinder, radius 4, height 20
    - 'box:l=10,w=10,h=10' → box 10x10x10

    Args:
        tool_shape_cmd: Tool descriptor: 'cylinder:r=<R>,h=<H>' or 'box:l=<L>,w=<W>,h=<H>'.
        tool_pos: [x, y, z] center of the tool primitive in mm.

    Returns:
        JSON summary after subtraction.
    """
    result = await _tools.boolean_subtract(tool_shape_cmd, tool_pos)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def boolean_union(other_shape_cmd: str, other_pos: list[float]) -> str:
    """Union a primitive with the current model (e.g. add a boss, attach a bracket).

    Descriptor format same as boolean_subtract.

    Args:
        other_shape_cmd: Shape descriptor: 'cylinder:r=<R>,h=<H>' or 'box:l=<L>,w=<W>,h=<H>'.
        other_pos: [x, y, z] center of the added primitive in mm.

    Returns:
        JSON summary after union.
    """
    result = await _tools.boolean_union(other_shape_cmd, other_pos)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


# ── export & viewer ────────────────────────────────────────────

@mcp.tool()
async def export_step(path: Optional[str] = None) -> str:
    """Export the current model to a STEP file.

    Args:
        path: Output file path. If omitted, returns metadata only.

    Returns:
        JSON dict with file path (if written) and size.
    """
    result = await _tools.export_step(path)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def push_to_viewer(source: str = "manual") -> str:
    """Export the current model as STEP and push it to the HTML viewer via WebSocket.

    The viewer must be open in a browser and connected to ws://localhost:8765.
    Call this after any modeling operation so the user sees the result in real time.

    Args:
        source: Human-readable label for what triggered this push.

    Returns:
        JSON dict describing the push result and model info.
    """
    result = await _tools.push_to_viewer(source)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


# ── scene templates ────────────────────────────────────────────

@mcp.tool()
async def create_mounting_hole(
    m_size: str = "M8",
    pos: Optional[list[float]] = None,
    depth: Optional[float] = None,
    through: bool = True,
) -> str:
    """Drill a standard metric clearance mounting hole into the current model.

    Supports M3–M20. Creates a clearance hole (not tapped). For through-holes
    the depth is auto-extended beyond the model's bounding box.

    Args:
        m_size: Metric thread size, e.g. 'M6', 'M8', 'M10'.
        pos: [x, y, z] center of hole in mm.
        depth: Hole depth in mm. Omit for through-hole.
        through: Make a through-hole (default true).

    Returns:
        JSON summary after drilling.
    """
    result = await _templates.create_mounting_hole(m_size, pos, depth, through)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def create_flange(
    width: float = 60.0,
    thickness: float = 8.0,
    hole_pattern: str = "4-corner",
    hole_size: str = "M6",
    center_bore: Optional[float] = None,
) -> str:
    """Generate a flange plate with standard corner mounting holes.

    REPLACES the current model. Good starting point for brackets and adapter plates.

    Args:
        width: Square plate side in mm.
        thickness: Plate thickness in mm.
        hole_pattern: '4-corner' (default) or 'none'.
        hole_size: Metric size for corner holes (e.g. 'M6').
        center_bore: Optional center bore diameter in mm.

    Returns:
        JSON summary of the created flange.
    """
    result = await _templates.create_flange(width, thickness, hole_pattern, hole_size, center_bore)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def create_bore(
    diameter: float,
    depth: Optional[float] = None,
    pos: Optional[list[float]] = None,
    through: bool = False,
) -> str:
    """Bore an arbitrary-diameter hole into the current model.

    Useful for bearing seats, cable pass-throughs, custom shaft holes.

    Args:
        diameter: Bore diameter in mm.
        depth: Depth in mm. Omit for through.
        pos: [x, y, z] center position.
        through: Make through-hole.

    Returns:
        JSON summary after boring.
    """
    result = await _templates.create_bore(diameter, depth, pos, through)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def create_gripper_base(
    jaw_length: float = 40.0,
    jaw_width: float = 12.0,
    jaw_height: float = 20.0,
    gap: float = 8.0,
    base_thickness: float = 8.0,
) -> str:
    """Generate a simple two-jaw gripper base (base plate + two parallel jaws).

    Useful as a starting point for robotic-arm gripper second-development.

    Args:
        jaw_length: Jaw length in mm (Y direction).
        jaw_width: Jaw width in mm (X direction).
        jaw_height: Jaw height in mm (Z direction).
        gap: Distance between jaws in mm.
        base_thickness: Base plate thickness in mm.

    Returns:
        JSON summary of the created gripper base.
    """
    result = await _templates.create_gripper_base(
        jaw_length, jaw_width, jaw_height, gap, base_thickness
    )
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


# ── utility ────────────────────────────────────────────────────

@mcp.tool()
async def get_model_info() -> str:
    """Return bounding box, volume, and shape count of the current model."""
    result = await _tools.get_model_info()
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def reset_model() -> str:
    """Clear the in-memory model. Start a fresh session."""
    result = await _tools.reset_model()
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def undo() -> str:
    """Undo the last modeling operation."""
    result = await _tools.undo()
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def redo() -> str:
    """Redo a previously undone operation."""
    result = await _tools.redo()
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


# ── entry point ────────────────────────────────────────────────


async def _main_async() -> None:
    """Start the WebSocket viewer server, then run the MCP stdio server."""
    viewer_port = int(os.environ.get("VIEWER_PORT", "8765"))
    await start_server(port=viewer_port)
    logger.info(
        "Viewer WS server on port %d — open viewer/index.html in a browser",
        viewer_port,
    )
    # Run MCP stdio server (this blocks)
    await mcp.run_stdio_async()


def main() -> None:
    """Entry point for the step-modeler-mcp console script."""
    asyncio.run(_main_async())


if __name__ == "__main__":
    main()
