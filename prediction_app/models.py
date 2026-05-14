from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()


class DiseaseModel(models.Model):
    """Stores information about trained ML models"""
    DISEASE_CHOICES = [
        ('diabetes', 'Diabetes'),
        ('heart', 'Heart Disease'),
        ('kidney', 'Kidney Disease'),
        ('parkinson', 'Parkinson Disease'),
        ('breast_cancer', 'Breast Cancer'),
        ('liver', 'Liver Disease'),
    ]
    
    name = models.CharField(max_length=100, choices=DISEASE_CHOICES, unique=True)
    model_file = models.FileField(upload_to='ml_models/')
    scaler_file = models.FileField(upload_to='ml_models/scalers/', null=True, blank=True)
    accuracy = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.get_name_display()} Model (Accuracy: {self.accuracy:.2%})"


class Prediction(models.Model):
    """Stores prediction history"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='predictions')
    disease_model = models.ForeignKey(DiseaseModel, on_delete=models.CASCADE)
    prediction_result = models.FloatField()  # Probability or score
    prediction_label = models.CharField(max_length=50)  # Positive/Negative or specific label
    confidence = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    input_data = models.JSONField()  # Store the input parameters
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['disease_model']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.disease_model.name} - {self.prediction_label}"


class HealthReport(models.Model):
    """Comprehensive health report for users"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='health_reports')
    report_date = models.DateField(auto_now_add=True)
    overall_risk_score = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    risk_level = models.CharField(max_length=20, choices=[
        ('low', 'Low Risk'),
        ('moderate', 'Moderate Risk'),
        ('high', 'High Risk'),
        ('critical', 'Critical Risk'),
    ])
    recommendations = models.TextField()
    findings = models.JSONField()  # Store detailed findings
    generated_by = models.CharField(max_length=100, choices=[
        ('system', 'System Generated'),
        ('doctor', 'Doctor Generated'),
    ])
    doctor_notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-report_date']
        unique_together = ['user', 'report_date']
    
    def __str__(self):
        return f"{self.user.email} - {self.report_date} - {self.risk_level}"


class Symptom(models.Model):
    """Medical symptoms database"""
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField()
    category = models.CharField(max_length=100, choices=[
        ('general', 'General'),
        ('respiratory', 'Respiratory'),
        ('cardiovascular', 'Cardiovascular'),
        ('neurological', 'Neurological'),
        ('gastrointestinal', 'Gastrointestinal'),
        ('musculoskeletal', 'Musculoskeletal'),
    ])
    severity_levels = models.JSONField()  # Store severity scale
    
    def __str__(self):
        return self.name


class PatientSymptom(models.Model):
    """Tracks patient-reported symptoms"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='symptoms')
    symptom = models.ForeignKey(Symptom, on_delete=models.CASCADE)
    severity = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(10)])
    onset_date = models.DateField()
    duration_days = models.IntegerField(validators=[MinValueValidator(1)])
    notes = models.TextField(blank=True, null=True)
    recorded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-recorded_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.symptom.name}"