"""End-to-end smoke test for step-modeler-mcp.

Spins up the viewer WebSocket server, calls a few tools, and checks
that a STEP file would be pushed.  Does NOT require an actual browser
to be open — verifies the modeling + export path works.
"""

import asyncio
import json
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from step_modeler.state import get_state
from step_modeler import tools
from step_modeler import templates
from step_modeler.viewer_ws import start_server, stop_server, push_model


async def main():
    print("=" * 60)
    print("step-modeler-mcp — End-to-End Smoke Test")
    print("=" * 60)

    # 1. Start viewer WS server
    print("\n[1/6] Starting viewer WebSocket server on port 8765...")
    await start_server(port=8765)
    print("   OK — ws://127.0.0.1:8765")

    # 2. Create a box
    print("\n[2/6] create_box(80, 60, 8)...")
    r = await tools.create_box(80, 60, 8)
    print(f"   OK — bbox size: {r['bbox']['size']} mm, volume: {r.get('volume')} mm³")

    # 3. Add M8 mounting holes at 4 corners
    print("\n[3/6] create_mounting_hole('M8', [±35, ±25, 0]) x4...")
    for x, y in [(35, 25), (-35, 25), (35, -25), (-35, -25)]:
        r = await templates.create_mounting_hole("M8", [x, y, 0])
    state = get_state()
    info = state.info()
    print(f"   OK — volume after holes: {info.get('volume')} mm³")

    # 4. Add center bore Ø25
    print("\n[4/6] create_bore(25, through=True)...")
    r = await templates.create_bore(25, through=True)
    info = state.info()
    print(f"   OK — volume after bore: {info.get('volume')} mm³")

    # 5. Export STEP
    print("\n[5/6] export_step('test_output.step')...")
    r = await tools.export_step("test_output.step")
    print(f"   OK — wrote {r['size']} bytes to {r['path']}")

    # Also test export to bytes (no path)
    r = await tools.export_step()
    print(f"   OK — in-memory STEP bytes: {r['size']} bytes")

    # 6. Push to viewer (will report 0 viewers since no browser open)
    print("\n[6/6] push_to_viewer('smoke test')...")
    r = await tools.push_to_viewer("smoke test")
    print(f"   OK — pushed {r['size']} bytes to {r['viewers_connected']} viewer(s)")

    # Test undo
    print("\n[bonus] undo()...")
    r = await tools.undo()
    print(f"   OK — undo success={r['success']}, volume now {r['info'].get('volume')} mm³")

    # Test redo
    print("\n[bonus] redo()...")
    r = await tools.redo()
    print(f"   OK — redo success={r['success']}, volume now {r['info'].get('volume')} mm³")

    # Test gripper base template
    print("\n[bonus] create_gripper_base()...")
    r = await templates.create_gripper_base(jaw_length=50, jaw_width=15, jaw_height=25, gap=10)
    info = state.info()
    print(f"   OK — bbox: {info['bbox']['size']} mm, volume: {info.get('volume')} mm³")

    await stop_server()

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)

    # Cleanup test file
    if os.path.exists("test_output.step"):
        os.remove("test_output.step")
        print("\n(cleaned up test_output.step)")


if __name__ == "__main__":
    asyncio.run(main())
