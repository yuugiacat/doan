from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.v1 import sessions, analytics
from app.api import admin
from app.streaming.ws_manager import manager
from app.streaming.ws_handlers import get_or_create_pipeline, remove_pipeline
from app.storage.event_buffer import store
from app.storage import db

app = FastAPI(title="Learning Analytics AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _on_startup():
    await db.init_pool()


@app.on_event("shutdown")
async def _on_shutdown():
    await db.close_pool()


app.include_router(sessions.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/admin")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    # Ensure session exists
    if not store.get(session_id):
        await websocket.close(code=4004, reason="Session not found")
        return

    await manager.connect(session_id, websocket)
    pipeline = get_or_create_pipeline(session_id)

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "frame")

            if msg_type == "frame":
                result = pipeline.process_frame(data)
                await manager.send_json(session_id, result)

            elif msg_type == "calibration":
                pipeline.set_calibration(data.get("baseline", {}))
                await manager.send_json(session_id, {"type": "calibration_ack"})

            elif msg_type == "ping":
                await manager.send_json(session_id, {"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(session_id)
        remove_pipeline(session_id)
