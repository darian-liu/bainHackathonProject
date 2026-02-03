from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.event_bus import event_bus

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await event_bus.connect(websocket)
    try:
        while True:
            # Keep connection alive, handle any incoming messages if needed
            data = await websocket.receive_text()
            # Could handle client-to-server messages here
    except WebSocketDisconnect:
        await event_bus.disconnect(websocket)
