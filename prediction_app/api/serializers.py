from rest_framework import serializers
from django.utils import timezone
from datetime import datetime
import re

from prediction_app.models import (
    Prediction, HealthReport, Symptom, PatientSymptom, DiseaseModel
)


class PredictionSerializer(serializers.ModelSerializer):
    """Serializer for Prediction model."""
    
    disease_name = serializers.CharField(source='disease_model.get_name_display', read_only=True)
    confidence_percentage = serializers.SerializerMethodField()
    created_at_formatted = serializers.SerializerMethodField()
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = Prediction
        fields = [
            'id', 'user', 'user_email', 'disease_model', 'disease_name',
            'prediction_result', 'prediction_label', 'confidence',
            'confidence_percentage', 'input_data', 'created_at',
            'created_at_formatted'
        ]
        read_only_fields = ['user', 'created_at']
    
    def get_confidence_percentage(self, obj):
        """Format confidence as percentage."""
        return f"{obj.confidence:.2%}"
    
    def get_created_at_formatted(self, obj):
        """Format created_at date."""
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    
    def validate_input_data(self, value):
        """Validate input data."""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Input data must be a dictionary")
        
        # Ensure input data is not too large
        if len(str(value)) > 10000:
            raise serializers.ValidationError("Input data too large")
        
        return value
    
    def create(self, validated_data):
        """Create prediction with current user."""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['user'] = request.user
        return super().create(validated_data)


class HealthReportSerializer(serializers.ModelSerializer):
    """Serializer for HealthReport model."""
    
    risk_level_display = serializers.CharField(source='get_risk_level_display', read_only=True)
    generated_by_display = serializers.CharField(source='get_generated_by_display', read_only=True)
    report_date_formatted = serializers.SerializerMethodField()
    overall_risk_score_percentage = serializers.SerializerMethodField()
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = HealthReport
        fields = [
            'id', 'user', 'user_email', 'report_date', 'report_date_formatted',
            'overall_risk_score', 'overall_risk_score_percentage',
            'risk_level', 'risk_level_display', 'recommendations',
            'findings', 'generated_by', 'generated_by_display',
            'doctor_notes', 'created_at'
        ]
        read_only_fields = ['user', 'created_at']
    
    def get_report_date_formatted(self, obj):
        """Format report date."""
        return obj.report_date.strftime('%Y-%m-%d')
    
    def get_overall_risk_score_percentage(self, obj):
        """Format risk score as percentage."""
        return f"{obj.overall_risk_score:.2%}"
    
    def validate_report_date(self, value):
        """Validate report date."""
        if value > timezone.now().date():
            raise serializers.ValidationError("Report date cannot be in the future")
        return value
    
    def validate_overall_risk_score(self, value):
        """Validate risk score."""
        if value < 0 or value > 1:
            raise serializers.ValidationError("Risk score must be between 0 and 1")
        return value


class SymptomSerializer(serializers.ModelSerializer):
    """Serializer for Symptom model."""
    
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    
    class Meta:
        model = Symptom
        fields = [
            'id', 'name', 'description', 'category', 'category_display',
            'severity_levels'
        ]
    
    def validate_name(self, value):
        """Validate symptom name."""
        if len(value) < 2:
            raise serializers.ValidationError("Symptom name must be at least 2 characters")
        return value.strip()
    
    def validate_severity_levels(self, value):
        """Validate severity levels JSON."""
        import json
        
        try:
            if isinstance(value, str):
                data = json.loads(value)
            else:
                data = value
            
            if not isinstance(data, dict):
                raise serializers.ValidationError("Severity levels must be a dictionary")
            
            # Ensure severity levels are valid
            for level, description in data.items():
                if not isinstance(level, (str, int)):
                    raise serializers.ValidationError("Severity levels must have string or integer keys")
                if not isinstance(description, str):
                    raise serializers.ValidationError("Severity level descriptions must be strings")
            
            return value
            
        except json.JSONDecodeError:
            raise serializers.ValidationError("Invalid JSON format for severity levels")


