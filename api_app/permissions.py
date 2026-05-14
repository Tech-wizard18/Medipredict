from rest_framework import permissions
from django.utils import timezone
from .models import APIKey
import json
import hashlib
import hmac
import base64
import time


class HasAPIKey(permissions.BasePermission):
    """
    Custom permission to check API key authentication
    """
    message = 'Invalid or missing API key'

    def has_permission(self, request, view):
        # Get API key from headers
        api_key_id = request.META.get('HTTP_X_API_KEY')
        signature = request.META.get('HTTP_X_SIGNATURE')
        timestamp = request.META.get('HTTP_X_TIMESTAMP')

        # Check if all required headers are present
        if not all([api_key_id, signature, timestamp]):
            return False

        try:
            # Validate timestamp (5 minute window)
            current_time = int(time.time())
            if abs(current_time - int(timestamp)) > 300:
                return False

            # Get API key from database
            api_key = APIKey.objects.get(
                key_id=api_key_id,
                is_active=True
            )

            # Check if API key is expired
            if api_key.is_expired():
                return False

            # Check IP restrictions
            client_ip = self._get_client_ip(request)
            if not api_key.is_allowed_ip(client_ip):
                return False

            # Check method restrictions
            if not api_key.is_allowed_method(request.method):
                return False

            # Check endpoint restrictions
            if not api_key.is_allowed_endpoint(request.path):
                return False

            # Check rate limits
            is_allowed, limit_type = api_key.check_rate_limit()
            if not is_allowed:
                # Set rate limit exceeded flag
                request.rate_limit_exceeded = True
                request.rate_limit_type = limit_type
                return True  # Still return True so we can handle rate limit in view

            # Verify signature
            body = None
            if request.body and request.method in ['POST', 'PUT', 'PATCH']:
                try:
                    body = json.loads(request.body.decode('utf-8'))
                except:
                    body = None

            expected_signature = api_key.generate_signature(
                timestamp=timestamp,
                method=request.method,
                endpoint=request.path,
                body=body
            )

            if not hmac.compare_digest(signature, expected_signature):
                return False

            # Increment rate limit
            api_key.increment_rate_limit()

            # Attach API key to request for later use
            request.api_key = api_key

            return True

        except APIKey.DoesNotExist:
            return False
        except Exception as e:
            # Log error for debugging
            if hasattr(view, '_log_auth_error'):
                view._log_auth_error(request, str(e))
            return False

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


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Object-level permission to only allow owners or admins to access an object
    """
    def has_object_permission(self, request, view, obj):
        # Check if user is admin
        if request.user.is_staff:
            return True

        # Check if user is owner
        if hasattr(obj, 'user'):
            return obj.user == request.user

        # For APIKey, check if user is the owner
        if isinstance(obj, APIKey):
            return obj.user == request.user

        return False


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Permission to allow read-only access to everyone, but write only to admins
    """
    def has_permission(self, request, view):
        # Allow GET, HEAD, OPTIONS requests
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions only for admin users
        return request.user and request.user.is_staff


class RateLimitExceeded(permissions.BasePermission):
    """
    Permission to handle rate limit exceeded
    """
    message = 'Rate limit exceeded'

    def has_permission(self, request, view):
        # Check if rate limit was exceeded in HasAPIKey permission
        if hasattr(request, 'rate_limit_exceeded') and request.rate_limit_exceeded:
            # Set rate limit info on request
            request.rate_limit_info = {
                'type': request.rate_limit_type,
                'message': f'Rate limit exceeded for {request.rate_limit_type}'
            }
            return False
        return True


class HasAPIAccess(permissions.BasePermission):
    """
    Permission to check if user has API access
    """
    message = 'API access is not enabled for your account'

    def has_permission(self, request, view):
        # Check if user has API access enabled
        if hasattr(request.user, 'profile'):
            return getattr(request.user.profile, 'api_access_enabled', False)
        return False


class IsValidAPIKey(permissions.BasePermission):
    """
    Simplified API key permission (for less sensitive endpoints)
    """
    message = 'Invalid API key'

    def has_permission(self, request, view):
        api_key_id = request.META.get('HTTP_X_API_KEY')
        
        if not api_key_id:
            return False

        try:
            api_key = APIKey.objects.get(
                key_id=api_key_id,
                is_active=True
            )
            
            # Check rate limit
            is_allowed, limit_type = api_key.check_rate_limit()
            if not is_allowed:
                request.rate_limit_exceeded = True
                request.rate_limit_type = limit_type
                return True
            
            # Increment rate limit
            api_key.increment_rate_limit()
            
            # Attach API key to request
            request.api_key = api_key
            
            return True
            
        except APIKey.DoesNotExist:
            return False