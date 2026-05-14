"""
Django middleware for request/response logging
"""

import time
import json
import logging
from typing import Dict, Any
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('django.request')

class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log all HTTP requests and responses
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Log request
        request_start_time = time.time()
        
        # Skip logging for static/media files
        path = request.path
        if any(path.startswith(prefix) for prefix in ['/static/', '/media/', '/favicon.ico']):
            return self.get_response(request)
        
        # Log request details
        request_log_data = self.get_request_log_data(request)
        logger.info(f"Request: {json.dumps(request_log_data)}")
        
        # Process the request
        response = self.get_response(request)
        
        # Log response
        response_time = time.time() - request_start_time
        response_log_data = self.get_response_log_data(request, response, response_time)
        
        # Log based on status code
        if response.status_code >= 500:
            logger.error(f"Response: {json.dumps(response_log_data)}")
        elif response.status_code >= 400:
            logger.warning(f"Response: {json.dumps(response_log_data)}")
        else:
            logger.info(f"Response: {json.dumps(response_log_data)}")
        
        return response
    
    def get_request_log_data(self, request) -> Dict[str, Any]:
        """Extract request data for logging."""
        user = getattr(request, 'user', None)
        
        return {
            'timestamp': time.time(),
            'method': request.method,
            'path': request.path,
            'query_params': dict(request.GET),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'ip_address': self.get_client_ip(request),
            'user_id': user.id if user and user.is_authenticated else 'anonymous',
            'content_type': request.content_type,
            'content_length': len(request.body) if hasattr(request, 'body') else 0,
        }
    
    def get_response_log_data(self, request, response, response_time: float) -> Dict[str, Any]:
        """Extract response data for logging."""
        user = getattr(request, 'user', None)
        
        log_data = {
            'timestamp': time.time(),
            'method': request.method,
            'path': request.path,
            'status_code': response.status_code,
            'response_time': round(response_time, 4),
            'user_id': user.id if user and user.is_authenticated else 'anonymous',
            'ip_address': self.get_client_ip(request),
        }
        
        # Add additional info for errors
        if response.status_code >= 400:
            if hasattr(response, 'data'):
                log_data['error_data'] = str(response.data)
            elif hasattr(response, 'content'):
                log_data['error_content'] = response.content.decode('utf-8', errors='ignore')[:500]
        
        return log_data
    
    def get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class PredictionLoggingMiddleware(MiddlewareMixin):
    """
    Middleware specifically for prediction request logging
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.prediction_logger = logging.getLogger('prediction_app')
    
    def __call__(self, request):
        # Check if this is a prediction request
        is_prediction = any(pattern in request.path for pattern in [
            '/predict/', '/api/predict/', '/prediction/'
        ])
        
        if is_prediction:
            prediction_start_time = time.time()
            
            # Process the request
            response = self.get_response(request)
            
            # Log prediction details
            prediction_time = time.time() - prediction_start_time
            
            self.log_prediction(request, response, prediction_time)
            
            return response
        
        return self.get_response(request)
    
    def log_prediction(self, request, response, prediction_time: float):
        """Log prediction request details."""
        try:
            log_data = {
                'timestamp': time.time(),
                'endpoint': request.path,
                'method': request.method,
                'prediction_time': round(prediction_time, 4),
                'status_code': response.status_code,
                'user_id': getattr(request.user, 'id', 'anonymous') if hasattr(request, 'user') else 'anonymous',
                'ip_address': self.get_client_ip(request),
            }
            
            # Try to extract disease type from path
            for disease in ['diabetes', 'heart', 'kidney', 'parkinson', 'liver', 'breast_cancer']:
                if disease in request.path:
                    log_data['disease_type'] = disease
                    break
            
            # Log prediction result if successful
            if response.status_code == 200 and hasattr(response, 'data'):
                try:
                    response_data = response.data
                    if isinstance(response_data, dict):
                        if 'prediction' in response_data:
                            log_data['prediction_result'] = response_data['prediction']
                        if 'probability' in response_data:
                            log_data['probability'] = response_data['probability']
                        if 'confidence' in response_data:
                            log_data['confidence'] = response_data['confidence']
                except:
                    pass
            
            self.prediction_logger.info(f"Prediction: {json.dumps(log_data)}")
            
        except Exception as e:
            self.prediction_logger.error(f"Error logging prediction: {e}")
    
    def get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip