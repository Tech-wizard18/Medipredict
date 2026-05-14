"""
Test cases for Django models in MEDIPREDICT
"""

import os
import tempfile
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.utils import timezone

from prediction_app.models import (
    Prediction, DiseaseType, MLModel, PredictionHistory,
    Report, UserFeedback, Symptom
)
from users_app.models import UserProfile, DoctorProfile, PatientProfile
from consultations_app.models import Consultation, Appointment
from prescriptions_app.models import Prescription, Medication
from notifications_app.models import Notification

User = get_user_model()


class UserModelTests(TestCase):
    """Test User model and related profiles."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='John',
            last_name='Doe'
        )
    
    def test_create_user(self):
        """Test creating a regular user."""
        self.assertEqual(self.user.email, 'test@example.com')
        self.assertEqual(self.user.first_name, 'John')
        self.assertEqual(self.user.last_name, 'Doe')
        self.assertTrue(self.user.check_password('testpass123'))
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)
        self.assertTrue(self.user.is_active)
    
    def test_create_superuser(self):
        """Test creating a superuser."""
        admin_user = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpass123'
        )
        self.assertEqual(admin_user.email, 'admin@example.com')
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
        self.assertTrue(admin_user.is_active)
    
    def test_user_str_representation(self):
        """Test string representation of user."""
        self.assertEqual(str(self.user), 'test@example.com')
    
    def test_user_full_name(self):
        """Test user's full name property."""
        self.assertEqual(self.user.get_full_name(), 'John Doe')
    
    def test_user_email_normalization(self):
        """Test email is normalized."""
        email = 'Test@EXAMPLE.com'
        user = User.objects.create_user(email, 'test123')
        self.assertEqual(user.email, 'Test@example.com')
    
    def test_create_user_without_email_raises_error(self):
        """Test that creating user without email raises ValueError."""
        with self.assertRaises(ValueError):
            User.objects.create_user(email='', password='test123')
    
    def test_user_profile_creation_signal(self):
        """Test that user profile is created automatically."""
        self.assertTrue(hasattr(self.user, 'profile'))
        self.assertIsNotNone(self.user.profile)
    
    def test_doctor_profile_creation(self):
        """Test doctor profile creation."""
        doctor_user = User.objects.create_user(
            email='doctor@example.com',
            password='doctor123',
            user_type='doctor'
        )
        self.assertTrue(hasattr(doctor_user, 'doctor_profile'))
        self.assertEqual(doctor_user.doctor_profile.specialization, 'General')


