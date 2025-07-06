import threading
import time
from .monitor import get_services, check_service_status
from .ai_fix import ai_fix_service
from .logger import log_event
from .config import MONITOR_INTERVAL

def monitor_and_fix():
    while True:
        services = get_services()
        for service in services:
            status = check_service_status(service)
            if status not in ("active", "running"):
                log_event(f"Service {service} is not running. Status: {status}. Attempting AI fix.")
                ai_fix_service(service, f"Status: {status}")
        time.sleep(MONITOR_INTERVAL)

def start_background_monitor():
    t = threading.Thread(target=monitor_and_fix, daemon=True)
    t.start() 