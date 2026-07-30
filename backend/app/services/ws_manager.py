import asyncio

from fastapi import WebSocket

# ws -> business_id, so a broadcast only reaches connections for the tenant
# the event belongs to (Kitchen Display/Online Orders for Restaurant A must
# never see Restaurant B's order pushes).
_active_connections: dict[WebSocket, int] = {}
_event_loop: asyncio.AbstractEventLoop | None = None


def set_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Captured once at app startup so sync route handlers (this codebase's
    SQLAlchemy-sync routes) can schedule an async broadcast from a worker thread."""
    global _event_loop
    _event_loop = loop


async def connect(ws: WebSocket, business_id: int) -> None:
    await ws.accept()
    _active_connections[ws] = business_id


def disconnect(ws: WebSocket) -> None:
    _active_connections.pop(ws, None)


async def _broadcast_async(message: dict, business_id: int) -> None:
    dead = []
    for ws, ws_business_id in _active_connections.items():
        if ws_business_id != business_id:
            continue
        try:
            await ws.send_json(message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _active_connections.pop(ws, None)


def broadcast(message: dict, business_id: int) -> None:
    """
    Called from synchronous request-handling code (order_service.py,
    orders.py, public_checkout_service.py). Schedules the actual send on the
    app's event loop from whatever thread the sync route is running in —
    the standard pattern for a sync FastAPI route to trigger an async
    WebSocket broadcast. No-op if nothing is connected yet or the loop
    hasn't started (e.g. during tests/migrations).
    """
    if _event_loop is None or not _active_connections:
        return
    asyncio.run_coroutine_threadsafe(_broadcast_async(message, business_id), _event_loop)
