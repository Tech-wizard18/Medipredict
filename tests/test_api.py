"""
Test cases for REST API endpoints in MEDIPREDICT
"""

import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from prediction_app.models import (
    Prediction, DiseaseType, MLModel, Report, UserFeedback
)
from users_app.models import UserProfile
from consultations_app.models import Consultation
from prescriptions_app.models import Prescription

User = get_user_model()


class AuthenticationAPITests(TestCase):
    """Test authentication-related API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='John',
            last_name='Doe'
        )
        self.user.profile.phone = '1234567890'
        self.user.profile.save()
    
    def test_api_token_obtain(self):
        """Test obtaining JWT token."""
        response = self.client.post('/api/token/', {
            'email': 'test@example.com',
            'password': 'testpass123'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        
        # Verify token can be used
        token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        response = self.client.get('/api/user/profile/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_api_token_obtain_invalid_credentials(self):
        """Test obtaining token with invalid credentials."""
        response = self.client.post('/api/token/', {
            'email': 'test@example.com',
            'password': 'wrongpassword'
        })
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('detail', response.data)
    
    def test_api_token_refresh(self):
        """Test refreshing JWT token."""
        # First get a token
        response = self.client.post('/api/token/', {
            'email': 'test@example.com',
            'password': 'testpass123'
        })
        refresh_token = response.data['refresh']
        
        # Refresh the token
        response = self.client.post('/api/token/refresh/', {
            'refresh': refresh_token
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
    
    def test_api_register_user(self):
        """Test user registration API."""
        response = self.client.post('/api/register/', {
            'email': 'newuser@example.com',
            'password': 'ComplexPass123!',
            'password2': 'ComplexPass123!',
            'first_name': 'Jane',
            'last_name': 'Smith',
            'phone': '9876543210',
            'user_type': 'patient'
        })
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['email'], 'newuser@example.com')
        self.assertEqual(response.data['first_name'], 'Jane')
        self.assertEqual(response.data['last_name'], 'Smith')
        self.assertIn('token', response.data)
        
        # Verify user was created
        user = User.objects.get(email='newuser@example.com')
        self.assertEqual(user.profile.phone, '9876543210')
    
    def test_api_register_user_invalid_data(self):
        """Test user registration with invalid data."""
        response = self.client.post('/api/register/', {
            'email': 'invalid-email',
            'password': 'simple',
            'password2': 'different'
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
        self.assertIn('password', response.data)


class UserProfileAPITests(TestCase):
    """Test user profile API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='John',
            last_name='Doe'
        )
        self.user.profile.phone = '1234567890'
        self.user.profile.date_of_birth = datetime(1990, 1, 1).date()
        self.user.profile.save()
        
        # Authenticate
        response = self.client.post('/api/token/', {
            'email': 'test@example.com',
            'password': 'testpass123'
        })
        token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    
    def test_get_user_profile(self):
        """Test retrieving user profile."""
        response = self.client.get('/api/user/profile/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'test@example.com')
        self.assertEqual(response.data['first_name'], 'John')
        self.assertEqual(response.data['last_name'], 'Doe')
        self.assertEqual(response.data['profile']['phone'], '1234567890')
        self.assertEqual(response.data['profile']['date_of_birth'], '1990-01-01')
    
    def test_update_user_profile(self):
        """Test updating user profile."""
        response = self.client.patch('/api/user/profile/', {
            'first_name': 'Jonathan',
            'profile': {
                'phone': '0987654321',
                'gender': 'male',
                'address': '123 Main St'
            }
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], 'Jonathan')
        self.assertEqual(response.data['profile']['phone'], '0987654321')
        self.assertEqual(response.data['profile']['gender'], 'male')
        
        # Verify updates
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Jonathan')
        self.assertEqual(self.user.profile.phone, '0987654321')
        self.assertEqual(self.user.profile.gender, 'male')
    
    def test_change_password(self):
        """Test changing password."""
        response = self.client.post('/api/user/change-password/', {
            'old_password': 'testpass123',
            'new_password': 'NewComplexPass123!',
            'new_password2': 'NewComplexPass123!'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Password changed successfully')
        
        # Verify password was changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewComplexPass123!'))
    
    def test_change_password_wrong_old_password(self):
        """Test changing password with wrong old password."""
        response = self.client.post('/api/user/change-password/', {
            'old_password': 'wrongpassword',
            'new_password': 'NewComplexPass123!',
            'new_password2': 'NewComplexPass123!'
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('old_password', response.data)


class DiseaseTypeAPITests(TestCase):
    """Test disease type API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        # Authenticate
        response = self.client.post('/api/token/', {
            'email': 'test@example.com',
            'password': 'testpass123'
        })
        token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Create disease types
        self.diabetes = DiseaseType.objects.create(
            name='Diabetes',
            code='diabetes',
            description='Diabetes prediction model',
            is_active=True
        )
        
        self.heart = DiseaseType.objects.create(
            name='Heart Disease',
            code='heart',
            description='Heart disease prediction model',
            is_active=True
        )
        
        self.inactive = DiseaseType.objects.create(
            name='Inactive Disease',
            code='inactive',
            description='Inactive disease',
            is_active=False
        )
    
    def test_list_disease_types(self):
        """Test listing disease types."""
        response = self.client.get('/api/diseases/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Only active diseases
        
        # Check data
        disease_names = [d['name'] for d in response.data]
        self.assertIn('Diabetes', disease_names)
        self.assertIn('Heart Disease', disease_names)
        self.assertNotIn('Inactive Disease', disease_names)
    
    def test_retrieve_disease_type(self):
        """Test retrieving a specific disease type."""
        response = self.client.get(f'/api/diseases/{self.diabetes.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Diabetes')
        self.assertEqual(response.data['code'], 'diabetes')
        self.assertEqual(response.data['description'], 'Diabetes prediction model')
        self.assertTrue(response.data['is_active'])
    
    def test_retrieve_nonexistent_disease_type(self):
        """Test retrieving a non-existent disease type."""
        response = self.client.get('/api/diseases/999/')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_filter_disease_types_by_name(self):
        """Test filtering disease types by name."""
        response = self.client.get('/api/diseases/?search=diabetes')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Diabetes')
    
    def test_disease_type_input_fields(self):
        """Test disease type input fields."""
        # Update diabetes with input fields
        self.diabetes.input_fields = json.dumps([
            {'name': 'glucose', 'label': 'Glucose', 'type': 'number'},
            {'name': 'bmi', 'label': 'BMI', 'type': 'number'}
        ])
        self.diabetes.save()
        
        response = self.client.get(f'/api/diseases/{self.diabetes.id}/input-fields/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['name'], 'glucose')
        self.assertEqual(response.data[1]['name'], 'bmi')


class PredictionAPITests(TestCase):
    """Test prediction API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='patient@example.com',
            password='testpass123',
            user_type='patient'
        )
        
        # Authenticate
        response = self.client.post('/api/token/', {
            'email': 'patient@example.com',
            'password': 'testpass123'
        })
        token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Create disease type
        self.diabetes = DiseaseType.objects.create(
            name='Diabetes',
            code='diabetes',
            is_active=True
        )
        
        # Create ML model
        self.ml_model = MLModel.objects.create(
            disease_type=self.diabetes,
            name='Random Forest',
            version='1.0.0',
            accuracy=0.85,
            is_active=True
        )
        
        # Create existing predictions
        self.prediction1 = Prediction.objects.create(
            user=self.user,
            disease_type=self.diabetes,
            ml_model=self.ml_model,
            input_data={'glucose': 120, 'bmi': 25.5},
            prediction_result={'has_disease': True, 'probability': 0.78},
            confidence_score=0.78,
            is_positive=True,
            created_at=timezone.now() - timedelta(days=1)
        )
        
        self.prediction2 = Prediction.objects.create(
            user=self.user,
            disease_type=self.diabetes,
            ml_model=self.ml_model,
            input_data={'glucose': 90, 'bmi': 22.0},
            prediction_result={'has_disease': False, 'probability': 0.15},
            confidence_score=0.85,
            is_positive=False,
            created_at=timezone.now()
        )
    
    def test_create_prediction(self):
        """Test creating a prediction."""
        with patch('prediction_app.ml_utils.load_model') as mock_load_model:
            mock_model = MagicMock()
            mock_model.predict.return_value = [1]
            mock_model.predict_proba.return_value = [[0.2, 0.8]]
            mock_load_model.return_value = mock_model
            
            response = self.client.post('/api/predictions/', {
                'disease_type': self.diabetes.id,
                'input_data': {
                    'glucose': 130,
                    'bmi': 28.5,
                    'age': 45,
                    'blood_pressure': 85,
                    'skin_thickness': 30,
                    'insulin': 150,
                    'diabetes_pedigree': 0.6,
                    'pregnancies': 2
                }
            }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check response data
        self.assertEqual(response.data['disease_type']['id'], self.diabetes.id)
        self.assertEqual(response.data['disease_type']['name'], 'Diabetes')
        self.assertEqual(response.data['input_data']['glucose'], 130)
        self.assertEqual(response.data['input_data']['bmi'], 28.5)
        self.assertIn('prediction_result', response.data)
        self.assertIn('confidence_score', response.data)
        self.assertIn('risk_level', response.data)
        
        # Check prediction was created
        prediction = Prediction.objects.filter(
            user=self.user,
            disease_type=self.diabetes
        ).latest('created_at')
        
        self.assertIsNotNone(prediction)
        self.assertEqual(prediction.input_data['glucose'], 130)
        self.assertEqual(prediction.input_data['bmi'], 28.5)
    
    def test_create_prediction_invalid_disease(self):
        """Test creating a prediction for invalid disease."""
        response = self.client.post('/api/predictions/', {
            'disease_type': 999,  # Non-existent disease
            'input_data': {'glucose': 130}
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('disease_type', response.data)
    
    def test_create_prediction_missing_data(self):
        """Test creating a prediction with missing required data."""
        response = self.client.post('/api/predictions/', {
            'disease_type': self.diabetes.id,
            'input_data': {}  # Empty data
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_list_predictions(self):
        """Test listing user predictions."""
        response = self.client.get('/api/predictions/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Both predictions
        
        # Check data
        prediction_ids = [p['id'] for p in response.data]
        self.assertIn(self.prediction1.id, prediction_ids)
        self.assertIn(self.prediction2.id, prediction_ids)
    
    def test_filter_predictions_by_disease(self):
        """Test filtering predictions by disease."""
        # Create another disease and prediction
        heart = DiseaseType.objects.create(
            name='Heart Disease',
            code='heart',
            is_active=True
        )
        
        heart_prediction = Prediction.objects.create(
            user=self.user,
            disease_type=heart,
            input_data={'bp': 140},
            prediction_result={'has_disease': True},
            confidence_score=0.75
        )
        
        response = self.client.get(f'/api/predictions/?disease={self.diabetes.id}')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Only diabetes predictions
        
        for prediction in response.data:
            self.assertEqual(prediction['disease_type']['id'], self.diabetes.id)
    
    def test_filter_predictions_by_date(self):
        """Test filtering predictions by date range."""
        # Create old prediction
        old_prediction = Prediction.objects.create(
            user=self.user,
            disease_type=self.diabetes,
            input_data={'glucose': 100},
            prediction_result={'has_disease': False},
            confidence_score=0.70,
            created_at=timezone.now() - timedelta(days=60)
        )
        
        response = self.client.get('/api/predictions/?start_date=2024-01-01&end_date=2024-01-31')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should not include old prediction
        prediction_ids = [p['id'] for p in response.data]
        self.assertNotIn(old_prediction.id, prediction_ids)
    
    def test_retrieve_prediction(self):
        """Test retrieving a specific prediction."""
        response = self.client.get(f'/api/predictions/{self.prediction1.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.prediction1.id)
        self.assertEqual(response.data['disease_type']['name'], 'Diabetes')
        self.assertEqual(response.data['input_data']['glucose'], 120)
        self.assertEqual(response.data['confidence_score'], '0.78')
        self.assertEqual(response.data['risk_level'], 'High')
    
    def test_retrieve_prediction_not_owner(self):
        """Test retrieving prediction that doesn't belong to user."""
        other_user = User.objects.create_user(
            email='other@example.com',
            password='otherpass123'
        )
        
        other_prediction = Prediction.objects.create(
            user=other_user,
            disease_type=self.diabetes,
            input_data={'glucose': 110},
            prediction_result={'has_disease': False},
            confidence_score=0.65
        )
        
        response = self.client.get(f'/api/predictions/{other_prediction.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_update_prediction(self):
        """Test updating a prediction (e.g., adding notes)."""
        response = self.client.patch(f'/api/predictions/{self.prediction1.id}/', {
            'user_notes': 'Need to follow up with doctor',
            'is_important': True
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check updates
        self.prediction1.refresh_from_db()
        self.assertEqual(self.prediction1.user_notes, 'Need to follow up with doctor')
        self.assertTrue(self.prediction1.is_important)
    
    def test_delete_prediction(self):
        """Test deleting a prediction."""
        response = self.client.delete(f'/api/predictions/{self.prediction1.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Check prediction was deleted
        with self.assertRaises(Prediction.DoesNotExist):
            Prediction.objects.get(id=self.prediction1.id)
    
    def test_prediction_statistics(self):
        """Test prediction statistics endpoint."""
        response = self.client.get('/api/predictions/statistics/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check statistics data
        self.assertIn('total_predictions', response.data)
        self.assertIn('positive_count', response.data)
        self.assertIn('negative_count', response.data)
        self.assertIn('average_confidence', response.data)
        self.assertIn('disease_breakdown', response.data)
        
        self.assertEqual(response.data['total_predictions'], 2)
        self.assertEqual(response.data['positive_count'], 1)
        self.assertEqual(response.data['negative_count'], 1)
        self.assertAlmostEqual(float(response.data['average_confidence']), 0.815, places=3)
    
    def test_batch_prediction(self):
        """Test batch prediction endpoint."""
        with patch('prediction_app.ml_utils.load_model') as mock_load_model:
            mock_model = MagicMock()
            mock_model.predict.return_value = [1, 0, 1]
            mock_model.predict_proba.return_value = [[0.3, 0.7], [0.8, 0.2], [0.4, 0.6]]
            mock_load_model.return_value = mock_model
            
            response = self.client.post('/api/predictions/batch/', {
                'disease_type': self.diabetes.id,
                'input_data_list': [
                    {'glucose': 130, 'bmi': 28.5},
                    {'glucose': 90, 'bmi': 22.0},
                    {'glucose': 115, 'bmi': 26.0}
                ]
            }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data), 3)  # Three predictions
        
        # Check predictions were created
        new_predictions = Prediction.objects.filter(
            user=self.user,
            disease_type=self.diabetes
        ).order_by('-created_at')[:3]
        
        self.assertEqual(new_predictions.count(), 3)


class ReportAPITests(TestCase):
    """Test report API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='patient@example.com',
            password='testpass123',
            user_type='patient'
        )
        
        # Authenticate
        response = self.client.post('/api/token/', {
            'email': 'patient@example.com',
            'password': 'testpass123'
        })
        token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Create disease and prediction
        self.diabetes = DiseaseType.objects.create(
            name='Diabetes',
            code='diabetes'
        )
        
        self.prediction = Prediction.objects.create(
            user=self.user,
            disease_type=self.diabetes,
            input_data={'glucose': 120},
            prediction_result={'has_disease': True},
            confidence_score=0.85
        )
        
        # Create reports
        self.report1 = Report.objects.create(
            user=self.user,
            title='Diabetes Screening Report',
            report_type='screening',
            content={
                'summary': 'High risk detected',
                'recommendations': ['Consult doctor', 'Monitor sugar']
            }
        )
        self.report1.predictions.add(self.prediction)
        
        self.report2 = Report.objects.create(
            user=self.user,
            title='Follow-up Report',
            report_type='followup',
            content={'summary': 'Follow-up needed'}
        )
    
    def test_list_reports(self):
        """Test listing user reports."""
        response = self.client.get('/api/reports/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        
        # Check data
        report_titles = [r['title'] for r in response.data]
        self.assertIn('Diabetes Screening Report', report_titles)
        self.assertIn('Follow-up Report', report_titles)
    
    def test_create_report(self):
        """Test creating a report."""
        response = self.client.post('/api/reports/', {
            'title': 'Comprehensive Health Report',
            'report_type': 'comprehensive',
            'content': {
                'summary': 'Overall health assessment',
                'recommendations': ['Regular exercise', 'Balanced diet'],
                'next_steps': ['Annual checkup', 'Blood tests']
            },
            'predictions': [self.prediction.id]
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'Comprehensive Health Report')
        self.assertEqual(response.data['report_type'], 'comprehensive')
        self.assertEqual(response.data['content']['summary'], 'Overall health assessment')
        self.assertEqual(len(response.data['predictions']), 1)
        
        # Check report was created
        report = Report.objects.filter(
            user=self.user,
            title='Comprehensive Health Report'
        ).first()
        
        self.assertIsNotNone(report)
        self.assertEqual(report.predictions.count(), 1)
        self.assertEqual(report.predictions.first(), self.prediction)
    
    def test_retrieve_report(self):
        """Test retrieving a specific report."""
        response = self.client.get(f'/api/reports/{self.report1.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Diabetes Screening Report')
        self.assertEqual(response.data['report_type'], 'screening')
        self.assertEqual(response.data['content']['summary'], 'High risk detected')
        self.assertEqual(len(response.data['predictions']), 1)
    
    def test_update_report(self):
        """Test updating a report."""
        response = self.client.patch(f'/api/reports/{self.report1.id}/', {
            'title': 'Updated Diabetes Report',
            'is_shared': True
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Updated Diabetes Report')
        self.assertTrue(response.data['is_shared'])
        
        # Check updates
        self.report1.refresh_from_db()
        self.assertEqual(self.report1.title, 'Updated Diabetes Report')
        self.assertTrue(self.report1.is_shared)
    
    def test_delete_report(self):
        """Test deleting a report."""
        response = self.client.delete(f'/api/reports/{self.report1.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Check report was deleted
        with self.assertRaises(Report.DoesNotExist):
            Report.objects.get(id=self.report1.id)
    
    def test_generate_pdf_report(self):
        """Test generating PDF for a report."""
        with patch('prediction_app.views.generate_pdf') as mock_generate_pdf:
            mock_generate_pdf.return_value = b'PDF content'
            
            response = self.client.get(f'/api/reports/{self.report1.id}/download/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response['Content-Disposition'].startswith('attachment'))
        self.assertEqual(response.content, b'PDF content')
    
    def test_share_report(self):
        """Test sharing a report with doctor."""
        doctor = User.objects.create_user(
            email='doctor@example.com',
            password='doctor123',
            user_type='doctor'
        )
        
        response = self.client.post(f'/api/reports/{self.report1.id}/share/', {
            'doctor_id': doctor.id,
            'notes': 'Please review this report'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check report was shared
        self.report1.refresh_from_db()
        self.assertTrue(self.report1.is_shared)
        self.assertEqual(self.report1.shared_with, doctor)
        self.assertEqual(self.report1.sharing_notes, 'Please review this report')


class ConsultationAPITests(TestCase):
    """Test consultation API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
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
        
        # Authenticate as patient
        response = self.client.post('/api/token/', {
            'email': 'patient@example.com',
            'password': 'patient123'
        })
        token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Create disease and prediction
        self.diabetes = DiseaseType.objects.create(
            name='Diabetes',
            code='diabetes'
        )
        
        self.prediction = Prediction.objects.create(
            user=self.patient,
            disease_type=self.diabetes,
            input_data={'glucose': 120},
            prediction_result={'has_disease': True},
            confidence_score=0.85
        )
        
        # Create consultation
        self.consultation = Consultation.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            prediction=self.prediction,
            consultation_type='initial',
            status='scheduled',
            scheduled_for=timezone.now() + timedelta(days=1),
            duration_minutes=30
        )
    
    def test_list_consultations_patient(self):
        """Test listing consultations for patient."""
        response = self.client.get('/api/consultations/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.consultation.id)
        self.assertEqual(response.data[0]['consultation_type'], 'initial')
        self.assertEqual(response.data[0]['status'], 'scheduled')
    
    def test_list_consultations_doctor(self):
        """Test listing consultations for doctor."""
        # Re-authenticate as doctor
        response = self.client.post('/api/token/', {
            'email': 'doctor@example.com',
            'password': 'doctor123'
        })
        token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        response = self.client.get('/api/consultations/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
    
    def test_create_consultation(self):
        """Test creating a consultation."""
        response = self.client.post('/api/consultations/', {
            'doctor': self.doctor.id,
            'prediction': self.prediction.id,
            'consultation_type': 'followup',
            'symptoms': 'Increased thirst, fatigue',
            'scheduled_for': (timezone.now() + timedelta(days=2)).isoformat(),
            'duration_minutes': 45,
            'notes': 'Need to discuss prediction results'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['consultation_type'], 'followup')
        self.assertEqual(response.data['symptoms'], 'Increased thirst, fatigue')
        self.assertEqual(response.data['duration_minutes'], 45)
        self.assertEqual(response.data['status'], 'pending')
        
        # Check consultation was created
        consultation = Consultation.objects.filter(
            patient=self.patient,
            doctor=self.doctor,
            consultation_type='followup'
        ).first()
        
        self.assertIsNotNone(consultation)
    
    def test_retrieve_consultation(self):
        """Test retrieving a specific consultation."""
        response = self.client.get(f'/api/consultations/{self.consultation.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.consultation.id)
        self.assertEqual(response.data['consultation_type'], 'initial')
        self.assertEqual(response.data['patient']['email'], 'patient@example.com')
        self.assertEqual(response.data['doctor']['email'], 'doctor@example.com')
    
    def test_update_consultation_status(self):
        """Test updating consultation status."""
        # Re-authenticate as doctor (only doctors can update status)
        response = self.client.post('/api/token/', {
            'email': 'doctor@example.com',
            'password': 'doctor123'
        })
        token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        response = self.client.patch(f'/api/consultations/{self.consultation.id}/', {
            'status': 'completed',
            'outcome': 'Patient advised to monitor blood sugar',
            'notes': 'Consultation went well'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'completed')
        self.assertEqual(response.data['outcome'], 'Patient advised to monitor blood sugar')
        
        # Check updates
        self.consultation.refresh_from_db()
        self.assertEqual(self.consultation.status, 'completed')
        self.assertEqual(self.consultation.outcome, 'Patient advised to monitor blood sugar')
        self.assertIsNotNone(self.consultation.completed_at)
    
    def test_cancel_consultation(self):
        """Test cancelling a consultation."""
        response = self.client.post(f'/api/consultations/{self.consultation.id}/cancel/', {
            'cancellation_reason': 'Unexpected conflict'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'cancelled')
        
        # Check consultation was cancelled
        self.consultation.refresh_from_db()
        self.assertEqual(self.consultation.status, 'cancelled')
        self.assertEqual(self.consultation.cancellation_reason, 'Unexpected conflict')
        self.assertIsNotNone(self.consultation.cancelled_at)
    
    def test_doctor_availability(self):
        """Test getting doctor availability."""
        response = self.client.get(f'/api/doctors/{self.doctor.id}/availability/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('doctor', response.data)
        self.assertIn('available_slots', response.data)
        self.assertEqual(response.data['doctor']['email'], 'doctor@example.com')


class FeedbackAPITests(TestCase):
    """Test feedback API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='user@example.com',
            password='testpass123'
        )
        
        # Authenticate
        response = self.client.post('/api/token/', {
            'email': 'user@example.com',
            'password': 'testpass123'
        })
        token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Create feedback
        self.feedback1 = UserFeedback.objects.create(
            user=self.user,
            rating=5,
            comment='Great prediction system!',
            feedback_type='prediction'
        )
        
        self.feedback2 = UserFeedback.objects.create(
            user=self.user,
            rating=4,
            comment='Good interface',
            feedback_type='ui'
        )
    
    def test_create_feedback(self):
        """Test creating feedback."""
        response = self.client.post('/api/feedback/', {
            'rating': 5,
            'comment': 'Excellent service! Very accurate predictions.',
            'feedback_type': 'prediction',
            'prediction_accuracy': 'accurate',
            'suggestions': 'Add more visualization options'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['rating'], 5)
        self.assertEqual(response.data['comment'], 'Excellent service! Very accurate predictions.')
        self.assertEqual(response.data['feedback_type'], 'prediction')
        
        # Check feedback was created
        feedback = UserFeedback.objects.filter(
            user=self.user,
            comment='Excellent service! Very accurate predictions.'
        ).first()
        
        self.assertIsNotNone(feedback)
    
    def test_list_user_feedback(self):
        """Test listing user's feedback."""
        response = self.client.get('/api/feedback/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        
        # Check data
        feedback_comments = [f['comment'] for f in response.data]
        self.assertIn('Great prediction system!', feedback_comments)
        self.assertIn('Good interface', feedback_comments)
    
    def test_feedback_statistics_admin(self):
        """Test feedback statistics (admin only)."""
        # Create admin user
        admin = User.objects.create_superuser(
            email='admin@example.com',
            password='admin123'
        )
        
        # Re-authenticate as admin
        response = self.client.post('/api/token/', {
            'email': 'admin@example.com',
            'password': 'admin123'
        })
        token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        response = self.client.get('/api/feedback/statistics/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check statistics
        self.assertIn('average_rating', response.data)
        self.assertIn('total_feedback', response.data)
        self.assertIn('rating_distribution', response.data)
        self.assertIn('feedback_types', response.data)
        
        self.assertEqual(response.data['total_feedback'], 2)
        self.assertEqual(response.data['average_rating'], 4.5)  # (5+4)/2
    
    def test_feedback_statistics_non_admin(self):
        """Test feedback statistics for non-admin user."""
        response = self.client.get('/api/feedback/statistics/')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class HealthCheckAPITests(TestCase):
    """Test health check API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
    
    def test_health_check(self):
        """Test basic health check endpoint."""
        response = self.client.get('/api/health/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'status': 'healthy'})
    
    def test_detailed_health_check(self):
        """Test detailed health check endpoint."""
        with patch('api_app.views.HealthChecker') as MockHealthChecker:
            mock_checker = MagicMock()
            mock_checker.run_health_check.return_value = {
                'summary': {'overall_status': 'healthy'},
                'checks': [
                    {'name': 'Database', 'status': 'OK', 'message': 'Connected'},
                    {'name': 'Redis', 'status': 'OK', 'message': 'Connected'},
                    {'name': 'Celery', 'status': 'OK', 'message': 'Running'}
                ]
            }
            MockHealthChecker.return_value = mock_checker
            
            response = self.client.get('/api/health/detailed/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['summary']['overall_status'], 'healthy')
        self.assertEqual(len(response.data['checks']), 3)
    
    def test_database_health_check(self):
        """Test database health check."""
        response = self.client.get('/api/health/database/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('status', response.data)
        self.assertIn('message', response.data)
        self.assertEqual(response.data['status'], 'healthy')
    
    def test_cache_health_check(self):
        """Test cache (Redis) health check."""
        with patch('api_app.views.cache') as mock_cache:
            mock_cache.get.return_value = 'test'
            
            response = self.client.get('/api/health/cache/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'healthy')


class MLModelAPITests(TestCase):
    """Test ML model API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            email='admin@example.com',
            password='admin123'
        )
        
        # Authenticate as admin
        response = self.client.post('/api/token/', {
            'email': 'admin@example.com',
            'password': 'admin123'
        })
        token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Create disease type
        self.diabetes = DiseaseType.objects.create(
            name='Diabetes',
            code='diabetes'
        )
        
        # Create ML models
        self.model1 = MLModel.objects.create(
            disease_type=self.diabetes,
            name='Random Forest',
            version='1.0.0',
            accuracy=0.85,
            is_active=True
        )
        
        self.model2 = MLModel.objects.create(
            disease_type=self.diabetes,
            name='SVM',
            version='1.0.0',
            accuracy=0.82,
            is_active=False
        )
    
    def test_list_mlmodels_admin(self):
        """Test listing ML models (admin only)."""
        response = self.client.get('/api/mlmodels/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        
        # Check data
        model_names = [m['name'] for m in response.data]
        self.assertIn('Random Forest', model_names)
        self.assertIn('SVM', model_names)
    
    def test_list_mlmodels_non_admin(self):
        """Test listing ML models for non-admin user."""
        regular_user = User.objects.create_user(
            email='user@example.com',
            password='user123'
        )
        
        # Re-authenticate as regular user
        response = self.client.post('/api/token/', {
            'email': 'user@example.com',
            'password': 'user123'
        })
        token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        response = self.client.get('/api/mlmodels/')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_retrieve_mlmodel(self):
        """Test retrieving a specific ML model."""
        response = self.client.get(f'/api/mlmodels/{self.model1.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Random Forest')
        self.assertEqual(response.data['version'], '1.0.0')
        self.assertEqual(response.data['accuracy'], '0.85')
        self.assertTrue(response.data['is_active'])
    
    def test_create_mlmodel(self):
        """Test creating an ML model."""
        # Mock file upload
        from io import BytesIO
        model_file = BytesIO(b'fake model content')
        model_file.name = 'diabetes_model.pkl'
        
        response = self.client.post('/api/mlmodels/', {
            'disease_type': self.diabetes.id,
            'name': 'XGBoost Classifier',
            'version': '1.0.0',
            'description': 'XGBoost model for diabetes prediction',
            'algorithm': 'xgboost',
            'accuracy': 0.88,
            'precision': 0.86,
            'recall': 0.89,
            'f1_score': 0.875,
            'roc_auc': 0.91,
            'dataset_size': 1000,
            'features': 'glucose,bmi,age',
            'model_file': model_file,
            'is_active': True
        }, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'XGBoost Classifier')
        self.assertEqual(response.data['version'], '1.0.0')
        self.assertEqual(response.data['accuracy'], '0.88')
        
        # Check model was created
        model = MLModel.objects.filter(
            disease_type=self.diabetes,
            name='XGBoost Classifier'
        ).first()
        
        self.assertIsNotNone(model)
    
    def test_update_mlmodel(self):
        """Test updating an ML model."""
        response = self.client.patch(f'/api/mlmodels/{self.model1.id}/', {
            'name': 'Random Forest Updated',
            'version': '1.1.0',
            'accuracy': 0.87
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Random Forest Updated')
        self.assertEqual(response.data['version'], '1.1.0')
        self.assertEqual(response.data['accuracy'], '0.87')
        
        # Check updates
        self.model1.refresh_from_db()
        self.assertEqual(self.model1.name, 'Random Forest Updated')
        self.assertEqual(self.model1.version, '1.1.0')
        self.assertEqual(self.model1.accuracy, 0.87)
    
    def test_toggle_mlmodel_active(self):
        """Test toggling ML model active status."""
        self.assertTrue(self.model1.is_active)
        
        response = self.client.post(f'/api/mlmodels/{self.model1.id}/toggle-active/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_active'])
        
        # Check status was toggled
        self.model1.refresh_from_db()
        self.assertFalse(self.model1.is_active)
    
    def test_mlmodel_performance(self):
        """Test ML model performance endpoint."""
        # Create predictions for the model
        user = User.objects.create_user(
            email='patient@example.com',
            password='patient123'
        )
        
        for i in range(5):
            Prediction.objects.create(
                user=user,
                disease_type=self.diabetes,
                ml_model=self.model1,
                input_data={'glucose': 100 + i},
                prediction_result={'has_disease': i % 2 == 0},
                confidence_score=0.7 + i * 0.05
            )
        
        response = self.client.get(f'/api/mlmodels/{self.model1.id}/performance/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('model', response.data)
        self.assertIn('predictions_count', response.data)
        self.assertIn('accuracy_distribution', response.data)
        
        self.assertEqual(response.data['predictions_count'], 5)
    
    def test_best_model_for_disease(self):
        """Test getting best model for a disease."""
        # Create a better model
        better_model = MLModel.objects.create(
            disease_type=self.diabetes,
            name='Neural Network',
            version='1.0.0',
            accuracy=0.92,
            is_active=True
        )
        
        response = self.client.get(f'/api/diseases/{self.diabetes.id}/best-model/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Neural Network')
        self.assertEqual(response.data['accuracy'], '0.92')


class AnalyticsAPITests(TestCase):
    """Test analytics API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            email='admin@example.com',
            password='admin123'
        )
        
        # Authenticate as admin
        response = self.client.post('/api/token/', {
            'email': 'admin@example.com',
            'password': 'admin123'
        })
        token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Create users
        self.patient1 = User.objects.create_user(
            email='patient1@example.com',
            password='patient123',
            user_type='patient'
        )
        
        self.patient2 = User.objects.create_user(
            email='patient2@example.com',
            password='patient123',
            user_type='patient'
        )
        
        # Create disease types
        self.diabetes = DiseaseType.objects.create(
            name='Diabetes',
            code='diabetes'
        )
        
        self.heart = DiseaseType.objects.create(
            name='Heart Disease',
            code='heart'
        )
        
        # Create predictions
        for i in range(3):
            Prediction.objects.create(
                user=self.patient1,
                disease_type=self.diabetes,
                input_data={'glucose': 100 + i},
                prediction_result={'has_disease': i % 2 == 0},
                confidence_score=0.7 + i * 0.05,
                created_at=timezone.now() - timedelta(days=i)
            )
        
        for i in range(2):
            Prediction.objects.create(
                user=self.patient2,
                disease_type=self.heart,
                input_data={'bp': 130 + i},
                prediction_result={'has_disease': True},
                confidence_score=0.8 + i * 0.05,
                created_at=timezone.now() - timedelta(days=i)
            )
    
    def test_system_analytics(self):
        """Test system analytics endpoint."""
        response = self.client.get('/api/analytics/system/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check analytics data
        self.assertIn('user_count', response.data)
        self.assertIn('prediction_count', response.data)
        self.assertIn('consultation_count', response.data)
        self.assertIn('feedback_count', response.data)
        self.assertIn('user_growth', response.data)
        self.assertIn('prediction_trends', response.data)
        
        self.assertEqual(response.data['user_count'], 3)  # admin + 2 patients
        self.assertEqual(response.data['prediction_count'], 5)
    
    def test_disease_analytics(self):
        """Test disease analytics endpoint."""
        response = self.client.get('/api/analytics/diseases/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should have analytics for both diseases
        self.assertEqual(len(response.data), 2)
        
        # Check diabetes analytics
        diabetes_analytics = [d for d in response.data if d['disease']['id'] == self.diabetes.id][0]
        self.assertEqual(diabetes_analytics['prediction_count'], 3)
        self.assertEqual(diabetes_analytics['positive_count'], 2)  # Even indices are positive
        self.assertEqual(diabetes_analytics['negative_count'], 1)
    
    def test_user_analytics(self):
        """Test user analytics endpoint."""
        response = self.client.get('/api/analytics/users/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should have analytics for patient users
        self.assertEqual(len(response.data), 2)
        
        # Check patient1 analytics
        patient1_analytics = [u for u in response.data if u['user']['email'] == 'patient1@example.com'][0]
        self.assertEqual(patient1_analytics['prediction_count'], 3)
        self.assertEqual(patient1_analytics['consultation_count'], 0)
    
    def test_prediction_analytics(self):
        """Test prediction analytics endpoint."""
        response = self.client.get('/api/analytics/predictions/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check prediction analytics
        self.assertIn('total_predictions', response.data)
        self.assertIn('positive_rate', response.data)
        self.assertIn('average_confidence', response.data)
        self.assertIn('daily_predictions', response.data)
        self.assertIn('hourly_distribution', response.data)
        
        self.assertEqual(response.data['total_predictions'], 5)
        # 3 out of 5 predictions are positive = 60%
        self.assertAlmostEqual(response.data['positive_rate'], 0.6, places=1)
    
    def test_trend_analytics(self):
        """Test trend analytics endpoint."""
        response = self.client.get('/api/analytics/trends/?period=7')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check trend data
        self.assertIn('predictions_trend', response.data)
        self.assertIn('users_trend', response.data)
        self.assertIn('consultations_trend', response.data)
    
    def test_export_analytics(self):
        """Test analytics export endpoint."""
        response = self.client.get('/api/analytics/export/?format=csv')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertTrue(response['Content-Disposition'].startswith('attachment'))
        
        # Check CSV content
        content = response.content.decode('utf-8')
        self.assertIn('Diabetes', content)
        self.assertIn('Heart Disease', content)