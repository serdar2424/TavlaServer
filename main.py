import contextlib

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocket, WebSocketDisconnect

from middlewares.auth import AuthMiddleware
from routes import routers
from services.database import create_indexes, initialize_db_connection
from services.websocket import get_current_user, manager

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to your needs
    allow_credentials=True,
    allow_methods=["*"],  # This allows all methods, including OPTIONS
    allow_headers=["*"],
)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize the database connection
    initialize_db_connection()
    await create_indexes()
    yield
    # Add any shutdown tasks here if needed


app.router.lifespan_context = lifespan
app.add_middleware(AuthMiddleware)

# Include the routers
for router in routers:
    app.include_router(router)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str):
    username = await get_current_user(token)
    await manager.connect(websocket, username)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.handle_message(data, websocket, username)
    except WebSocketDisconnect:
        manager.disconnect(websocket, username)


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
