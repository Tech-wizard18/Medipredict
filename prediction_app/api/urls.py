from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'predictions', views.PredictionViewSet, basename='prediction')
router.register(r'health-reports', views.HealthReportViewSet, basename='health-report')
router.register(r'symptoms', views.SymptomViewSet, basename='symptom')
router.register(r'patient-symptoms', views.PatientSymptomViewSet, basename='patient-symptom')
router.register(r'disease-models', views.DiseaseModelViewSet, basename='disease-model')

urlpatterns = [
    path('', include(router.urls)),
    
    # Prediction endpoints
    path('predict/diabetes/', views.PredictDiabetesView.as_view(), name='predict_diabetes'),
    path('predict/heart/', views.PredictHeartDiseaseView.as_view(), name='predict_heart'),
    path('predict/kidney/', views.PredictKidneyDiseaseView.as_view(), name='predict_kidney'),
    path('predict/parkinson/', views.PredictParkinsonView.as_view(), name='predict_parkinson'),
    path('predict/breast-cancer/', views.PredictBreastCancerView.as_view(), name='predict_breast_cancer'),
    path('predict/liver/', views.PredictLiverDiseaseView.as_view(), name='predict_liver'),
    path('predict/<str:disease>/', views.PredictDiseaseView.as_view(), name='predict_disease'),
    
    # Analytics endpoints
    path('analytics/stats/', views.AnalyticsStatsView.as_view(), name='analytics_stats'),
    path('analytics/trends/', views.AnalyticsTrendsView.as_view(), name='analytics_trends'),
    path('analytics/disease-distribution/', views.DiseaseDistributionView.as_view(), name='disease_distribution'),
    
    # Report generation
    path('reports/generate/', views.GenerateReportView.as_view(), name='generate_report'),
    path('reports/<int:pk>/download/', views.DownloadReportView.as_view(), name='download_report'),
    
    # Model management (admin only)
    path('models/status/', views.ModelStatusView.as_view(), name='model_status'),
    path('models/<str:disease>/reload/', views.ReloadModelView.as_view(), name='reload_model'),
    path('models/<str:disease>/retrain/', views.RetrainModelView.as_view(), name='retrain_model'),
    
    # Export endpoints
    path('export/predictions/csv/', views.ExportPredictionsCSVView.as_view(), name='export_predictions_csv'),
    path('export/predictions/json/', views.ExportPredictionsJSONView.as_view(), name='export_predictions_json'),
    path('export/reports/pdf/', views.ExportReportsPDFView.as_view(), name='export_reports_pdf'),
    
    # Batch operations
    path('batch/predict/', views.BatchPredictView.as_view(), name='batch_predict'),
    path('batch/symptoms/', views.BatchSymptomsView.as_view(), name='batch_symptoms'),
    
    # Webhook endpoints
    path('webhook/prediction/', views.PredictionWebhookView.as_view(), name='prediction_webhook'),
    path('webhook/health-alert/', views.HealthAlertWebhookView.as_view(), name='health_alert_webhook'),
    
    # Health check
    path('health/', views.APIHealthCheckView.as_view(), name='api_health_check'),
    
    # Version info
    path('version/', views.APIVersionView.as_view(), name='api_version'),
    
    # Rate limit info
    path('rate-limits/', views.RateLimitInfoView.as_view(), name='rate_limit_info'),
]