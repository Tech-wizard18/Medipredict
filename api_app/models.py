import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.cache import cache
from datetime import datetime, timedelta
import json
import hashlib
import hmac
import base64

User = get_user_model()


class APIKey(models.Model):
    """
    Model for API Key authentication
    """
    key_id = models.CharField(
        max_length=50,
        unique=True,
        editable=False,
        verbose_name='Key ID'
    )
    secret_key = models.CharField(
        max_length=100,
        unique=True,
        editable=False,
        verbose_name='Secret Key'
    )
    name = models.CharField(max_length=100, verbose_name='API Key Name')
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='api_keys',
        verbose_name='User'
    )
    description = models.TextField(blank=True, verbose_name='Description')
    is_active = models.BooleanField(default=True, verbose_name='Is Active')
    
    # Rate limiting
    rate_limit_per_minute = models.IntegerField(default=60, verbose_name='Requests per Minute')
    rate_limit_per_hour = models.IntegerField(default=1000, verbose_name='Requests per Hour')
    rate_limit_per_day = models.IntegerField(default=10000, verbose_name='Requests per Day')
    
    # Permissions
    allowed_ips = models.JSONField(
        default=list,
        blank=True,
        help_text='List of allowed IP addresses (empty for all)',
        verbose_name='Allowed IPs'
    )
    
    allowed_methods = models.CharField(
        max_length=255,
        default='["GET","POST","PUT","DELETE"]',  # JSON string
        help_text='List of allowed HTTP methods (JSON array)',
        verbose_name='Allowed Methods'
    )

    allowed_endpoints = models.TextField(
        default='[]',  # JSON string
        blank=True,
        help_text='List of allowed endpoints (JSON array, empty for all)',
        verbose_name='Allowed Endpoints'
    )
    
    # Usage tracking
    requests_today = models.IntegerField(default=0, verbose_name='Requests Today')
    total_requests = models.IntegerField(default=0, verbose_name='Total Requests')
    last_used = models.DateTimeField(null=True, blank=True, verbose_name='Last Used')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name='Expires At')
    
    class Meta:
        verbose_name = 'API Key'
        verbose_name_plural = 'API Keys'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['key_id']),
            models.Index(fields=['user']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.name} ({self.key_id})"

    def save(self, *args, **kwargs):
        if not self.key_id:
            self.key_id = f"api_{uuid.uuid4().hex[:16]}"
        if not self.secret_key:
            self.secret_key = f"sk_{uuid.uuid4().hex[:32]}"
        super().save(*args, **kwargs)

    def generate_signature(self, timestamp, method, endpoint, body=None):
        """
        Generate HMAC signature for API requests
        """
        message = f"{timestamp}{method}{endpoint}"
        if body:
            message += json.dumps(body, sort_keys=True)
        
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        return base64.b64encode(signature).decode('utf-8')

    def check_rate_limit(self):
        """
        Check if rate limit is exceeded
        """
        cache_key_minute = f"api_rate_limit:{self.key_id}:minute"
        cache_key_hour = f"api_rate_limit:{self.key_id}:hour"
        cache_key_day = f"api_rate_limit:{self.key_id}:day"
        
        # Get current counts
        minute_count = cache.get(cache_key_minute, 0)
        hour_count = cache.get(cache_key_hour, 0)
        day_count = cache.get(cache_key_day, 0)
        
        # Check limits
        if minute_count >= self.rate_limit_per_minute:
            return False, 'minute'
        if hour_count >= self.rate_limit_per_hour:
            return False, 'hour'
        if day_count >= self.rate_limit_per_day:
            return False, 'day'
        
        return True, None

    def increment_rate_limit(self):
        """
        Increment rate limit counters
        """
        now = timezone.now()
        
        # Minute counter
        cache_key_minute = f"api_rate_limit:{self.key_id}:minute"
        minute_count = cache.get(cache_key_minute, 0)
        cache.set(cache_key_minute, minute_count + 1, timeout=60)
        
        # Hour counter
        cache_key_hour = f"api_rate_limit:{self.key_id}:hour"
        hour_count = cache.get(cache_key_hour, 0)
        cache.set(cache_key_hour, hour_count + 1, timeout=3600)
        
        # Day counter
        cache_key_day = f"api_rate_limit:{self.key_id}:day"
        day_count = cache.get(cache_key_day, 0)
        cache.set(cache_key_day, day_count + 1, timeout=86400)
        
        # Update model statistics
        self.requests_today = day_count + 1
        self.total_requests += 1
        self.last_used = now
        self.save(update_fields=['requests_today', 'total_requests', 'last_used'])

    def is_allowed_ip(self, ip_address):
        """
        Check if IP address is allowed
        """
        if not self.allowed_ips:
            return True
        return ip_address in self.allowed_ips

    def is_allowed_method(self, method):
        """
        Check if HTTP method is allowed
        """
        return method in self.allowed_methods

    def is_allowed_endpoint(self, endpoint):
        """
        Check if endpoint is allowed
        """
        if not self.allowed_endpoints:
            return True
        
        for pattern in self.allowed_endpoints:
            if endpoint.startswith(pattern):
                return True
        
        return False

    def is_expired(self):
        """
        Check if API key is expired
        """
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at


