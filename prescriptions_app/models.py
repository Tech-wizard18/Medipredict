from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import uuid

User = get_user_model()

# Create function for prescription ID
def generate_prescription_id():
    return f"RX-{uuid.uuid4().hex[:8].upper()}"

class Medicine(models.Model):   
    """Medicine database with comprehensive information"""
    
    CATEGORY_CHOICES = [
        ('antibiotic', 'Antibiotic'),
        ('analgesic', 'Analgesic (Pain Reliever)'),
        ('antihypertensive', 'Antihypertensive'),
        ('antidiabetic', 'Antidiabetic'),
        ('antiinflammatory', 'Anti-inflammatory'),
        ('antidepressant', 'Antidepressant'),
        ('antihistamine', 'Antihistamine'),
        ('vitamin', 'Vitamin/Supplement'),
        ('other', 'Other'),
    ]
    
    FORM_CHOICES = [
        ('tablet', 'Tablet'),
        ('capsule', 'Capsule'),
        ('syrup', 'Syrup/Liquid'),
        ('injection', 'Injection'),
        ('ointment', 'Ointment/Cream'),
        ('inhaler', 'Inhaler'),
        ('drops', 'Drops'),
        ('other', 'Other'),
    ]
    
    # Basic Information
    name = models.CharField(max_length=200, unique=True)
    generic_name = models.CharField(max_length=200, blank=True)
    brand_name = models.CharField(max_length=200, blank=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    form = models.CharField(max_length=50, choices=FORM_CHOICES)
    
    # Dosage Information
    strength = models.CharField(max_length=100, help_text="e.g., 500mg, 10mg/ml")
    manufacturer = models.CharField(max_length=200, blank=True)
    
    # Safety Information
    side_effects = models.TextField(blank=True)
    contraindications = models.TextField(blank=True)
    pregnancy_category = models.CharField(max_length=10, blank=True)
    storage_instructions = models.TextField(blank=True)
    
    # Regulatory
    requires_prescription = models.BooleanField(default=True)
    is_controlled_substance = models.BooleanField(default=False)
    schedule = models.CharField(max_length=10, blank=True, help_text="Drug schedule classification")
    
    # Images & Documentation
    medicine_image = models.ImageField(upload_to='medicine_images/', blank=True, null=True)
    leaflet = models.FileField(upload_to='medicine_leaflets/', blank=True, null=True)
    
    # Stock Information
    is_available = models.BooleanField(default=True)
    stock_quantity = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=10)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = "Medicine"
        verbose_name_plural = "Medicines"
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['category']),
            models.Index(fields=['is_available']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.strength})"
    
    def needs_reorder(self):
        """Check if medicine needs reordering"""
        return self.stock_quantity <= self.reorder_level
    
    def get_dosage_options(self):
        """Get available dosage options based on form"""
        options = []
        if self.form in ['tablet', 'capsule']:
            options = ['0.5', '1', '1.5', '2', '2.5', '3']
        elif self.form == 'syrup':
            options = ['5ml', '10ml', '15ml', '20ml']
        elif self.form == 'injection':
            options = ['0.5ml', '1ml', '2ml', '5ml']
        return options


