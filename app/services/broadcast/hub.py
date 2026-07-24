import asyncio

from fastapi import WebSocket


class BroadcastHub:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)

    async def publish(self, payload: dict) -> None:
        async with self._lock:
            connections = list(self._connections)
        stale = []
        for connection in connections:
            try:
                await connection.send_json(payload)
            except Exception:
                stale.append(connection)
        if stale:
            async with self._lock:
                for connection in stale:
                    self._connections.discard(connection)
