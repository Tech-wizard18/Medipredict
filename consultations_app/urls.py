from django.urls import path
from . import views

app_name = 'consultations'

urlpatterns = [
    # Doctor List & Search
    path('doctors/', views.doctor_list_view, name='doctor_list'),
    path('doctors/<int:doctor_id>/', views.doctor_detail_view, name='doctor_detail'),
    
    # Consultation Booking
    path('doctors/<int:doctor_id>/book/', views.book_consultation_view, name='book_consultation'),
    
    # Patient Views
    path('my-consultations/', views.my_consultations_view, name='my_consultations'),
    path('consultation/<int:consultation_id>/', views.consultation_detail_view, name='consultation_detail'),
    path('consultation/<int:consultation_id>/review/', views.submit_review_view, name='submit_review'),
    
    # Doctor Views
    path('doctor/consultations/', views.doctor_consultations_view, name='doctor_consultations'),
    path('doctor/consultation/<int:consultation_id>/', views.doctor_consultation_detail_view, name='doctor_consultation_detail'),
    path('doctor/dashboard/', views.doctor_dashboard_view, name='doctor_dashboard'),
    path('doctor/slots/', views.manage_slots_view, name='manage_slots'),
    
    # Prescription Management
    path('consultation/<int:consultation_id>/prescription/create/', 
         views.create_prescription_view, name='create_prescription'),
    
    # Messaging
    path('consultation/<int:consultation_id>/send-message/', 
         views.send_message_view, name='send_message'),
    path('consultation/<int:consultation_id>/get-messages/', 
         views.get_messages_view, name='get_messages'),
    
    # Slot Management
    path('slot/<int:slot_id>/delete/', views.delete_slot_view, name='delete_slot'),
    
    # Notifications
    path('notifications/', views.notifications_view, name='notifications'),
]