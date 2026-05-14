"""
Logging configuration for MEDIPREDICT
"""

import os
from pathlib import Path
from django.utils.log import DEFAULT_LOGGING

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Logging Configuration
LOGGING_DIR = BASE_DIR / 'logs'
LOGGING_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'django.server': {
            '()': 'django.utils.log.ServerFormatter',
            'format': '[{server_time}] {message}',
            'style': '{',
        },
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '''
                asctime: %(asctime)s
                created: %(created)f
                filename: %(filename)s
                funcName: %(funcName)s
                levelname: %(levelname)s
                levelno: %(levelno)s
                lineno: %(lineno)d
                message: %(message)s
                module: %(module)s
                msecs: %(msecs)d
                name: %(name)s
                pathname: %(pathname)s
                process: %(process)d
                processName: %(processName)s
                relativeCreated: %(relativeCreated)d
                thread: %(thread)d
                threadName: %(threadName)s
            ''',
        }
    },
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        # Django Log File
        'django_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGGING_DIR / 'django.log',
            'maxBytes': 1024 * 1024 * 100,  # 100 MB
            'backupCount': 10,
            'formatter': 'verbose',
            'filters': ['require_debug_false'],
        },
        # Django Debug File (development only)
        'django_debug_file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGGING_DIR / 'django_debug.log',
            'maxBytes': 1024 * 1024 * 50,  # 50 MB
            'backupCount': 5,
            'formatter': 'verbose',
            'filters': ['require_debug_true'],
        },
        # Error Log File
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGGING_DIR / 'errors.log',
            'maxBytes': 1024 * 1024 * 50,  # 50 MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        # Celery Log File
        'celery_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGGING_DIR / 'celery.log',
            'maxBytes': 1024 * 1024 * 100,  # 100 MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        # Prediction App Log File
        'prediction_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGGING_DIR / 'prediction.log',
            'maxBytes': 1024 * 1024 * 50,  # 50 MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        # API Log File
        'api_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGGING_DIR / 'api.log',
            'maxBytes': 1024 * 1024 * 50,  # 50 MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        # Console output (development)
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
            'filters': ['require_debug_true'],
        },
        # Mail admins on critical errors
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'filters': ['require_debug_false'],
            'formatter': 'verbose',
        },
        # Request/Response logging
        'request_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGGING_DIR / 'requests.log',
            'maxBytes': 1024 * 1024 * 50,  # 50 MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        # Django logger
        'django': {
            'handlers': ['console', 'django_file', 'django_debug_file'],
            'level': 'INFO',
            'propagate': True,
        },
        # Django request logger
        'django.request': {
            'handlers': ['request_file', 'error_file', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        # Django server logger
        'django.server': {
            'handlers': ['console', 'request_file'],
            'level': 'INFO',
            'propagate': False,
        },
        # Django database logger
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        # Django template logger
        'django.template': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        # Django security logger
        'django.security': {
            'handlers': ['error_file', 'mail_admins'],
            'level': 'WARNING',
            'propagate': False,
        },
        # Celery logger
        'celery': {
            'handlers': ['console', 'celery_file'],
            'level': 'INFO',
            'propagate': False,
        },
        # Celery task logger
        'celery.task': {
            'handlers': ['celery_file'],
            'level': 'INFO',
            'propagate': False,
        },
        # Prediction app logger
        'prediction_app': {
            'handlers': ['console', 'prediction_file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
        # ML models logger
        'prediction_app.ml_models': {
            'handlers': ['console', 'prediction_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        # API logger
        'api_app': {
            'handlers': ['console', 'api_file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
        # Users app logger
        'users_app': {
            'handlers': ['console', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
        # Consultations app logger
        'consultations_app': {
            'handlers': ['console', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
        # Notifications app logger
        'notifications_app': {
            'handlers': ['console', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
        # Root logger
        '': {
            'handlers': ['console', 'error_file'],
            'level': 'WARNING',
            'propagate': True,
        },
    },
}