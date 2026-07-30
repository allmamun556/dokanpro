from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.db.session import get_scoped_session
from app.core.security import decode_access_token
from app.core.permissions import has_permission
from app.models.user import User
from app.services import ws_manager

router = APIRouter()


@router.websocket("/ws/orders")
async def orders_websocket(websocket: WebSocket, token: str = ""):
    """
    Pushes a small ping whenever an order is created or its fulfillment
    status changes, so Kitchen Display / Online Orders can refresh instantly
    instead of waiting for their 15s poll. The poll stays as a fallback.

    WebSocket routes have no Request object, so this can't use get_db as a
    FastAPI dependency (that needs request.state.business_id) — it decodes
    the token itself and opens a scoped session directly, the same way
    get_db does internally.
    """
    payload = decode_access_token(token)
    if payload is None or payload.get("type", "staff") != "staff":
        await websocket.close(code=4401)
        return

    business_id = payload.get("business_id")
    if business_id is None:
        await websocket.close(code=4401)
        return

    db = get_scoped_session(business_id)
    try:
        user = db.get(User, int(payload.get("sub", 0)))
        if user is None or not user.is_active or not has_permission(user, "orders.fulfill"):
            await websocket.close(code=4403)
            return
    finally:
        db.close()

    await ws_manager.connect(websocket, business_id)
    try:
        while True:
            # No client->server messages expected; just keep the connection open.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(websocket)
