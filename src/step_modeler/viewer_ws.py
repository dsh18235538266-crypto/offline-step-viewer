"""WebSocket server that pushes model updates to the HTML viewer.

Runs in a background asyncio task alongside the MCP server.
The viewer connects to ws://localhost:{port} and listens for
JSON messages with model bytes.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from typing import Set

import websockets
from websockets.asyncio.server import ServerConnection

logger = logging.getLogger("step_modeler.viewer_ws")

# Track connected viewer clients
_clients: Set[ServerConnection] = set()
_server = None
_port: int = 8765


def set_port(port: int) -> None:
    global _port
    _port = port


async def _handler(websocket: ServerConnection) -> None:
    """Handle a single viewer connection."""
    _clients.add(websocket)
    logger.info("Viewer connected (total: %d)", len(_clients))
    try:
        # Send hello so the viewer knows it's connected
        await websocket.send(json.dumps({"type": "hello", "msg": "connected"}))
        # Keep connection open; viewer doesn't send anything
        async for _ in websocket:
            pass
    except websockets.ConnectionClosed:
        pass
    finally:
        _clients.discard(websocket)
        logger.info("Viewer disconnected (total: %d)", len(_clients))


async def push_model(step_bytes: bytes, source: str = "tool") -> None:
    """Push a STEP model (as bytes) to all connected viewers.

    Args:
        step_bytes: Raw STEP file bytes.
        source: Human-readable description of what triggered this update.
    """
    if not _clients:
        logger.info("No viewers connected; model not pushed.")
        return

    payload = {
        "type": "model_update",
        "format": "step",
        "source": source,
        "size": len(step_bytes),
        "data": base64.b64encode(step_bytes).decode("ascii"),
    }
    msg = json.dumps(payload)

    disconnected = []
    for ws in _clients:
        try:
            await ws.send(msg)
        except websockets.ConnectionClosed:
            disconnected.append(ws)

    for ws in disconnected:
        _clients.discard(ws)

    logger.info("Pushed STEP model (%d bytes) to %d viewer(s)", len(step_bytes), len(_clients))


async def push_mesh(meshes: list, source: str = "tool") -> int:
    """Push tessellated mesh data to all connected viewers.

    Args:
        meshes: List of dicts with 'vertices' (flat list of floats),
                'indices' (flat list of ints), optional 'color' ([r,g,b] 0-1).
        source: Human-readable label.

    Returns:
        Number of viewers that received the push.
    """
    if not _clients:
        logger.info("No viewers connected; mesh not pushed.")
        return 0

    payload = {
        "type": "mesh_update",
        "source": source,
        "mesh_count": len(meshes),
        "meshes": meshes,
    }
    msg = json.dumps(payload)

    disconnected = []
    sent = 0
    for ws in _clients:
        try:
            await ws.send(msg)
            sent += 1
        except websockets.ConnectionClosed:
            disconnected.append(ws)

    for ws in disconnected:
        _clients.discard(ws)

    logger.info("Pushed mesh (%d parts) to %d viewer(s)", len(meshes), sent)
    return sent


async def start_server(port: int = 8765) -> None:
    """Start the WebSocket server in the background."""
    global _server, _port
    _port = port

    _server = await websockets.serve(_handler, "127.0.0.1", port)
    logger.info("Viewer WebSocket server listening on ws://127.0.0.1:%d", port)


async def stop_server() -> None:
    """Shut down the WebSocket server."""
    global _server
    if _server:
        _server.close()
        await _server.wait_closed()
        _server = None


def get_port() -> int:
    return _port
