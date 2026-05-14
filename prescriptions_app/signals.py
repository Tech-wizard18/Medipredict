from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from .models import Prescription, PrescriptionAlert, PrescriptionItem


@receiver(pre_save, sender=Prescription)
def update_prescription_status(sender, instance, **kwargs):
    """Update prescription status based on dates and refills"""
    today = timezone.now().date()
    
    # Check if prescription has expired
    if instance.valid_until and instance.valid_until < today and instance.status == 'active':
        instance.status = 'expired'
    
    # Check if refills are exhausted
    if instance.refills_remaining == 0 and instance.status == 'active':
        instance.status = 'completed'
    
    # Set default validity if not set
    if not instance.valid_until and instance.issue_date:
        instance.valid_until = instance.issue_date + timedelta(days=30)


@receiver(post_save, sender=Prescription)
def create_expiration_alert(sender, instance, created, **kwargs):
    """Create alert when prescription is about to expire"""
    if instance.status == 'active' and instance.valid_until:
        days_remaining = (instance.valid_until - timezone.now().date()).days
        
        # Create alert 7 days before expiration
        if days_remaining <= 7:
            alert, created = PrescriptionAlert.objects.get_or_create(
                patient=instance.patient,
                prescription=instance,
                alert_type='expiring_soon',
                defaults={
                    'priority': 'high' if days_remaining <= 3 else 'medium',
                    'message': f"Prescription {instance.prescription_id} expires in {days_remaining} day(s). Please refill if needed.",
                    'expires_at': instance.valid_until,
                }
            )


@receiver(post_save, sender=PrescriptionItem)
def update_medicine_stock(sender, instance, created, **kwargs):
    """Update medicine stock when prescription item is dispensed"""
    if instance.is_dispensed and instance.dispensed_quantity > 0:
        medicine = instance.medicine
        if medicine.stock_quantity >= instance.dispensed_quantity:
            medicine.stock_quantity -= instance.dispensed_quantity
            medicine.save()
            
            # Create low stock alert if needed
            if medicine.needs_reorder():
                PrescriptionAlert.objects.create(
                    patient=instance.prescription.patient,
                    alert_type='refill_due',
                    priority='medium',
                    message=f"Medicine {medicine.name} is running low. Current stock: {medicine.stock_quantity}",
                    related_medicine=medicine,
                )