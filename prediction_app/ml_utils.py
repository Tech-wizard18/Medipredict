import pickle
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
import joblib
import os
from django.conf import settings
import logging
from typing import List,Dict, Any, Optional, Tuple
import warnings

warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)


class ModelManager:
    """Manager for loading and accessing ML models."""
    
    _models = {}
    _scalers = {}
    _initialized = False
    
    @classmethod
    def initialize_models(cls):
        """Initialize all ML models."""
        if cls._initialized:
            return
        
        try:
            models_dir = os.path.join(settings.BASE_DIR, 'prediction_app', 'ml_models')
            
            # Load disease models
            disease_models = {
                'diabetes': 'diabetes_model.pkl',
                'heart': 'heart_model.pkl',
                'kidney': 'kidney_model.pkl',
                'parkinson': 'parkinson_model.pkl',
                'breast_cancer': 'breast_cancer_model.pkl',
                'liver': 'liver_model.pkl',
            }
            
            for disease, model_file in disease_models.items():
                model_path = os.path.join(models_dir, model_file)
                scaler_path = os.path.join(models_dir, 'scalers', f'{disease}_scaler.pkl')
                
                # Load model
                if os.path.exists(model_path):
                    try:
                        with open(model_path, 'rb') as f:
                            cls._models[disease] = pickle.load(f)
                        logger.info(f"Loaded {disease} model from {model_path}")
                    except Exception as e:
                        logger.error(f"Failed to load {disease} model: {e}")
                        cls._models[disease] = None
                else:
                    logger.warning(f"Model file not found: {model_path}")
                    cls._models[disease] = None
                
                # Load scaler
                if os.path.exists(scaler_path):
                    try:
                        with open(scaler_path, 'rb') as f:
                            cls._scalers[disease] = pickle.load(f)
                        logger.info(f"Loaded {disease} scaler from {scaler_path}")
                    except Exception as e:
                        logger.error(f"Failed to load {disease} scaler: {e}")
                        cls._scalers[disease] = None
                else:
                    logger.warning(f"Scaler file not found: {scaler_path}")
                    cls._scalers[disease] = None
            
            cls._initialized = True
            logger.info("All ML models initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize models: {e}")
            raise
    
    @classmethod
    def get_model(cls, disease: str):
        """Get model for specific disease."""
        if not cls._initialized:
            cls.initialize_models()
        
        return cls._models.get(disease)
    
    @classmethod
    def get_scaler(cls, disease: str):
        """Get scaler for specific disease."""
        if not cls._initialized:
            cls.initialize_models()
        
        return cls._scalers.get(disease)
    
    @classmethod
    def load_model(cls, disease: str):
        """Load a specific model (useful for hot reloading)."""
        models_dir = os.path.join(settings.BASE_DIR, 'prediction_app', 'ml_models')
        model_file = f"{disease}_model.pkl"
        model_path = os.path.join(models_dir, model_file)
        
        if os.path.exists(model_path):
            try:
                with open(model_path, 'rb') as f:
                    cls._models[disease] = pickle.load(f)
                logger.info(f"Reloaded {disease} model")
                return True
            except Exception as e:
                logger.error(f"Failed to reload {disease} model: {e}")
                return False
        else:
            logger.error(f"Model file not found: {model_path}")
            return False
    
    @classmethod
    def cleanup(cls):
        """Clean up model resources."""
        cls._models.clear()
        cls._scalers.clear()
        cls._initialized = False
        logger.info("ML models cleaned up")
    
    @classmethod
    def get_model_info(cls, disease: str) -> Dict[str, Any]:
        """Get information about a model."""
        model = cls.get_model(disease)
        if model is None:
            return {'loaded': False, 'error': 'Model not loaded'}
        
        info = {
            'loaded': True,
            'type': type(model).__name__,
            'features': getattr(model, 'n_features_in_', 'Unknown'),
            'params': getattr(model, 'get_params', lambda: {})()
        }
        
        # Add model-specific info
        if hasattr(model, 'classes_'):
            info['classes'] = model.classes_.tolist()
        if hasattr(model, 'coef_'):
            info['coefficients'] = model.coef_.tolist() if hasattr(model.coef_, 'tolist') else str(model.coef_)
        
        return info
    
    @classmethod
    def get_all_model_info(cls) -> Dict[str, Dict[str, Any]]:
        """Get information about all models."""
        return {disease: cls.get_model_info(disease) for disease in cls._models.keys()}


