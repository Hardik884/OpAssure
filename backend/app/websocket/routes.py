"""WS /ws — the realtime channel. Server -> client events; see docs/api/README.md.

On connect the client receives a `replay_status` event. Clients may send
{"action": "ping"} (-> `pong`); anything else gets an `error` event, the connection stays open.
"""

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.websocket import events
from app.websocket.manager import manager

logger = logging.getLogger("opassure.ws")

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    from app.api.demo import replay_engine  # late import: avoids a cycle at startup

    await manager.connect(ws)
    try:
        await manager.send(ws, events.replay_status(**replay_engine.status()))
        while True:
            raw = await ws.receive_text()
            try:
                message = json.loads(raw)
                action = message.get("action") if isinstance(message, dict) else None
            except json.JSONDecodeError:
                action = None
            if action == "ping":
                await manager.send(ws, events.envelope("pong", {}))
            elif action == "status":
                await manager.send(ws, events.replay_status(**replay_engine.status()))
            else:
                await manager.send(ws, events.error('Unsupported message; send {"action": "ping"} or {"action": "status"}'))
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001
        logger.exception("WebSocket connection error")
    finally:
        manager.disconnect(ws)
