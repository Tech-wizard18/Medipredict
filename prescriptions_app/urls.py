from django.urls import path
from . import views

app_name = 'prescriptions_app'

urlpatterns = [
    # Prescription URLs
    path('', views.prescription_list_view, name='prescription_list'),
    path('create/', views.create_prescription_view, name='create_prescription'),
    path('<int:prescription_id>/', views.prescription_detail_view, name='prescription_detail'),
    path('<int:prescription_id>/edit/', views.edit_prescription_view, name='edit_prescription'),
    path('<int:prescription_id>/print/', views.prescription_print_view, name='print_prescription'),
    
    # Refill URLs
    path('<int:prescription_id>/refill/', views.request_refill_view, name='request_refill'),
    path('refills/manage/', views.manage_refill_requests_view, name='manage_refill_requests'),
    path('refills/<int:request_id>/process/', views.process_refill_request_view, name='process_refill_request'),
    
    # Medicine URLs
    path('medicines/', views.medicine_list_view, name='medicine_list'),
    path('medicines/add/', views.add_medicine_view, name='add_medicine'),
    path('medicines/<int:medicine_id>/', views.medicine_detail_view, name='medicine_detail'),
    path('medicines/<int:medicine_id>/edit/', views.edit_medicine_view, name='edit_medicine'),
    
    # History URLs
    path('history/', views.medication_history_view, name='medication_history'),
    
    # Drug Interaction URLs
    path('interactions/', views.drug_interactions_view, name='drug_interactions'),
    
    # Pharmacy URLs
    path('pharmacies/', views.pharmacy_finder_view, name='pharmacy_finder'),
    path('pharmacies/<int:pharmacy_id>/', views.pharmacy_detail_view, name='pharmacy_detail'),
    
    # Alert URLs
    path('alerts/', views.alerts_view, name='alerts'),
    path('alerts/<int:alert_id>/resolve/', views.mark_alert_resolved_view, name='mark_alert_resolved'),
    
    # Dashboard
    path('dashboard/', views.dashboard_view, name='dashboard'),
    
    # Export URLs
    path('export/csv/', views.export_prescriptions_csv, name='export_csv'),
    
    # API URLs
    path('api/medicines/search/', views.api_search_medicines, name='api_search_medicines'),
    path('api/medicines/<int:medicine_id>/', views.api_medicine_detail, name='api_medicine_detail'),
]   