class PatientSymptomSerializer(serializers.ModelSerializer):
    """Serializer for PatientSymptom model."""
    
    symptom_name = serializers.CharField(source='symptom.name', read_only=True)
    symptom_description = serializers.CharField(source='symptom.description', read_only=True)
    recorded_at_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = PatientSymptom
        fields = [
            'id', 'user', 'symptom', 'symptom_name', 'symptom_description',
            'severity', 'onset_date', 'duration_days', 'notes',
            'recorded_at', 'recorded_at_formatted'
        ]
        read_only_fields = ['user', 'recorded_at']
    
    def get_recorded_at_formatted(self, obj):
        """Format recorded_at date."""
        return obj.recorded_at.strftime('%Y-%m-%d %H:%M')
    
    def validate_severity(self, value):
        """Validate severity value."""
        if value < 1 or value > 10:
            raise serializers.ValidationError("Severity must be between 1 and 10")
        return value
    
    def validate_duration_days(self, value):
        """Validate duration days."""
        if value < 1:
            raise serializers.ValidationError("Duration must be at least 1 day")
        return value
    
    def validate_onset_date(self, value):
        """Validate onset date."""
        if value > timezone.now().date():
            raise serializers.ValidationError("Onset date cannot be in the future")
        return value
    
    def create(self, validated_data):
        """Create patient symptom with current user."""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['user'] = request.user
        return super().create(validated_data)


