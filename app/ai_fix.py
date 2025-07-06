import openai
from .config import OPENAI_API_KEY
from .logger import log_event
import subprocess
import platform

openai.api_key = OPENAI_API_KEY

def ai_fix_service(service_name, error_message):
    prompt = f"Service '{service_name}' has failed with error: {error_message}. Suggest a shell command to fix and restart the service on {platform.system()}. Only output the command, nothing else."
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that provides shell commands to fix service issues. Only respond with the command, no explanations."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0.2
        )
        command = response.choices[0].message.content.strip()
        log_event(f"AI suggested fix for {service_name}: {command}")
        # Execute the command
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        log_event(f"Executed fix for {service_name}: {result.stdout} {result.stderr}")
        return command, result.stdout, result.stderr
    except Exception as e:
        log_event(f"AI fix failed for {service_name}: {e}")
        return None, None, str(e) 