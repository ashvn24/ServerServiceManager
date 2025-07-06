from fastapi import FastAPI
from .logger import get_logs
from .auto_monitor import start_background_monitor

app = FastAPI(title="AI Service Monitor")

@app.get("/")
def root():
    return {"message": "AI Service Monitor is running."}

@app.get("/logs")
def read_logs():
    return {"logs": get_logs()}

@app.on_event("startup")
def startup_event():
    start_background_monitor() 