from fastapi import WebSocket
from typing import Dict, Set
import asyncio

class WebSocketHub:
    def __init__(self):
        self.visitor_connections: Dict[str, WebSocket] = {}
        self.admin_connections: Set[WebSocket] = set()
        
    async def connect_visitor(self, token: str, ws: WebSocket):
        await ws.accept()
        self.visitor_connections[token] = ws
        
    def disconnect_visitor(self, token: str):
        if token in self.visitor_connections:
            del self.visitor_connections[token]
            
    async def send_to_visitor(self, token: str, data: dict):
        if token in self.visitor_connections:
            try:
                await self.visitor_connections[token].send_json(data)
            except Exception:
                self.disconnect_visitor(token)

    async def connect_admin(self, ws: WebSocket):
        await ws.accept()
        self.admin_connections.add(ws)
        
    def disconnect_admin(self, ws: WebSocket):
        if ws in self.admin_connections:
            self.admin_connections.remove(ws)
            
    async def broadcast_admin(self, data: dict):
        tasks = []
        to_remove = []
        for ws in self.admin_connections:
            try:
                tasks.append(ws.send_json(data))
            except Exception:
                to_remove.append(ws)
                
        for ws in to_remove:
            self.disconnect_admin(ws)
            
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

hub = WebSocketHub()
