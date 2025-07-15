import threading
import time
from .monitor import get_services, check_service_status
from .ai_fix import queue_service_restart
from .logger import log_event
from .config import MONITOR_INTERVAL

def monitor_and_fix(selected_services=None):
    while True:
        services = selected_services if selected_services is not None else get_services()
        for service in services:
            status = check_service_status(service)
            if status not in ("active", "running"):
                log_event(f"Service {service} is not running. Status: {status}. Queuing AI fix.")
                queue_service_restart(service, f"Status: {status}")
        time.sleep(MONITOR_INTERVAL)

def start_background_monitor(selected_services=None):
    t = threading.Thread(target=monitor_and_fix, args=(selected_services,), daemon=True)
    t.start() 