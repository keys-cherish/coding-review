"""
WebSocket 连接管理与扫描进度广播服务。

使用 asyncio Queue 解耦扫描业务和 WebSocket 推送，避免阻塞。
"""
from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

from fastapi import WebSocket

from backend.utils import logger


class ConnectionManager:
    """WebSocket 连接管理器（按 scan_id 分组）。"""

    def __init__(self) -> None:
        self._conns: dict[int, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, scan_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._conns[scan_id].add(websocket)

    async def disconnect(self, scan_id: int, websocket: WebSocket) -> None:
        async with self._lock:
            self._conns[scan_id].discard(websocket)
            if not self._conns[scan_id]:
                self._conns.pop(scan_id, None)

    async def broadcast(self, scan_id: int, payload: dict[str, Any]) -> None:
        async with self._lock:
            targets = list(self._conns.get(scan_id, set()))
        for ws in targets:
            try:
                await ws.send_json(payload)
            except Exception as e:
                logger.warning(f"WebSocket 推送失败: {e}")


manager = ConnectionManager()
