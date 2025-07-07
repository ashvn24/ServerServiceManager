import logging
from pathlib import Path
import re

LOG_FILE = Path(__file__).parent / "service_monitor.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def log_event(message: str):
    logging.info(message)

def get_logs():
    if LOG_FILE.exists():
        with open(LOG_FILE, "r") as f:
            return f.readlines()[-100:]  # Return last 100 lines
    return []

def get_logs_by_service(service_name: str):
    """Get logs filtered by service name"""
    if LOG_FILE.exists():
        with open(LOG_FILE, "r") as f:
            all_logs = f.readlines()
            # Filter logs that contain the service name
            filtered_logs = [log for log in all_logs if service_name.lower() in log.lower()]
            return filtered_logs[-50:]  # Return last 50 filtered lines
    return []

def get_logs_by_level(level: str):
    """Get logs filtered by log level"""
    if LOG_FILE.exists():
        with open(LOG_FILE, "r") as f:
            all_logs = f.readlines()
            # Filter logs by level
            filtered_logs = [log for log in all_logs if level.upper() in log.upper()]
            return filtered_logs[-50:]  # Return last 50 filtered lines
    return []

def get_recent_logs(count: int = 100):
    """Get the most recent logs with specified count"""
    if LOG_FILE.exists():
        with open(LOG_FILE, "r") as f:
            all_logs = f.readlines()
            return all_logs[-count:]
    return [] 