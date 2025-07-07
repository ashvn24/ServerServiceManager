import asyncio
import json
import time
import threading
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict
import psutil
import platform
import subprocess
from .monitor import get_services, check_service_status
from .logger import log_event

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.selected_services: Dict[WebSocket, List[str]] = {}  # Track selected services per connection

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.selected_services[websocket] = None  # None means all services by default

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        if websocket in self.selected_services:
            del self.selected_services[websocket]

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                self.active_connections.remove(connection)
                if connection in self.selected_services:
                    del self.selected_services[connection]

    def set_selected_services(self, websocket: WebSocket, services: List[str]):
        self.selected_services[websocket] = services

    def get_selected_services(self, websocket: WebSocket):
        return self.selected_services.get(websocket, None)

manager = ConnectionManager()

def get_service_stats(service_name: str) -> Dict:
    """Get detailed statistics for a specific service"""
    stats = {
        "name": service_name,
        "status": check_service_status(service_name),
        "timestamp": time.time()
    }
    
    # Get system stats
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        stats.update({
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": disk.percent,
                "memory_used": memory.used,
                "memory_total": memory.total,
                "disk_used": disk.used,
                "disk_total": disk.total
            }
        })
    except Exception as e:
        log_event(f"Error getting system stats: {e}")
    
    return stats

def get_services_stats_for(websocket: WebSocket) -> List[Dict]:
    selected = manager.get_selected_services(websocket)
    all_services = get_services()
    if selected is None:
        services = all_services
    else:
        # Only include valid services
        services = [s for s in selected if s in all_services]
    return [get_service_stats(service) for service in services]

async def monitor_services_websocket():
    """Background task to monitor services and broadcast updates"""
    while True:
        try:
            for connection in list(manager.active_connections):
                services_stats = get_services_stats_for(connection)
                message = {
                    "type": "services_update",
                    "data": services_stats,
                    "timestamp": time.time()
                }
                await manager.send_personal_message(json.dumps(message), connection)
                # Check for any services that are down
                for service in services_stats:
                    if service["status"] not in ("active", "running"):
                        alert_message = {
                            "type": "service_alert",
                            "data": {
                                "service": service["name"],
                                "status": service["status"],
                                "message": f"Service {service['name']} is not running. Status: {service['status']}"
                            },
                            "timestamp": time.time()
                        }
                        await manager.send_personal_message(json.dumps(alert_message), connection)
                        log_event(f"Service {service['name']} is not running. Status: {service['status']}")
            await asyncio.sleep(5)
        except Exception as e:
            log_event(f"Error in WebSocket monitoring: {e}")
            await asyncio.sleep(5)

# Create FastAPI app for WebSocket
websocket_app = FastAPI(title="Service Monitor WebSocket")

# Add CORS middleware
websocket_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your React app URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@websocket_app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send initial services data (all services by default)
        services_stats = get_services_stats_for(websocket)
        initial_message = {
            "type": "initial_data",
            "data": services_stats,
            "timestamp": time.time()
        }
        await manager.send_personal_message(json.dumps(initial_message), websocket)
        # Listen for service selection messages
        while True:
            msg = await websocket.receive_text()
            try:
                data = json.loads(msg)
                if data.get("type") == "select_services":
                    # Update selected services for this connection
                    services = data.get("services", None)
                    if isinstance(services, list):
                        manager.set_selected_services(websocket, services)
                    else:
                        manager.set_selected_services(websocket, None)  # None means all
            except Exception as e:
                log_event(f"Error handling WebSocket message: {e}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@websocket_app.on_event("startup")
async def startup_event():
    # Start the background monitoring task
    asyncio.create_task(monitor_services_websocket()) 