from django.urls import path, include
from django.contrib.auth.decorators import login_required
from . import views
from .api import views as api_views

app_name = 'prediction_app'

urlpatterns = [
    # Home page
    path('', views.home, name='home'),
    
    # Dashboard
    path('dashboard/', login_required(views.DashboardView.as_view()), name='dashboard'),
    
    # Disease prediction pages
    path('diabetes/', login_required(views.DiabetesPredictionView.as_view()), name='diabetes'),
    path('heart/', login_required(views.HeartDiseasePredictionView.as_view()), name='heart'),
    path('kidney/', login_required(views.KidneyDiseasePredictionView.as_view()), name='kidney'),
    path('parkinson/', login_required(views.ParkinsonPredictionView.as_view()), name='parkinson'),
    path('breast-cancer/', login_required(views.BreastCancerPredictionView.as_view()), name='breast_cancer'),
    path('liver/', login_required(views.LiverDiseasePredictionView.as_view()), name='liver'),
    
    # Prediction history
    path('history/', login_required(views.PredictionHistoryView.as_view()), name='history'),
    path('history/<int:pk>/', login_required(views.PredictionDetailView.as_view()), name='prediction_detail'),
    path('history/<int:pk>/delete/', login_required(views.PredictionDeleteView.as_view()), name='prediction_delete'),
    
    # Health reports
    path('reports/', login_required(views.HealthReportsView.as_view()), name='reports'),
    path('reports/<int:pk>/', login_required(views.HealthReportDetailView.as_view()), name='report_detail'),
    path('reports/<int:pk>/download/', login_required(views.download_health_report), name='download_report'),
    path('reports/generate/', login_required(views.generate_health_report), name='generate_report'),
    
    # Symptoms tracking
    path('symptoms/', login_required(views.SymptomsListView.as_view()), name='symptoms'),
    path('symptoms/add/', login_required(views.SymptomCreateView.as_view()), name='symptom_add'),
    path('symptoms/<int:pk>/edit/', login_required(views.SymptomUpdateView.as_view()), name='symptom_edit'),
    path('symptoms/<int:pk>/delete/', login_required(views.SymptomDeleteView.as_view()), name='symptom_delete'),
    
    # Prediction results
    path('results/<int:prediction_id>/', login_required(views.prediction_result), name='prediction_result'),
    path('results/<int:prediction_id>/save/', login_required(views.save_prediction_result), name='save_prediction_result'),
    
    # API endpoints (include API app URLs)
    path('api/', include('prediction_app.api.urls')),
    
    # WebSocket endpoint for real-time predictions
    path('ws/predictions/', views.PredictionWebSocketView.as_view(), name='prediction_ws'),
    
    # Export endpoints
    path('export/predictions/', login_required(views.export_predictions), name='export_predictions'),
    path('export/reports/', login_required(views.export_reports), name='export_reports'),
    
    # Analytics
    path('analytics/', login_required(views.AnalyticsView.as_view()), name='analytics'),
    path('analytics/data/', login_required(views.analytics_data), name='analytics_data'),
    
    # Model management (admin only)
    path('models/', login_required(views.ModelManagementView.as_view()), name='models'),
    path('models/<str:disease>/reload/', login_required(views.reload_model), name='reload_model'),
    
    # Settings
    path('settings/', login_required(views.PredictionSettingsView.as_view()), name='settings'),
    
    # Help and documentation
    path('help/', views.HelpView.as_view(), name='help'),
    path('documentation/', views.DocumentationView.as_view(), name='documentation'),
    
    # Error handling
    path('error/<str:error_type>/', views.error_view, name='error'),
    
    # Webhook for external integrations
    path('webhook/prediction/', views.prediction_webhook, name='prediction_webhook'),
]

# Additional patterns for specific formats
urlpatterns += [
    path('predictions.csv', login_required(views.export_predictions_csv), name='export_predictions_csv'),
    path('predictions.json', login_required(views.export_predictions_json), name='export_predictions_json'),
    path('reports.pdf', login_required(views.export_reports_pdf), name='export_reports_pdf'),
]

# AJAX endpoints
urlpatterns += [
    path('ajax/predict/<str:disease>/', login_required(views.ajax_predict), name='ajax_predict'),
    path('ajax/stats/', login_required(views.ajax_stats), name='ajax_stats'),
    path('ajax/recent-predictions/', login_required(views.ajax_recent_predictions), name='ajax_recent_predictions'),
    path('ajax/risk-assessment/', login_required(views.ajax_risk_assessment), name='ajax_risk_assessment'),
]

# Redirects for backward compatibility
urlpatterns += [
    path('old-diabetes/', views.redirect_to_diabetes, name='redirect_diabetes'),
    path('old-heart/', views.redirect_to_heart, name='redirect_heart'),
]

# Static pages
urlpatterns += [
    path('about-predictions/', views.AboutPredictionsView.as_view(), name='about_predictions'),
    path('privacy-policy/', views.PrivacyPolicyView.as_view(), name='privacy_policy'),
    path('terms-of-service/', views.TermsOfServiceView.as_view(), name='terms_of_service'),
]

# Search
urlpatterns += [
    path('search/', views.search_view, name='search'),
]

# Health check endpoint
urlpatterns += [
    path('health/', views.health_check, name='health_check'),
]

# Rate limiting info
urlpatterns += [
    path('rate-limit-info/', views.rate_limit_info, name='rate_limit_info'),
]

# WebSocket test page
urlpatterns += [
    path('ws-test/', views.WebSocketTestView.as_view(), name='ws_test'),
]