class UserProfileModelTests(TestCase):
    """Test UserProfile model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='profile@example.com',
            password='testpass123'
        )
        self.profile = self.user.profile
    
    def test_profile_str_representation(self):
        """Test string representation of profile."""
        self.assertEqual(str(self.profile), 'profile@example.com Profile')
    
    def test_profile_default_values(self):
        """Test default values for profile."""
        self.assertEqual(self.profile.date_of_birth, None)
        self.assertEqual(self.profile.gender, '')
        self.assertEqual(self.profile.phone, '')
        self.assertEqual(self.profile.address, '')
        self.assertEqual(self.profile.city, '')
        self.assertEqual(self.profile.country, '')
        self.assertEqual(self.profile.blood_group, '')
        self.assertEqual(self.profile.allergies, '')
        self.assertEqual(self.profile.medical_history, '')
        self.assertIsNotNone(self.profile.created_at)
    
    def test_profile_age_calculation(self):
        """Test age calculation from date of birth."""
        # Test with date of birth
        self.profile.date_of_birth = datetime(1990, 1, 1).date()
        self.profile.save()
        
        with patch('users_app.models.timezone') as mock_timezone:
            mock_timezone.now.return_value = datetime(2024, 1, 1)
            self.assertEqual(self.profile.age, 34)
    
    def test_profile_age_without_dob(self):
        """Test age calculation without date of birth."""
        self.profile.date_of_birth = None
        self.profile.save()
        self.assertIsNone(self.profile.age)
    
    def test_profile_photo_upload(self):
        """Test profile photo upload."""
        # Create a dummy image file
        image_content = b'fake image content'
        image_file = SimpleUploadedFile(
            'test.jpg',
            image_content,
            content_type='image/jpeg'
        )
        
        self.profile.profile_photo = image_file
        self.profile.save()
        
        self.assertTrue(self.profile.profile_photo.name.startswith('profiles/'))
        self.assertTrue(self.profile.profile_photo.name.endswith('.jpg'))


class PredictionModelTests(TestCase):
    """Test Prediction model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='user@example.com',
            password='testpass123'
        )
        
        # Create disease types
        self.diabetes = DiseaseType.objects.create(
            name='Diabetes',
            code='diabetes',
            description='Diabetes prediction model'
        )
        
        self.heart = DiseaseType.objects.create(
            name='Heart Disease',
            code='heart',
            description='Heart disease prediction model'
        )
        
        # Create ML models
        self.ml_model = MLModel.objects.create(
            disease_type=self.diabetes,
            name='Random Forest Diabetes',
            version='1.0.0',
            accuracy=0.85,
            path='models/diabetes_model.pkl',
            is_active=True
        )
    
    def test_create_prediction(self):
        """Test creating a prediction."""
        prediction = Prediction.objects.create(
            user=self.user,
            disease_type=self.diabetes,
            ml_model=self.ml_model,
            input_data={'glucose': 120, 'bmi': 25.5},
            prediction_result={'has_disease': True, 'probability': 0.78},
            confidence_score=0.78,
            is_positive=True
        )
        
        self.assertEqual(prediction.user, self.user)
        self.assertEqual(prediction.disease_type, self.diabetes)
        self.assertEqual(prediction.ml_model, self.ml_model)
        self.assertEqual(prediction.input_data, {'glucose': 120, 'bmi': 25.5})
        self.assertEqual(prediction.prediction_result, {'has_disease': True, 'probability': 0.78})
        self.assertEqual(prediction.confidence_score, 0.78)
        self.assertTrue(prediction.is_positive)
        self.assertFalse(prediction.reviewed_by_doctor)
        self.assertIsNotNone(prediction.created_at)
    
    def test_prediction_str_representation(self):
        """Test string representation of prediction."""
        prediction = Prediction.objects.create(
            user=self.user,
            disease_type=self.diabetes,
            ml_model=self.ml_model,
            input_data={'glucose': 120},
            prediction_result={'has_disease': True},
            confidence_score=0.78,
            is_positive=True
        )
        
        expected_str = f"Diabetes prediction for {self.user.email} at {prediction.created_at}"
        self.assertEqual(str(prediction), expected_str)
    
    def test_prediction_get_risk_level(self):
        """Test risk level calculation."""
        # High risk
        prediction1 = Prediction.objects.create(
            user=self.user,
            disease_type=self.diabetes,
            ml_model=self.ml_model,
            confidence_score=0.85,
            is_positive=True
        )
        self.assertEqual(prediction1.get_risk_level(), 'High')
        
        # Medium risk
        prediction2 = Prediction.objects.create(
            user=self.user,
            disease_type=self.diabetes,
            ml_model=self.ml_model,
            confidence_score=0.65,
            is_positive=True
        )
        self.assertEqual(prediction2.get_risk_level(), 'Medium')
        
        # Low risk
        prediction3 = Prediction.objects.create(
            user=self.user,
            disease_type=self.diabetes,
            ml_model=self.ml_model,
            confidence_score=0.45,
            is_positive=True
        )
        self.assertEqual(prediction3.get_risk_level(), 'Low')
        
        # Negative result
        prediction4 = Prediction.objects.create(
            user=self.user,
            disease_type=self.diabetes,
            ml_model=self.ml_model,
            confidence_score=0.90,
            is_positive=False
        )
        self.assertEqual(prediction4.get_risk_level(), 'Negative')
    
    def test_prediction_queryset_methods(self):
        """Test prediction queryset methods."""
        # Create predictions
        Prediction.objects.create(
            user=self.user,
            disease_type=self.diabetes,
            ml_model=self.ml_model,
            is_positive=True,
            confidence_score=0.85
        )
        
        Prediction.objects.create(
            user=self.user,
            disease_type=self.diabetes,
            ml_model=self.ml_model,
            is_positive=False,
            confidence_score=0.90
        )
        
        # Test positive predictions
        positive_predictions = Prediction.objects.positive()
        self.assertEqual(positive_predictions.count(), 1)
        
        # Test high risk predictions
        high_risk = Prediction.objects.high_risk()
        self.assertEqual(high_risk.count(), 1)
        
        # Test recent predictions
        recent = Prediction.objects.recent(days=7)
        self.assertEqual(recent.count(), 2)
    
    def test_prediction_doctor_review(self):
        """Test prediction doctor review functionality."""
        doctor = User.objects.create_user(
            email='doctor@example.com',
            password='doctor123',
            user_type='doctor'
        )
        
        prediction = Prediction.objects.create(
            user=self.user,
            disease_type=self.diabetes,
            ml_model=self.ml_model,
            is_positive=True
        )
        
        # Mark as reviewed
        prediction.mark_as_reviewed(doctor, 'Looks accurate, recommend follow-up tests.')
        
        self.assertTrue(prediction.reviewed_by_doctor)
        self.assertEqual(prediction.reviewed_by, doctor)
        self.assertIsNotNone(prediction.reviewed_at)
        self.assertEqual(prediction.doctor_notes, 'Looks accurate, recommend follow-up tests.')