class Prescription(models.Model):
    """Main prescription model"""
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ]
    
    TYPE_CHOICES = [
        ('new', 'New Prescription'),
        ('refill', 'Refill'),
        ('emergency', 'Emergency'),
        ('chronic', 'Chronic Condition'),
        ('preventive', 'Preventive'),
    ]
    
    # Prescription Information
    prescription_id = models.CharField(
        max_length=20,
        unique=True,
        default=generate_prescription_id,  # FIXED: Function reference
        verbose_name='Prescription ID'
    )
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prescriptions')
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='doctor_prescriptions')
    
    # Consultation Reference (optional)
    consultation = models.ForeignKey(
        'consultations_app.Consultation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='prescription_link'
    )
    
    # Prescription Details
    diagnosis = models.TextField(blank=True)
    notes = models.TextField(blank=True, help_text="Additional instructions for patient")
    prescription_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='new')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Validity
    issue_date = models.DateField(default=timezone.now)
    valid_until = models.DateField()
    refills_allowed = models.PositiveIntegerField(default=0)
    refills_remaining = models.PositiveIntegerField(default=0)
    
    # Digital Signature
    doctor_signature = models.ImageField(upload_to='signatures/', blank=True, null=True)
    digital_signature_hash = models.CharField(max_length=255, blank=True)
    
    # Pharmacy Information
    pharmacy_notes = models.TextField(blank=True)
    is_pharmacy_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_prescriptions'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-issue_date']
        verbose_name = "Prescription"
        verbose_name_plural = "Prescriptions"
        indexes = [
            models.Index(fields=['prescription_id']),
            models.Index(fields=['patient', 'status']),
            models.Index(fields=['doctor', 'issue_date']),
            models.Index(fields=['valid_until', 'status']),
        ]
    
    def __str__(self):
        return f"{self.prescription_id} - {self.patient.get_full_name()}"
    
    def save(self, *args, **kwargs):
        """Override save to handle refills"""
        if not self.valid_until:
            # Default validity: 30 days for new prescriptions
            self.valid_until = self.issue_date + timezone.timedelta(days=30)
        
        if self.refills_allowed > 0 and self.refills_remaining == 0:
            self.refills_remaining = self.refills_allowed
        
        super().save(*args, **kwargs)
    
    def is_valid(self):
        """Check if prescription is still valid"""
        return (
            self.status == 'active' and
            timezone.now().date() <= self.valid_until and
            self.refills_remaining > 0
        )
    
    def days_remaining(self):
        """Get days remaining until expiration"""
        if self.valid_until:
            remaining = (self.valid_until - timezone.now().date()).days
            return max(0, remaining)
        return 0
    
    def can_refill(self):
        """Check if prescription can be refilled"""
        return (
            self.is_valid() and
            self.refills_remaining > 0 and
            self.prescription_type in ['chronic', 'refill']
        )
    
    def process_refill(self):
        """Process a refill request"""
        if self.can_refill():
            self.refills_remaining -= 1
            if self.refills_remaining == 0:
                self.status = 'completed'
            self.save()
            return True
        return False
    
    def get_total_items(self):
        """Get total number of prescription items"""
        return self.items.count()
    
    def get_total_cost(self):
        """Calculate total cost of prescription"""
        total = sum(item.calculate_cost() for item in self.items.all())
        return round(total, 2)


