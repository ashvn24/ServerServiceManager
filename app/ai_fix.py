import google.generativeai as genai
from .config import GEMINI_API_KEY
from .logger import log_event
from .error_learner import ErrorLearner
import subprocess
import platform

genai.configure(api_key=GEMINI_API_KEY)
error_learner = ErrorLearner()

def ai_fix_service(service_name, error_message):
    # First, check if we have a known fix for this error
    known_fix = error_learner.find_known_fix(service_name, error_message)
    if known_fix:
        log_event(f"Using known fix for {service_name}: {known_fix}")
        result = subprocess.run(known_fix, shell=True, capture_output=True, text=True)
        log_event(f"Executed known fix for {service_name}: {result.stdout} {result.stderr}")
        
        # Update success count for this known fix
        error_pattern = error_learner._extract_error_pattern(error_message)
        error_learner.update_success_count(error_pattern)
        
        return known_fix, result.stdout, result.stderr
    
    # If no known fix, use Gemini
    prompt = f"Service '{service_name}' has failed with error: {error_message}. Suggest a shell command to fix and restart the service on {platform.system()}. Only output the command, nothing else."
    try:
        model = genai.GenerativeModel('gemini-1.5-pro')
        response = model.generate_content(prompt)
        content = response.text if hasattr(response, 'text') else None
        if not content:
            log_event(f"Gemini fix failed for {service_name}: No response content")
            return None, None, "No response content"
        command = content.strip()
        log_event(f"Gemini suggested fix for {service_name}: {command}")
        # Execute the command
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        log_event(f"Executed fix for {service_name}: {result.stdout} {result.stderr}")
        # Learn from this attempt
        success = result.returncode == 0
        error_learner.learn_fix(service_name, error_message, command, success, result.stdout, result.stderr)
        return command, result.stdout, result.stderr
    except Exception as e:
        log_event(f"Gemini fix failed for {service_name}: {e}")
        return None, None, str(e)

def get_learning_stats():
    """Get and display learning statistics"""
    stats = error_learner.get_learning_stats()
    print(f"Learning System Statistics:")
    print(f"  Successful fixes learned: {stats['successful_fixes']}")
    print(f"  Failed patterns tracked: {stats['failed_patterns']}")
    print(f"  Total failed attempts: {stats['total_failed_attempts']}")
    
    # Show some examples of learned fixes
    if error_learner.error_patterns["successful_fixes"]:
        print(f"\nLearned Fixes:")
        for pattern, fix_info in list(error_learner.error_patterns["successful_fixes"].items())[:5]:
            print(f"  Service: {fix_info['service']}")
            print(f"  Command: {fix_info['command']}")
            print(f"  Success count: {fix_info['success_count']}")
            print(f"  Last used: {fix_info['last_used']}")
            print()
    
    return stats 