class DiseaseTypeModelTests(TestCase):
    """Test DiseaseType model."""
    
    def test_create_disease_type(self):
        """Test creating a disease type."""
        disease = DiseaseType.objects.create(
            name='Diabetes',
            code='diabetes',
            description='Diabetes mellitus prediction',
            symptoms_description='Increased thirst, frequent urination, fatigue',
            prevention_tips='Maintain healthy weight, exercise regularly, balanced diet',
            risk_factors='Family history, obesity, age over 45',
            is_active=True
        )
        
        self.assertEqual(disease.name, 'Diabetes')
        self.assertEqual(disease.code, 'diabetes')
        self.assertEqual(disease.description, 'Diabetes mellitus prediction')
        self.assertTrue(disease.is_active)
        self.assertIsNotNone(disease.created_at)
    
    def test_disease_type_str_representation(self):
        """Test string representation of disease type."""
        disease = DiseaseType.objects.create(
            name='Heart Disease',
            code='heart'
        )
        self.assertEqual(str(disease), 'Heart Disease (heart)')
    
    def test_disease_type_slug_generation(self):
        """Test slug generation for disease type."""
        disease = DiseaseType.objects.create(
            name='Breast Cancer',
            code='breast_cancer'
        )
        self.assertEqual(disease.slug, 'breast-cancer')
    
    def test_disease_type_available_models(self):
        """Test available ML models for disease type."""
        disease = DiseaseType.objects.create(
            name='Diabetes',
            code='diabetes'
        )
        
        # Create active and inactive models
        MLModel.objects.create(
            disease_type=disease,
            name='Model 1',
            version='1.0.0',
            is_active=True
        )
        
        MLModel.objects.create(
            disease_type=disease,
            name='Model 2',
            version='1.1.0',
            is_active=False
        )
        
        MLModel.objects.create(
            disease_type=disease,
            name='Model 3',
            version='2.0.0',
            is_active=True
        )
        
        available_models = disease.available_models
        self.assertEqual(available_models.count(), 2)
        self.assertEqual(available_models.first().name, 'Model 1')
        self.assertEqual(available_models.last().name, 'Model 3')
    
    def test_disease_type_best_model(self):
        """Test getting the best model for disease type."""
        disease = DiseaseType.objects.create(
            name='Diabetes',
            code='diabetes'
        )
        
        # Create models with different accuracy
        model1 = MLModel.objects.create(
            disease_type=disease,
            name='Model 1',
            version='1.0.0',
            accuracy=0.85,
            is_active=True
        )
        
        model2 = MLModel.objects.create(
            disease_type=disease,
            name='Model 2',
            version='1.1.0',
            accuracy=0.92,
            is_active=True
        )
        
        best_model = disease.best_model
        self.assertEqual(best_model, model2)


