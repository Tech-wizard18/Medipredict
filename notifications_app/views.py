from django.shortcuts import render, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.views.generic import ListView, DetailView, TemplateView
from django.http import JsonResponse, HttpResponseForbidden
from django.db.models import Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
import json

from .models import Notification, NotificationPreference, NotificationTemplate
from .serializers import NotificationSerializer, NotificationPreferenceSerializer
from users_app.models import User


class NotificationListView(LoginRequiredMixin, ListView):
    """
    View for listing all notifications for a user
    """
    model = Notification
    template_name = 'notifications_app/notification_list.html'
    context_object_name = 'notifications'
    paginate_by = 20

    def get_queryset(self):
        queryset = Notification.objects.filter(user=self.request.user)
        
        # Filter by type if provided
        notification_type = self.request.GET.get('type')
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)
        
        # Filter by read status if provided
        is_read = self.request.GET.get('is_read')
        if is_read in ['true', 'false']:
            queryset = queryset.filter(is_read=(is_read == 'true'))
        
        # Filter by date range if provided
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unread_count'] = Notification.objects.filter(
            user=self.request.user,
            is_read=False
        ).count()
        context['notification_types'] = Notification.NotificationType.choices
        return context


class UnreadNotificationListView(LoginRequiredMixin, ListView):
    """
    View for listing unread notifications
    """
    model = Notification
    template_name = 'notifications_app/unread_notifications.html'
    context_object_name = 'notifications'
    paginate_by = 10

    def get_queryset(self):
        return Notification.objects.filter(
            user=self.request.user,
            is_read=False
        ).order_by('-created_at')


class NotificationDetailView(LoginRequiredMixin, DetailView):
    """
    View for displaying a single notification
    """
    model = Notification
    template_name = 'notifications_app/notification_detail.html'
    context_object_name = 'notification'

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        
        # Mark as read when viewed
        notification = self.get_object()
        if not notification.is_read:
            notification.mark_as_read()
        
        return response


class MarkAsReadView(LoginRequiredMixin, View):
    """
    API view to mark a notification as read
    """
    def post(self, request, pk):
        notification = get_object_or_404(
            Notification,
            pk=pk,
            user=request.user
        )
        notification.mark_as_read()
        return JsonResponse({
            'success': True,
            'message': 'Notification marked as read'
        })


class MarkAllAsReadView(LoginRequiredMixin, View):
    """
    API view to mark all notifications as read
    """
    def post(self, request):
        updated_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())
        
        return JsonResponse({
            'success': True,
            'message': f'{updated_count} notifications marked as read'
        })


class NotificationCountView(LoginRequiredMixin, View):
    """
    API view to get unread notification count
    """
    def get(self, request):
        unread_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        return JsonResponse({
            'unread_count': unread_count,
            'total_count': Notification.objects.filter(user=request.user).count()
        })


class NotificationPreferenceView(LoginRequiredMixin, TemplateView):
    """
    View for displaying and managing notification preferences
    """
    template_name = 'notifications_app/preferences.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get or create preferences
        preferences, created = NotificationPreference.objects.get_or_create(
            user=self.request.user
        )
        
        context['preferences'] = preferences
        context['notification_types'] = Notification.NotificationType.choices
        return context


