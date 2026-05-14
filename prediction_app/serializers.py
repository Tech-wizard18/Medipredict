# prediction_app/serializers.py
from rest_framework import serializers
from .models import (
    DiseaseModel, Prediction, HealthReport, Symptom, PatientSymptom
)

# Disease Model Serializer
class DiseaseModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiseaseModel
        fields = ['id', 'name', 'description', 'is_active', 'created_at', 'updated_at']


# Prediction Serializer
class PredictionSerializer(serializers.ModelSerializer):
    disease_model = DiseaseModelSerializer(read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)

    class Meta:
        model = Prediction
        fields = [
            'id', 'user_id', 'disease_model', 'prediction_result', 
            'prediction_label', 'confidence', 'input_data', 'created_at', 'updated_at'
        ]


# Health Report Serializer
class HealthReportSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)

    class Meta:
        model = HealthReport
        fields = [
            'id', 'user_id', 'report_date', 'overall_risk_score', 
            'risk_level', 'recommendations', 'findings', 'generated_by', 'created_at', 'updated_at'
        ]


# Symptom Serializer
class SymptomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Symptom
        fields = ['id', 'name', 'category', 'description', 'created_at', 'updated_at']


# Patient Symptom Serializer
class PatientSymptomSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    symptom = SymptomSerializer(read_only=True)

    class Meta:
        model = PatientSymptom
        fields = [
            'id', 'user_id', 'symptom', 'severity', 'onset_date', 
            'recorded_at', 'notes', 'created_at', 'updated_at'
        ]
