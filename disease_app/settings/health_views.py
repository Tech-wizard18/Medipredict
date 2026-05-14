# disease_app/health_views.py
from django.http import JsonResponse
from django.db import connection
from django.views import View

class HealthCheckView(View):
    def get(self, request):
        """Simple health check endpoint"""
        checks = {}
        
        # Database check
        try:
            connection.ensure_connection()
            checks['database'] = 'healthy'
        except Exception as e:
            checks['database'] = f'unhealthy: {e}'
        
        # Determine overall status
        status = 'healthy' if all('healthy' in str(v) for v in checks.values()) else 'unhealthy'
        
        return JsonResponse({
            'status': status,
            'checks': checks,
            'service': 'MEDIPREDICT'
        })