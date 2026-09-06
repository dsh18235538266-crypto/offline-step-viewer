"""High-level scene templates for common mechanical-arm features.

These compose atomic build123d operations into ready-made features
tailored to robotics second-development: mounting holes, flanges,
bearing bores, etc.  They reduce the number of tool calls the agent
needs for typical requests.
"""

from __future__ import annotations

import logging
from typing import Optional

from build123d import (
    Box,
    Cylinder,
    Circle,
    Pos,
    Vector,
    Compound,
    Align,
    Plane,
    Location,
    Mode,
)

from .state import get_state
from .viewer_ws import push_model

logger = logging.getLogger("step_modeler.templates")


# ── standard metric thread clearance / tap drill sizes ──────────
# (clearance hole diameter ≈ nominal + 1mm for M-size holes through-holes)
_METRIC_CLEARANCE = {
    "M3": 3.3,
    "M4": 4.5,
    "M5": 5.5,
    "M6": 6.6,
    "M8": 9.0,
    "M10": 11.0,
    "M12": 13.5,
    "M16": 17.5,
    "M20": 22.0,
}


async def create_mounting_hole(
    m_size: str = "M8",
    pos: list[float] = None,
    depth: Optional[float] = None,
    through: bool = True,
) -> dict:
    """Drill a standard metric mounting hole at the given position.

    Creates a clearance hole (not tapped).  For through-holes the depth
    is auto-extended 5mm beyond the model's bounding box to ensure it
    cuts all the way through.

    Args:
        m_size: Thread size string, e.g. "M6", "M8", "M10".
        pos: [x, y, z] center of hole entry point in mm.
        depth: Hole depth in mm. If None and through=True, auto-calculated.
        through: If True (default), make a through-hole by extending the
            cylinder beyond the model bbox.

    Returns:
        Summary dict.
    """
    state = get_state()
    if state.is_empty():
        raise ValueError("No base model. Create a box/cylinder first.")

    m_size = m_size.upper()
    if m_size not in _METRIC_CLEARANCE:
        raise ValueError(
            f"Unsupported size '{m_size}'. Supported: {', '.join(_METRIC_CLEARANCE)}"
        )

    clearance_d = _METRIC_CLEARANCE[m_size]
    radius = clearance_d / 2

    if pos is None:
        pos = [0, 0, 0]

    # Auto-depth: extend 10mm beyond bbox Z-extent
    if depth is None or through:
        info = state.info()
        bbox = info.get("bbox", {})
        if bbox:
            z_size = bbox["size"][2]
            z_min = bbox["min"][2]
            depth = z_size + 20  # extend 10mm each side
            # shift Z so cylinder covers full model
            pos = list(pos)
            pos[2] = (z_min + bbox["max"][2]) / 2  # center on model
        else:
            depth = depth or 20.0

    tool = Cylinder(radius, depth, align=Align.CENTER)
    tool = tool.moved(Pos(*pos))

    current = state.current
    new_shape = current - tool

    state.replace(new_shape if new_shape is not None else current)

    result = state.info()
    result["action"] = "create_mounting_hole"
    result["params"] = {
        "m_size": m_size,
        "clearance_diameter": clearance_d,
        "pos": pos,
        "depth": depth,
        "through": through,
    }
    logger.info("Drilled %s hole (Ø%.1f) at %s", m_size, clearance_d, pos)
    return result


async def create_flange(
    width: float = 60.0,
    thickness: float = 8.0,
    hole_pattern: str = "4-corner",
    hole_size: str = "M6",
    center_bore: Optional[float] = None,
) -> dict:
    """Create a flange plate with standard mounting holes.

    This REPLACES the current model (it's a standalone part generator).

    Args:
        width: Square plate side length in mm.
        thickness: Plate thickness in mm.
        hole_pattern: "4-corner" (default) for holes at 4 corners,
            "none" for a plain plate.
        hole_size: Metric size for corner holes (e.g. "M6").
        center_bore: Optional center bore diameter in mm.

    Returns:
        Summary dict.
    """
    state = get_state()

    plate = Box(width, width, thickness, align=Align.CENTER)

    # Add corner holes
    if hole_pattern == "4-corner" and hole_size:
        m_size = hole_size.upper()
        clearance_d = _METRIC_CLEARANCE.get(m_size, 6.6)
        r = clearance_d / 2
        offset = width / 2 - clearance_d  # hole center inset
        hole_depth = thickness + 20

        for sx in (-1, 1):
            for sy in (-1, 1):
                hole = Cylinder(r, hole_depth, align=Align.CENTER)
                hole = hole.moved(Pos(sx * offset, sy * offset, 0))
                plate = plate - hole

    # Center bore
    if center_bore and center_bore > 0:
        bore = Cylinder(center_bore / 2, thickness + 20, align=Align.CENTER)
        plate = plate - bore

    new_shape = Compound.make_compound([plate]) if not isinstance(plate, Compound) else plate
    state.replace(new_shape)

    result = state.info()
    result["action"] = "create_flange"
    result["params"] = {
        "width": width,
        "thickness": thickness,
        "hole_pattern": hole_pattern,
        "hole_size": hole_size,
        "center_bore": center_bore,
    }
    logger.info("Created flange %.0f x %.0f t=%.1f", width, width, thickness)
    return result


