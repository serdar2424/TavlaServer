import json
from core.config import SECRET_KEY, ALGORITHM
from fastapi import WebSocket, HTTPException, status
from jose import JWTError, jwt
from typing import List, Dict


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.online_users: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, username: str):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.online_users[username] = websocket

    def disconnect(self, websocket: WebSocket, username: str):
        self.active_connections.remove(websocket)
        if username in self.online_users:
            del self.online_users[username]

    async def get_user(self, username: str):
        return self.online_users.get(username)

    async def send_personal_message(self, message: json, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast(self, message: json):
        for connection in self.active_connections:
            await connection.send_json(message)

    async def handle_message(self, message: str, websocket: WebSocket, username: str):
        try:
            json_decoded = json.loads(message)
            message_type = json_decoded.get("type")
            message_content = json_decoded.get("msg")

            if message_type == "msg":
                recipient = json_decoded.get("recipient")
                if recipient in self.online_users:
                    await self.send_personal_message({"type": "msg", "msg": f"{username} says: {message_content}"},
                                                     self.online_users[recipient])
                else:
                    await self.send_personal_message({"type": "error", "msg": f"User {recipient} is not online"}, websocket)
            else:
                await self.send_personal_message({"type": "error", "msg": "Unknown message type"}, websocket)
        except json.JSONDecodeError:
            await self.send_personal_message({"type": "error", "msg": "Invalid JSON format"}, websocket)


manager = ConnectionManager()


async def get_current_user(token: str):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return username
