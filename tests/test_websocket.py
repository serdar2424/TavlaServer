import pytest

from main import app
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect


def test_websocket_endpoint_general_errors(token: str):
    with TestClient(app) as client:
        with client.websocket_connect(f"/ws?token={token}") as websocket:
            websocket.send_json({"type":"not_existing", "recipient": "testuser", "msg": "xyz"})
            resp = websocket.receive_json()
            assert resp == {"type":"error", "msg":"Unknown message type"}
            websocket.send_text('{"type":"msg"')
            resp = websocket.receive_json()
            assert resp == {"type":"error", "msg": "Invalid JSON format"}

def test_websocket_endpoint_chat(token: str):
    with TestClient(app) as client:
        with client.websocket_connect(f"/ws?token={token}") as websocket:
            websocket.send_json({"type":"msg", "recipient": "testuser", "msg": "xyz"})
            resp = websocket.receive_json()
            assert resp == {"type":"msg", "msg":"testuser says: xyz"}
            websocket.send_json({"type":"msg", "recipient": "a", "msg": "xyz"})
            resp = websocket.receive_json()
            assert resp == {"type":"error", "msg":"User a is not online"}

def test_websocket_endpoint_no_token():
    with TestClient(app) as client:
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/ws") as websocket:
                websocket.receive_text()