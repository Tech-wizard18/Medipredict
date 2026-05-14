from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import Consultation, ConsultationSlot, Notification


@receiver(post_save, sender=Consultation)
def consultation_status_changed(sender, instance, created, **kwargs):
    """Handle consultation status changes"""
    if not created:
        # Send notifications based on status change
        if instance.status == 'confirmed':
            # Send confirmation email to patient
            subject = f"Consultation Confirmed - {instance.consultation_id}"
            html_message = render_to_string('consultations_app/emails/consultation_confirmed.html', {
                'consultation': instance,
                'patient': instance.patient,
            })
            
            send_mail(
                subject=subject,
                message='',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[instance.patient.email],
                html_message=html_message,
            )
            
            # Create notification
            Notification.objects.create(
                user=instance.patient,
                notification_type='consultation_confirmed',
                message=f"Your consultation with Dr. {instance.doctor.user.get_full_name()} has been confirmed",
                consultation=instance
            )
            
        elif instance.status == 'cancelled':
            # Free up the slot
            if instance.slot:
                instance.slot.is_booked = False
                instance.slot.save()
            
            # Create notifications
            Notification.objects.create(
                user=instance.patient,
                notification_type='consultation_cancelled',
                message=f"Consultation {instance.consultation_id} has been cancelled",
                consultation=instance
            )
            
            Notification.objects.create(
                user=instance.doctor.user,
                notification_type='consultation_cancelled',
                message=f"Consultation {instance.consultation_id} has been cancelled",
                consultation=instance
            )


@receiver(pre_save, sender=ConsultationSlot)
def calculate_end_time(sender, instance, **kwargs):
    """Calculate end time for consultation slot"""
    if instance.start_time and instance.duration_minutes and not instance.end_time:
        instance.end_time = instance.start_time + timezone.timedelta(minutes=instance.duration_minutes)


@receiver(post_delete, sender=ConsultationSlot)
def handle_slot_deletion(sender, instance, **kwargs):
    """Handle slot deletion"""
    # If slot was booked, cancel the associated consultation
    if instance.is_booked:
        consultation = Consultation.objects.filter(slot=instance).first()
        if consultation:
            consultation.status = 'cancelled'
            consultation.cancelled_at = timezone.now()
            consultation.save()


@receiver(post_save, sender=Notification)
def send_email_notification(sender, instance, created, **kwargs):
    """Send email for important notifications"""
    if created and instance.user.email_notifications:
        # Only send email for important notifications
        important_types = [
            'consultation_booked',
            'consultation_confirmed',
            'consultation_cancelled',
            'prescription_ready',
        ]
        
        if instance.notification_type in important_types:
            subject = f"MEDIPREDICT - {instance.get_notification_type_display()}"
            html_message = render_to_string('consultations_app/emails/notification.html', {
                'notification': instance,
                'user': instance.user,
            })
            
            send_mail(
                subject=subject,
                message='',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[instance.user.email],
                html_message=html_message,
                fail_silently=True,
            )