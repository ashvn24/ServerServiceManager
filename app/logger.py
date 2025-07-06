import logging
from pathlib import Path

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