import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.redis import redis_client

ws_router = APIRouter()

@ws_router.websocket("/ws/updates")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("order_updates")
    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message:
                await websocket.send_text(message['data'])
            await asyncio.sleep(0.01)
    except WebSocketDisconnect:
        await pubsub.unsubscribe("order_updates")