class UpdateNotificationPreferenceView(LoginRequiredMixin, View):
    """
    API view to update notification preferences
    """
    def post(self, request):
        try:
            preferences = NotificationPreference.objects.get(user=request.user)
            data = json.loads(request.body)
            
            # Update email preferences
            if 'email_notifications' in data:
                preferences.email_notifications = data['email_notifications']
            if 'email_prediction_results' in data:
                preferences.email_prediction_results = data['email_prediction_results']
            if 'email_appointment_reminders' in data:
                preferences.email_appointment_reminders = data['email_appointment_reminders']
            if 'email_prescription_updates' in data:
                preferences.email_prescription_updates = data['email_prescription_updates']
            if 'email_security_alerts' in data:
                preferences.email_security_alerts = data['email_security_alerts']
            if 'email_promotional' in data:
                preferences.email_promotional = data['email_promotional']
            
            # Update push preferences
            if 'push_notifications' in data:
                preferences.push_notifications = data['push_notifications']
            if 'push_prediction_results' in data:
                preferences.push_prediction_results = data['push_prediction_results']
            if 'push_appointment_reminders' in data:
                preferences.push_appointment_reminders = data['push_appointment_reminders']
            
            # Update SMS preferences
            if 'sms_notifications' in data:
                preferences.sms_notifications = data['sms_notifications']
            if 'sms_important_alerts' in data:
                preferences.sms_important_alerts = data['sms_important_alerts']
            
            # Update frequency
            if 'notification_frequency' in data:
                preferences.notification_frequency = data['notification_frequency']
            
            # Update do not disturb
            if 'do_not_disturb_start' in data:
                preferences.do_not_disturb_start = data['do_not_disturb_start']
            if 'do_not_disturb_end' in data:
                preferences.do_not_disturb_end = data['do_not_disturb_end']
            
            preferences.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Preferences updated successfully'
            })
            
        except NotificationPreference.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Preferences not found'
            }, status=404)
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid JSON data'
            }, status=400)


class NotificationStatsView(LoginRequiredMixin, View):
    """
    View for notification statistics (admin only)
    """
    def get(self, request):
        if not request.user.is_staff:
            return HttpResponseForbidden("Access denied")
        
        # Date range for stats (default: last 30 days)
        days = int(request.GET.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        
        # Total notifications
        total_notifications = Notification.objects.filter(
            created_at__gte=start_date
        ).count()
        
        # Notifications by type
        notifications_by_type = Notification.objects.filter(
            created_at__gte=start_date
        ).values('notification_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Notifications by priority
        notifications_by_priority = Notification.objects.filter(
            created_at__gte=start_date
        ).values('priority').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Read vs unread
        read_count = Notification.objects.filter(
            created_at__gte=start_date,
            is_read=True
        ).count()
        unread_count = Notification.objects.filter(
            created_at__gte=start_date,
            is_read=False
        ).count()
        
        # Daily notifications for the last 7 days
        daily_stats = []
        for i in range(7):
            date = timezone.now() - timedelta(days=i)
            date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            date_end = date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            daily_count = Notification.objects.filter(
                created_at__range=[date_start, date_end]
            ).count()
            
            daily_stats.append({
                'date': date.date().isoformat(),
                'count': daily_count
            })
        
        return JsonResponse({
            'total_notifications': total_notifications,
            'read_count': read_count,
            'unread_count': unread_count,
            'read_rate': (read_count / total_notifications * 100) if total_notifications > 0 else 0,
            'notifications_by_type': list(notifications_by_type),
            'notifications_by_priority': list(notifications_by_priority),
            'daily_stats': daily_stats,
            'time_period': f'Last {days} days'
        })


class NotificationTemplateListView(LoginRequiredMixin, ListView):
    """
    View for listing notification templates (admin only)
    """
    model = NotificationTemplate
    template_name = 'notifications_app/template_list.html'
    context_object_name = 'templates'
    paginate_by = 20
    
    def get_queryset(self):
        if not self.request.user.is_staff:
            return NotificationTemplate.objects.none()
        
        queryset = NotificationTemplate.objects.all()
        
        # Filter by type
        template_type = self.request.GET.get('type')
        if template_type:
            queryset = queryset.filter(template_type=template_type)
        
        # Filter by active status
        is_active = self.request.GET.get('is_active')
        if is_active in ['true', 'false']:
            queryset = queryset.filter(is_active=(is_active == 'true'))
        
        return queryset.order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['template_types'] = NotificationTemplate.TemplateType.choices
        return context


class NotificationTemplateDetailView(LoginRequiredMixin, DetailView):
    """
    View for displaying notification template details (admin only)
    """
    model = NotificationTemplate
    template_name = 'notifications_app/template_detail.html'
    context_object_name = 'template'
    
    def get_queryset(self):
        if not self.request.user.is_staff:
            return NotificationTemplate.objects.none()
        return NotificationTemplate.objects.all()