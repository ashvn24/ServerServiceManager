import platform
import subprocess
import psutil
from .logger import log_event


def get_services():
    system = platform.system()
    services = []
    if system == "Linux":
        try:
            result = subprocess.run([
                "systemctl", "list-units", "--type=service", "--all", "--no-pager", "--no-legend"
            ], capture_output=True, text=True)
            for line in result.stdout.splitlines():
                parts = line.split()
                if parts:
                    services.append(parts[0])
                    print(services)
        except Exception as e:
            log_event(f"Error listing Linux services: {e}")
    elif system == "Windows":
        try:
            for service in psutil.win_service_iter():
                services.append(service.name())
        except Exception as e:
            log_event(f"Error listing Windows services: {e}")
    return services


def check_service_status(service_name):
    system = platform.system()
    if system == "Linux":
        try:
            result = subprocess.run([
                "systemctl", "is-active", service_name
            ], capture_output=True, text=True)
            return result.stdout.strip()
        except Exception as e:
            log_event(f"Error checking status for {service_name}: {e}")
            return "unknown"
    elif system == "Windows":
        try:
            service = psutil.win_service_get(service_name)
            return service.status()
        except Exception as e:
            log_event(f"Error checking status for {service_name}: {e}")
            return "unknown"
    return "unsupported"


def monitor_services():
    services = get_services()
    for service in services:
        status = check_service_status(service)
        if status not in ("active", "running"):
            log_event(f"Service {service} is not running. Status: {status}") 