from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .logger import get_logs
from .auto_monitor import start_background_monitor
from .websocket_server import websocket_app

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

@app.on_event("startup")
def startup_event():
    start_background_monitor()

# Mount the WebSocket app
app.mount("/ws", websocket_app) 