class PrescriptionItem(models.Model):
    """Individual items in a prescription"""
    
    FREQUENCY_CHOICES = [
        ('once_daily', 'Once Daily'),
        ('twice_daily', 'Twice Daily'),
        ('thrice_daily', 'Three Times Daily'),
        ('four_times_daily', 'Four Times Daily'),
        ('every_other_day', 'Every Other Day'),
        ('weekly', 'Once Weekly'),
        ('as_needed', 'As Needed (PRN)'),
        ('before_meal', 'Before Meal'),
        ('after_meal', 'After Meal'),
        ('at_bedtime', 'At Bedtime'),
    ]
    
    DURATION_UNIT_CHOICES = [
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
        ('indefinite', 'Until Finished'),
    ]
    
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='items')
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    
    # Dosage Details
    dosage = models.CharField(max_length=100, help_text="e.g., 1 tablet, 10ml")
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='once_daily')
    duration = models.PositiveIntegerField(default=7)
    duration_unit = models.CharField(max_length=10, choices=DURATION_UNIT_CHOICES, default='days')
    
    # Instructions
    instructions = models.TextField(blank=True, help_text="Specific instructions for this medicine")
    take_with_food = models.BooleanField(default=False)
    avoid_alcohol = models.BooleanField(default=False)
    
    # Timing Information
    specific_times = models.CharField(max_length=200, blank=True, help_text="e.g., 8:00, 20:00")
    
    # Quantity & Pricing
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Status
    is_dispensed = models.BooleanField(default=False)
    dispensed_quantity = models.PositiveIntegerField(default=0)
    dispensed_at = models.DateTimeField(null=True, blank=True)
    
    # Substitution
    allow_generic = models.BooleanField(default=True)
    substituted_with = models.ForeignKey(
        Medicine,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='substituted_items'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['id']
        verbose_name = "Prescription Item"
        verbose_name_plural = "Prescription Items"
    
    def __str__(self):
        return f"{self.medicine.name} - {self.dosage} {self.frequency}"
    
    def calculate_duration_days(self):
        """Calculate total duration in days"""
        if self.duration_unit == 'days':
            return self.duration
        elif self.duration_unit == 'weeks':
            return self.duration * 7
        elif self.duration_unit == 'months':
            return self.duration * 30  # Approximate
        return self.duration
    
    def calculate_total_dose(self):
        """Calculate total number of doses"""
        frequency_map = {
            'once_daily': 1,
            'twice_daily': 2,
            'thrice_daily': 3,
            'four_times_daily': 4,
            'every_other_day': 0.5,
            'weekly': 1/7,
            'as_needed': 0,
        }
        
        daily_doses = frequency_map.get(self.frequency, 1)
        total_days = self.calculate_duration_days()
        return round(daily_doses * total_days)
    
    def calculate_cost(self):
        """Calculate total cost for this item"""
        if self.is_dispensed:
            quantity = self.dispensed_quantity
        else:
            quantity = self.quantity
        
        return quantity * self.unit_price
    
    def get_frequency_display_text(self):
        """Get human-readable frequency text"""
        frequency_map = {
            'once_daily': 'Once a day',
            'twice_daily': 'Twice a day',
            'thrice_daily': 'Three times a day',
            'four_times_daily': 'Four times a day',
            'every_other_day': 'Every other day',
            'weekly': 'Once a week',
            'as_needed': 'As needed',
            'before_meal': 'Before meals',
            'after_meal': 'After meals',
            'at_bedtime': 'At bedtime',
        }
        return frequency_map.get(self.frequency, self.frequency)
    
    def get_detailed_instructions(self):
        """Generate detailed instructions for patient"""
        instructions = []
        
        # Basic instruction
        instructions.append(f"Take {self.dosage} {self.get_frequency_display_text().lower()}")
        
        # Add duration
        if self.duration_unit != 'indefinite':
            instructions.append(f"for {self.duration} {self.duration_unit}")
        
        # Add specific times
        if self.specific_times:
            times = self.specific_times.split(',')
            time_list = ', '.join([t.strip() for t in times])
            instructions.append(f"at {time_list}")
        
        # Add food instructions
        if self.take_with_food:
            instructions.append("with food")
        
        # Add alcohol warning
        if self.avoid_alcohol:
            instructions.append("(avoid alcohol)")
        
        # Add custom instructions
        if self.instructions:
            instructions.append(f"Additional: {self.instructions}")
        
        return ' '.join(instructions)


class RefillRequest(models.Model):
    """Prescription refill requests"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
        ('cancelled', 'Cancelled'),
    ]
    
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='refill_requests')
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='refill_requests')
    
    # Request Details
    request_date = models.DateTimeField(auto_now_add=True)
    requested_refill_count = models.PositiveIntegerField(default=1)
    reason = models.TextField(blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Doctor Response
    doctor_response = models.TextField(blank=True)
    responded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_refills'
    )
    responded_at = models.DateTimeField(null=True, blank=True)
    
    # Pharmacy Information
    pharmacy_notes = models.TextField(blank=True)
    is_ready_for_pickup = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-request_date']
        verbose_name = "Refill Request"
        verbose_name_plural = "Refill Requests"
        indexes = [
            models.Index(fields=['prescription', 'status']),
            models.Index(fields=['patient', 'status']),
        ]
    
    def __str__(self):
        return f"Refill for {self.prescription.prescription_id}"
    
    def can_be_processed(self):
        """Check if refill can be processed"""
        return (
            self.status == 'pending' and
            self.prescription.can_refill() and
            self.requested_refill_count <= self.prescription.refills_remaining
        )
    
    def process_approval(self, doctor, notes=""):
        """Process approval of refill request"""
        if self.can_be_processed():
            # Update prescription
            for _ in range(self.requested_refill_count):
                if not self.prescription.process_refill():
                    break
            
            # Update refill request
            self.status = 'approved'
            self.responded_by = doctor
            self.responded_at = timezone.now()
            self.doctor_response = notes or "Refill approved"
            self.save()
            return True
        return False
    
    def process_denial(self, doctor, reason):
        """Process denial of refill request"""
        if self.status == 'pending':
            self.status = 'denied'
            self.responded_by = doctor
            self.responded_at = timezone.now()
            self.doctor_response = reason
            self.save()
            return True
        return False


class MedicationHistory(models.Model):
    """Track patient's medication history"""
    
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='medication_history')
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='history_entries')
    prescription_item = models.ForeignKey(PrescriptionItem, on_delete=models.CASCADE, null=True, blank=True)
    
    # Action Details
    action = models.CharField(max_length=50, choices=[
        ('prescribed', 'Prescribed'),
        ('dispensed', 'Dispensed'),
        ('administered', 'Administered'),
        ('missed', 'Missed Dose'),
        ('stopped', 'Stopped'),
        ('changed', 'Dosage Changed'),
        ('refilled', 'Refilled'),
    ])
    
    # Details
    details = models.TextField(blank=True)
    dosage_taken = models.CharField(max_length=100, blank=True)
    taken_at = models.DateTimeField(null=True, blank=True)
    
    # Side Effects (if reported)
    side_effects = models.TextField(blank=True)
    severity = models.CharField(max_length=20, choices=[
        ('mild', 'Mild'),
        ('moderate', 'Moderate'),
        ('severe', 'Severe'),
    ], blank=True)
    
    # Effectiveness
    effectiveness_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True
    )
    
    # Location Information
    location = models.CharField(max_length=200, blank=True)
    administered_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='administered_medications'
    )
    
    # Timestamps
    recorded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-recorded_at']
        verbose_name = "Medication History"
        verbose_name_plural = "Medication History"
        indexes = [
            models.Index(fields=['patient', 'recorded_at']),
            models.Index(fields=['prescription', 'action']),
        ]
    
    def __str__(self):
        return f"{self.patient.get_full_name()} - {self.action} - {self.recorded_at.date()}"


