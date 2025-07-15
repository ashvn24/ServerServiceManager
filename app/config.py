import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
MONITOR_INTERVAL = int(os.getenv("MONITOR_INTERVAL", 60))  # seconds 