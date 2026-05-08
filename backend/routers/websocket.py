"""
WebSocket 路由：扫描进度实时推送。
"""
from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.services.ws_manager import manager

router = APIRouter()


@router.websocket("/ws/scans/{scan_id}")
async def websocket_scan_progress(websocket: WebSocket, scan_id: int) -> None:
    """前端订阅某次扫描的进度推送。"""
    await manager.connect(scan_id, websocket)
    try:
        while True:
            # 不期望客户端发送消息，仅保持连接
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(scan_id, websocket)