class APILog(models.Model):
    """
    Model for logging API requests
    """
    api_key = models.ForeignKey(
        APIKey,
        on_delete=models.SET_NULL,
        null=True,
        related_name='logs',
        verbose_name='API Key'
    )
    
    # Request details
    method = models.CharField(max_length=10, verbose_name='HTTP Method')
    endpoint = models.CharField(max_length=500, verbose_name='Endpoint')
    request_data = models.JSONField(null=True, blank=True, verbose_name='Request Data')
    query_params = models.JSONField(null=True, blank=True, verbose_name='Query Parameters')
    
    # Response details
    status_code = models.IntegerField(verbose_name='Status Code')
    response_data = models.JSONField(null=True, blank=True, verbose_name='Response Data')
    response_time = models.FloatField(verbose_name='Response Time (ms)')
    error_message = models.TextField(blank=True, null=True, verbose_name='Error Message')
    
    # Client information
    ip_address = models.GenericIPAddressField(verbose_name='IP Address')
    user_agent = models.TextField(verbose_name='User Agent')
    referer = models.URLField(blank=True, null=True, verbose_name='Referer')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    
    class Meta:
        verbose_name = 'API Log'
        verbose_name_plural = 'API Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['api_key', 'created_at']),
            models.Index(fields=['status_code']),
            models.Index(fields=['endpoint']),
            models.Index(fields=['ip_address']),
        ]

    def __str__(self):
        return f"{self.method} {self.endpoint} - {self.status_code}"

    def save(self, *args, **kwargs):
        # Truncate long fields
        if len(self.endpoint) > 500:
            self.endpoint = self.endpoint[:500]
        if self.user_agent and len(self.user_agent) > 1000:
            self.user_agent = self.user_agent[:1000]
        super().save(*args, **kwargs)


class APIRateLimit(models.Model):
    """
    Model for tracking rate limits (alternative to cache)
    """
    api_key = models.OneToOneField(
        APIKey,
        on_delete=models.CASCADE,
        related_name='rate_limit',
        verbose_name='API Key'
    )
    
    # Counter fields
    minute_count = models.IntegerField(default=0, verbose_name='Minute Count')
    hour_count = models.IntegerField(default=0, verbose_name='Hour Count')
    day_count = models.IntegerField(default=0, verbose_name='Day Count')
    
    # Timestamps for resetting
    minute_window_start = models.DateTimeField(auto_now_add=True, verbose_name='Minute Window Start')
    hour_window_start = models.DateTimeField(auto_now_add=True, verbose_name='Hour Window Start')
    day_window_start = models.DateTimeField(auto_now_add=True, verbose_name='Day Window Start')
    
    # Last update
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    
    class Meta:
        verbose_name = 'API Rate Limit'
        verbose_name_plural = 'API Rate Limits'

    def __str__(self):
        return f"Rate limit for {self.api_key.key_id}"

    def check_and_increment(self):
        """
        Check rate limits and increment counters
        """
        now = timezone.now()
        
        # Reset counters if window has passed
        if now - self.minute_window_start > timedelta(minutes=1):
            self.minute_count = 0
            self.minute_window_start = now
        
        if now - self.hour_window_start > timedelta(hours=1):
            self.hour_count = 0
            self.hour_window_start = now
        
        if now - self.day_window_start > timedelta(days=1):
            self.day_count = 0
            self.day_window_start = now
        
        # Check limits
        if self.minute_count >= self.api_key.rate_limit_per_minute:
            return False, 'minute'
        if self.hour_count >= self.api_key.rate_limit_per_hour:
            return False, 'hour'
        if self.day_count >= self.api_key.rate_limit_per_day:
            return False, 'day'
        
        # Increment counters
        self.minute_count += 1
        self.hour_count += 1
        self.day_count += 1
        self.save()
        
        return True, None


class APIVersion(models.Model):
    """
    Model for API version management
    """
    version = models.CharField(max_length=20, unique=True, verbose_name='API Version')
    is_active = models.BooleanField(default=True, verbose_name='Is Active')
    is_deprecated = models.BooleanField(default=False, verbose_name='Is Deprecated')
    deprecation_date = models.DateField(null=True, blank=True, verbose_name='Deprecation Date')
    sunset_date = models.DateField(null=True, blank=True, verbose_name='Sunset Date')
    
    # Documentation
    changelog = models.TextField(blank=True, verbose_name='Changelog')
    documentation_url = models.URLField(blank=True, verbose_name='Documentation URL')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    
    class Meta:
        verbose_name = 'API Version'
        verbose_name_plural = 'API Versions'
        ordering = ['-version']

    def __str__(self):
        return f"API v{self.version}"