async def create_bore(
    diameter: float,
    depth: Optional[float] = None,
    pos: Optional[list[float]] = None,
    through: bool = False,
) -> dict:
    """Bore a hole of arbitrary diameter into the current model.

    Unlike create_mounting_hole, this takes a raw diameter (not a
    metric thread size) — useful for bearing seats, cable pass-throughs,
    etc.

    Args:
        diameter: Bore diameter in mm.
        depth: Bore depth in mm. If None, auto-extended through model.
        pos: [x, y, z] center position. Defaults to [0,0,0].
        through: If True, extends the bore through the entire model.

    Returns:
        Summary dict.
    """
    state = get_state()
    if state.is_empty():
        raise ValueError("No base model to bore into.")

    if pos is None:
        pos = [0, 0, 0]

    radius = diameter / 2

    if depth is None or through:
        info = state.info()
        bbox = info.get("bbox", {})
        if bbox:
            depth = bbox["size"][2] + 20
            pos = list(pos)
            pos[2] = (bbox["min"][2] + bbox["max"][2]) / 2
        else:
            depth = depth or 20.0

    tool = Cylinder(radius, depth, align=Align.CENTER)
    tool = tool.moved(Pos(*pos))

    current = state.current
    new_shape = current - tool

    state.replace(new_shape if new_shape is not None else current)

    result = state.info()
    result["action"] = "create_bore"
    result["params"] = {
        "diameter": diameter,
        "depth": depth,
        "pos": pos,
        "through": through,
    }
    logger.info("Bored Ø%.1f x %.1f deep at %s", diameter, depth, pos)
    return result


async def create_gripper_base(
    jaw_length: float = 40.0,
    jaw_width: float = 12.0,
    jaw_height: float = 20.0,
    gap: float = 8.0,
    base_thickness: float = 8.0,
) -> dict:
    """Generate a simple two-jaw gripper base model.

    This is a starter template for robotic-arm gripper second-development:
    a base plate with two parallel jaws and a configurable gap between them.

    Args:
        jaw_length: Jaw finger length in mm (Y direction).
        jaw_width: Jaw finger width in mm (X direction).
        jaw_height: Jaw finger height in mm (Z direction).
        gap: Distance between the two jaws in mm.
        base_thickness: Base plate thickness in mm.

    Returns:
        Summary dict.
    """
    state = get_state()

    # Base plate
    base_w = jaw_width * 2 + gap + 20  # some margin
    base_d = jaw_length + 10
    base = Box(base_w, base_d, base_thickness, align=Align.CENTER)
    base = base.moved(Pos(0, 0, -jaw_height / 2 - base_thickness / 2))

    # Left jaw
    jaw_l = Box(jaw_width, jaw_length, jaw_height, align=Align.CENTER)
    jaw_l = jaw_l.moved(Pos(-(jaw_width / 2 + gap / 2), 0, 0))

    # Right jaw
    jaw_r = Box(jaw_width, jaw_length, jaw_height, align=Align.CENTER)
    jaw_r = jaw_r.moved(Pos(jaw_width / 2 + gap / 2, 0, 0))

    gripper = base + jaw_l + jaw_r

    new_shape = Compound.make_compound([gripper]) if not isinstance(gripper, Compound) else gripper
    state.replace(new_shape)

    result = state.info()
    result["action"] = "create_gripper_base"
    result["params"] = {
        "jaw_length": jaw_length,
        "jaw_width": jaw_width,
        "jaw_height": jaw_height,
        "gap": gap,
        "base_thickness": base_thickness,
    }
    logger.info("Created gripper base (gap=%.1f, jaw %.0fx%.0fx%.0f)", gap, jaw_width, jaw_length, jaw_height)
    return result
