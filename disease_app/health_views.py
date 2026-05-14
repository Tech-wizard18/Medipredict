# Create a new file: disease_app/health_views.py
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
import redis

def health_check(request):
    """Simple health check endpoint."""
    checks = {}
    
    # Database check
    try:
        connection.ensure_connection()
        checks['database'] = 'healthy'
    except Exception as e:
        checks['database'] = f'unhealthy: {str(e)}'
    
    # Cache check
    try:
        cache.set('health_check', 'ok', 1)
        cache.get('health_check')
        checks['cache'] = 'healthy'
    except Exception as e:
        checks['cache'] = f'unhealthy: {str(e)}'
    
    # Overall status
    status = 'healthy' if all('healthy' in v for v in checks.values()) else 'unhealthy'
    
    return JsonResponse({
        'status': status,
        'checks': checks,
        'service': 'MEDIPREDICT Disease Prediction System'
    })