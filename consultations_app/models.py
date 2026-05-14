from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

User = get_user_model()
# Create functions for default values
def generate_consultation_id():
    return f"CON-{uuid.uuid4().hex[:8].upper()}"


class Specialization(models.Model):
    """Doctor specializations"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default='fas fa-stethoscope')
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Doctor(models.Model):
    """Doctor profile model"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor_profile')
    specialization = models.ForeignKey(Specialization, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Professional Information
    license_number = models.CharField(max_length=50, unique=True)
    years_of_experience = models.PositiveIntegerField(default=0)
    qualifications = models.TextField()
    bio = models.TextField(blank=True)
    
    # Contact Information
    hospital_name = models.CharField(max_length=200, blank=True)
    hospital_address = models.TextField(blank=True)
    
    # Availability
    is_available = models.BooleanField(default=True)
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Ratings
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    total_reviews = models.PositiveIntegerField(default=0)
    
    # Verification
    is_verified = models.BooleanField(default=False)
    verification_documents = models.FileField(upload_to='doctor_docs/', blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-average_rating']
    
    def __str__(self):
        return f"Dr. {self.user.get_full_name()}"
    
    @property
    def formatted_fee(self):
        """Return formatted consultation fee"""
        return f"${self.consultation_fee:.2f}"
    
    @property
    def available_slots(self):
        """Get available consultation slots"""
        now = timezone.now()
        return self.slots.filter(
            start_time__gt=now,
            is_booked=False
        ).order_by('start_time')


class ConsultationSlot(models.Model):
    """Available time slots for consultations"""
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='slots')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=30)
    is_booked = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['start_time']
        unique_together = ['doctor', 'start_time']
    
    def __str__(self):
        return f"{self.doctor.user.get_full_name()} - {self.start_time.strftime('%Y-%m-%d %H:%M')}"
    
    def is_available(self):
        """Check if slot is still available"""
        return not self.is_booked and self.start_time > timezone.now()


class Consultation(models.Model):
    """Consultation booking model"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ]
    
    TYPE_CHOICES = [
        ('video', 'Video Call'),
        ('audio', 'Audio Call'),
        ('chat', 'Chat'),
        ('in_person', 'In Person'),
    ]
    
    # Basic Information
    consultation_id = models.CharField(
        max_length=20,
        unique=True,
        default=generate_consultation_id,  # FIXED: Function reference
        verbose_name='Consultation ID'
    )    
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='patient_consultations')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='doctor_consultations')
    slot = models.ForeignKey(ConsultationSlot, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Consultation Details
    consultation_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='video')
    symptoms = models.TextField()
    medical_history_notes = models.TextField(blank=True)
    current_medications = models.TextField(blank=True)
    allergies = models.TextField(blank=True)
    
    # Status & Payment
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2)
    is_paid = models.BooleanField(default=False)
    payment_id = models.CharField(max_length=100, blank=True)
    
    # Consultation Results
    diagnosis = models.TextField(blank=True)
    prescription = models.TextField(blank=True)
    recommendations = models.TextField(blank=True)
    follow_up_date = models.DateField(blank=True, null=True)
    
    # Timestamps
    booked_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(blank=True, null=True)
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    cancelled_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-booked_at']
    
    def __str__(self):
        return f"{self.consultation_id} - {self.patient.get_full_name()} with {self.doctor}"
    
    def save(self, *args, **kwargs):
        """Override save to handle slot booking"""
        if self.slot and self.status == 'confirmed':
            self.slot.is_booked = True
            self.slot.save()
        
        if self.status == 'completed' and not self.completed_at:
            self.completed_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    @property
    def duration(self):
        """Get consultation duration"""
        if self.slot:
            return self.slot.duration_minutes
        return 30  # Default duration
    
    @property
    def is_upcoming(self):
        """Check if consultation is upcoming"""
        if self.slot:
            return self.slot.start_time > timezone.now() and self.status in ['confirmed', 'pending']
        return False
    
    @property
    def is_active(self):
        """Check if consultation is currently active"""
        if self.slot:
            now = timezone.now()
            return (self.slot.start_time <= now <= self.slot.end_time and 
                    self.status == 'confirmed')
        return False
    
    def get_status_color(self):
        """Return Bootstrap color for status"""
        colors = {
            'pending': 'warning',
            'confirmed': 'info',
            'in_progress': 'primary',
            'completed': 'success',
            'cancelled': 'danger',
            'no_show': 'secondary',
        }
        return colors.get(self.status, 'secondary')


class ConsultationMessage(models.Model):
    """Messages within a consultation"""
    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    attachment = models.FileField(upload_to='consultation_attachments/', blank=True, null=True)
    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"Message from {self.sender.get_full_name()} in {self.consultation.consultation_id}"


class Prescription(models.Model):
    """Detailed prescriptions"""
    consultation = models.OneToOneField(Consultation, on_delete=models.CASCADE, related_name='detailed_prescription')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    patient = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Prescription Details
    diagnosis_summary = models.TextField()
    instructions = models.TextField()
    follow_up_instructions = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Prescription for {self.patient.get_full_name()}"


class PrescriptionItem(models.Model):
    """Individual items in a prescription"""
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='items')
    medicine_name = models.CharField(max_length=200)
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100)
    duration = models.CharField(max_length=100)
    instructions = models.TextField(blank=True)
    
    class Meta:
        ordering = ['id']
    
    def __str__(self):
        return f"{self.medicine_name} - {self.dosage}"


class Review(models.Model):
    """Patient reviews for doctors"""
    consultation = models.OneToOneField(Consultation, on_delete=models.CASCADE, related_name='review')
    patient = models.ForeignKey(User, on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='reviews')
    
    # Ratings (1-5)
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    review_text = models.TextField()
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['consultation', 'patient']
    
    def __str__(self):
        return f"Review by {self.patient.get_full_name()} for Dr. {self.doctor.user.get_full_name()}"
    
    def save(self, *args, **kwargs):
        """Update doctor's average rating when review is saved"""
        super().save(*args, **kwargs)
        self.update_doctor_rating()
    
    def update_doctor_rating(self):
        """Update doctor's average rating"""
        reviews = Review.objects.filter(doctor=self.doctor)
        total_rating = sum(review.rating for review in reviews)
        average_rating = total_rating / reviews.count() if reviews.count() > 0 else 0
        
        self.doctor.average_rating = round(average_rating, 2)
        self.doctor.total_reviews = reviews.count()
        self.doctor.save()


class Billing(models.Model):
    """Consultation billing information"""
    consultation = models.OneToOneField(Consultation, on_delete=models.CASCADE, related_name='billing')
    
    # Payment Details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Payment Status
    payment_status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ], default='pending')
    
    payment_method = models.CharField(max_length=50, blank=True)
    transaction_id = models.CharField(max_length=100, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Bill for {self.consultation.consultation_id}"
    
    def calculate_total(self):
        """Calculate total amount including tax"""
        self.total_amount = self.amount + self.tax_amount
        return self.total_amount


class Notification(models.Model):
    """Notifications for consultations"""
    TYPE_CHOICES = [
        ('consultation_booked', 'Consultation Booked'),
        ('consultation_confirmed', 'Consultation Confirmed'),
        ('consultation_cancelled', 'Consultation Cancelled'),
        ('consultation_reminder', 'Consultation Reminder'),
        ('prescription_ready', 'Prescription Ready'),
        ('message_received', 'Message Received'),
        ('review_request', 'Review Request'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='consultation_notifications')
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    message = models.TextField()
    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.notification_type} for {self.user.get_full_name()}"