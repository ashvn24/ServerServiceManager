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

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove disconnected clients
                self.active_connections.remove(connection)

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

def get_all_services_stats() -> List[Dict]:
    """Get statistics for all monitored services"""
    services = get_services()
    return [get_service_stats(service) for service in services]

async def monitor_services_websocket():
    """Background task to monitor services and broadcast updates"""
    while True:
        try:
            services_stats = get_all_services_stats()
            message = {
                "type": "services_update",
                "data": services_stats,
                "timestamp": time.time()
            }
            await manager.broadcast(json.dumps(message))
            
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
                    await manager.broadcast(json.dumps(alert_message))
                    log_event(f"Service {service['name']} is not running. Status: {service['status']}")
            
            await asyncio.sleep(5)  # Update every 5 seconds
            
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
        # Send initial services data
        services_stats = get_all_services_stats()
        initial_message = {
            "type": "initial_data",
            "data": services_stats,
            "timestamp": time.time()
        }
        await manager.send_personal_message(json.dumps(initial_message), websocket)
        
        # Keep connection alive
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@websocket_app.on_event("startup")
async def startup_event():
    # Start the background monitoring task
    asyncio.create_task(monitor_services_websocket()) 