class MLModelModelTests(TestCase):
    """Test MLModel model."""
    
    def setUp(self):
        self.disease = DiseaseType.objects.create(
            name='Diabetes',
            code='diabetes'
        )
    
    def test_create_ml_model(self):
        """Test creating an ML model."""
        ml_model = MLModel.objects.create(
            disease_type=self.disease,
            name='Random Forest Classifier',
            version='1.0.0',
            description='Random Forest model for diabetes prediction',
            algorithm='random_forest',
            accuracy=0.85,
            precision=0.82,
            recall=0.87,
            f1_score=0.84,
            roc_auc=0.89,
            training_date=timezone.now(),
            dataset_size=1000,
            features=['glucose', 'bmi', 'age'],
            path='models/diabetes_rf.pkl',
            is_active=True
        )
        
        self.assertEqual(ml_model.disease_type, self.disease)
        self.assertEqual(ml_model.name, 'Random Forest Classifier')
        self.assertEqual(ml_model.version, '1.0.0')
        self.assertEqual(ml_model.accuracy, 0.85)
        self.assertEqual(ml_model.algorithm, 'random_forest')
        self.assertTrue(ml_model.is_active)
    
    def test_ml_model_str_representation(self):
        """Test string representation of ML model."""
        ml_model = MLModel.objects.create(
            disease_type=self.disease,
            name='SVM Classifier',
            version='1.0.0',
            accuracy=0.82
        )
        
        expected_str = 'Diabetes - SVM Classifier v1.0.0 (82.0%)'
        self.assertEqual(str(ml_model), expected_str)
    
    def test_ml_model_performance_dict(self):
        """Test performance metrics dictionary."""
        ml_model = MLModel.objects.create(
            disease_type=self.disease,
            name='Test Model',
            version='1.0.0',
            accuracy=0.85,
            precision=0.82,
            recall=0.87,
            f1_score=0.84,
            roc_auc=0.89
        )
        
        performance = ml_model.get_performance_dict()
        self.assertEqual(performance['accuracy'], 0.85)
        self.assertEqual(performance['precision'], 0.82)
        self.assertEqual(performance['recall'], 0.87)
        self.assertEqual(performance['f1_score'], 0.84)
        self.assertEqual(performance['roc_auc'], 0.89)
    
    def test_ml_model_deactivate(self):
        """Test deactivating an ML model."""
        ml_model = MLModel.objects.create(
            disease_type=self.disease,
            name='Test Model',
            version='1.0.0',
            is_active=True
        )
        
        self.assertTrue(ml_model.is_active)
        
        ml_model.deactivate()
        self.assertFalse(ml_model.is_active)
        
        # Reactivate
        ml_model.activate()
        self.assertTrue(ml_model.is_active)
    
    def test_ml_model_get_latest_version(self):
        """Test getting latest version of models."""
        # Create multiple versions
        MLModel.objects.create(
            disease_type=self.disease,
            name='Model',
            version='1.0.0',
            is_active=True
        )
        
        MLModel.objects.create(
            disease_type=self.disease,
            name='Model',
            version='1.1.0',
            is_active=True
        )
        
        MLModel.objects.create(
            disease_type=self.disease,
            name='Model',
            version='2.0.0',
            is_active=True
        )
        
        latest = MLModel.objects.get_latest_version(self.disease, 'Model')
        self.assertEqual(latest.version, '2.0.0')