class DiseaseModelSerializer(serializers.ModelSerializer):
    """Serializer for DiseaseModel."""
    
    name_display = serializers.CharField(source='get_name_display', read_only=True)
    accuracy_percentage = serializers.SerializerMethodField()
    created_at_formatted = serializers.SerializerMethodField()
    updated_at_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = DiseaseModel
        fields = [
            'id', 'name', 'name_display', 'model_file', 'scaler_file',
            'accuracy', 'accuracy_percentage', 'is_active',
            'created_at', 'created_at_formatted',
            'updated_at', 'updated_at_formatted'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_accuracy_percentage(self, obj):
        """Format accuracy as percentage."""
        return f"{obj.accuracy:.2%}"
    
    def get_created_at_formatted(self, obj):
        """Format created_at date."""
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    
    def get_updated_at_formatted(self, obj):
        """Format updated_at date."""
        return obj.updated_at.strftime('%Y-%m-%d %H:%M')
    
    def validate_accuracy(self, value):
        """Validate accuracy value."""
        if value < 0 or value > 1:
            raise serializers.ValidationError("Accuracy must be between 0 and 1")
        return value
    
    def validate_model_file(self, value):
        """Validate model file."""
        if value:
            if not value.name.endswith(('.pkl', '.joblib')):
                raise serializers.ValidationError(
                    "Model file must be .pkl or .joblib format"
                )
        return value


# Disease-specific prediction serializers
class DiabetesPredictionSerializer(serializers.Serializer):
    """Serializer for diabetes prediction input."""
    
    pregnancies = serializers.IntegerField(min_value=0, max_value=20)
    glucose = serializers.FloatField(min_value=0, max_value=300)
    blood_pressure = serializers.FloatField(min_value=0, max_value=200)
    skin_thickness = serializers.FloatField(min_value=0, max_value=100)
    insulin = serializers.FloatField(min_value=0, max_value=900)
    bmi = serializers.FloatField(min_value=0, max_value=100)
    diabetes_pedigree_function = serializers.FloatField(min_value=0, max_value=3)
    age = serializers.IntegerField(min_value=0, max_value=120)
    
    def validate_glucose(self, value):
        """Validate glucose value."""
        if value > 126 and value < 200:
            self.context['warnings'] = self.context.get('warnings', [])
            self.context['warnings'].append(
                "Glucose level indicates prediabetes. Consult a doctor."
            )
        elif value >= 200:
            self.context['warnings'] = self.context.get('warnings', [])
            self.context['warnings'].append(
                "Glucose level indicates diabetes. Immediate consultation recommended."
            )
        return value
    
    def validate_bmi(self, value):
        """Validate BMI value."""
        if value >= 30:
            self.context['warnings'] = self.context.get('warnings', [])
            self.context['warnings'].append(
                "BMI indicates obesity. Consider weight management."
            )
        return value


class HeartDiseasePredictionSerializer(serializers.Serializer):
    """Serializer for heart disease prediction input."""
    
    age = serializers.IntegerField(min_value=0, max_value=120)
    sex = serializers.ChoiceField(choices=[(0, 'Female'), (1, 'Male')])
    cp = serializers.ChoiceField(choices=[
    (0, "Typical Angina"),
    (1, "Atypical Angina"),
    (2, "Non-anginal Pain"),
    (3, "Asymptomatic")
    ])    
    trestbps = serializers.IntegerField(min_value=0, max_value=300)
    chol = serializers.IntegerField(min_value=0, max_value=600)
    fbs = serializers.ChoiceField(choices=[(0, 1)])
    restecg = serializers.ChoiceField(choices=[
        (0, "Normal"),
        (1, "ST-T wave abnormality"),
        (2, "Left ventricular hypertrophy")
    ])    
    thalach = serializers.IntegerField(min_value=0, max_value=300)
    exang = serializers.ChoiceField(choices=[(0, 1)])
    oldpeak = serializers.FloatField(min_value=0, max_value=10)
    slope = serializers.ChoiceField(choices=[
        (0, "Upsloping"),
        (1, "Flat"),
        (2, "Downsloping")
    ])  
    ca = serializers.IntegerField(min_value=0, max_value=4)
    thal = serializers.ChoiceField(choices=[
        (1, "Normal"),
        (2, "Fixed Defect"),
        (3, "Reversible Defect")
    ])
    
    def validate_trestbps(self, value):
        """Validate blood pressure."""
        if value > 140:
            self.context['warnings'] = self.context.get('warnings', [])
            self.context['warnings'].append(
                "High blood pressure detected. Monitor regularly."
            )
        return value
    
    def validate_chol(self, value):
        """Validate cholesterol."""
        if value > 240:
            self.context['warnings'] = self.context.get('warnings', [])
            self.context['warnings'].append(
                "High cholesterol level detected."
            )
        return value


class KidneyDiseasePredictionSerializer(serializers.Serializer):
    """Serializer for kidney disease prediction input."""
    
    age = serializers.IntegerField(min_value=0, max_value=120)
    blood_pressure = serializers.IntegerField(min_value=0, max_value=300)
    specific_gravity = serializers.FloatField(min_value=1.000, max_value=1.050)
    albumin = serializers.IntegerField(min_value=0, max_value=5)
    sugar = serializers.IntegerField(min_value=0, max_value=5)
    red_blood_cells = serializers.ChoiceField(choices=[(0, 'Normal'), (1, 'Abnormal')])
    pus_cell = serializers.ChoiceField(choices=[(0, 'Normal'), (1, 'Abnormal')])
    pus_cell_clumps = serializers.ChoiceField(choices=[(0, 'Not Present'), (1, 'Present')])
    bacteria = serializers.ChoiceField(choices=[(0, 'Not Present'), (1, 'Present')])
    blood_glucose_random = serializers.FloatField(min_value=0, max_value=500)
    blood_urea = serializers.FloatField(min_value=0, max_value=200)
    serum_creatinine = serializers.FloatField(min_value=0, max_value=20)
    sodium = serializers.FloatField(min_value=100, max_value=200)
    potassium = serializers.FloatField(min_value=0, max_value=10)
    hemoglobin = serializers.FloatField(min_value=0, max_value=20)
    packed_cell_volume = serializers.IntegerField(min_value=0, max_value=100)
    white_blood_cell_count = serializers.IntegerField(min_value=0, max_value=50000)
    red_blood_cell_count = serializers.FloatField(min_value=0, max_value=10)
    hypertension = serializers.ChoiceField(choices=[(0, 'No'), (1, 'Yes')])
    diabetes_mellitus = serializers.ChoiceField(choices=[(0, 'No'), (1, 'Yes')])
    coronary_artery_disease = serializers.ChoiceField(choices=[(0, 'No'), (1, 'Yes')])
    appetite = serializers.ChoiceField(choices=[(0, 'Good'), (1, 'Poor')])
    pedal_edema = serializers.ChoiceField(choices=[(0, 'No'), (1, 'Yes')])
    anemia = serializers.ChoiceField(choices=[(0, 'No'), (1, 'Yes')])
    
    def validate_serum_creatinine(self, value):
        """Validate serum creatinine."""
        if value > 1.2:  # Normal range is 0.6-1.2 mg/dL
            self.context['warnings'] = self.context.get('warnings', [])
            self.context['warnings'].append(
                "Elevated serum creatinine level detected."
            )
        return value


class ParkinsonPredictionSerializer(serializers.Serializer):
    """Serializer for Parkinson disease prediction input."""
    
    mdvp_fo = serializers.FloatField()
    mdvp_fhi = serializers.FloatField()
    mdvp_flo = serializers.FloatField()
    mdvp_jitter_percent = serializers.FloatField()
    mdvp_jitter_abs = serializers.FloatField()
    mdvp_rap = serializers.FloatField()
    mdvp_ppq = serializers.FloatField()
    jitter_ddp = serializers.FloatField()
    mdvp_shimmer = serializers.FloatField()
    mdvp_shimmer_db = serializers.FloatField()
    shimmer_apq3 = serializers.FloatField()
    shimmer_apq5 = serializers.FloatField()
    mdvp_apq = serializers.FloatField()
    shimmer_dda = serializers.FloatField()
    nhr = serializers.FloatField()
    hnr = serializers.FloatField()
    rpde = serializers.FloatField()
    dfa = serializers.FloatField()
    spread1 = serializers.FloatField()
    spread2 = serializers.FloatField()
    d2 = serializers.FloatField()
    ppe = serializers.FloatField()


class BreastCancerPredictionSerializer(serializers.Serializer):
    """Serializer for breast cancer prediction input."""
    
    # Mean values
    radius_mean = serializers.FloatField()
    texture_mean = serializers.FloatField()
    perimeter_mean = serializers.FloatField()
    area_mean = serializers.FloatField()
    smoothness_mean = serializers.FloatField()
    compactness_mean = serializers.FloatField()
    concavity_mean = serializers.FloatField()
    concave_points_mean = serializers.FloatField()
    symmetry_mean = serializers.FloatField()
    fractal_dimension_mean = serializers.FloatField()
    
    # SE values
    radius_se = serializers.FloatField()
    texture_se = serializers.FloatField()
    perimeter_se = serializers.FloatField()
    area_se = serializers.FloatField()
    smoothness_se = serializers.FloatField()
    compactness_se = serializers.FloatField()
    concavity_se = serializers.FloatField()
    concave_points_se = serializers.FloatField()
    symmetry_se = serializers.FloatField()
    fractal_dimension_se = serializers.FloatField()
    
    # Worst values
    radius_worst = serializers.FloatField()
    texture_worst = serializers.FloatField()
    perimeter_worst = serializers.FloatField()
    area_worst = serializers.FloatField()
    smoothness_worst = serializers.FloatField()
    compactness_worst = serializers.FloatField()
    concavity_worst = serializers.FloatField()
    concave_points_worst = serializers.FloatField()
    symmetry_worst = serializers.FloatField()
    fractal_dimension_worst = serializers.FloatField()


class LiverDiseasePredictionSerializer(serializers.Serializer):
    """Serializer for liver disease prediction input."""
    
    age = serializers.IntegerField(min_value=0, max_value=120)
    gender = serializers.ChoiceField(choices=[(0, 'Female'), (1, 'Male')])
    total_bilirubin = serializers.FloatField(min_value=0, max_value=100)
    direct_bilirubin = serializers.FloatField(min_value=0, max_value=50)
    alkaline_phosphotase = serializers.IntegerField(min_value=0, max_value=2000)
    alamine_aminotransferase = serializers.IntegerField(min_value=0, max_value=2000)
    aspartate_aminotransferase = serializers.IntegerField(min_value=0, max_value=5000)
    total_proteins = serializers.FloatField(min_value=0, max_value=10)
    albumin = serializers.FloatField(min_value=0, max_value=10)
    albumin_globulin_ratio = serializers.FloatField(min_value=0, max_value=5)
    
    def validate_total_bilirubin(self, value):
        """Validate total bilirubin."""
        if value > 1.2:  # Normal range is 0.3-1.2 mg/dL
            self.context['warnings'] = self.context.get('warnings', [])
            self.context['warnings'].append(
                "Elevated bilirubin level detected."
            )
        return value

    
# Batch operation serializers
class BatchPredictionSerializer(serializers.Serializer):
    """Serializer for batch predictions."""
    
    disease_type = serializers.ChoiceField(choices=[
        ('diabetes', 'Diabetes'),
        ('heart', 'Heart Disease'),
        ('kidney', 'Kidney Disease'),
        ('parkinson', 'Parkinson Disease'),
        ('breast_cancer', 'Breast Cancer'),
        ('liver', 'Liver Disease'),
    ])
    inputs = serializers.ListField(
        child=serializers.DictField(),
        max_length=100  # Limit batch size
    )
    
    def validate_inputs(self, value):
        """Validate batch inputs."""
        if len(value) > 100:
            raise serializers.ValidationError("Maximum 100 inputs per batch")
        return value


class BatchSymptomSerializer(serializers.Serializer):
    """Serializer for batch symptom creation."""
    
    symptoms = serializers.ListField(
        child=serializers.DictField(),
        max_length=50
    )
    
    def validate_symptoms(self, value):
        """Validate batch symptoms."""
        if len(value) > 50:
            raise serializers.ValidationError("Maximum 50 symptoms per batch")
        
        # Validate each symptom
        for symptom in value:
            if 'symptom' not in symptom:
                raise serializers.ValidationError("Each symptom must have a symptom ID")
        
        return value


# Result serializers
class PredictionResultSerializer(serializers.Serializer):
    """Serializer for prediction results."""
    
    disease = serializers.CharField()
    prediction = serializers.IntegerField()
    label = serializers.CharField()
    probability = serializers.FloatField()
    confidence = serializers.FloatField()
    risk_level = serializers.CharField()
    probabilities = serializers.DictField()
    timestamp = serializers.DateTimeField()
    
    def to_representation(self, instance):
        """Format the output."""
        data = super().to_representation(instance)
        
        # Add formatted fields
        data['probability_percentage'] = f"{data['probability']:.2%}"
        data['confidence_percentage'] = f"{data['confidence']:.2%}"
        data['timestamp_formatted'] = instance['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        
        return data


class HealthReportResultSerializer(serializers.Serializer):
    """Serializer for health report results."""
    
    report_id = serializers.IntegerField()
    report_date = serializers.DateField()
    overall_risk_score = serializers.FloatField()
    risk_level = serializers.CharField()
    recommendations = serializers.CharField()
    findings = serializers.DictField()
    
    def to_representation(self, instance):
        """Format the output."""
        data = super().to_representation(instance)
        
        # Add formatted fields
        data['risk_score_percentage'] = f"{data['overall_risk_score']:.2%}"
        data['report_date_formatted'] = instance['report_date'].strftime('%Y-%m-%d')
        
        return data