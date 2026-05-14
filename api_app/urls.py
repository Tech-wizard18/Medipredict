from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'api'

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r'keys', views.APIKeyViewSet, basename='apikey')
router.register(r'logs', views.APILogViewSet, basename='apilog')
router.register(r'versions', views.APIVersionViewSet, basename='apiversion')

urlpatterns = [
    # API documentation
    path('', views.APIDocumentationView.as_view(), name='documentation'),
    path('docs/', views.APIDocumentationView.as_view(), name='docs'),
    
    # Authentication
    path('auth/generate-key/', views.GenerateAPIKeyView.as_view(), name='generate_key'),
    path('auth/verify/', views.VerifyAPIKeyView.as_view(), name='verify_key'),
    path('auth/revoke/<str:key_id>/', views.RevokeAPIKeyView.as_view(), name='revoke_key'),
    
    # API endpoints
    path('v1/', include([
        # Health check
        path('health/', views.HealthCheckView.as_view(), name='health_check'),
        
        # Predictions
        path('predict/', views.PredictionAPIView.as_view(), name='predict'),
        path('predict/<str:disease>/', views.SpecificDiseasePredictionView.as_view(), name='predict_disease'),
        
        # User data
        path('user/profile/', views.UserProfileAPIView.as_view(), name='user_profile'),
        path('user/predictions/', views.UserPredictionsAPIView.as_view(), name='user_predictions'),
        path('user/predictions/<int:prediction_id>/', views.PredictionDetailAPIView.as_view(), name='prediction_detail'),
        
        # Notifications
        path('notifications/', views.NotificationsAPIView.as_view(), name='notifications'),
        path('notifications/<int:notification_id>/', views.NotificationDetailAPIView.as_view(), name='notification_detail'),
        
        # Statistics
        path('stats/usage/', views.APIUsageStatsView.as_view(), name='usage_stats'),
        path('stats/predictions/', views.PredictionStatsView.as_view(), name='prediction_stats'),
    ])),
    
    # Router URLs
    path('management/', include(router.urls)),
    
    # API version handling
    path('version/', views.APIVersionView.as_view(), name='api_version'),
    
    # Webhook endpoints
    path('webhooks/prediction-complete/', views.PredictionWebhookView.as_view(), name='prediction_webhook'),
    path('webhooks/error-report/', views.ErrorWebhookView.as_view(), name='error_webhook'),
]

# Add versioned API patterns
urlpatterns += [
    path('v<int:version>/', include([
        path('predict/', views.PredictionAPIView.as_view(), name='predict_versioned'),
        path('health/', views.HealthCheckView.as_view(), name='health_check_versioned'),
    ])),
]