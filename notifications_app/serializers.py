from rest_framework import serializers
from .models import Notification, NotificationPreference, NotificationTemplate


class NotificationSerializer(serializers.ModelSerializer):
    """
    Serializer for Notification model
    """
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")
    read_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", allow_null=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'message', 'notification_type', 'priority',
            'is_read', 'action_url', 'metadata', 'created_at', 'read_at'
        ]
        read_only_fields = ['id', 'created_at', 'read_at']


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """
    Serializer for NotificationPreference model
    """
    class Meta:
        model = NotificationPreference
        fields = [
            'email_notifications', 'email_prediction_results',
            'email_appointment_reminders', 'email_prescription_updates',
            'email_security_alerts', 'email_promotional',
            'push_notifications', 'push_prediction_results',
            'push_appointment_reminders', 'sms_notifications',
            'sms_important_alerts', 'notification_frequency',
            'do_not_disturb_start', 'do_not_disturb_end'
        ]


class NotificationTemplateSerializer(serializers.ModelSerializer):
    """
    Serializer for NotificationTemplate model
    """
    class Meta:
        model = NotificationTemplate
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']