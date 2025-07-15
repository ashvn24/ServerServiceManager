import redis
import json
import time
from app.ai_fix import ai_fix_service

def process_job(job):
    service_name = job["service_name"]
    error_message = job["error_message"]
    print(f"Processing restart for {service_name} due to: {error_message}")
    ai_fix_service(service_name, error_message)

if __name__ == "__main__":
    redis_client = redis.Redis(host='localhost', port=6379, db=0)
    print("Service restart worker started. Waiting for jobs...")
    while True:
        msg = redis_client.blpop("service_restart_queue", timeout=5)
        if msg:
            _, data = msg
            job = json.loads(data)
            process_job(job)
        else:
            time.sleep(1) 