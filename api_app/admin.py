from django.contrib import admin
from .models import APIKey, APILog, APIRateLimit

@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ('key_id', 'name', 'user', 'is_active', 'requests_today', 'total_requests', 'created_at')
    list_filter = ('is_active', 'created_at', 'user')
    search_fields = ('key_id', 'name', 'user__username', 'user__email')
    readonly_fields = ('key_id', 'secret_key', 'created_at', 'last_used', 'total_requests')
    list_per_page = 25
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('key_id', 'name', 'user', 'description')
        }),
        ('Authentication', {
            'fields': ('secret_key', 'is_active')
        }),
        ('Rate Limiting', {
            'fields': ('rate_limit_per_minute', 'rate_limit_per_hour', 'rate_limit_per_day')
        }),
        ('Permissions', {
            'fields': ('allowed_ips', 'allowed_methods', 'allowed_endpoints')
        }),
        ('Usage Statistics', {
            'fields': ('requests_today', 'total_requests', 'last_used', 'created_at')
        }),
    )
    
    actions = ['activate_keys', 'deactivate_keys', 'reset_rate_limit']
    
    def activate_keys(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} API keys activated.')
    
    def deactivate_keys(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} API keys deactivated.')
    
    def reset_rate_limit(self, request, queryset):
        updated = queryset.update(requests_today=0)
        self.message_user(request, f'Rate limit reset for {updated} API keys.')

@admin.register(APILog)
class APILogAdmin(admin.ModelAdmin):
    list_display = ('id', 'api_key', 'method', 'endpoint', 'status_code', 'response_time', 'created_at')
    list_filter = ('method', 'status_code', 'created_at', 'api_key')
    search_fields = ('api_key__key_id', 'endpoint', 'ip_address', 'user_agent')
    readonly_fields = ('created_at',)
    list_per_page = 50
    
    fieldsets = (
        ('Request Details', {
            'fields': ('api_key', 'method', 'endpoint', 'request_data', 'query_params')
        }),
        ('Response Details', {
            'fields': ('status_code', 'response_data', 'response_time', 'error_message')
        }),
        ('Client Information', {
            'fields': ('ip_address', 'user_agent', 'referer')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )

@admin.register(APIRateLimit)
class APIRateLimitAdmin(admin.ModelAdmin):
    # FIXED: Use api_key instead of key_id or create a method
    list_display = ('api_key', 'minute_count', 'hour_count', 'day_count', 'updated_at')
    list_filter = ('updated_at',)
    search_fields = ('api_key__key_id', 'api_key__name')
    readonly_fields = ('updated_at',)
    list_per_page = 25