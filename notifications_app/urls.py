from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # Notification endpoints
    path('', views.NotificationListView.as_view(), name='notification_list'),
    path('unread/', views.UnreadNotificationListView.as_view(), name='unread_notifications'),
    path('<int:pk>/', views.NotificationDetailView.as_view(), name='notification_detail'),
    path('<int:pk>/read/', views.MarkAsReadView.as_view(), name='mark_as_read'),
    path('mark-all-read/', views.MarkAllAsReadView.as_view(), name='mark_all_read'),
    path('count/', views.NotificationCountView.as_view(), name='notification_count'),
    
    # Preferences endpoints
    path('preferences/', views.NotificationPreferenceView.as_view(), name='preferences'),
    path('preferences/update/', views.UpdateNotificationPreferenceView.as_view(), name='update_preferences'),
    
    # Admin/Stats endpoints
    path('stats/', views.NotificationStatsView.as_view(), name='notification_stats'),
    path('templates/', views.NotificationTemplateListView.as_view(), name='template_list'),
    path('templates/<int:pk>/', views.NotificationTemplateDetailView.as_view(), name='template_detail'),
]