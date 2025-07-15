from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .logger import get_logs, get_logs_by_service
from .auto_monitor import start_background_monitor
from .websocket_server import websocket_app, GLOBAL_MONITORED_SERVICES
from .monitor import get_services, check_service_status
import psutil
import time

app = FastAPI(title="AI Service Monitor")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your React app URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "AI Service Monitor is running."}

@app.get("/logs")
def read_logs():
    return {"logs": get_logs()}

@app.get("/logs/{service_name}")
def read_logs_by_service(service_name: str):
    return {"logs": get_logs_by_service(service_name)}

@app.get("/services")
def get_all_services():
    services = get_services()
    service_statuses = []
    
    for service in services:
        status = check_service_status(service)
        service_statuses.append({
            "name": service,
            "status": status,
            "timestamp": time.time()
        })
    
    return {"services": service_statuses}

@app.get("/system/metrics")
def get_system_metrics():
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "disk_percent": disk.percent,
            "memory_used": memory.used,
            "memory_total": memory.total,
            "disk_used": disk.used,
            "disk_total": disk.total,
            "timestamp": time.time()
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": time.time()}

@app.get("/monitored_services")
def get_monitored_services():
    return {"monitored_services": GLOBAL_MONITORED_SERVICES}

@app.on_event("startup")
def startup_event():
    # In the future, you can pass a list of selected services to monitor only those
    start_background_monitor()  # Currently monitors all services

# Mount the WebSocket app
app.mount("/ws", websocket_app) 