class PredictionHistoryModelTests(TestCase):
    """Test PredictionHistory model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='user@example.com',
            password='testpass123'
        )
        
        self.disease = DiseaseType.objects.create(
            name='Diabetes',
            code='diabetes'
        )
        
        self.prediction = Prediction.objects.create(
            user=self.user,
            disease_type=self.disease,
            input_data={'glucose': 120},
            prediction_result={'has_disease': True},
            confidence_score=0.78
        )
    
    def test_create_prediction_history(self):
        """Test creating prediction history entry."""
        history = PredictionHistory.objects.create(
            prediction=self.prediction,
            action='created',
            details='Prediction was created',
            changed_by=self.user
        )
        
        self.assertEqual(history.prediction, self.prediction)
        self.assertEqual(history.action, 'created')
        self.assertEqual(history.details, 'Prediction was created')
        self.assertEqual(history.changed_by, self.user)
        self.assertIsNotNone(history.changed_at)
    
    def test_prediction_history_auto_creation_signal(self):
        """Test that history is created automatically on prediction save."""
        # Initial prediction creation should have a history entry
        history_count = PredictionHistory.objects.filter(prediction=self.prediction).count()
        self.assertEqual(history_count, 1)
        
        # Update prediction should create another history entry
        self.prediction.confidence_score = 0.85
        self.prediction.save()
        
        history_count = PredictionHistory.objects.filter(prediction=self.prediction).count()
        self.assertEqual(history_count, 2)
    
    def test_prediction_history_str_representation(self):
        """Test string representation of prediction history."""
        history = PredictionHistory.objects.create(
            prediction=self.prediction,
            action='updated',
            details='Confidence score updated',
            changed_by=self.user
        )
        
        expected_str = f'History for prediction {self.prediction.id} - updated'
        self.assertEqual(str(history), expected_str)


class ReportModelTests(TestCase):
    """Test Report model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='user@example.com',
            password='testpass123'
        )
        
        self.disease = DiseaseType.objects.create(
            name='Diabetes',
            code='diabetes'
        )
        
        self.prediction = Prediction.objects.create(
            user=self.user,
            disease_type=self.disease,
            input_data={'glucose': 120},
            prediction_result={'has_disease': True},
            confidence_score=0.78
        )
    
    def test_create_report(self):
        """Test creating a report."""
        report = Report.objects.create(
            user=self.user,
            title='Diabetes Screening Report',
            report_type='screening',
            content={
                'summary': 'High risk of diabetes detected',
                'recommendations': ['Consult a doctor', 'Monitor blood sugar'],
                'next_steps': ['Schedule appointment', 'Lifestyle changes']
            },
            predictions=[self.prediction],
            doctor_notes='Patient shows early signs of diabetes',
            is_shared=True
        )
        
        self.assertEqual(report.user, self.user)
        self.assertEqual(report.title, 'Diabetes Screening Report')
        self.assertEqual(report.report_type, 'screening')
        self.assertEqual(report.content['summary'], 'High risk of diabetes detected')
        self.assertEqual(report.predictions.first(), self.prediction)
        self.assertTrue(report.is_shared)
        self.assertIsNotNone(report.generated_at)
    
    def test_report_str_representation(self):
        """Test string representation of report."""
        report = Report.objects.create(
            user=self.user,
            title='Test Report',
            report_type='screening'
        )
        
        expected_str = f'Test Report for {self.user.email}'
        self.assertEqual(str(report), expected_str)
    
    def test_report_generate_pdf(self):
        """Test PDF generation for report."""
        report = Report.objects.create(
            user=self.user,
            title='Test Report',
            report_type='screening',
            content={
                'summary': 'Test summary',
                'recommendations': ['Test recommendation']
            }
        )
        
        # Test PDF generation (mocked)
        with patch('prediction_app.models.generate_pdf') as mock_generate_pdf:
            mock_generate_pdf.return_value = b'PDF content'
            
            pdf_content = report.generate_pdf()
            
            self.assertEqual(pdf_content, b'PDF content')
            mock_generate_pdf.assert_called_once_with(report.content)
    
    def test_report_share_with_doctor(self):
        """Test sharing report with doctor."""
        doctor = User.objects.create_user(
            email='doctor@example.com',
            password='doctor123',
            user_type='doctor'
        )
        
        report = Report.objects.create(
            user=self.user,
            title='Test Report',
            report_type='screening'
        )
        
        # Share with doctor
        report.share_with_doctor(doctor, 'Please review this report')
        
        self.assertTrue(report.is_shared)
        self.assertEqual(report.shared_with, doctor)
        self.assertIsNotNone(report.shared_at)
        self.assertEqual(report.sharing_notes, 'Please review this report')


