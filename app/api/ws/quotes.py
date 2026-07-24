from fastapi import WebSocket, WebSocketDisconnect


async def quotes_websocket(websocket: WebSocket) -> None:
    container = websocket.app.state.container
    await container.hub.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await container.hub.disconnect(websocket)
    except Exception:
        await container.hub.disconnect(websocket)
