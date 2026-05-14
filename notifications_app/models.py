from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import json

User = get_user_model()


class Notification(models.Model):
    """
    Model for storing user notifications
    """
    class NotificationType(models.TextChoices):
        SYSTEM = 'system', 'System Notification'
        PREDICTION = 'prediction', 'Prediction Result'
        APPOINTMENT = 'appointment', 'Appointment Reminder'
        PRESCRIPTION = 'prescription', 'Prescription Update'
        SECURITY = 'security', 'Security Alert'
        HEALTH_TIP = 'health_tip', 'Health Tip'
        PROMOTIONAL = 'promotional', 'Promotional'

    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'
        CRITICAL = 'critical', 'Critical'

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='User'
    )
    title = models.CharField(max_length=200, verbose_name='Notification Title')
    message = models.TextField(verbose_name='Notification Message')
    notification_type = models.CharField(
        max_length=50,
        choices=NotificationType.choices,
        default=NotificationType.SYSTEM,
        verbose_name='Notification Type'
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        verbose_name='Priority'
    )
    is_read = models.BooleanField(default=False, verbose_name='Is Read')
    action_url = models.URLField(blank=True, null=True, verbose_name='Action URL')
    metadata = models.JSONField(default=dict, blank=True, verbose_name='Additional Data')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    read_at = models.DateTimeField(null=True, blank=True, verbose_name='Read At')
    scheduled_for = models.DateTimeField(null=True, blank=True, verbose_name='Scheduled For')
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['created_at']),
            models.Index(fields=['notification_type']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.title}"

    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

    def send_email(self):
        """Send email notification"""
        try:
            user_preference = NotificationPreference.objects.get(user=self.user)
            if user_preference.email_notifications:
                subject = f"[MediPredict] {self.title}"
                
                # Render HTML email
                context = {
                    'notification': self,
                    'user': self.user,
                    'action_url': self.action_url,
                }
                
                html_message = render_to_string('notifications_app/email/notification.html', context)
                plain_message = strip_tags(html_message)
                
                send_mail(
                    subject=subject,
                    message=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[self.user.email],
                    html_message=html_message,
                    fail_silently=False,
                )
                return True
        except Exception as e:
            # Log error but don't crash
            if settings.DEBUG:
                print(f"Error sending email: {str(e)}")
            return False

    def to_dict(self):
        """Convert notification to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'message': self.message,
            'type': self.notification_type,
            'priority': self.priority,
            'is_read': self.is_read,
            'action_url': self.action_url,
            'created_at': self.created_at.isoformat(),
            'read_at': self.read_at.isoformat() if self.read_at else None,
        }


class NotificationPreference(models.Model):
    """
    Model for storing user notification preferences
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='notification_preferences',
        verbose_name='User'
    )
    
    # Email notifications
    email_notifications = models.BooleanField(default=True, verbose_name='Email Notifications')
    email_prediction_results = models.BooleanField(default=True, verbose_name='Prediction Results')
    email_appointment_reminders = models.BooleanField(default=True, verbose_name='Appointment Reminders')
    email_prescription_updates = models.BooleanField(default=True, verbose_name='Prescription Updates')
    email_security_alerts = models.BooleanField(default=True, verbose_name='Security Alerts')
    email_promotional = models.BooleanField(default=False, verbose_name='Promotional Emails')
    
    # Push notifications
    push_notifications = models.BooleanField(default=True, verbose_name='Push Notifications')
    push_prediction_results = models.BooleanField(default=True, verbose_name='Prediction Results')
    push_appointment_reminders = models.BooleanField(default=True, verbose_name='Appointment Reminders')
    
    # SMS notifications
    sms_notifications = models.BooleanField(default=False, verbose_name='SMS Notifications')
    sms_important_alerts = models.BooleanField(default=False, verbose_name='Important Alerts')
    
    # Frequency
    notification_frequency = models.CharField(
        max_length=20,
        choices=[
            ('immediate', 'Immediate'),
            ('daily_digest', 'Daily Digest'),
            ('weekly_digest', 'Weekly Digest')
        ],
        default='immediate',
        verbose_name='Notification Frequency'
    )
    
    # Do not disturb
    do_not_disturb_start = models.TimeField(null=True, blank=True, verbose_name='Do Not Disturb Start')
    do_not_disturb_end = models.TimeField(null=True, blank=True, verbose_name='Do Not Disturb End')
    
    class Meta:
        verbose_name = 'Notification Preference'
        verbose_name_plural = 'Notification Preferences'

    def __str__(self):
        return f"Preferences for {self.user.email}"


class NotificationTemplate(models.Model):
    """
    Model for storing reusable notification templates
    """
    class TemplateType(models.TextChoices):
        EMAIL = 'email', 'Email Template'
        PUSH = 'push', 'Push Notification Template'
        SMS = 'sms', 'SMS Template'
        IN_APP = 'in_app', 'In-App Notification Template'

    name = models.CharField(max_length=100, unique=True, verbose_name='Template Name')
    description = models.TextField(blank=True, verbose_name='Description')
    template_type = models.CharField(
        max_length=20,
        choices=TemplateType.choices,
        verbose_name='Template Type'
    )
    subject = models.CharField(max_length=200, blank=True, verbose_name='Subject')
    body = models.TextField(verbose_name='Template Body')
    variables = models.JSONField(default=list, blank=True, verbose_name='Template Variables')
    is_active = models.BooleanField(default=True, verbose_name='Is Active')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')

    class Meta:
        verbose_name = 'Notification Template'
        verbose_name_plural = 'Notification Templates'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.template_type})"

    def render_template(self, context):
        """Render template with context variables"""
        from django.template import Template, Context
        template = Template(self.body)
        return template.render(Context(context))


class NotificationLog(models.Model):
    """
    Model for logging notification delivery status
    """
    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name='logs',
        verbose_name='Notification'
    )
    delivery_method = models.CharField(
        max_length=20,
        choices=[
            ('email', 'Email'),
            ('push', 'Push'),
            ('sms', 'SMS'),
            ('in_app', 'In-App')
        ],
        verbose_name='Delivery Method'
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('sent', 'Sent'),
            ('delivered', 'Delivered'),
            ('failed', 'Failed'),
            ('read', 'Read')
        ],
        default='pending',
        verbose_name='Delivery Status'
    )
    error_message = models.TextField(blank=True, null=True, verbose_name='Error Message')
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name='Sent At')
    delivered_at = models.DateTimeField(null=True, blank=True, verbose_name='Delivered At')
    
    class Meta:
        verbose_name = 'Notification Log'
        verbose_name_plural = 'Notification Logs'
        ordering = ['-sent_at']

    def __str__(self):
        return f"Log for {self.notification.title}"