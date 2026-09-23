"""WebSocket connection manager: many clients, JSON broadcast, dead clients dropped quietly."""

import asyncio
import logging

from fastapi import WebSocket

logger = logging.getLogger("opassure.ws")

SEND_TIMEOUT_S = 5.0  # a stuck client must not stall the replay


class ConnectionManager:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()

    @property
    def count(self) -> int:
        return len(self._clients)

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._clients.add(ws)
        logger.info("WebSocket client connected (%d total)", self.count)

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self._clients:
            self._clients.discard(ws)
            logger.info("WebSocket client disconnected (%d left)", self.count)

    async def send(self, ws: WebSocket, message: dict) -> bool:
        try:
            await asyncio.wait_for(ws.send_json(message), timeout=SEND_TIMEOUT_S)
            return True
        except Exception as exc:  # noqa: BLE001 - closed socket, timeout, ...
            logger.warning("Dropping WebSocket client after failed send: %r", exc)
            self.disconnect(ws)
            return False

    async def broadcast(self, message: dict) -> None:
        """Send to every client concurrently. Never raises; with no clients it is a no-op."""
        clients = list(self._clients)
        if clients:
            await asyncio.gather(*(self.send(ws, message) for ws in clients))


manager = ConnectionManager()
