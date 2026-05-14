from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'users_app'

urlpatterns = [
    # Authentication URLs
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Profile URLs
    path('profile/', views.profile_view, name='profile'),
    path('profile/setup/', views.profile_setup_view, name='profile_setup'),
    path('profile/change-password/', views.change_password_view, name='change_password'),
    
    # Email Verification URLs
    path('verify-email/<str:token>/', views.verify_email_view, name='verify_email'),
    path('resend-verification/', views.resend_verification_email_view, name='resend_verification'),
    
    # Password Reset URLs
    path('password-reset/', views.password_reset_request_view, name='password_reset_request'),
    path('password-reset/<str:token>/', views.password_reset_view, name='password_reset'),
    
    # Account Management URLs
    path('profile/notifications/', views.update_notification_settings, name='update_notifications'),
    path('profile/delete/', views.delete_account_view, name='delete_account'),
    
    # API/JSON URLs
    path('api/update-settings/', views.update_notification_settings, name='api_update_settings'),
]