#!/usr/bin/env python3
"""
CLI tool for managing the ML error model
"""

import argparse
import json
from ml_error_model import MLErrorModel
from smart_ai_fix import smart_fix

def view_ml_stats():
    """Display ML model statistics"""
    stats = smart_fix.get_performance_stats()
    
    print("=== ML Model Performance Statistics ===")
    print(f"Total fix attempts: {stats['total_attempts']}")
    print(f"ML predictions: {stats['ml_predictions']}")
    print(f"AI calls: {stats['ai_calls']}")
    print(f"Successful fixes: {stats['successful_fixes']}")
    print(f"Failed fixes: {stats['failed_fixes']}")
    print(f"Overall success rate: {stats['overall_success_rate']:.2%}")
    print(f"ML accuracy: {stats['ml_accuracy']:.2%}")
    
    ml_stats = stats['ml_model_stats']
    print(f"\nML Model Details:")
    print(f"  Total errors in training data: {ml_stats['total_errors']}")
    print(f"  Successful fixes learned: {ml_stats['successful_fixes']}")
    print(f"  Success rate: {ml_stats['success_rate']:.2%}")
    print(f"  Estimated model accuracy: {ml_stats['model_accuracy']:.2%}")

def view_service_recommendations(service_name):
    """Display fix recommendations for a service"""
    recommendations = smart_fix.get_recommendations(service_name)
    
    if not recommendations:
        print(f"No recommendations available for {service_name}")
        return
    
    print(f"=== Fix Recommendations for {service_name} ===")
    for i, rec in enumerate(recommendations, 1):
        print(f"\n{i}. Command: {rec['command']}")
        print(f"   Success count: {rec['success_count']}")
        print(f"   Confidence: {rec['confidence']:.2%}")
        print(f"   Last used: {rec['last_used']}")

def retrain_model():
    """Manually trigger model retraining"""
    ml_model = MLErrorModel()
    ml_model._retrain_models()
    print("ML model retraining completed")

def export_model_data(filename):
    """Export model data to JSON"""
    ml_model = MLErrorModel()
    stats = smart_fix.get_performance_stats()
    
    export_data = {
        'performance_stats': stats,
        'ml_model_data': {
            'error_data_count': len(ml_model.error_data),
            'service_patterns': ml_model.service_patterns
        }
    }
    
    with open(filename, 'w') as f:
        json.dump(export_data, f, indent=2)
    
    print(f"Model data exported to {filename}")

def view_training_data():
    """Display training data statistics"""
    ml_model = MLErrorModel()
    
    print("=== Training Data Statistics ===")
    print(f"Total error entries: {len(ml_model.error_data)}")
    
    if ml_model.error_data:
        services = {}
        success_count = 0
        
        for entry in ml_model.error_data:
            service = entry['service']
            if service not in services:
                services[service] = {'total': 0, 'success': 0}
            
            services[service]['total'] += 1
            if entry['success']:
                services[service]['success'] += 1
                success_count += 1
        
        print(f"Successful fixes: {success_count}")
        print(f"Overall success rate: {success_count/len(ml_model.error_data):.2%}")
        
        print(f"\nService breakdown:")
        for service, stats in services.items():
            success_rate = stats['success'] / stats['total']
            print(f"  {service}: {stats['total']} errors, {stats['success']} fixes ({success_rate:.2%})")

def optimize_model():
    """Run model optimization"""
    smart_fix.auto_optimize()
    print("Model optimization completed")

def main():
    parser = argparse.ArgumentParser(description="ML Error Model CLI")
    parser.add_argument("command", 
                       choices=["stats", "recommendations", "retrain", "export", "data", "optimize"],
                       help="Command to execute")
    parser.add_argument("--service", "-s", help="Service name for recommendations")
    parser.add_argument("--output", "-o", help="Output file for export command")
    
    args = parser.parse_args()
    
    if args.command == "stats":
        view_ml_stats()
    elif args.command == "recommendations":
        if not args.service:
            print("Please specify a service name with --service")
            return
        view_service_recommendations(args.service)
    elif args.command == "retrain":
        retrain_model()
    elif args.command == "export":
        filename = args.output or "ml_model_export.json"
        export_model_data(filename)
    elif args.command == "data":
        view_training_data()
    elif args.command == "optimize":
        optimize_model()

if __name__ == "__main__":
    main() 