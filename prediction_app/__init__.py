""" 

__version__ = '1.0.0'
__author__ = 'MEDIPREDICT Team'

import os
import logging

# prediction_app/__init__.py
default_app_config = 'prediction_app.apps.PredictionAppConfig'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Application constants
APP_NAME = 'prediction_app'
DISEASE_MODELS = {
    'diabetes': {
        'name': 'Diabetes',
        'description': 'Predicts likelihood of diabetes',
        'icon': 'fa-heartbeat',
        'color': 'danger',
    },
    'heart': {
        'name': 'Heart Disease',
        'description': 'Predicts cardiovascular diseases',
        'icon': 'fa-heart',
        'color': 'danger',
    },
    'kidney': {
        'name': 'Kidney Disease',
        'description': 'Predicts chronic kidney disease',
        'icon': 'fa-kidneys',
        'color': 'info',
    },
    'parkinson': {
        'name': 'Parkinson Disease',
        'description': 'Predicts Parkinson disease',
        'icon': 'fa-brain',
        'color': 'warning',
    },
    'breast_cancer': {
        'name': 'Breast Cancer',
        'description': 'Predicts breast cancer',
        'icon': 'fa-ribbon',
        'color': 'pink',
    },
    'liver': {
        'name': 'Liver Disease',
        'description': 'Predicts liver conditions',
        'icon': 'fa-liver',
        'color': 'success',
    }
}

# Import models for easy access
#from .models import DiseaseModel, Prediction, HealthReport
from .ml_utils import ModelManager, PredictionEngine

# Initialize ML models on app startup
def initialize_models():
   
    try:
        ModelManager.initialize_models()
        logging.info(f"ML models initialized successfully for {APP_NAME}")
    except Exception as e:
        logging.error(f"Failed to initialize ML models: {e}")

# Context processor for templates
def disease_models(request):
   
    return {
        'disease_models': DISEASE_MODELS,
        'app_name': APP_NAME,
    }

# Export prediction engine
def get_prediction_engine():
    
    return PredictionEngine()

# Export model manager
def get_model_manager():
   
    return ModelManager

# Run initialization
initialize_models()


 """