class DrugInteraction(models.Model):
    """Drug interaction database"""
    
    SEVERITY_CHOICES = [
        ('minor', 'Minor'),
        ('moderate', 'Moderate'),
        ('major', 'Major'),
        ('contraindicated', 'Contraindicated'),
    ]
    
    medicine1 = models.ForeignKey(Medicine, on_delete=models.CASCADE, related_name='interactions_as_first')
    medicine2 = models.ForeignKey(Medicine, on_delete=models.CASCADE, related_name='interactions_as_second')
    
    # Interaction Details
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    description = models.TextField()
    mechanism = models.TextField(blank=True)
    recommendations = models.TextField(blank=True)
    
    # References
    reference = models.URLField(blank=True)
    last_updated = models.DateField(auto_now=True)
    
    class Meta:
        ordering = ['severity', 'medicine1__name']
        verbose_name = "Drug Interaction"
        verbose_name_plural = "Drug Interactions"
        unique_together = ['medicine1', 'medicine2']
    
    def __str__(self):
        return f"{self.medicine1.name} + {self.medicine2.name} - {self.severity}"


class Pharmacy(models.Model):
    """Pharmacy information"""
    
    name = models.CharField(max_length=200)
    address = models.TextField()
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    
    # Operating Hours
    opening_time = models.TimeField(default='09:00')
    closing_time = models.TimeField(default='21:00')
    is_24_hours = models.BooleanField(default=False)
    
    # Services
    delivers = models.BooleanField(default=False)
    accepts_insurance = models.BooleanField(default=True)
    has_compounding = models.BooleanField(default=False)
    
    # Location
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Verification
    is_verified = models.BooleanField(default=False)
    license_number = models.CharField(max_length=100, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = "Pharmacy"
        verbose_name_plural = "Pharmacies"
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['is_verified']),
        ]
    
    def __str__(self):
        return self.name
    
    def operating_hours(self):
        """Get formatted operating hours"""
        if self.is_24_hours:
            return "24 Hours"
        return f"{self.opening_time.strftime('%I:%M %p')} - {self.closing_time.strftime('%I:%M %p')}"
    
    def distance_from(self, lat, lng):
        """Calculate distance from given coordinates (simplified)"""
        if self.latitude and self.longitude:
            # Simplified distance calculation
            # In production, use proper geodetic calculation
            return None  # Placeholder
        return None


class PrescriptionAlert(models.Model):
    """Alerts for prescriptions"""
    
    ALERT_TYPE_CHOICES = [
        ('refill_due', 'Refill Due'),
        ('expiring_soon', 'Prescription Expiring'),
        ('interaction', 'Drug Interaction'),
        ('allergy', 'Allergy Alert'),
        ('dosage', 'Dosage Alert'),
        ('compliance', 'Compliance Issue'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prescription_alerts')
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, null=True, blank=True)
    
    # Alert Details
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPE_CHOICES)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    message = models.TextField()
    
    # Status
    is_read = models.BooleanField(default=False)
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_alerts'
    )
    
    # Related Data
    related_medicine = models.ForeignKey(Medicine, on_delete=models.SET_NULL, null=True, blank=True)
    related_interaction = models.ForeignKey(DrugInteraction, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-priority', '-created_at']
        verbose_name = "Prescription Alert"
        verbose_name_plural = "Prescription Alerts"
        indexes = [
            models.Index(fields=['patient', 'is_read']),
            models.Index(fields=['alert_type', 'priority']),
        ]
    
    def __str__(self):
        return f"{self.alert_type} - {self.patient.get_full_name()}"
    
    def is_active(self):
        """Check if alert is still active"""
        if self.is_resolved:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True
    
    def get_color_class(self):
        """Get Bootstrap color class for alert"""
        priority_colors = {
            'low': 'info',
            'medium': 'warning',
            'high': 'danger',
            'critical': 'dark',
        }
        return priority_colors.get(self.priority, 'info')