import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from .logger import log_event

class ErrorLearner:
    def __init__(self, knowledge_file: str = "error_knowledge.json"):
        self.knowledge_file = knowledge_file
        self.error_patterns = self._load_knowledge()
    
    def _load_knowledge(self) -> Dict:
        """Load existing error knowledge from file"""
        if os.path.exists(self.knowledge_file):
            try:
                with open(self.knowledge_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                log_event("Failed to load error knowledge, starting fresh")
        return {"patterns": {}, "successful_fixes": {}}
    
    def _save_knowledge(self):
        """Save error knowledge to file"""
        try:
            with open(self.knowledge_file, 'w') as f:
                json.dump(self.error_patterns, f, indent=2)
        except Exception as e:
            log_event(f"Failed to save error knowledge: {e}")
    
    def _extract_error_pattern(self, error_message: str) -> str:
        """Extract a normalized pattern from error message"""
        # Remove variable parts like timestamps, file paths, etc.
        pattern = error_message.lower()
        
        # Remove common variable parts
        pattern = re.sub(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', '[TIMESTAMP]', pattern)
        pattern = re.sub(r'/[\w/.-]+', '[PATH]', pattern)
        pattern = re.sub(r'\d+', '[NUMBER]', pattern)
        pattern = re.sub(r'[a-f0-9]{8,}', '[HASH]', pattern)
        
        # Remove extra whitespace
        pattern = re.sub(r'\s+', ' ', pattern).strip()
        
        return pattern
    
    def find_known_fix(self, service_name: str, error_message: str) -> Optional[str]:
        """Find a known fix for the error pattern"""
        error_pattern = self._extract_error_pattern(error_message)
        
        # Check if we have a successful fix for this pattern
        if error_pattern in self.error_patterns["successful_fixes"]:
            fix_info = self.error_patterns["successful_fixes"][error_pattern]
            log_event(f"Found known fix for {service_name}: {fix_info['command']}")
            return fix_info["command"]
        
        # Check for similar patterns (fuzzy matching)
        for pattern, fix_info in self.error_patterns["successful_fixes"].items():
            similarity = self._calculate_similarity(error_pattern, pattern)
            if similarity > 0.8:  # 80% similarity threshold
                log_event(f"Found similar fix for {service_name}: {fix_info['command']}")
                return fix_info["command"]
        
        return None
    
    def _calculate_similarity(self, pattern1: str, pattern2: str) -> float:
        """Calculate similarity between two error patterns"""
        words1 = set(pattern1.split())
        words2 = set(pattern2.split())
        
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    def learn_fix(self, service_name: str, error_message: str, command: str, 
                  success: bool, stdout: str = "", stderr: str = ""):
        """Learn from a fix attempt"""
        error_pattern = self._extract_error_pattern(error_message)
        
        if success:
            # Store successful fix
            self.error_patterns["successful_fixes"][error_pattern] = {
                "command": command,
                "service": service_name,
                "first_seen": datetime.now().isoformat(),
                "last_used": datetime.now().isoformat(),
                "success_count": 1,
                "stdout": stdout,
                "stderr": stderr
            }
            log_event(f"Learned successful fix for {service_name}: {command}")
        else:
            # Track failed attempts
            if error_pattern not in self.error_patterns["patterns"]:
                self.error_patterns["patterns"][error_pattern] = {
                    "failed_attempts": [],
                    "service": service_name,
                    "first_seen": datetime.now().isoformat()
                }
            
            self.error_patterns["patterns"][error_pattern]["failed_attempts"].append({
                "command": command,
                "timestamp": datetime.now().isoformat(),
                "stdout": stdout,
                "stderr": stderr
            })
            log_event(f"Tracked failed fix attempt for {service_name}: {command}")
        
        self._save_knowledge()
    
    def update_success_count(self, error_pattern: str):
        """Update success count for a known fix"""
        if error_pattern in self.error_patterns["successful_fixes"]:
            fix_info = self.error_patterns["successful_fixes"][error_pattern]
            fix_info["success_count"] += 1
            fix_info["last_used"] = datetime.now().isoformat()
            self._save_knowledge()
    
    def get_learning_stats(self) -> Dict:
        """Get statistics about the learning system"""
        successful_count = len(self.error_patterns["successful_fixes"])
        failed_patterns = len(self.error_patterns["patterns"])
        total_failed_attempts = sum(
            len(pattern["failed_attempts"]) 
            for pattern in self.error_patterns["patterns"].values()
        )
        
        return {
            "successful_fixes": successful_count,
            "failed_patterns": failed_patterns,
            "total_failed_attempts": total_failed_attempts
        } 