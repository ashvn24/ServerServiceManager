import json
import os
import re
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
import pickle
import hashlib
from .logger import log_event

class MLErrorModel:
    def __init__(self, model_dir: str = "ml_models"):
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)
        
        # Initialize ML components
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            ngram_range=(1, 3),
            stop_words='english',
            min_df=2
        )
        self.classifier = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        self.label_encoder = LabelEncoder()
        
        # Data storage
        self.error_data = []
        self.fix_data = []
        self.service_patterns = {}
        
        # Load existing models
        self._load_models()
    
    def _load_models(self):
        """Load trained models if they exist"""
        try:
            if os.path.exists(f"{self.model_dir}/vectorizer.pkl"):
                with open(f"{self.model_dir}/vectorizer.pkl", 'rb') as f:
                    self.vectorizer = pickle.load(f)
            
            if os.path.exists(f"{self.model_dir}/classifier.pkl"):
                with open(f"{self.model_dir}/classifier.pkl", 'rb') as f:
                    self.classifier = pickle.load(f)
            
            if os.path.exists(f"{self.model_dir}/label_encoder.pkl"):
                with open(f"{self.model_dir}/label_encoder.pkl", 'rb') as f:
                    self.label_encoder = pickle.load(f)
            
            if os.path.exists(f"{self.model_dir}/data.json"):
                with open(f"{self.model_dir}/data.json", 'r') as f:
                    data = json.load(f)
                    self.error_data = data.get('error_data', [])
                    self.fix_data = data.get('fix_data', [])
                    self.service_patterns = data.get('service_patterns', {})
            
            log_event("ML models loaded successfully")
        except Exception as e:
            log_event(f"Failed to load ML models: {e}")
    
    def _save_models(self):
        """Save trained models"""
        try:
            with open(f"{self.model_dir}/vectorizer.pkl", 'wb') as f:
                pickle.dump(self.vectorizer, f)
            
            with open(f"{self.model_dir}/classifier.pkl", 'wb') as f:
                pickle.dump(self.classifier, f)
            
            with open(f"{self.model_dir}/label_encoder.pkl", 'wb') as f:
                pickle.dump(self.label_encoder, f)
            
            with open(f"{self.model_dir}/data.json", 'w') as f:
                json.dump({
                    'error_data': self.error_data,
                    'fix_data': self.fix_data,
                    'service_patterns': self.service_patterns
                }, f, indent=2)
            
            log_event("ML models saved successfully")
        except Exception as e:
            log_event(f"Failed to save ML models: {e}")
    
    def _extract_features(self, error_message: str, service_name: str) -> Dict[str, Any]:
        """Extract comprehensive features from error message"""
        features = {
            'error_length': len(error_message),
            'service_name': service_name,
            'has_timestamp': bool(re.search(r'\d{4}-\d{2}-\d{2}', error_message)),
            'has_path': bool(re.search(r'/[^\s]+', error_message)),
            'has_number': bool(re.search(r'\d+', error_message)),
            'has_hash': bool(re.search(r'[a-f0-9]{8,}', error_message)),
            'word_count': len(error_message.split()),
            'uppercase_ratio': sum(1 for c in error_message if c.isupper()) / len(error_message) if error_message else 0,
            'special_char_ratio': sum(1 for c in error_message if not c.isalnum() and not c.isspace()) / len(error_message) if error_message else 0
        }
        
        # Extract common error keywords
        error_keywords = [
            'error', 'failed', 'exception', 'timeout', 'connection', 'permission',
            'denied', 'not found', 'invalid', 'corrupt', 'memory', 'disk', 'network'
        ]
        
        for keyword in error_keywords:
            features[f'has_{keyword}'] = keyword.lower() in error_message.lower()
        
        return features
    
    def _normalize_error(self, error_message: str) -> str:
        """Normalize error message for better pattern matching"""
        normalized = error_message.lower()
        
        # Remove variable parts
        normalized = re.sub(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', '[TIMESTAMP]', normalized)
        normalized = re.sub(r'/[\w/.-]+', '[PATH]', normalized)
        normalized = re.sub(r'\d+', '[NUMBER]', normalized)
        normalized = re.sub(r'[a-f0-9]{8,}', '[HASH]', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def _calculate_similarity(self, error1: str, error2: str) -> float:
        """Calculate similarity between two error messages"""
        try:
            # Vectorize the errors
            vectors = self.vectorizer.transform([error1, error2])
            similarity = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]
            return similarity
        except:
            return 0.0
    
    def predict_fix(self, service_name: str, error_message: str) -> Optional[Dict]:
        """Predict the best fix for an error using ML models"""
        if not self.error_data:
            return None
        
        normalized_error = self._normalize_error(error_message)
        features = self._extract_features(error_message, service_name)
        
        # Find similar errors using vectorization
        similar_fixes = []
        
        for error_entry in self.error_data:
            if error_entry['service'] == service_name:
                similarity = self._calculate_similarity(normalized_error, error_entry['normalized_error'])
                if similarity > 0.7:  # High similarity threshold
                    similar_fixes.append({
                        'fix': error_entry['fix'],
                        'similarity': similarity,
                        'success_rate': error_entry['success_rate'],
                        'last_used': error_entry['last_used']
                    })
        
        if similar_fixes:
            # Sort by combination of similarity and success rate
            similar_fixes.sort(key=lambda x: (x['similarity'] * 0.7 + x['success_rate'] * 0.3), reverse=True)
            best_fix = similar_fixes[0]
            
            log_event(f"ML predicted fix for {service_name} with {best_fix['similarity']:.2f} similarity")
            return {
                'command': best_fix['fix'],
                'confidence': best_fix['similarity'],
                'success_rate': best_fix['success_rate'],
                'method': 'ml_prediction'
            }
        
        return None
    
    def learn_from_attempt(self, service_name: str, error_message: str, 
                          command: str, success: bool, stdout: str = "", stderr: str = ""):
        """Learn from a fix attempt and update ML models"""
        normalized_error = self._normalize_error(error_message)
        features = self._extract_features(error_message, service_name)
        
        # Store error data
        error_entry = {
            'service': service_name,
            'error': error_message,
            'normalized_error': normalized_error,
            'fix': command,
            'success': success,
            'stdout': stdout,
            'stderr': stderr,
            'timestamp': datetime.now().isoformat(),
            'features': features
        }
        
        self.error_data.append(error_entry)
        
        # Update service patterns
        if service_name not in self.service_patterns:
            self.service_patterns[service_name] = {
                'total_errors': 0,
                'successful_fixes': {},
                'failed_attempts': []
            }
        
        self.service_patterns[service_name]['total_errors'] += 1
        
        if success:
            # Update successful fixes
            if command not in self.service_patterns[service_name]['successful_fixes']:
                self.service_patterns[service_name]['successful_fixes'][command] = {
                    'count': 0,
                    'first_seen': datetime.now().isoformat(),
                    'last_used': datetime.now().isoformat()
                }
            
            self.service_patterns[service_name]['successful_fixes'][command]['count'] += 1
            self.service_patterns[service_name]['successful_fixes'][command]['last_used'] = datetime.now().isoformat()
        else:
            # Track failed attempts
            self.service_patterns[service_name]['failed_attempts'].append({
                'command': command,
                'error': error_message,
                'timestamp': datetime.now().isoformat(),
                'stdout': stdout,
                'stderr': stderr
            })
        
        # Retrain models periodically (every 10 new entries)
        if len(self.error_data) % 10 == 0:
            self._retrain_models()
        
        self._save_models()
        log_event(f"ML model learned from {service_name} fix attempt (success: {success})")
    
    def _retrain_models(self):
        """Retrain ML models with new data"""
        if len(self.error_data) < 5:
            return
        
        try:
            # Prepare training data
            error_texts = [entry['normalized_error'] for entry in self.error_data]
            service_names = [entry['service'] for entry in self.error_data]
            success_labels = [1 if entry['success'] else 0 for entry in self.error_data]
            
            # Fit vectorizer
            self.vectorizer.fit(error_texts)
            
            # Transform text features
            text_features = self.vectorizer.transform(error_texts)
            
            # Prepare additional features
            additional_features = []
            for entry in self.error_data:
                features = entry['features']
                feature_vector = [
                    features['error_length'],
                    features['has_timestamp'],
                    features['has_path'],
                    features['has_number'],
                    features['has_hash'],
                    features['word_count'],
                    features['uppercase_ratio'],
                    features['special_char_ratio']
                ]
                # Add keyword features
                for keyword in ['error', 'failed', 'exception', 'timeout', 'connection', 'permission']:
                    feature_vector.append(features.get(f'has_{keyword}', False))
                
                additional_features.append(feature_vector)
            
            # Combine features with proper type handling
            try:
                text_array = text_features.toarray()
            except AttributeError:
                # Fallback if toarray() is not available
                text_array = np.array(text_features.todense()) if hasattr(text_features, 'todense') else np.array(text_features)
            
            additional_array = np.array(additional_features, dtype=float)
            combined_features = np.hstack([text_array, additional_array])
            
            # Encode service names
            service_encoded = self.label_encoder.fit_transform(service_names)
            
            # Add service encoding to features with error handling
            if service_encoded is not None:
                final_features = np.column_stack([combined_features, service_encoded.reshape(-1, 1)])
            else:
                final_features = combined_features
            
            # Train classifier
            self.classifier.fit(final_features, success_labels)
            
            log_event("ML models retrained successfully")
        except Exception as e:
            log_event(f"Failed to retrain ML models: {e}")
    
    def get_model_stats(self) -> Dict:
        """Get statistics about the ML model"""
        total_errors = len(self.error_data)
        successful_fixes = sum(1 for entry in self.error_data if entry['success'])
        success_rate = successful_fixes / total_errors if total_errors > 0 else 0
        
        service_stats = {}
        for service_name, patterns in self.service_patterns.items():
            service_stats[service_name] = {
                'total_errors': patterns['total_errors'],
                'successful_fixes': len(patterns['successful_fixes']),
                'failed_attempts': len(patterns['failed_attempts'])
            }
        
        return {
            'total_errors': total_errors,
            'successful_fixes': successful_fixes,
            'success_rate': success_rate,
            'services': service_stats,
            'model_accuracy': self._estimate_accuracy()
        }
    
    def _estimate_accuracy(self) -> float:
        """Estimate model accuracy using cross-validation"""
        if len(self.error_data) < 10:
            return 0.0
        
        try:
            # Simple accuracy estimation using recent data
            recent_data = self.error_data[-10:]
            correct_predictions = 0
            
            for entry in recent_data:
                prediction = self.predict_fix(entry['service'], entry['error'])
                if prediction and prediction['command'] == entry['fix']:
                    correct_predictions += 1
            
            return correct_predictions / len(recent_data)
        except:
            return 0.0
    
    def get_recommendations(self, service_name: str) -> List[Dict]:
        """Get fix recommendations for a service"""
        if service_name not in self.service_patterns:
            return []
        
        service_data = self.service_patterns[service_name]
        recommendations = []
        
        for command, data in service_data['successful_fixes'].items():
            recommendations.append({
                'command': command,
                'success_count': data['count'],
                'last_used': data['last_used'],
                'confidence': min(data['count'] / 10, 1.0)  # Confidence based on usage count
            })
        
        # Sort by success count
        recommendations.sort(key=lambda x: x['success_count'], reverse=True)
        return recommendations[:5]  # Top 5 recommendations 