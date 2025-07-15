from google import genai
from .config import GEMINI_API_KEY
from .logger import log_event
from .ml_error_model import MLErrorModel
from .error_learner import ErrorLearner
import subprocess
import platform
import time
from typing import Dict, Optional, Tuple, List
import multiprocessing

client = genai.Client(api_key=GEMINI_API_KEY)
ml_model = MLErrorModel()
error_learner = ErrorLearner()

def gemini_generate_content(prompt, queue):
    try:
        from google import genai
        client = genai.Client()
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        content = response.text if hasattr(response, 'text') else None
        queue.put(content)
    except Exception as e:
        queue.put(None)

class SmartAIFix:
    def __init__(self):
        self.fix_history = []
        self.performance_metrics = {
            'ml_predictions': 0,
            'ai_calls': 0,
            'successful_fixes': 0,
            'failed_fixes': 0
        }
    
    def fix_service(self, service_name: str, error_message: str) -> Tuple[Optional[str], str, str]:
        """
        Smart service fixing with ML prediction and AI fallback
        """
        start_time = time.time()
        
        # Step 1: Try ML prediction first
        ml_prediction = ml_model.predict_fix(service_name, error_message)
        
        if ml_prediction and ml_prediction['confidence'] > 0.8:
            log_event(f"Using ML prediction for {service_name} (confidence: {ml_prediction['confidence']:.2f})")
            self.performance_metrics['ml_predictions'] += 1
            
            command = ml_prediction['command']
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            success = result.returncode == 0
            
            # Learn from this attempt
            ml_model.learn_from_attempt(service_name, error_message, command, success, result.stdout, result.stderr)
            error_learner.learn_fix(service_name, error_message, command, success, result.stdout, result.stderr)
            
            if success:
                self.performance_metrics['successful_fixes'] += 1
            else:
                self.performance_metrics['failed_fixes'] += 1
            
            execution_time = time.time() - start_time
            self._record_fix_attempt(service_name, error_message, command, success, execution_time, 'ml_prediction')
            
            return command, result.stdout, result.stderr
        
        # Step 2: Try error learner (simple pattern matching)
        known_fix = error_learner.find_known_fix(service_name, error_message)
        
        if known_fix:
            log_event(f"Using known fix for {service_name}")
            result = subprocess.run(known_fix, shell=True, capture_output=True, text=True)
            success = result.returncode == 0
            
            # Learn from this attempt
            ml_model.learn_from_attempt(service_name, error_message, known_fix, success, result.stdout, result.stderr)
            error_learner.learn_fix(service_name, error_message, known_fix, success, result.stdout, result.stderr)
            
            if success:
                self.performance_metrics['successful_fixes'] += 1
            else:
                self.performance_metrics['failed_fixes'] += 1
            
            execution_time = time.time() - start_time
            self._record_fix_attempt(service_name, error_message, known_fix, success, execution_time, 'known_fix')
            
            return known_fix, result.stdout, result.stderr
        
        # Step 3: Use AI as fallback
        log_event(f"Using AI fallback for {service_name}")
        self.performance_metrics['ai_calls'] += 1
        
        ai_result = self._call_ai_for_fix(service_name, error_message)
        
        if ai_result:
            command, stdout, stderr = ai_result
            success = subprocess.run(command, shell=True, capture_output=True, text=True).returncode == 0
            
            # Learn from AI attempt
            ml_model.learn_from_attempt(service_name, error_message, command, success, stdout, stderr)
            error_learner.learn_fix(service_name, error_message, command, success, stdout, stderr)
            
            if success:
                self.performance_metrics['successful_fixes'] += 1
            else:
                self.performance_metrics['failed_fixes'] += 1
            
            execution_time = time.time() - start_time
            self._record_fix_attempt(service_name, error_message, command, success, execution_time, 'ai_fallback')
            
            return command, stdout, stderr
        
        return None, "", "Failed to generate fix"
    
    def _call_ai_for_fix(self, service_name: str, error_message: str) -> Optional[Tuple[str, str, str]]:
        """Call Gemini to generate a fix in a subprocess"""
        prompt = f"""
Service '{service_name}' has failed with error: {error_message}

Based on the error message, suggest a shell command to fix and restart the service on {platform.system()}.
Consider common service issues like:
- Permission problems
- Port conflicts
- Configuration errors
- Resource issues
- Dependency problems

Only output the command, nothing else.
"""
        queue = multiprocessing.Queue()
        p = multiprocessing.Process(target=gemini_generate_content, args=(prompt, queue))
        p.start()
        p.join(timeout=30)  # 30 seconds timeout
        if p.is_alive():
            p.terminate()
            log_event(f"Gemini fix timed out for {service_name}")
            return None
        content = queue.get() if not queue.empty() else None
        if not content:
            log_event(f"Gemini fix failed for {service_name}: No response content")
            return None
        command = content.strip()
        log_event(f"Gemini suggested fix for {service_name}: {command}")
        return command, "", ""
    
    def _record_fix_attempt(self, service_name: str, error_message: str, command: str, 
                           success: bool, execution_time: float, method: str):
        """Record fix attempt for analysis"""
        self.fix_history.append({
            'service': service_name,
            'error': error_message,
            'command': command,
            'success': success,
            'execution_time': execution_time,
            'method': method,
            'timestamp': time.time()
        })
    
    def get_performance_stats(self) -> Dict:
        """Get performance statistics"""
        total_attempts = self.performance_metrics['ml_predictions'] + self.performance_metrics['ai_calls']
        success_rate = self.performance_metrics['successful_fixes'] / total_attempts if total_attempts > 0 else 0
        
        ml_accuracy = 0
        if self.performance_metrics['ml_predictions'] > 0:
            ml_successes = sum(1 for attempt in self.fix_history 
                             if attempt['method'] == 'ml_prediction' and attempt['success'])
            ml_accuracy = ml_successes / self.performance_metrics['ml_predictions']
        
        return {
            'total_attempts': total_attempts,
            'ml_predictions': self.performance_metrics['ml_predictions'],
            'ai_calls': self.performance_metrics['ai_calls'],
            'successful_fixes': self.performance_metrics['successful_fixes'],
            'failed_fixes': self.performance_metrics['failed_fixes'],
            'overall_success_rate': success_rate,
            'ml_accuracy': ml_accuracy,
            'ml_model_stats': ml_model.get_model_stats()
        }
    
    def get_recommendations(self, service_name: str) -> List[Dict]:
        """Get fix recommendations for a service"""
        return ml_model.get_recommendations(service_name)
    
    def auto_optimize(self):
        """Automatically optimize the ML model based on performance"""
        stats = self.get_performance_stats()
        
        if stats['ml_accuracy'] < 0.7 and stats['ml_predictions'] > 10:
            log_event("ML model accuracy below 70%, triggering retraining")
            ml_model._retrain_models()
        
        # Clean up old history (keep last 1000 entries)
        if len(self.fix_history) > 1000:
            self.fix_history = self.fix_history[-1000:]

# Global instance
smart_fix = SmartAIFix()

def smart_ai_fix_service(service_name: str, error_message: str) -> Tuple[Optional[str], str, str]:
    """Main function for smart AI fix service"""
    return smart_fix.fix_service(service_name, error_message) 