class PredictionEngine:
    """Engine for making predictions using ML models."""
    
    def __init__(self):
        self.model_manager = ModelManager
        self.model_manager.initialize_models()
    
    def predict(self, disease_type: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make a prediction for a specific disease.
        
        Args:
            disease_type: Type of disease (diabetes, heart, etc.)
            input_data: Dictionary of input features
            
        Returns:
            Dictionary with prediction results
        """
        try:
            # Get model and scaler
            model = self.model_manager.get_model(disease_type)
            scaler = self.model_manager.get_scaler(disease_type)
            
            if model is None:
                raise ValueError(f"Model for {disease_type} not loaded")
            
            # Prepare input data based on disease type
            processed_input = self._prepare_input(disease_type, input_data)
            
            # Scale features if scaler exists
            if scaler is not None:
                processed_input = scaler.transform(processed_input)
            
            # Make prediction
            prediction = model.predict(processed_input)
            probability = model.predict_proba(processed_input)
            
            # Format results
            result = self._format_result(disease_type, prediction[0], probability[0])
            
            return result
            
        except Exception as e:
            logger.error(f"Prediction error for {disease_type}: {e}")
            raise
    
    def _prepare_input(self, disease_type: str, input_data: Dict[str, Any]) -> np.ndarray:
        """Prepare input data for specific disease model."""
        # Define feature order for each disease
        feature_orders = {
            'diabetes': ['pregnancies', 'glucose', 'blood_pressure', 'skin_thickness',
                        'insulin', 'bmi', 'diabetes_pedigree_function', 'age'],
            'heart': ['age', 'sex', 'cp', 'trestbps', 'chol', 'fbs', 'restecg',
                     'thalach', 'exang', 'oldpeak', 'slope', 'ca', 'thal'],
            'kidney': ['age', 'blood_pressure', 'specific_gravity', 'albumin', 'sugar',
                      'red_blood_cells', 'pus_cell', 'pus_cell_clumps', 'bacteria',
                      'blood_glucose_random', 'blood_urea', 'serum_creatinine',
                      'sodium', 'potassium', 'hemoglobin', 'packed_cell_volume',
                      'white_blood_cell_count', 'red_blood_cell_count', 'hypertension',
                      'diabetes_mellitus', 'coronary_artery_disease', 'appetite',
                      'pedal_edema', 'anemia'],
            'parkinson': ['mdvp_fo', 'mdvp_fhi', 'mdvp_flo', 'mdvp_jitter_percent',
                         'mdvp_jitter_abs', 'mdvp_rap', 'mdvp_ppq', 'jitter_ddp',
                         'mdvp_shimmer', 'mdvp_shimmer_db', 'shimmer_apq3',
                         'shimmer_apq5', 'mdvp_apq', 'shimmer_dda', 'nhr', 'hnr',
                         'rpde', 'dfa', 'spread1', 'spread2', 'd2', 'ppe'],
            'breast_cancer': ['radius_mean', 'texture_mean', 'perimeter_mean', 'area_mean',
                             'smoothness_mean', 'compactness_mean', 'concavity_mean',
                             'concave_points_mean', 'symmetry_mean', 'fractal_dimension_mean',
                             'radius_se', 'texture_se', 'perimeter_se', 'area_se',
                             'smoothness_se', 'compactness_se', 'concavity_se',
                             'concave_points_se', 'symmetry_se', 'fractal_dimension_se',
                             'radius_worst', 'texture_worst', 'perimeter_worst', 'area_worst',
                             'smoothness_worst', 'compactness_worst', 'concavity_worst',
                             'concave_points_worst', 'symmetry_worst', 'fractal_dimension_worst'],
            'liver': ['age', 'gender', 'total_bilirubin', 'direct_bilirubin',
                     'alkaline_phosphotase', 'alamine_aminotransferase',
                     'aspartate_aminotransferase', 'total_proteins', 'albumin',
                     'albumin_globulin_ratio']
        }
        
        if disease_type not in feature_orders:
            raise ValueError(f"Unknown disease type: {disease_type}")
        
        # Extract features in correct order
        features = []
        for feature in feature_orders[disease_type]:
            if feature in input_data:
                features.append(float(input_data[feature]))
            else:
                # Use default value for missing features
                features.append(0.0)
                logger.warning(f"Missing feature {feature} for {disease_type}")
        
        # Convert to numpy array and reshape for single prediction
        return np.array(features).reshape(1, -1)
    
    def _format_result(self, disease_type: str, prediction: Any, probability: np.ndarray) -> Dict[str, Any]:
        """Format prediction result."""
        # Map prediction to human-readable labels
        label_mappings = {
            'diabetes': {0: 'Negative', 1: 'Positive'},
            'heart': {0: 'No Disease', 1: 'Heart Disease'},
            'kidney': {0: 'No Disease', 1: 'Kidney Disease'},
            'parkinson': {0: 'Healthy', 1: 'Parkinson Disease'},
            'breast_cancer': {0: 'Benign', 1: 'Malignant'},
            'liver': {0: 'No Disease', 1: 'Liver Disease'},
        }
        
        # Get label
        label = label_mappings.get(disease_type, {}).get(int(prediction), str(prediction))
        
        # Calculate confidence (probability of predicted class)
        confidence = float(probability[int(prediction)])
        
        # Calculate risk level
        risk_level = self._calculate_risk_level(confidence, disease_type)
        
        # Get probability for each class
        probabilities = {}
        if disease_type in label_mappings:
            for class_idx, class_label in label_mappings[disease_type].items():
                if class_idx < len(probability):
                    probabilities[class_label] = float(probability[class_idx])
        
        return {
            'disease': disease_type,
            'prediction': int(prediction),
            'label': label,
            'probability': float(probability.max()),
            'confidence': confidence,
            'risk_level': risk_level,
            'probabilities': probabilities,
            'timestamp': pd.Timestamp.now().isoformat()
        }
    
    def _calculate_risk_level(self, confidence: float, disease_type: str) -> str:
        """Calculate risk level based on confidence score."""
        # Different thresholds for different diseases
        thresholds = {
            'diabetes': {'low': 0.3, 'moderate': 0.6, 'high': 0.8},
            'heart': {'low': 0.4, 'moderate': 0.7, 'high': 0.85},
            'kidney': {'low': 0.35, 'moderate': 0.65, 'high': 0.8},
            'parkinson': {'low': 0.4, 'moderate': 0.7, 'high': 0.85},
            'breast_cancer': {'low': 0.3, 'moderate': 0.6, 'high': 0.8},
            'liver': {'low': 0.35, 'moderate': 0.65, 'high': 0.8},
        }
        
        default_thresholds = {'low': 0.3, 'moderate': 0.6, 'high': 0.8}
        disease_thresholds = thresholds.get(disease_type, default_thresholds)
        
        if confidence < disease_thresholds['low']:
            return 'Low'
        elif confidence < disease_thresholds['moderate']:
            return 'Moderate'
        elif confidence < disease_thresholds['high']:
            return 'High'
        else:
            return 'Critical'
    
    def batch_predict(self, disease_type: str, input_data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Make predictions for multiple inputs."""
        results = []
        for input_data in input_data_list:
            try:
                result = self.predict(disease_type, input_data)
                results.append(result)
            except Exception as e:
                logger.error(f"Batch prediction error: {e}")
                results.append({'error': str(e), 'input_data': input_data})
        
        return results
    
    def validate_input(self, disease_type: str, input_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate input data for a specific disease."""
        errors = []
        
        # Get feature ranges for validation
        feature_ranges = self._get_feature_ranges(disease_type)
        
        for feature, value in input_data.items():
            if feature in feature_ranges:
                min_val, max_val = feature_ranges[feature]
                try:
                    num_value = float(value)
                    if not (min_val <= num_value <= max_val):
                        errors.append(f"{feature}: Value {value} out of range [{min_val}, {max_val}]")
                except ValueError:
                    errors.append(f"{feature}: Invalid numeric value")
        
        return len(errors) == 0, errors
    
    def _get_feature_ranges(self, disease_type: str) -> Dict[str, Tuple[float, float]]:
        """Get valid ranges for features of a specific disease."""
        # These ranges should be based on your training data
        ranges = {
            'diabetes': {
                'pregnancies': (0, 20),
                'glucose': (0, 300),
                'blood_pressure': (0, 200),
                'skin_thickness': (0, 100),
                'insulin': (0, 900),
                'bmi': (0, 100),
                'diabetes_pedigree_function': (0, 3),
                'age': (0, 120),
            },
            'heart': {
                'age': (0, 120),
                'sex': (0, 1),
                'cp': (0, 3),
                'trestbps': (0, 300),
                'chol': (0, 600),
                'fbs': (0, 1),
                'restecg': (0, 2),
                'thalach': (0, 300),
                'exang': (0, 1),
                'oldpeak': (0, 10),
                'slope': (0, 2),
                'ca': (0, 4),
                'thal': (0, 3),
            },
            # Add ranges for other diseases...
        }
        
        return ranges.get(disease_type, {})
    
    def get_feature_importance(self, disease_type: str) -> Optional[Dict[str, float]]:
        """Get feature importance for a model (if available)."""
        model = self.model_manager.get_model(disease_type)
        
        if model is None:
            return None
        
        try:
            if hasattr(model, 'feature_importances_'):
                # Tree-based models
                feature_names = self._get_feature_names(disease_type)
                importances = model.feature_importances_
                
                if len(feature_names) == len(importances):
                    return dict(zip(feature_names, importances.tolist()))
            
            elif hasattr(model, 'coef_'):
                # Linear models
                feature_names = self._get_feature_names(disease_type)
                coefficients = model.coef_[0] if len(model.coef_.shape) > 1 else model.coef_
                
                if len(feature_names) == len(coefficients):
                    # Return absolute values for importance
                    importance = np.abs(coefficients)
                    importance_dict = dict(zip(feature_names, importance.tolist()))
                    
                    # Normalize to 0-1 range
                    max_val = max(importance_dict.values())
                    if max_val > 0:
                        for key in importance_dict:
                            importance_dict[key] /= max_val
                    
                    return importance_dict
        
        except Exception as e:
            logger.error(f"Failed to get feature importance for {disease_type}: {e}")
        
        return None
    
    def _get_feature_names(self, disease_type: str) -> List[str]:
        """Get feature names for a disease."""
        feature_orders = {
            'diabetes': ['pregnancies', 'glucose', 'blood_pressure', 'skin_thickness',
                        'insulin', 'bmi', 'diabetes_pedigree_function', 'age'],
            'heart': ['age', 'sex', 'cp', 'trestbps', 'chol', 'fbs', 'restecg',
                     'thalach', 'exang', 'oldpeak', 'slope', 'ca', 'thal'],
            # Add other diseases...
        }
        
        return feature_orders.get(disease_type, [])
    
    def explain_prediction(self, disease_type: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate explanation for a prediction."""
        try:
            result = self.predict(disease_type, input_data)
            feature_importance = self.get_feature_importance(disease_type)
            
            explanation = {
                'prediction': result,
                'top_features': [],
                'reasoning': self._generate_reasoning(disease_type, result, input_data)
            }
            
            if feature_importance:
                # Get top 5 most important features for this prediction
                sorted_features = sorted(
                    feature_importance.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5]
                
                explanation['top_features'] = [
                    {'feature': feat, 'importance': imp}
                    for feat, imp in sorted_features
                ]
            
            return explanation
            
        except Exception as e:
            logger.error(f"Failed to explain prediction: {e}")
            return {'error': str(e)}
    
    def _generate_reasoning(self, disease_type: str, result: Dict[str, Any], 
                           input_data: Dict[str, Any]) -> str:
        """Generate natural language reasoning for prediction."""
        label = result['label']
        confidence = result['confidence']
        
        reasoning = f"The model predicts {label.lower()} with {confidence:.1%} confidence. "
        
        # Add disease-specific reasoning
        if disease_type == 'diabetes':
            if 'glucose' in input_data and input_data['glucose'] > 140:
                reasoning += "High glucose levels significantly contribute to this prediction. "
            if 'bmi' in input_data and input_data['bmi'] > 30:
                reasoning += "Elevated BMI increases diabetes risk. "
        
        elif disease_type == 'heart':
            if 'trestbps' in input_data and input_data['trestbps'] > 140:
                reasoning += "Elevated blood pressure is a key risk factor. "
            if 'chol' in input_data and input_data['chol'] > 240:
                reasoning += "High cholesterol levels increase cardiovascular risk. "
        
        reasoning += "This is based on statistical patterns learned from medical datasets."
        
        return reasoning