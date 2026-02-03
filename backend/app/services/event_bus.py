from typing import Set
from fastapi import WebSocket
import json
import asyncio


class EventBus:
    def __init__(self):
        self.connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.connections.add(websocket)
    
    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            self.connections.discard(websocket)
    
    async def broadcast(self, event: dict):
        """Broadcast event to all connected clients."""
        message = json.dumps(event, default=str)
        disconnected = set()
        
        for ws in self.connections.copy():
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.add(ws)
        
        if disconnected:
            async with self._lock:
                self.connections -= disconnected


# Singleton instance
event_bus = EventBus()
