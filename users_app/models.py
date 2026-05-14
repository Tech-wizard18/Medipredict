from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone 
import uuid


# Create function for user ID
def generate_user_id():
    return f"USR-{uuid.uuid4().hex[:8].upper()}"


class User(AbstractUser):
    """Custom User model extending Django's AbstractUser"""
    
    # Additional fields
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(
        max_length=20,
        choices=[
            ('male', 'Male'),
            ('female', 'Female'),
            ('other', 'Other'),
            ('prefer_not_to_say', 'Prefer not to say')
        ],
        blank=True,
        null=True
    )

    # Basic Information
    user_id = models.CharField(
        max_length=20,
        unique=True,
        default=generate_user_id,  # FIXED: Function reference
        verbose_name='User ID'
    )
    
    
    # Medical profile fields
    blood_group = models.CharField(
        max_length=5,
        choices=[
            ('A+', 'A+'),
            ('A-', 'A-'),
            ('B+', 'B+'),
            ('B-', 'B-'),
            ('AB+', 'AB+'),
            ('AB-', 'AB-'),
            ('O+', 'O+'),
            ('O-', 'O-')
        ],
        blank=True,
        null=True
    )
    
    height = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        blank=True, 
        null=True,
        help_text="Height in cm"
    )
    
    weight = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        blank=True, 
        null=True,
        help_text="Weight in kg"
    )
    
    # Medical conditions
    has_diabetes = models.BooleanField(default=False)
    has_hypertension = models.BooleanField(default=False)
    has_heart_disease = models.BooleanField(default=False)
    has_kidney_disease = models.BooleanField(default=False)
    has_liver_disease = models.BooleanField(default=False)
    
    # Family history
    family_history = models.TextField(blank=True, null=True)
    
    # Lifestyle
    smokes = models.BooleanField(default=False)
    drinks_alcohol = models.BooleanField(default=False)
    exercise_frequency = models.CharField(
        max_length=20,
        choices=[
            ('never', 'Never'),
            ('occasionally', 'Occasionally (1-2 times/week)'),
            ('regularly', 'Regularly (3-5 times/week)'),
            ('daily', 'Daily')
        ],
        default='occasionally'
    )
    
    # Profile settings
    profile_picture = models.ImageField(
        upload_to='profile_pictures/',
        blank=True,
        null=True,
        default='profile_pictures/default.png'
    )
    
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(blank=True, null=True)
    
    # User preferences
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    dark_mode = models.BooleanField(default=False)
    
    # Security
    two_factor_enabled = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-date_joined']
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return self.username
    
    @property
    def full_name(self):
        """Return the full name of the user"""
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def bmi(self):
        """Calculate and return BMI if height and weight are available"""
        if self.height and self.weight:
            # Convert height from cm to meters
            height_m = float(self.height) / 100
            bmi_value = float(self.weight) / (height_m ** 2)
            return round(bmi_value, 1)
        return None
    
    @property
    def bmi_category(self):
        """Return BMI category"""
        bmi_value = self.bmi
        if bmi_value:
            if bmi_value < 18.5:
                return "Underweight"
            elif bmi_value < 25:
                return "Normal"
            elif bmi_value < 30:
                return "Overweight"
            else:
                return "Obese"
        return None
    
    @property
    def age(self):
        """Calculate age from date of birth"""
        if self.date_of_birth:
            today = timezone.now().date()
            age = today.year - self.date_of_birth.year
            # Adjust if birthday hasn't occurred this year
            if today.month < self.date_of_birth.month or \
               (today.month == self.date_of_birth.month and today.day < self.date_of_birth.day):
                age -= 1
            return age
        return None
    
    def get_medical_conditions(self):
        """Return a list of active medical conditions"""
        conditions = []
        if self.has_diabetes:
            conditions.append("Diabetes")
        if self.has_hypertension:
            conditions.append("Hypertension")
        if self.has_heart_disease:
            conditions.append("Heart Disease")
        if self.has_kidney_disease:
            conditions.append("Kidney Disease")
        if self.has_liver_disease:
            conditions.append("Liver Disease")
        return conditions


class UserActivity(models.Model):
    """Track user activities for security and analytics"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(
        max_length=50,
        choices=[
            ('login', 'Login'),
            ('logout', 'Logout'),
            ('profile_update', 'Profile Update'),
            ('password_change', 'Password Change'),
            ('prediction_made', 'Prediction Made'),
            ('report_generated', 'Report Generated'),
            ('account_settings_changed', 'Account Settings Changed')
        ]
    )
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.JSONField(blank=True, null=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'User Activity'
        verbose_name_plural = 'User Activities'
    
    def __str__(self):
        return f"{self.user.username} - {self.activity_type} at {self.timestamp}"


class EmailVerification(models.Model):
    """Store email verification tokens"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_verifications')
    token = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    verified = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']


class PasswordResetToken(models.Model):
    """Store password reset tokens"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_tokens')
    token = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.activity_type} - {self.created_at}"