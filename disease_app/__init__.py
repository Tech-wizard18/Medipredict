from .celery import app as celery_app

__all__ = ('celery_app',)











""" 

__version__ = '1.0.0'
__author__ = 'MEDIPREDICT Team'
__email__ = 'support@medipredict.com'

import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Ensure Celery app is loaded when Django starts
from .celery import app as celery_app

# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
__all__ = ('celery_app',)

# Project metadata
PROJECT_NAME = 'MEDIPREDICT'
PROJECT_DESCRIPTION = 'AI-Powered Disease Prediction and Healthcare Management System'
PROJECT_URL = 'https://medipredict.example.com'

# Initialize Django settings
import django
from django.conf import settings

if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'disease_app.settings')
    django.setup()

# Custom exception classes
class MedipredictError(Exception):
    
    pass

class ModelLoadingError(MedipredictError):
   
    pass

class PredictionError(MedipredictError):
    
    pass

class DatabaseConnectionError(MedipredictError):
    
    pass

# Utility functions
def get_project_info():
    
    return {
        'name': PROJECT_NAME,
        'version': __version__,
        'description': PROJECT_DESCRIPTION,
        'url': PROJECT_URL,
        'author': __author__,
    }

def check_database_connection():
    
    from django.db import connection
    try:
        connection.ensure_connection()
        return True
    except Exception as e:
        logging.error(f"Database connection failed: {e}")
        return False

def check_redis_connection():
    
    try:
        from redis import Redis
        redis_client = Redis.from_url(celery_app.conf.broker_url)
        redis_client.ping()
        return True
    except Exception as e:
        logging.error(f"Redis connection failed: {e}")
        return False

# Initialize system checks
def initialize_system():
    
    logger = logging.getLogger(__name__)
    
    logger.info(f"Initializing {PROJECT_NAME} v{__version__}")
    
    # Check database connection
    if check_database_connection():
        logger.info("Database connection successful")
    else:
        logger.warning("Database connection failed")
    
    # Check Redis connection for Celery
    if check_redis_connection():
        logger.info("Redis connection successful")
    else:
        logger.warning("Redis connection failed")
    
    # Check if ML models directory exists
    models_dir = os.path.join(os.path.dirname(__file__), '..', 'prediction_app', 'ml_models')
    if os.path.exists(models_dir):
        logger.info(f"ML models directory found: {models_dir}")
    else:
        logger.warning(f"ML models directory not found: {models_dir}")
    
    logger.info(f"{PROJECT_NAME} initialization complete")

# Run initialization when module is imported
if os.environ.get('DJANGO_SETTINGS_MODULE'):
    initialize_system()



from .base import *
from .development import *

# Or specify based on environment
import os

env = os.environ.get('DJANGO_ENV', 'development')

if env == 'production':
    from .production import *
elif env == 'testing':
    from .testing import *
else:
    from .development import * """