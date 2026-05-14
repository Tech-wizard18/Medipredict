"""
Custom error handlers for MEDIPREDICT project.

This module provides custom error pages and error handling
for different HTTP error codes.
"""

import logging
from django.shortcuts import render
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.db import DatabaseError

logger = logging.getLogger(__name__)


def bad_request(request, exception=None):
    """
    Custom 400 Bad Request error handler.
    """
    logger.warning(f"Bad request: {request.path} - {exception}")
    
    if request.headers.get('Accept') == 'application/json':
        return JsonResponse({
            'error': 'Bad Request',
            'message': 'The request could not be understood by the server.',
            'status': 400
        }, status=400)
    
    context = {
        'error_code': 400,
        'error_title': 'Bad Request',
        'error_message': 'The request could not be understood by the server.',
        'suggestions': [
            'Check the URL for errors',
            'Clear your browser cache and cookies',
            'Try again later'
        ]
    }
    return render(request, 'error_pages/400.html', context, status=400)


def permission_denied(request, exception=None):
    """
    Custom 403 Forbidden error handler.
    """
    logger.warning(f"Permission denied: {request.path} - {exception}")
    
    if request.headers.get('Accept') == 'application/json':
        return JsonResponse({
            'error': 'Forbidden',
            'message': 'You do not have permission to access this resource.',
            'status': 403
        }, status=403)
    
    context = {
        'error_code': 403,
        'error_title': 'Access Denied',
        'error_message': 'You do not have permission to access this page.',
        'suggestions': [
            'Login with a different account',
            'Contact the administrator for access',
            'Return to the homepage'
        ]
    }
    return render(request, 'error_pages/403.html', context, status=403)


def page_not_found(request, exception=None):
    """
    Custom 404 Not Found error handler.
    """
    logger.warning(f"Page not found: {request.path} - {exception}")
    
    if request.headers.get('Accept') == 'application/json':
        return JsonResponse({
            'error': 'Not Found',
            'message': 'The requested resource was not found.',
            'status': 404
        }, status=404)
    
    context = {
        'error_code': 404,
        'error_title': 'Page Not Found',
        'error_message': 'The page you are looking for does not exist.',
        'suggestions': [
            'Check the URL for typos',
            'Go back to the previous page',
            'Visit our homepage',
            'Use the search function'
        ]
    }
    return render(request, 'error_pages/404.html', context, status=404)


def server_error(request, exception=None):
    """
    Custom 500 Internal Server Error handler.
    """
    logger.error(f"Server error: {request.path} - {exception}")
    
    if request.headers.get('Accept') == 'application/json':
        return JsonResponse({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred on the server.',
            'status': 500
        }, status=500)
    
    context = {
        'error_code': 500,
        'error_title': 'Internal Server Error',
        'error_message': 'Something went wrong on our end. We are working to fix it.',
        'suggestions': [
            'Try refreshing the page',
            'Clear your browser cache',
            'Try again in a few minutes',
            'Contact support if the problem persists'
        ]
    }
    return render(request, 'error_pages/500.html', context, status=500)


def database_error(request, exception=None):
    """
    Custom database error handler.
    """
    logger.error(f"Database error: {exception}")
    
    if request.headers.get('Accept') == 'application/json':
        return JsonResponse({
            'error': 'Database Error',
            'message': 'A database error occurred. Please try again later.',
            'status': 503
        }, status=503)
    
    context = {
        'error_code': 503,
        'error_title': 'Service Unavailable',
        'error_message': 'We are experiencing database issues. Please try again later.',
        'suggestions': [
            'Try again in a few minutes',
            'Check our status page for updates',
            'Contact support if the problem persists'
        ]
    }
    return render(request, 'error_pages/503.html', context, status=503)


def csrf_failure(request, reason=""):
    """
    Custom CSRF failure handler.
    """
    logger.warning(f"CSRF failure: {request.path} - {reason}")
    
    if request.headers.get('Accept') == 'application/json':
        return JsonResponse({
            'error': 'CSRF Verification Failed',
            'message': 'Your session has expired or the request was invalid.',
            'status': 403
        }, status=403)
    
    context = {
        'error_code': 403,
        'error_title': 'Session Expired',
        'error_message': 'Your session has expired. Please refresh the page and try again.',
        'suggestions': [
            'Refresh the page',
            'Clear your browser cookies',
            'Login again if necessary'
        ]
    }
    return render(request, 'error_pages/csrf.html', context, status=403)


def handle_exception(request, exception):
    """
    Generic exception handler.
    """
    logger.exception(f"Unhandled exception: {exception}")
    
    # Check for specific exception types
    if isinstance(exception, DatabaseError):
        return database_error(request, exception)
    elif isinstance(exception, PermissionDenied):
        return permission_denied(request, exception)
    
    # Default to server error
    return server_error(request, exception)