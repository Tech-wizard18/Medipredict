""" 
import os
import sys
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add the project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Set Django settings module based on environment
DJANGO_ENV = os.environ.get('DJANGO_ENV', 'production')

if DJANGO_ENV == 'development':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'disease_app.settings.development')
    logger.info("Using development settings")
elif DJANGO_ENV == 'testing':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'disease_app.settings.testing')
    logger.info("Using testing settings")
else:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'disease_app.settings.production')
    logger.info("Using production settings")

# Import Django and get WSGI application
from django.core.wsgi import get_wsgi_application

# Initialize Django
try:
    import django
    django.setup()
    logger.info("Django initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Django: {e}")
    raise

# Get WSGI application
application = get_wsgi_application()

# Optional: WhiteNoise for static files (if not using a CDN)
try:
    from whitenoise import WhiteNoise
    from django.conf import settings
    
    # Serve static files through WhiteNoise
    application = WhiteNoise(
        application,
        root=settings.STATIC_ROOT,
        prefix=settings.STATIC_URL,
        max_age=31536000 if not settings.DEBUG else 0,  # 1 year cache
        allow_all_origins=True,
        charset='utf-8',
    )
    
    # Add additional directories to WhiteNoise
    if hasattr(settings, 'WHITENOISE_ROOT'):
        for root in settings.WHITENOISE_ROOT:
            application.add_files(root, prefix='/')
    
    logger.info("WhiteNoise middleware configured")
    
except ImportError:
    logger.warning("WhiteNoise not installed, static files may not be served correctly")
except Exception as e:
    logger.error(f"Failed to configure WhiteNoise: {e}")

# Optional: Add security headers middleware
class SecurityHeadersMiddleware:
    
    .
    
    def __init__(self, app):
        self.app = app
    
    def __call__(self, environ, start_response):
        def custom_start_response(status, headers, exc_info=None):
            # Add security headers
            security_headers = [
                ('X-Content-Type-Options', 'nosniff'),
                ('X-Frame-Options', 'DENY'),
                ('X-XSS-Protection', '1; mode=block'),
                ('Referrer-Policy', 'strict-origin-when-cross-origin'),
                ('Permissions-Policy', 'camera=(), microphone=(), geolocation=()'),
            ]
            
            # Add CSP in production
            if not settings.DEBUG:
                csp = (
                    "default-src 'self'; "
                    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                    "font-src 'self' https://fonts.gstatic.com; "
                    "img-src 'self' data: https:; "
                    "connect-src 'self' wss://*; "
                    "frame-ancestors 'none'; "
                    "base-uri 'self'; "
                    "form-action 'self';"
                )
                security_headers.append(('Content-Security-Policy', csp))
            
            headers.extend(security_headers)
            return start_response(status, headers, exc_info)
        
        return self.app(environ, custom_start_response)

# Apply security middleware in production
if not settings.DEBUG:
    application = SecurityHeadersMiddleware(application)
    logger.info("Security headers middleware configured")

# Optional: Add request logging middleware
class RequestLoggingMiddleware:
    
    def __init__(self, app):
        self.app = app
    
    def __call__(self, environ, start_response):
        # Log request
        method = environ.get('REQUEST_METHOD', 'UNKNOWN')
        path = environ.get('PATH_INFO', '')
        query = environ.get('QUERY_STRING', '')
        
        if query:
            path = f"{path}?{query}"
        
        logger.info(f"WSGI Request: {method} {path}")
        
        # Process request
        return self.app(environ, start_response)

# Apply request logging
application = RequestLoggingMiddleware(application)
logger.info("Request logging middleware configured")

# Health check endpoint
def health_check_app(environ, start_response):
    
    if environ.get('PATH_INFO') == '/health/wsgi/':
        start_response('200 OK', [
            ('Content-Type', 'application/json'),
            ('Cache-Control', 'no-store, no-cache, must-revalidate'),
        ])
        return [b'{"status": "healthy", "service": "wsgi"}']
    
    # Pass through to main application
    return application(environ, start_response)

# Wrap application with health check
application = health_check_app

# Gunicorn configuration (if using Gunicorn)
def when_ready(server):
    
    logger.info(f"Gunicorn worker ready on {server.address}")
    logger.info(f"MEDIPREDICT WSGI application loaded")

def worker_int(worker):
    
    logger.warning(f"Worker {worker.pid} received interrupt signal")

def worker_abort(worker):
    "
    logger.error(f"Worker {worker.pid} received abort signal")

# Export WSGI application
__all__ = ['application']

# WSGI server configuration
WSGI_CONFIG = {
    'worker_class': 'sync',  # or 'gthread', 'gevent', etc.
    'workers': 4,
    'threads': 2,
    'max_requests': 1000,
    'timeout': 30,
    'keepalive': 2,
}

logger.info(f"WSGI Application configured: {WSGI_CONFIG}")
logger.info(f"MEDIPREDICT is ready to serve requests")


import os
from django.core.wsgi import get_wsgi_application

# Use development settings by default
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'disease_app.settings.development')

application = get_wsgi_application() """



"""
WSGI config for MEDIPREDICT project.
"""

import os
from django.core.wsgi import get_wsgi_application

# Default settings file
os.environ.setdefault(
    'DJANGO_SETTINGS_MODULE',
    'disease_app.settings.base'   # ← change if your main file is different
)

application = get_wsgi_application()
