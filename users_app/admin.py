from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserActivity, EmailVerification, PasswordResetToken

class UserAdmin(BaseUserAdmin):
    """Custom admin interface for User model"""
    
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'email_verified', 'date_joined')
    list_filter = ('is_staff', 'is_active', 'email_verified', 'gender', 'has_diabetes', 'has_hypertension')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone_number')
    ordering = ('-date_joined',)
    readonly_fields = ('last_login', 'created_at', 'updated_at')
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': (
            'first_name', 'last_name', 'email', 'phone_number',
            'date_of_birth', 'gender', 'profile_picture'
        )}),
        ('Medical Profile', {'fields': (
            'blood_group', 'height', 'weight',
            'has_diabetes', 'has_hypertension', 'has_heart_disease',
            'has_kidney_disease', 'has_liver_disease', 'family_history',
            'smokes', 'drinks_alcohol', 'exercise_frequency'
        )}),
        ('Permissions', {'fields': (
            'is_active', 'is_staff', 'is_superuser',
            'groups', 'user_permissions'
        )}),
        ('Preferences', {'fields': (
            'email_notifications', 'sms_notifications', 'dark_mode',
            'two_factor_enabled'
        )}),
        ('Important Dates', {'fields': (
            'last_login', 'date_joined', 'created_at', 'updated_at'
        )}),
        ('Verification', {'fields': ('email_verified', 'phone_verified')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username', 'email', 'password1', 'password2',
                'first_name', 'last_name', 'is_staff', 'is_active'
            ),
        }),
    )


class UserActivityAdmin(admin.ModelAdmin):
    """Admin interface for UserActivity model"""
    
    list_display = ('user', 'activity_type', 'ip_address', 'location', 'timestamp')
    list_filter = ('activity_type', 'timestamp')
    search_fields = ('user__username', 'user__email', 'ip_address', 'location')
    readonly_fields = ('timestamp',)
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        (None, {'fields': ('user', 'activity_type')}),
        ('Technical Details', {'fields': ('ip_address', 'user_agent', 'location')}),
        ('Additional Info', {'fields': ('timestamp', 'details')}),
    )


class EmailVerificationAdmin(admin.ModelAdmin):
    """Admin interface for EmailVerification model"""
    
    list_display = ('user', 'token', 'created_at', 'expires_at', 'verified')
    list_filter = ('verified', 'created_at')
    search_fields = ('user__username', 'user__email', 'token')
    readonly_fields = ('created_at',)
    
    fieldsets = (
        (None, {'fields': ('user', 'token')}),
        ('Status', {'fields': ('verified',)}),
        ('Timestamps', {'fields': ('created_at', 'expires_at')}),
    )


class PasswordResetTokenAdmin(admin.ModelAdmin):
    """Admin interface for PasswordResetToken model"""
    
    list_display = ('user', 'token', 'created_at', 'expires_at', 'used')
    list_filter = ('used', 'created_at')
    search_fields = ('user__username', 'user__email', 'token')
    readonly_fields = ('created_at',)
    
    fieldsets = (
        (None, {'fields': ('user', 'token')}),
        ('Status', {'fields': ('used',)}),
        ('Timestamps', {'fields': ('created_at', 'expires_at')}),
    )


# Register models
admin.site.register(User, UserAdmin)
admin.site.register(UserActivity, UserActivityAdmin)
admin.site.register(EmailVerification, EmailVerificationAdmin)
admin.site.register(PasswordResetToken, PasswordResetTokenAdmin)