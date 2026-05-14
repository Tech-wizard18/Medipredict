import time
import json
import hashlib
import hmac
import base64
from datetime import datetime, timedelta
from django.utils import timezone
from django.shortcuts import render, get_object_or_404
from django.db.models import Count, Avg, Q
from django.core.cache import cache
from django.conf import settings
from django.http import JsonResponse, HttpResponseForbidden
from rest_framework import viewsets, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError, PermissionDenied, Throttled
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle

from .models import APIKey, APILog, APIVersion
from .serializers import (
    APIKeySerializer, APILogSerializer, APIVersionSerializer,
    APIRequestSerializer, PredictionRequestSerializer,
    PredictionResponseSerializer, ErrorResponseSerializer,
    RateLimitResponseSerializer
)
from .permissions import HasAPIKey, IsOwnerOrAdmin, IsAdminOrReadOnly
from prediction_app.models import Prediction
from notifications_app.models import Notification
from users_app.models import User


class APIDocumentationView(APIView):
    """
    View for API documentation
    """
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle]

    def get(self, request):
        """
        Return API documentation
        """
        docs = {
            'title': 'MediPredict API Documentation',
            'version': '1.0.0',
            'base_url': request.build_absolute_uri('/api/v1/'),
            'description': 'API for MediPredict Disease Prediction System',
            'authentication': {
                'type': 'API Key with HMAC Signature',
                'headers': {
                    'X-API-Key': 'Your API Key ID',
                    'X-Signature': 'HMAC SHA256 Signature',
                    'X-Timestamp': 'Unix Timestamp'
                }
            },
            'endpoints': {
                'health': {
                    'url': '/api/v1/health/',
                    'method': 'GET',
                    'description': 'Check API health status',
                    'authentication': 'Optional'
                },
                'predict': {
                    'url': '/api/v1/predict/',
                    'method': 'POST',
                    'description': 'Make disease prediction',
                    'parameters': {
                        'disease_type': 'Type of disease (diabetes, heart, kidney, etc.)',
                        'age': 'Patient age',
                        'gender': 'Patient gender',
                        'parameters': 'Disease-specific parameters as JSON'
                    }
                },
                'user_profile': {
                    'url': '/api/v1/user/profile/',
                    'method': 'GET',
                    'description': 'Get user profile information',
                    'authentication': 'Required'
                },
                'user_predictions': {
                    'url': '/api/v1/user/predictions/',
                    'method': 'GET',
                    'description': 'Get user prediction history',
                    'authentication': 'Required'
                }
            },
            'rate_limits': {
                'free': '60 requests per minute, 1000 per hour',
                'premium': '120 requests per minute, 5000 per hour'
            },
            'error_codes': {
                '400': 'Bad Request',
                '401': 'Unauthorized',
                '403': 'Forbidden',
                '404': 'Not Found',
                '429': 'Too Many Requests',
                '500': 'Internal Server Error'
            }
        }
        
        return Response(docs)


class HealthCheckView(APIView):
    """
    Health check endpoint
    """
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle]

    def get(self, request):
        """
        Return health status
        """
        # Check database connection
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            db_status = 'healthy'
        except Exception:
            db_status = 'unhealthy'

        # Check cache
        try:
            cache.set('health_check', 'ok', 10)
            cache_status = 'healthy' if cache.get('health_check') == 'ok' else 'unhealthy'
        except Exception:
            cache_status = 'unhealthy'

        health_data = {
            'status': 'ok',
            'timestamp': timezone.now().isoformat(),
            'version': '1.0.0',
            'services': {
                'database': db_status,
                'cache': cache_status,
                'ml_models': 'healthy' if hasattr(settings, 'ML_MODELS_LOADED') else 'unhealthy'
            },
            'uptime': getattr(self, '_uptime', 0)
        }

        return Response(health_data)


class GenerateAPIKeyView(APIView):
    """
    Generate a new API key
    """
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def post(self, request):
        """
        Generate a new API key for the authenticated user
        """
        serializer = APIKeySerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            api_key = serializer.save()
            
            response_data = {
                'success': True,
                'message': 'API key generated successfully',
                'key_id': api_key.key_id,
                'secret_key': api_key.secret_key,
                'name': api_key.name,
                'created_at': api_key.created_at.isoformat(),
                'warning': 'Save the secret key now. It will not be shown again!'
            }
            
            return Response(response_data, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class VerifyAPIKeyView(APIView):
    """
    Verify an API key
    """
    permission_classes = [HasAPIKey]
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        """
        Verify API key and return its details
        """
        api_key = request.api_key
        
        return Response({
            'success': True,
            'key_id': api_key.key_id,
            'name': api_key.name,
            'user': api_key.user.username,
            'is_active': api_key.is_active,
            'rate_limits': {
                'per_minute': api_key.rate_limit_per_minute,
                'per_hour': api_key.rate_limit_per_hour,
                'per_day': api_key.rate_limit_per_day
            },
            'usage': {
                'today': api_key.requests_today,
                'total': api_key.total_requests
            },
            'last_used': api_key.last_used.isoformat() if api_key.last_used else None,
            'created_at': api_key.created_at.isoformat()
        })


class RevokeAPIKeyView(APIView):
    """
    Revoke an API key
    """
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def delete(self, request, key_id):
        """
        Revoke (deactivate) an API key
        """
        api_key = get_object_or_404(APIKey, key_id=key_id, user=request.user)
        
        if not api_key.is_active:
            return Response({
                'success': False,
                'message': 'API key is already inactive'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        api_key.is_active = False
        api_key.save()
        
        return Response({
            'success': True,
            'message': 'API key revoked successfully'
        })


class PredictionAPIView(APIView):
    """
    API endpoint for making predictions
    """
    permission_classes = [HasAPIKey]
    throttle_classes = [UserRateThrottle]

    def post(self, request):
        """
        Make a disease prediction
        """
        start_time = time.time()
        
        try:
            # Validate request data
            prediction_serializer = PredictionRequestSerializer(data=request.data)
            if not prediction_serializer.is_valid():
                return Response({
                    'success': False,
                    'errors': prediction_serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            data = prediction_serializer.validated_data
            disease_type = data['disease_type']
            parameters = data['parameters']
            
            # Get prediction from ML model (simplified)
            from prediction_app.ml_utils import predict_disease
            prediction_result = predict_disease(disease_type, parameters)
            
            # Save prediction to database
            prediction = Prediction.objects.create(
                user=request.api_key.user if request.api_key else None,
                disease_type=disease_type,
                input_data=parameters,
                prediction_result=prediction_result['prediction'],
                probability=prediction_result['probability'],
                confidence_level=prediction_result['confidence'],
                api_key=request.api_key
            )
            
            # Create notification
            Notification.objects.create(
                user=request.api_key.user,
                title=f"New {disease_type.replace('_', ' ').title()} Prediction",
                message=f"Your {disease_type.replace('_', ' ')} prediction is ready.",
                notification_type=Notification.NotificationType.PREDICTION,
                priority=Notification.Priority.MEDIUM,
                action_url=f"/predictions/{prediction.id}/"
            )
            
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            # Log API request
            self._log_request(request, status.HTTP_200_OK, response_time)
            
            # Prepare response
            response_data = {
                'success': True,
                'prediction_id': str(prediction.id),
                'disease_type': disease_type,
                'prediction': prediction_result['prediction'],
                'probability': prediction_result['probability'],
                'confidence_level': prediction_result['confidence'],
                'parameters_used': parameters,
                'timestamp': prediction.created_at.isoformat(),
                'recommendations': prediction_result.get('recommendations', []),
                'response_time_ms': response_time
            }
            
            return Response(response_data)
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self._log_request(request, status.HTTP_500_INTERNAL_SERVER_ERROR, response_time, str(e))
            
            return Response({
                'success': False,
                'error': 'Prediction failed',
                'message': str(e),
                'response_time_ms': response_time
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _log_request(self, request, status_code, response_time, error_message=None):
        """
        Log API request
        """
        if not hasattr(request, 'api_key'):
            return
        
        try:
            APILog.objects.create(
                api_key=request.api_key,
                method=request.method,
                endpoint=request.path,
                request_data=request.data,
                query_params=request.GET.dict(),
                status_code=status_code,
                response_time=response_time,
                error_message=error_message,
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                referer=request.META.get('HTTP_REFERER', None)
            )
        except Exception:
            # Don't crash if logging fails
            pass

    def _get_client_ip(self, request):
        """
        Get client IP address
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class SpecificDiseasePredictionView(PredictionAPIView):
    """
    API endpoint for specific disease predictions
    """
    def post(self, request, disease):
        """
        Make prediction for specific disease
        """
        request.data['disease_type'] = disease
        return super().post(request)


class UserProfileAPIView(APIView):
    """
    API endpoint for user profile
    """
    permission_classes = [HasAPIKey]
    throttle_classes = [UserRateThrottle]

    def get(self, request):
        """
        Get user profile information
        """
        user = request.api_key.user
        
        profile_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'date_joined': user.date_joined.isoformat(),
            'is_active': user.is_active,
            'profile': {
                'age': getattr(user.profile, 'age', None) if hasattr(user, 'profile') else None,
                'gender': getattr(user.profile, 'gender', None) if hasattr(user, 'profile') else None,
                'phone': getattr(user.profile, 'phone', None) if hasattr(user, 'profile') else None,
            }
        }
        
        return Response(profile_data)


class UserPredictionsAPIView(APIView):
    """
    API endpoint for user predictions
    """
    permission_classes = [HasAPIKey]
    throttle_classes = [UserRateThrottle]

    def get(self, request):
        """
        Get user prediction history
        """
        user = request.api_key.user
        
        # Get query parameters
        disease_type = request.GET.get('disease_type')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        limit = int(request.GET.get('limit', 50))
        offset = int(request.GET.get('offset', 0))
        
        # Filter predictions
        predictions = Prediction.objects.filter(user=user)
        
        if disease_type:
            predictions = predictions.filter(disease_type=disease_type)
        
        if start_date:
            predictions = predictions.filter(created_at__date__gte=start_date)
        
        if end_date:
            predictions = predictions.filter(created_at__date__lte=end_date)
        
        total_count = predictions.count()
        predictions = predictions.order_by('-created_at')[offset:offset + limit]
        
        # Prepare response
        prediction_list = []
        for prediction in predictions:
            prediction_list.append({
                'id': prediction.id,
                'disease_type': prediction.disease_type,
                'prediction': prediction.prediction_result,
                'probability': prediction.probability,
                'confidence_level': prediction.confidence_level,
                'created_at': prediction.created_at.isoformat(),
                'input_parameters': prediction.input_data
            })
        
        return Response({
            'success': True,
            'total_count': total_count,
            'count': len(prediction_list),
            'offset': offset,
            'limit': limit,
            'predictions': prediction_list
        })


class PredictionDetailAPIView(APIView):
    """
    API endpoint for specific prediction details
    """
    permission_classes = [HasAPIKey]
    throttle_classes = [UserRateThrottle]

    def get(self, request, prediction_id):
        """
        Get details of a specific prediction
        """
        prediction = get_object_or_404(
            Prediction,
            id=prediction_id,
            user=request.api_key.user
        )
        
        response_data = {
            'id': prediction.id,
            'disease_type': prediction.disease_type,
            'prediction': prediction.prediction_result,
            'probability': prediction.probability,
            'confidence_level': prediction.confidence_level,
            'input_data': prediction.input_data,
            'created_at': prediction.created_at.isoformat(),
            'updated_at': prediction.updated_at.isoformat(),
            'api_key_used': prediction.api_key.key_id if prediction.api_key else None
        }
        
        return Response(response_data)


class NotificationsAPIView(APIView):
    """
    API endpoint for user notifications
    """
    permission_classes = [HasAPIKey]
    throttle_classes = [UserRateThrottle]

    def get(self, request):
        """
        Get user notifications
        """
        user = request.api_key.user
        
        # Get query parameters
        is_read = request.GET.get('is_read')
        notification_type = request.GET.get('type')
        limit = int(request.GET.get('limit', 20))
        offset = int(request.GET.get('offset', 0))
        
        # Filter notifications
        notifications = Notification.objects.filter(user=user)
        
        if is_read in ['true', 'false']:
            notifications = notifications.filter(is_read=(is_read == 'true'))
        
        if notification_type:
            notifications = notifications.filter(notification_type=notification_type)
        
        total_count = notifications.count()
        notifications = notifications.order_by('-created_at')[offset:offset + limit]
        
        # Prepare response
        notification_list = []
        for notification in notifications:
            notification_list.append({
                'id': notification.id,
                'title': notification.title,
                'message': notification.message,
                'type': notification.notification_type,
                'priority': notification.priority,
                'is_read': notification.is_read,
                'action_url': notification.action_url,
                'created_at': notification.created_at.isoformat(),
                'read_at': notification.read_at.isoformat() if notification.read_at else None
            })
        
        return Response({
            'success': True,
            'total_count': total_count,
            'unread_count': Notification.objects.filter(user=user, is_read=False).count(),
            'count': len(notification_list),
            'offset': offset,
            'limit': limit,
            'notifications': notification_list
        })


class NotificationDetailAPIView(APIView):
    """
    API endpoint for specific notification
    """
    permission_classes = [HasAPIKey]
    throttle_classes = [UserRateThrottle]

    def get(self, request, notification_id):
        """
        Get specific notification
        """
        notification = get_object_or_404(
            Notification,
            id=notification_id,
            user=request.api_key.user
        )
        
        # Mark as read
        if not notification.is_read:
            notification.mark_as_read()
        
        response_data = {
            'id': notification.id,
            'title': notification.title,
            'message': notification.message,
            'type': notification.notification_type,
            'priority': notification.priority,
            'is_read': notification.is_read,
            'action_url': notification.action_url,
            'metadata': notification.metadata,
            'created_at': notification.created_at.isoformat(),
            'read_at': notification.read_at.isoformat() if notification.read_at else None
        }
        
        return Response(response_data)


class APIUsageStatsView(APIView):
    """
    API endpoint for usage statistics
    """
    permission_classes = [HasAPIKey]
    throttle_classes = [UserRateThrottle]

    def get(self, request):
        """
        Get API usage statistics
        """
        api_key = request.api_key
        
        # Get date range
        days = int(request.GET.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        
        # Get logs
        logs = APILog.objects.filter(
            api_key=api_key,
            created_at__gte=start_date
        )
        
        # Calculate statistics
        total_requests = logs.count()
        successful_requests = logs.filter(status_code__lt=400).count()
        failed_requests = logs.filter(status_code__gte=400).count()
        
        # Average response time
        avg_response_time = logs.aggregate(Avg('response_time'))['response_time__avg'] or 0
        
        # Requests by endpoint
        endpoint_stats = logs.values('endpoint').annotate(
            count=Count('id'),
            avg_time=Avg('response_time')
        ).order_by('-count')[:10]
        
        # Requests by status code
        status_stats = logs.values('status_code').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Daily requests
        daily_stats = []
        for i in range(days):
            date = timezone.now() - timedelta(days=i)
            date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            date_end = date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            daily_count = logs.filter(
                created_at__range=[date_start, date_end]
            ).count()
            
            daily_stats.append({
                'date': date.date().isoformat(),
                'count': daily_count
            })
        
        return Response({
            'api_key': api_key.key_id,
            'time_period': f'Last {days} days',
            'summary': {
                'total_requests': total_requests,
                'successful_requests': successful_requests,
                'failed_requests': failed_requests,
                'success_rate': (successful_requests / total_requests * 100) if total_requests > 0 else 0,
                'average_response_time_ms': round(avg_response_time, 2)
            },
            'endpoint_stats': list(endpoint_stats),
            'status_stats': list(status_stats),
            'daily_stats': daily_stats,
            'rate_limit': {
                'current_usage': api_key.requests_today,
                'daily_limit': api_key.rate_limit_per_day,
                'usage_percentage': (api_key.requests_today / api_key.rate_limit_per_day * 100) if api_key.rate_limit_per_day > 0 else 0
            }
        })


class PredictionStatsView(APIView):
    """
    API endpoint for prediction statistics
    """
    permission_classes = [HasAPIKey]
    throttle_classes = [UserRateThrottle]

    def get(self, request):
        """
        Get prediction statistics
        """
        user = request.api_key.user
        
        # Get predictions
        predictions = Prediction.objects.filter(user=user)
        
        # Statistics by disease
        disease_stats = predictions.values('disease_type').annotate(
            count=Count('id'),
            avg_probability=Avg('probability')
        ).order_by('-count')
        
        # Statistics by result
        result_stats = predictions.values('prediction_result').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Monthly predictions
        monthly_stats = []
        for i in range(6):  # Last 6 months
            month_start = timezone.now().replace(day=1) - timedelta(days=30 * i)
            month_end = month_start.replace(day=28) + timedelta(days=4)
            
            month_count = predictions.filter(
                created_at__range=[month_start, month_end]
            ).count()
            
            monthly_stats.append({
                'month': month_start.strftime('%Y-%m'),
                'count': month_count
            })
        
        return Response({
            'user': user.username,
            'total_predictions': predictions.count(),
            'disease_stats': list(disease_stats),
            'result_stats': list(result_stats),
            'monthly_stats': monthly_stats,
            'average_confidence': predictions.aggregate(Avg('probability'))['probability__avg'] or 0
        })


class APIVersionView(APIView):
    """
    API endpoint for version information
    """
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle]

    def get(self, request):
        """
        Get API version information
        """
        versions = APIVersion.objects.filter(is_active=True).order_by('-version')
        
        version_list = []
        for version in versions:
            version_list.append({
                'version': version.version,
                'is_deprecated': version.is_deprecated,
                'deprecation_date': version.deprecation_date.isoformat() if version.deprecation_date else None,
                'sunset_date': version.sunset_date.isoformat() if version.sunset_date else None,
                'documentation_url': version.documentation_url
            })
        
        return Response({
            'current_version': '1.0.0',
            'available_versions': version_list,
            'base_url': request.build_absolute_uri('/api/'),
            'documentation_url': request.build_absolute_uri('/api/docs/')
        })


class PredictionWebhookView(APIView):
    """
    Webhook endpoint for prediction completion
    """
    permission_classes = [HasAPIKey]

    def post(self, request):
        """
        Handle prediction webhook
        """
        # Verify webhook signature
        signature = request.META.get('HTTP_X_WEBHOOK_SIGNATURE')
        if not self._verify_webhook_signature(request, signature):
            return Response({
                'success': False,
                'error': 'Invalid signature'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Process webhook
        data = request.data
        
        # Here you would typically process the webhook data
        # For example, update prediction status, send notifications, etc.
        
        return Response({
            'success': True,
            'message': 'Webhook received'
        })

    def _verify_webhook_signature(self, request, signature):
        """
        Verify webhook signature
        """
        # Implement webhook signature verification
        # This is a simplified example
        api_key = request.api_key
        expected_signature = hashlib.sha256(
            f"{api_key.secret_key}{json.dumps(request.data)}".encode()
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)


class ErrorWebhookView(APIView):
    """
    Webhook endpoint for error reporting
    """
    permission_classes = [HasAPIKey]

    def post(self, request):
        """
        Handle error webhook
        """
        # Log error
        error_data = request.data
        
        # Here you would typically log the error to your error tracking system
        print(f"Error webhook received: {error_data}")
        
        return Response({
            'success': True,
            'message': 'Error logged'
        })


# ViewSets for admin management
class APIKeyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for APIKey model
    """
    serializer_class = APIKeySerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return APIKey.objects.all()
        return APIKey.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def regenerate(self, request, pk=None):
        """
        Regenerate secret key
        """
        api_key = self.get_object()
        api_key.secret_key = f"sk_{uuid.uuid4().hex[:32]}"
        api_key.save()
        
        return Response({
            'success': True,
            'secret_key': api_key.secret_key,
            'warning': 'Save the new secret key now. It will not be shown again!'
        })
    
    @action(detail=True, methods=['post'])
    def reset_rate_limit(self, request, pk=None):
        """
        Reset rate limit counters
        """
        api_key = self.get_object()
        api_key.requests_today = 0
        api_key.save()
        
        # Clear cache
        cache.delete(f"api_rate_limit:{api_key.key_id}:minute")
        cache.delete(f"api_rate_limit:{api_key.key_id}:hour")
        cache.delete(f"api_rate_limit:{api_key.key_id}:day")
        
        return Response({
            'success': True,
            'message': 'Rate limit counters reset'
        })


class APILogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for APILog model
    """
    serializer_class = APILogSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return APILog.objects.all()
        return APILog.objects.filter(api_key__user=self.request.user)


class APIVersionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for APIVersion model
    """
    queryset = APIVersion.objects.all()
    serializer_class = APIVersionSerializer
    permission_classes = [permissions.IsAdminUser]