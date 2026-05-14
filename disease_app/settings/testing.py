"""
Testing settings for MediPredict project.
These settings are for running tests.
"""

import os
from .base import *

print("Loading testing settings...")

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-test-key-for-testing-only'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Allowed hosts for testing
ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    'testserver',
]

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
        'TEST': {
            'NAME': ':memory:',
        }
    }
}

# Cache configuration for testing
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# Email configuration for testing
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Celery Configuration for testing
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Static files for testing
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Security settings (relaxed for testing)
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0

# CORS settings for testing
CORS_ALLOW_ALL_ORIGINS = True

# Logging for testing
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'level': 'WARNING',
            'class': 'logging.StreamHandler',
        },
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
        },
        'django.db.backends': {
            'handlers': ['null'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'prediction_app': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# Speed up password hashing for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable Axes for testing
AXES_ENABLED = False

# Feature flags for testing
FEATURE_FLAGS.update({
    'ENABLE_REAL_ML_MODELS': False,
    'ENABLE_EMAIL_NOTIFICATIONS': False,
    'ENABLE_API_RATE_LIMITING': False,
    'ENABLE_ANALYTICS_TRACKING': False,
})

# Use mock ML models for testing
ML_MODELS_DIR = os.path.join(BASE_DIR, 'prediction_app', 'ml_models', 'test')

# Test runner
TEST_RUNNER = 'django.test.runner.DiscoverRunner'

# Test database setup
TEST_DATABASE_CHARSET = 'utf8'
TEST_DATABASE_COLLATION = 'utf8_general_ci'

# Disable migrations during tests
class DisableMigrations:
    def __contains__(self, item):
        return True
    
    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Test settings
TESTING = True

# Middleware for testing
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# REST Framework settings for testing
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'anon': '1000/minute',
    'user': '10000/minute',
}

# File upload settings for testing
FILE_UPLOAD_MAX_MEMORY_SIZE = 2621440  # 2.5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 2621440  # 2.5MB

# Session settings for testing
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# Media files for testing
MEDIA_ROOT = os.path.join(BASE_DIR, 'media_test')

# Static files for testing
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles_test')

# Create test directories
os.makedirs(MEDIA_ROOT, exist_ok=True)
os.makedirs(STATIC_ROOT, exist_ok=True)
os.makedirs(ML_MODELS_DIR, exist_ok=True)

# Test fixtures
FIXTURE_DIRS = [
    os.path.join(BASE_DIR, 'tests', 'fixtures'),
]

# Test data
TEST_DATA_DIR = os.path.join(BASE_DIR, 'tests', 'test_data')

# Print configuration summary
print("\n" + "="*50)
print("Testing Configuration Summary:")
print("="*50)
print(f"Database: {DATABASES['default']['ENGINE']} (in-memory)")
print(f"Cache: {CACHES['default']['BACKEND']}")
print(f"Celery: Eager mode")
print(f"ML Models: Mock models in test directory")
print("="*50 + "\n")