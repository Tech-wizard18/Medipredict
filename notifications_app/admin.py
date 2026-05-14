from django.contrib import admin
from .models import Notification, NotificationPreference, NotificationTemplate

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'title', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at', 'priority')
    search_fields = ('user__username', 'user__email', 'title', 'message')
    readonly_fields = ('created_at',)
    list_per_page = 25
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'title', 'message', 'notification_type')
        }),
        ('Status & Priority', {
            'fields': ('is_read', 'priority', 'action_url')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'read_at')
        }),
    )

@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'email_notifications', 'push_notifications', 'sms_notifications')
    list_filter = ('email_notifications', 'push_notifications', 'sms_notifications')
    search_fields = ('user__username', 'user__email')
    list_per_page = 25

@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'template_type', 'is_active', 'created_at')
    list_filter = ('template_type', 'is_active')
    search_fields = ('name', 'subject', 'body')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 25
    
    fieldsets = (
        ('Template Information', {
            'fields': ('name', 'description', 'template_type', 'is_active')
        }),
        ('Content', {
            'fields': ('subject', 'body')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )