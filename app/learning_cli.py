#!/usr/bin/env python3
"""
CLI tool for managing the error learning system
"""

import json
import argparse
from error_learner import ErrorLearner

def view_stats():
    """Display learning statistics"""
    learner = ErrorLearner()
    stats = learner.get_learning_stats()
    
    print("=== Error Learning System Statistics ===")
    print(f"Successful fixes learned: {stats['successful_fixes']}")
    print(f"Failed patterns tracked: {stats['failed_patterns']}")
    print(f"Total failed attempts: {stats['total_failed_attempts']}")

def view_fixes():
    """Display all learned fixes"""
    learner = ErrorLearner()
    
    if not learner.error_patterns["successful_fixes"]:
        print("No successful fixes learned yet.")
        return
    
    print("=== Learned Fixes ===")
    for i, (pattern, fix_info) in enumerate(learner.error_patterns["successful_fixes"].items(), 1):
        print(f"\n{i}. Service: {fix_info['service']}")
        print(f"   Pattern: {pattern[:100]}...")
        print(f"   Command: {fix_info['command']}")
        print(f"   Success count: {fix_info['success_count']}")
        print(f"   First seen: {fix_info['first_seen']}")
        print(f"   Last used: {fix_info['last_used']}")

def view_failures():
    """Display failed attempts"""
    learner = ErrorLearner()
    
    if not learner.error_patterns["patterns"]:
        print("No failed patterns tracked yet.")
        return
    
    print("=== Failed Patterns ===")
    for i, (pattern, pattern_info) in enumerate(learner.error_patterns["patterns"].items(), 1):
        print(f"\n{i}. Service: {pattern_info['service']}")
        print(f"   Pattern: {pattern[:100]}...")
        print(f"   Failed attempts: {len(pattern_info['failed_attempts'])}")
        print(f"   First seen: {pattern_info['first_seen']}")
        
        for j, attempt in enumerate(pattern_info['failed_attempts'][-3:], 1):  # Show last 3 attempts
            print(f"     {j}. Command: {attempt['command']}")
            print(f"        Error: {attempt['stderr'][:50]}...")

def clear_knowledge():
    """Clear all learned knowledge"""
    learner = ErrorLearner()
    learner.error_patterns = {"patterns": {}, "successful_fixes": {}}
    learner._save_knowledge()
    print("All learned knowledge has been cleared.")

def export_knowledge(filename):
    """Export knowledge to JSON file"""
    learner = ErrorLearner()
    with open(filename, 'w') as f:
        json.dump(learner.error_patterns, f, indent=2)
    print(f"Knowledge exported to {filename}")

def main():
    parser = argparse.ArgumentParser(description="Error Learning System CLI")
    parser.add_argument("command", choices=["stats", "fixes", "failures", "clear", "export"],
                       help="Command to execute")
    parser.add_argument("--output", "-o", help="Output file for export command")
    
    args = parser.parse_args()
    
    if args.command == "stats":
        view_stats()
    elif args.command == "fixes":
        view_fixes()
    elif args.command == "failures":
        view_failures()
    elif args.command == "clear":
        clear_knowledge()
    elif args.command == "export":
        filename = args.output or "error_knowledge_export.json"
        export_knowledge(filename)

if __name__ == "__main__":
    main() 