class UserFeedbackModelTests(TestCase):
    """Test UserFeedback model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='user@example.com',
            password='testpass123'
        )
    
    def test_create_user_feedback(self):
        """Test creating user feedback."""
        feedback = UserFeedback.objects.create(
            user=self.user,
            rating=5,
            comment='Great prediction system! Very accurate.',
            feedback_type='prediction',
            prediction_accuracy='accurate',
            suggestions='Add more disease types',
            is_resolved=False
        )
        
        self.assertEqual(feedback.user, self.user)
        self.assertEqual(feedback.rating, 5)
        self.assertEqual(feedback.comment, 'Great prediction system! Very accurate.')
        self.assertEqual(feedback.feedback_type, 'prediction')
        self.assertEqual(feedback.prediction_accuracy, 'accurate')
        self.assertFalse(feedback.is_resolved)
        self.assertIsNotNone(feedback.created_at)
    
    def test_user_feedback_str_representation(self):
        """Test string representation of user feedback."""
        feedback = UserFeedback.objects.create(
            user=self.user,
            rating=4,
            comment='Good service'
        )
        
        expected_str = f'Feedback from {self.user.email} - Rating: 4'
        self.assertEqual(str(feedback), expected_str)
    
    def test_user_feedback_mark_as_resolved(self):
        """Test marking feedback as resolved."""
        feedback = UserFeedback.objects.create(
            user=self.user,
            rating=3,
            comment='Need improvement',
            is_resolved=False
        )
        
        self.assertFalse(feedback.is_resolved)
        self.assertIsNone(feedback.resolved_at)
        self.assertIsNone(feedback.resolved_by)
        
        # Mark as resolved
        admin_user = User.objects.create_user(
            email='admin@example.com',
            password='admin123'
        )
        
        feedback.mark_as_resolved(admin_user, 'Implemented suggested changes')
        
        self.assertTrue(feedback.is_resolved)
        self.assertEqual(feedback.resolved_by, admin_user)
        self.assertIsNotNone(feedback.resolved_at)
        self.assertEqual(feedback.resolution_notes, 'Implemented suggested changes')
    
    def test_user_feedback_average_rating(self):
        """Test average rating calculation."""
        # Create multiple feedback entries
        UserFeedback.objects.create(user=self.user, rating=5)
        UserFeedback.objects.create(user=self.user, rating=4)
        UserFeedback.objects.create(user=self.user, rating=3)
        
        average_rating = UserFeedback.objects.average_rating()
        self.assertEqual(average_rating, 4.0)  # (5+4+3)/3 = 4.0


class SymptomModelTests(TestCase):
    """Test Symptom model."""
    
    def setUp(self):
        self.disease = DiseaseType.objects.create(
            name='Diabetes',
            code='diabetes'
        )
    
    def test_create_symptom(self):
        """Test creating a symptom."""
        symptom = Symptom.objects.create(
            name='Increased Thirst',
            description='Feeling unusually thirsty all the time',
            severity='moderate',
            disease_type=self.disease,
            is_common=True,
            frequency='often'
        )
        
        self.assertEqual(symptom.name, 'Increased Thirst')
        self.assertEqual(symptom.description, 'Feeling unusually thirsty all the time')
        self.assertEqual(symptom.severity, 'moderate')
        self.assertEqual(symptom.disease_type, self.disease)
        self.assertTrue(symptom.is_common)
        self.assertEqual(symptom.frequency, 'often')
    
    def test_symptom_str_representation(self):
        """Test string representation of symptom."""
        symptom = Symptom.objects.create(
            name='Fatigue',
            disease_type=self.disease
        )
        
        self.assertEqual(str(symptom), 'Fatigue (Diabetes)')
    
    def test_symptom_for_disease(self):
        """Test getting symptoms for a specific disease."""
        # Create symptoms for different diseases
        Symptom.objects.create(name='Symptom 1', disease_type=self.disease)
        Symptom.objects.create(name='Symptom 2', disease_type=self.disease)
        
        heart_disease = DiseaseType.objects.create(name='Heart Disease', code='heart')
        Symptom.objects.create(name='Symptom 3', disease_type=heart_disease)
        
        diabetes_symptoms = Symptom.objects.for_disease(self.disease)
        self.assertEqual(diabetes_symptoms.count(), 2)
        
        heart_symptoms = Symptom.objects.for_disease(heart_disease)
        self.assertEqual(heart_symptoms.count(), 1)
    
    def test_symptom_common_symptoms(self):
        """Test getting common symptoms."""
        Symptom.objects.create(
            name='Common Symptom',
            disease_type=self.disease,
            is_common=True
        )
        
        Symptom.objects.create(
            name='Rare Symptom',
            disease_type=self.disease,
            is_common=False
        )
        
        common_symptoms = Symptom.objects.common()
        self.assertEqual(common_symptoms.count(), 1)
        self.assertEqual(common_symptoms.first().name, 'Common Symptom')


class ConsultationModelTests(TestCase):
    """Test Consultation model."""
    
    def setUp(self):
        self.patient = User.objects.create_user(
            email='patient@example.com',
            password='patient123',
            user_type='patient'
        )
        
        self.doctor = User.objects.create_user(
            email='doctor@example.com',
            password='doctor123',
            user_type='doctor'
        )
        
        self.disease = DiseaseType.objects.create(
            name='Diabetes',
            code='diabetes'
        )
        
        self.prediction = Prediction.objects.create(
            user=self.patient,
            disease_type=self.disease,
            input_data={'glucose': 120},
            prediction_result={'has_disease': True},
            confidence_score=0.78
        )
    
    def test_create_consultation(self):
        """Test creating a consultation."""
        consultation = Consultation.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            prediction=self.prediction,
            consultation_type='followup',
            status='scheduled',
            symptoms='Increased thirst, fatigue',
            notes='Patient shows early signs of diabetes',
            scheduled_for=timezone.now() + timedelta(days=1),
            duration_minutes=30
        )
        
        self.assertEqual(consultation.patient, self.patient)
        self.assertEqual(consultation.doctor, self.doctor)
        self.assertEqual(consultation.prediction, self.prediction)
        self.assertEqual(consultation.consultation_type, 'followup')
        self.assertEqual(consultation.status, 'scheduled')
        self.assertEqual(consultation.symptoms, 'Increased thirst, fatigue')
        self.assertEqual(consultation.duration_minutes, 30)
    
    def test_consultation_str_representation(self):
        """Test string representation of consultation."""
        consultation = Consultation.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            status='scheduled'
        )
        
        expected_str = f'Consultation: {self.patient.email} with {self.doctor.email}'
        self.assertEqual(str(consultation), expected_str)
    
    def test_consultation_complete(self):
        """Test completing a consultation."""
        consultation = Consultation.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            status='scheduled'
        )
        
        self.assertEqual(consultation.status, 'scheduled')
        self.assertIsNone(consultation.completed_at)
        
        # Complete consultation
        consultation.complete('Consultation completed successfully')
        
        self.assertEqual(consultation.status, 'completed')
        self.assertIsNotNone(consultation.completed_at)
        self.assertEqual(consultation.outcome, 'Consultation completed successfully')
    
    def test_consultation_cancel(self):
        """Test cancelling a consultation."""
        consultation = Consultation.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            status='scheduled'
        )
        
        consultation.cancel('Patient rescheduled')
        
        self.assertEqual(consultation.status, 'cancelled')
        self.assertEqual(consultation.cancellation_reason, 'Patient rescheduled')
        self.assertIsNotNone(consultation.cancelled_at)
    
    def test_consultation_is_upcoming(self):
        """Test if consultation is upcoming."""
        # Future consultation
        future_consultation = Consultation.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            status='scheduled',
            scheduled_for=timezone.now() + timedelta(hours=2)
        )
        self.assertTrue(future_consultation.is_upcoming())
        
        # Past consultation
        past_consultation = Consultation.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            status='scheduled',
            scheduled_for=timezone.now() - timedelta(hours=2)
        )
        self.assertFalse(past_consultation.is_upcoming())


class PrescriptionModelTests(TestCase):
    """Test Prescription model."""
    
    def setUp(self):
        self.patient = User.objects.create_user(
            email='patient@example.com',
            password='patient123',
            user_type='patient'
        )
        
        self.doctor = User.objects.create_user(
            email='doctor@example.com',
            password='doctor123',
            user_type='doctor'
        )
        
        self.consultation = Consultation.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            status='completed'
        )
    
    def test_create_prescription(self):
        """Test creating a prescription."""
        prescription = Prescription.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            consultation=self.consultation,
            diagnosis='Type 2 Diabetes',
            instructions='Take medication as prescribed, monitor blood sugar',
            notes='Patient should follow up in 3 months',
            is_active=True
        )
        
        self.assertEqual(prescription.patient, self.patient)
        self.assertEqual(prescription.doctor, self.doctor)
        self.assertEqual(prescription.consultation, self.consultation)
        self.assertEqual(prescription.diagnosis, 'Type 2 Diabetes')
        self.assertTrue(prescription.is_active)
        self.assertIsNotNone(prescription.created_at)
    
    def test_prescription_str_representation(self):
        """Test string representation of prescription."""
        prescription = Prescription.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            diagnosis='Diabetes'
        )
        
        expected_str = f'Prescription for {self.patient.email} by {self.doctor.email}'
        self.assertEqual(str(prescription), expected_str)
    
    def test_prescription_add_medication(self):
        """Test adding medication to prescription."""
        prescription = Prescription.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            diagnosis='Diabetes'
        )
        
        # Create medication
        medication = Medication.objects.create(
            prescription=prescription,
            name='Metformin',
            dosage='500mg',
            frequency='Twice daily',
            duration_days=30,
            instructions='Take with meals'
        )
        
        self.assertEqual(medication.prescription, prescription)
        self.assertEqual(medication.name, 'Metformin')
        self.assertEqual(medication.dosage, '500mg')
        self.assertEqual(medication.duration_days, 30)
    
    def test_prescription_deactivate(self):
        """Test deactivating a prescription."""
        prescription = Prescription.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            diagnosis='Diabetes',
            is_active=True
        )
        
        self.assertTrue(prescription.is_active)
        
        prescription.deactivate('Patient switched to different medication')
        
        self.assertFalse(prescription.is_active)
        self.assertEqual(prescription.deactivation_reason, 'Patient switched to different medication')
        self.assertIsNotNone(prescription.deactivated_at)
    
    def test_prescription_is_active(self):
        """Test checking if prescription is still active based on duration."""
        # Active prescription (created recently)
        prescription1 = Prescription.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            diagnosis='Diabetes',
            is_active=True
        )
        self.assertTrue(prescription1.is_still_active())
        
        # Inactive prescription
        prescription2 = Prescription.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            diagnosis='Diabetes',
            is_active=False
        )
        self.assertFalse(prescription2.is_still_active())


class NotificationModelTests(TestCase):
    """Test Notification model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='user@example.com',
            password='testpass123'
        )
    
    def test_create_notification(self):
        """Test creating a notification."""
        notification = Notification.objects.create(
            user=self.user,
            title='New Prediction Available',
            message='Your diabetes prediction results are ready',
            notification_type='prediction',
            priority='medium',
            data={'prediction_id': 123, 'disease_type': 'diabetes'},
            is_read=False
        )
        
        self.assertEqual(notification.user, self.user)
        self.assertEqual(notification.title, 'New Prediction Available')
        self.assertEqual(notification.message, 'Your diabetes prediction results are ready')
        self.assertEqual(notification.notification_type, 'prediction')
        self.assertEqual(notification.priority, 'medium')
        self.assertEqual(notification.data, {'prediction_id': 123, 'disease_type': 'diabetes'})
        self.assertFalse(notification.is_read)
        self.assertIsNotNone(notification.created_at)
    
    def test_notification_str_representation(self):
        """Test string representation of notification."""
        notification = Notification.objects.create(
            user=self.user,
            title='Test Notification',
            message='Test message'
        )
        
        expected_str = f'Notification for {self.user.email}: Test Notification'
        self.assertEqual(str(notification), expected_str)
    
    def test_notification_mark_as_read(self):
        """Test marking notification as read."""
        notification = Notification.objects.create(
            user=self.user,
            title='Test',
            message='Test',
            is_read=False
        )
        
        self.assertFalse(notification.is_read)
        self.assertIsNone(notification.read_at)
        
        notification.mark_as_read()
        
        self.assertTrue(notification.is_read)
        self.assertIsNotNone(notification.read_at)
    
    def test_notification_mark_as_unread(self):
        """Test marking notification as unread."""
        notification = Notification.objects.create(
            user=self.user,
            title='Test',
            message='Test',
            is_read=True,
            read_at=timezone.now()
        )
        
        notification.mark_as_unread()
        
        self.assertFalse(notification.is_read)
        self.assertIsNone(notification.read_at)
    
    def test_notification_unread_count(self):
        """Test getting unread notification count."""
        # Create read and unread notifications
        Notification.objects.create(user=self.user, title='Test 1', message='Test', is_read=True)
        Notification.objects.create(user=self.user, title='Test 2', message='Test', is_read=False)
        Notification.objects.create(user=self.user, title='Test 3', message='Test', is_read=False)
        
        unread_count = Notification.objects.unread_count(self.user)
        self.assertEqual(unread_count, 2)
    
    def test_notification_send_email(self):
        """Test sending notification email."""
        notification = Notification.objects.create(
            user=self.user,
            title='Important Update',
            message='Your account has been updated',
            notification_type='account',
            priority='high'
        )
        
        with patch('notifications_app.models.send_mail') as mock_send_mail:
            notification.send_email()
            
            mock_send_mail.assert_called_once()
            call_args = mock_send_mail.call_args
            self.assertEqual(call_args[0][0], 'Important Update')
            self.assertEqual(call_args[0][1], 'Your account has been updated')
            self.assertEqual(call_args[0][2], 'noreply@medipredict.example.com')
            self.assertEqual(call_args[0][3], ['user@example.com'])