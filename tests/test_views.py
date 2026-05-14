"""
Test cases for Django views in MEDIPREDICT
"""

import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from decimal import Decimal

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from prediction_app.models import (
    Prediction, DiseaseType, MLModel, Report, UserFeedback
)
from users_app.models import UserProfile
from consultations_app.models import Consultation
from prescriptions_app.models import Prescription

User = get_user_model()


class AuthenticationViewTests(TestCase):
    """Test authentication-related views."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='John',
            last_name='Doe'
        )
        self.user.profile.phone = '1234567890'
        self.user.profile.save()
    
    def test_home_page_view(self):
        """Test home page view."""
        response = self.client.get(reverse('home'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'prediction_app/home.html')
        self.assertContains(response, 'MEDIPREDICT')
        self.assertContains(response, 'Disease Prediction')
    
    def test_user_login_view_get(self):
        """Test login page GET request."""
        response = self.client.get(reverse('login'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users_app/login.html')
        self.assertContains(response, 'Login')
        self.assertContains(response, 'Email')
        self.assertContains(response, 'Password')
    
    def test_user_login_view_post_success(self):
        """Test successful login."""
        response = self.client.post(reverse('login'), {
            'email': 'test@example.com',
            'password': 'testpass123'
        })
        
        self.assertEqual(response.status_code, 302)  # Redirect
        self.assertRedirects(response, reverse('dashboard'))
        
        # Check user is logged in
        self.assertTrue('_auth_user_id' in self.client.session)
    
    def test_user_login_view_post_invalid_credentials(self):
        """Test login with invalid credentials."""
        response = self.client.post(reverse('login'), {
            'email': 'test@example.com',
            'password': 'wrongpassword'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users_app/login.html')
        self.assertContains(response, 'Invalid email or password')
        self.assertFalse('_auth_user_id' in self.client.session)
    
    def test_user_logout_view(self):
        """Test logout view."""
        # First login
        self.client.login(email='test@example.com', password='testpass123')
        
        # Then logout
        response = self.client.get(reverse('logout'))
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('home'))
        self.assertFalse('_auth_user_id' in self.client.session)
    
    def test_user_register_view_get(self):
        """Test registration page GET request."""
        response = self.client.get(reverse('register'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users_app/register.html')
        self.assertContains(response, 'Register')
        self.assertContains(response, 'Create Account')
    
    def test_user_register_view_post_success(self):
        """Test successful user registration."""
        response = self.client.post(reverse('register'), {
            'email': 'newuser@example.com',
            'password1': 'ComplexPass123!',
            'password2': 'ComplexPass123!',
            'first_name': 'Jane',
            'last_name': 'Smith',
            'phone': '9876543210',
            'user_type': 'patient'
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dashboard'))
        
        # Check user was created
        user = User.objects.get(email='newuser@example.com')
        self.assertEqual(user.first_name, 'Jane')
        self.assertEqual(user.last_name, 'Smith')
        self.assertEqual(user.profile.phone, '9876543210')
        
        # Check user is logged in
        self.assertTrue('_auth_user_id' in self.client.session)
    
    def test_user_register_view_post_invalid_data(self):
        """Test registration with invalid data."""
        response = self.client.post(reverse('register'), {
            'email': 'invalid-email',
            'password1': 'simple',
            'password2': 'different'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users_app/register.html')
        
        # Check errors
        self.assertContains(response, 'Enter a valid email address')
        self.assertContains(response, 'This password is too short')
        self.assertContains(response, 'The two password fields didn&#x27;t match')
    
    def test_user_profile_view_authenticated(self):
        """Test profile view for authenticated user."""
        self.client.login(email='test@example.com', password='testpass123')
        
        response = self.client.get(reverse('profile'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users_app/profile.html')
        self.assertContains(response, 'John Doe')
        self.assertContains(response, 'test@example.com')
        self.assertContains(response, '1234567890')
    
    def test_user_profile_view_unauthenticated(self):
        """Test profile view for unauthenticated user."""
        response = self.client.get(reverse('profile'))
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('profile')}")
    
    def test_user_profile_update_view(self):
        """Test profile update view."""
        self.client.login(email='test@example.com', password='testpass123')
        
        response = self.client.post(reverse('profile_update'), {
            'first_name': 'Jonathan',
            'last_name': 'Doe',
            'phone': '0987654321',
            'date_of_birth': '1990-01-01',
            'gender': 'male',
            'address': '123 Main St',
            'city': 'New York',
            'country': 'USA'
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('profile'))
        
        # Check updates
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Jonathan')
        self.assertEqual(self.user.profile.phone, '0987654321')
        self.assertEqual(self.user.profile.date_of_birth, datetime(1990, 1, 1).date())
    
    def test_change_password_view(self):
        """Test password change view."""
        self.client.login(email='test@example.com', password='testpass123')
        
        response = self.client.post(reverse('change_password'), {
            'old_password': 'testpass123',
            'new_password1': 'NewComplexPass123!',
            'new_password2': 'NewComplexPass123!'
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('profile'))
        
        # Check password was changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewComplexPass123!'))


class DashboardViewTests(TestCase):
    """Test dashboard views."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            email='patient@example.com',
            password='testpass123',
            user_type='patient'
        )
        
        # Create disease types
        self.diabetes = DiseaseType.objects.create(
            name='Diabetes',
            code='diabetes',
            is_active=True
        )
        
        self.heart = DiseaseType.objects.create(
            name='Heart Disease',
            code='heart',
            is_active=True
        )
        
        # Create predictions for the user
        self.prediction1 = Prediction.objects.create(
            user=self.user,
            disease_type=self.diabetes,
            input_data={'glucose': 120},
            prediction_result={'has_disease': True},
            confidence_score=0.85,
            is_positive=True,
            created_at=timezone.now() - timedelta(days=1)
        )
        
        self.prediction2 = Prediction.objects.create(
            user=self.user,
            disease_type=self.heart,
            input_data={'bp': 140},
            prediction_result={'has_disease': False},
            confidence_score=0.92,
            is_positive=False,
            created_at=timezone.now()
        )
    
    def test_dashboard_view_authenticated_patient(self):
        """Test dashboard view for authenticated patient."""
        self.client.login(email='patient@example.com', password='testpass123')
        
        response = self.client.get(reverse('dashboard'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'prediction_app/dashboard.html')
        
        # Check context data
        self.assertIn('user', response.context)
        self.assertIn('recent_predictions', response.context)
        self.assertIn('disease_stats', response.context)
        
        # Check content
        self.assertContains(response, 'Dashboard')
        self.assertContains(response, 'Welcome back')
        self.assertContains(response, 'Diabetes')
        self.assertContains(response, 'Heart Disease')
        
        # Check prediction counts
        recent_predictions = response.context['recent_predictions']
        self.assertEqual(recent_predictions.count(), 2)
    
    def test_dashboard_view_authenticated_doctor(self):
        """Test dashboard view for authenticated doctor."""
        doctor = User.objects.create_user(
            email='doctor@example.com',
            password='doctor123',
            user_type='doctor'
        )
        
        self.client.login(email='doctor@example.com', password='doctor123')
        
        response = self.client.get(reverse('dashboard'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'prediction_app/dashboard.html')
        
        # Doctor dashboard should have different context
        self.assertContains(response, 'Doctor Dashboard')
        self.assertContains(response, 'Patient Statistics')
    
    def test_dashboard_view_unauthenticated(self):
        """Test dashboard view for unauthenticated user."""
        response = self.client.get(reverse('dashboard'))
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('dashboard')}")
    
    def test_dashboard_statistics(self):
        """Test dashboard statistics calculation."""
        self.client.login(email='patient@example.com', password='testpass123')
        
        response = self.client.get(reverse('dashboard'))
        
        # Check disease statistics
        disease_stats = response.context['disease_stats']
        
        # Should have stats for both diseases
        self.assertEqual(len(disease_stats), 2)
        
        # Check diabetes stats
        diabetes_stats = [stat for stat in disease_stats if stat['disease'] == 'Diabetes'][0]
        self.assertEqual(diabetes_stats['total'], 1)
        self.assertEqual(diabetes_stats['positive'], 1)
        self.assertEqual(diabetes_stats['negative'], 0)
        
        # Check heart disease stats
        heart_stats = [stat for stat in disease_stats if stat['disease'] == 'Heart Disease'][0]
        self.assertEqual(heart_stats['total'], 1)
        self.assertEqual(heart_stats['positive'], 0)
        self.assertEqual(heart_stats['negative'], 1)
    
    def test_dashboard_recent_activity(self):
        """Test recent activity in dashboard."""
        self.client.login(email='patient@example.com', password='testpass123')
        
        # Create a consultation
        doctor = User.objects.create_user(
            email='doctor@example.com',
            password='doctor123',
            user_type='doctor'
        )
        
        consultation = Consultation.objects.create(
            patient=self.user,
            doctor=doctor,
            prediction=self.prediction1,
            status='scheduled',
            scheduled_for=timezone.now() + timedelta(days=1)
        )
        
        response = self.client.get(reverse('dashboard'))
        
        self.assertIn('recent_activity', response.context)
        recent_activity = response.context['recent_activity']
        
        # Should include predictions and consultations
        self.assertGreaterEqual(len(recent_activity), 2)
    
    def test_dashboard_health_score(self):
        """Test health score calculation in dashboard."""
        self.client.login(email='patient@example.com', password='testpass123')
        
        response = self.client.get(reverse('dashboard'))
        
        self.assertIn('health_score', response.context)
        health_score = response.context['health_score']
        
        # Health score should be between 0 and 100
        self.assertIsInstance(health_score, (int, float))
        self.assertGreaterEqual(health_score, 0)
        self.assertLessEqual(health_score, 100)
        
        # With one positive and one negative prediction, score should be moderate
        self.assertGreater(health_score, 50)  # More negative than positive


class PredictionViewTests(TestCase):
    """Test prediction-related views."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            email='patient@example.com',
            password='testpass123',
            user_type='patient'
        )
        
        # Create disease types
        self.diabetes = DiseaseType.objects.create(
            name='Diabetes',
            code='diabetes',
            is_active=True,
            input_fields=json.dumps([
                {'name': 'pregnancies', 'label': 'Pregnancies', 'type': 'number', 'min': 0, 'max': 20},
                {'name': 'glucose', 'label': 'Glucose', 'type': 'number', 'min': 0, 'max': 200},
                {'name': 'blood_pressure', 'label': 'Blood Pressure', 'type': 'number', 'min': 0, 'max': 200},
                {'name': 'skin_thickness', 'label': 'Skin Thickness', 'type': 'number', 'min': 0, 'max': 100},
                {'name': 'insulin', 'label': 'Insulin', 'type': 'number', 'min': 0, 'max': 1000},
                {'name': 'bmi', 'label': 'BMI', 'type': 'number', 'step': '0.1', 'min': 0, 'max': 100},
                {'name': 'diabetes_pedigree', 'label': 'Diabetes Pedigree', 'type': 'number', 'step': '0.001', 'min': 0, 'max': 2.5},
                {'name': 'age', 'label': 'Age', 'type': 'number', 'min': 0, 'max': 120}
            ])
        )
        
        self.heart = DiseaseType.objects.create(
            name='Heart Disease',
            code='heart',
            is_active=True
        )
        
        # Create ML models
        self.ml_model = MLModel.objects.create(
            disease_type=self.diabetes,
            name='Random Forest',
            version='1.0.0',
            accuracy=0.85,
            path='models/diabetes_model.pkl',
            is_active=True
        )
        
        # Create existing prediction
        self.existing_prediction = Prediction.objects.create(
            user=self.user,
            disease_type=self.diabetes,
            ml_model=self.ml_model,
            input_data={'glucose': 120, 'bmi': 25.5},
            prediction_result={'has_disease': True, 'probability': 0.78},
            confidence_score=0.78,
            is_positive=True
        )
    
    def test_prediction_form_view_get(self):
        """Test prediction form page GET request."""
        self.client.login(email='patient@example.com', password='testpass123')
        
        response = self.client.get(reverse('predict_diabetes'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'prediction_app/diabetes.html')
        self.assertContains(response, 'Diabetes Prediction')
        self.assertContains(response, 'Glucose')
        self.assertContains(response, 'BMI')
        self.assertContains(response, 'Predict')
    
    def test_prediction_form_view_post_success(self):
        """Test successful prediction submission."""
        self.client.login(email='patient@example.com', password='testpass123')
        
        # Mock the ML model prediction
        with patch('prediction_app.ml_utils.load_model') as mock_load_model:
            mock_model = MagicMock()
            mock_model.predict.return_value = [1]
            mock_model.predict_proba.return_value = [[0.2, 0.8]]
            mock_load_model.return_value = mock_model
            
            response = self.client.post(reverse('predict_diabetes'), {
                'pregnancies': 2,
                'glucose': 120,
                'blood_pressure': 80,
                'skin_thickness': 25,
                'insulin': 100,
                'bmi': 25.5,
                'diabetes_pedigree': 0.5,
                'age': 35
            })
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'prediction_app/diabetes.html')
        
        # Check prediction was created
        new_prediction = Prediction.objects.filter(
            user=self.user,
            disease_type=self.diabetes
        ).exclude(id=self.existing_prediction.id).first()
        
        self.assertIsNotNone(new_prediction)
        self.assertEqual(new_prediction.input_data['glucose'], 120)
        self.assertEqual(new_prediction.input_data['bmi'], 25.5)
        
        # Check context contains prediction result
        self.assertIn('prediction_result', response.context)
        self.assertIn('probability', response.context)
        self.assertIn('risk_level', response.context)
        
        # Check response contains result
        self.assertContains(response, 'Prediction Result')
        self.assertContains(response, 'Risk Level')
    
    def test_prediction_form_view_post_invalid_data(self):
        """Test prediction submission with invalid data."""
        self.client.login(email='patient@example.com', password='testpass123')
        
        response = self.client.post(reverse('predict_diabetes'), {
            'glucose': 'not-a-number',  # Invalid
            'bmi': -5  # Negative value (invalid)
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'prediction_app/diabetes.html')
        
        # Check form errors
        self.assertContains(response, 'Enter a valid number')
        self.assertContains(response, 'Ensure this value is greater than or equal to')
        
        # No new prediction should be created
        prediction_count = Prediction.objects.filter(
            user=self.user,
            disease_type=self.diabetes
        ).count()
        self.assertEqual(prediction_count, 1)  # Only the existing one
    
    def test_prediction_form_view_post_missing_data(self):
        """Test prediction submission with missing required data."""
        self.client.login(email='patient@example.com', password='testpass123')
        
        response = self.client.post(reverse('predict_diabetes'), {
            # Missing required fields
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'prediction_app/diabetes.html')
        
        # Check form errors for required fields
        self.assertContains(response, 'This field is required')
    
    def test_prediction_form_view_unauthenticated(self):
        """Test prediction form for unauthenticated user."""
        response = self.client.get(reverse('predict_diabetes'))
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('predict_diabetes')}")
    
    def test_prediction_result_view(self):
        """Test prediction result detail view."""
        self.client.login(email='patient@example.com', password='testpass123')
        
        response = self.client.get(reverse('prediction_detail', args=[self.existing_prediction.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'prediction_app/prediction_detail.html')
        
        # Check context
        self.assertIn('prediction', response.context)
        self.assertEqual(response.context['prediction'], self.existing_prediction)
        
        # Check content
        self.assertContains(response, 'Diabetes Prediction Result')
        self.assertContains(response, 'Confidence Score')
        self.assertContains(response, '78%')
        self.assertContains(response, 'High Risk')  # Based on confidence score
    
    def test_prediction_result_view_not_owner(self):
        """Test prediction detail view when user doesn't own the prediction."""
        other_user = User.objects.create_user(
            email='other@example.com',
            password='otherpass123'
        )
        
        self.client.login(email='other@example.com', password='otherpass123')
        
        response = self.client.get(reverse('prediction_detail', args=[self.existing_prediction.id]))
        
        self.assertEqual(response.status_code, 404)  # Not found (or 403 depending on implementation)
    
    def test_prediction_history_view(self):
        """Test prediction history view."""
        self.client.login(email='patient@example.com', password='testpass123')
        
        # Create more predictions
        for i in range(5):
            Prediction.objects.create(
                user=self.user,
                disease_type=self.diabetes,
                input_data={'glucose': 100 + i},
                prediction_result={'has_disease': i % 2 == 0},
                confidence_score=0.7 + i * 0.05
            )
        
        response = self.client.get(reverse('prediction_history'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'prediction_app/history.html')
        
        # Check context
        self.assertIn('predictions', response.context)
        self.assertIn('disease_filter', response.context)
        self.assertIn('date_filter', response.context)
        
        # Should show all predictions for the user
        predictions = response.context['predictions']
        self.assertEqual(predictions.count(), 6)  # Existing + 5 new
    
    def test_prediction_history_view_with_filters(self):
        """Test prediction history view with filters."""
        self.client.login(email='patient@example.com', password='testpass123')
        
        # Create predictions for different diseases
        Prediction.objects.create(
            user=self.user,
            disease_type=self.heart,
            input_data={'bp': 140},
            prediction_result={'has_disease': False},
            confidence_score=0.92
        )
        
        # Test disease filter
        response = self.client.get(reverse('prediction_history'), {'disease': 'heart'})
        
        self.assertEqual(response.status_code, 200)
        predictions = response.context['predictions']
        self.assertEqual(predictions.count(), 1)
        self.assertEqual(predictions.first().disease_type, self.heart)
        
        # Test date filter
        old_prediction = Prediction.objects.create(
            user=self.user,
            disease_type=self.diabetes,
            input_data={'glucose': 90},
            prediction_result={'has_disease': False},
            confidence_score=0.60,
            created_at=timezone.now() - timedelta(days=60)
        )
        
        response = self.client.get(reverse('prediction_history'), {'date_range': '30'})
        
        predictions = response.context['predictions']
        # Should not include prediction older than 30 days
        self.assertNotIn(old_prediction, predictions)
    
    def test_prediction_delete_view(self):
        """Test prediction delete view."""
        self.client.login(email='patient@example.com', password='testpass123')
        
        # Create a prediction to delete
        prediction_to_delete = Prediction.objects.create(
            user=self.user,
            disease_type=self.diabetes,
            input_data={'glucose': 110},
            prediction_result={'has_disease': False},
            confidence_score=0.65
        )
        
        response = self.client.post(reverse('prediction_delete', args=[prediction_to_delete.id]))
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('prediction_history'))
        
        # Check prediction was deleted
        with self.assertRaises(Prediction.DoesNotExist):
            Prediction.objects.get(id=prediction_to_delete.id)
    
    def test_prediction_delete_view_not_owner(self):
        """Test delete prediction when user doesn't own it."""
        other_user = User.objects.create_user(
            email='other@example.com',
            password='otherpass123'
        )
        
        self.client.login(email='other@example.com', password='otherpass123')
        
        response = self.client.post(reverse('prediction_delete', args=[self.existing_prediction.id]))
        
        self.assertEqual(response.status_code, 404)  # Not found
        
        # Prediction should still exist
        self.existing_prediction.refresh_from_db()
        self.assertIsNotNone(self.existing_prediction)
    
    def test_prediction_export_view(self):
        """Test prediction export functionality."""
        self.client.login(email='patient@example.com', password='testpass123')
        
        response = self.client.get(reverse('export_predictions'), {'format': 'csv'})
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertTrue(response['Content-Disposition'].startswith('attachment'))
        
        # Check CSV content
        content = response.content.decode('utf-8')
        self.assertIn('Diabetes', content)
        self.assertIn('85', content)  # Confidence score
    
    def test_prediction_statistics_view(self):
        """Test prediction statistics view."""
        self.client.login(email='patient@example.com', password='testpass123')
        
        response = self.client.get(reverse('prediction_statistics'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'prediction_app/statistics.html')
        
        # Check context contains statistics
        self.assertIn('total_predictions', response.context)
        self.assertIn('positive_count', response.context)
        self.assertIn('negative_count', response.context)
        self.assertIn('disease_breakdown', response.context)
        self.assertIn('monthly_trend', response.context)
        
        # Check statistics
        self.assertEqual(response.context['total_predictions'], 1)
        self.assertEqual(response.context['positive_count'], 1)
        self.assertEqual(response.context['negative_count'], 0)


class ReportViewTests(TestCase):
    """Test report-related views."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            email='patient@example.com',
            password='testpass123',
            user_type='patient'
        )
        
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
        
        self.report = Report.objects.create(
            user=self.user,
            title='Diabetes Screening Report',
            report_type='screening',
            content={
                'summary': 'High risk detected',
                'recommendations': ['Consult doctor', 'Monitor sugar']
            },
            predictions=[self.prediction]
        )
    
    def test_report_list_view(self):
        """Test report list view."""
        self.client.login(email='patient@example.com', password='testpass123')
        
        # Create another report
        Report.objects.create(
            user=self.user,
            title='Follow-up Report',
            report_type='followup',
            content={'summary': 'Follow-up needed'}
        )
        
        response = self.client.get(reverse('report_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'prediction_app/reports.html')
        
        # Check context
        self.assertIn('reports', response.context)
        self.assertEqual(response.context['reports'].count(), 2)
        
        # Check content
        self.assertContains(response, 'Diabetes Screening Report')
        self.assertContains(response, 'Follow-up Report')
    
    def test_report_detail_view(self):
        """Test report detail view."""
        self.client.login(email='patient@example.com', password='testpass123')
        
        response = self.client.get(reverse('report_detail', args=[self.report.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'prediction_app/report_detail.html')
        
        # Check context
        self.assertIn('report', response.context)
        self.assertEqual(response.context['report'], self.report)
        
        # Check content
        self.assertContains(response, 'Diabetes Screening Report')
        self.assertContains(response, 'High risk detected')
        self.assertContains(response, 'Consult doctor')
    
    def test_report_detail_view_not_owner(self):
        """Test report detail view when user doesn't own the report."""
        other_user = User.objects.create_user(
            email='other@example.com',
            password='otherpass123'
        )
        
        self.client.login(email='other@example.com', password='otherpass123')
        
        response = self.client.get(reverse('report_detail', args=[self.report.id]))
        
        self.assertEqual(response.status_code, 404)
    
    def test_report_generate_view(self):
        """Test report generation view."""
        self.client.login(email='patient@example.com', password='testpass123')
        
        response = self.client.post(reverse('generate_report'), {
            'title': 'Comprehensive Health Report',
            'report_type': 'comprehensive',
            'include_predictions': [self.prediction.id],
            'notes': 'Please review this comprehensive report'
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('report_list'))
        
        # Check report was created
        new_report = Report.objects.filter(
            user=self.user,
            title='Comprehensive Health Report'
        ).first()
        
        self.assertIsNotNone(new_report)
        self.assertEqual(new_report.report_type, 'comprehensive')
        self.assertIn(self.prediction, new_report.predictions.all())
    
    def test_report_download_pdf_view(self):
        """Test PDF download for report."""
        self.client.login(email='patient@example.com', password='testpass123')
        
        with patch('prediction_app.views.generate_pdf') as mock_generate_pdf:
            mock_generate_pdf.return_value = b'PDF content'
            
            response = self.client.get(reverse('report_download', args=[self.report.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response['Content-Disposition'].startswith('attachment'))
        self.assertEqual(response.content, b'PDF content')
    
    def test_report_share_view(self):
        """Test report sharing view."""
        self.client.login(email='patient@example.com', password='testpass123')
        
        doctor = User.objects.create_user(
            email='doctor@example.com',
            password='doctor123',
            user_type='doctor'
        )
        
        response = self.client.post(reverse('report_share', args=[self.report.id]), {
            'doctor_id': doctor.id,
            'notes': 'Please review this report'
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('report_detail', args=[self.report.id]))
        
        # Check report was shared
        self.report.refresh_from_db()
        self.assertTrue(self.report.is_shared)
        self.assertEqual(self.report.shared_with, doctor)
        self.assertEqual(self.report.sharing_notes, 'Please review this report')
    
    def test_report_delete_view(self):
        """Test report delete view."""
        self.client.login(email='patient@example.com', password='testpass123')
        
        response = self.client.post(reverse('report_delete', args=[self.report.id]))
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('report_list'))
        
        # Check report was deleted
        with self.assertRaises(Report.DoesNotExist):
            Report.objects.get(id=self.report.id)


class ConsultationViewTests(TestCase):
    """Test consultation-related views."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
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
        
        self.consultation = Consultation.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            prediction=self.prediction,
            consultation_type='initial',
            status='scheduled',
            scheduled_for=timezone.now() + timedelta(days=1),
            duration_minutes=30
        )
    
    def test_consultation_list_view_patient(self):
        """Test consultation list view for patient."""
        self.client.login(email='patient@example.com', password='patient123')
        
        response = self.client.get(reverse('consultation_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'consultations_app/consultation_list.html')
        
        # Check context
        self.assertIn('consultations', response.context)
        self.assertIn('upcoming_consultations', response.context)
        self.assertIn('past_consultations', response.context)
        
        # Should show patient's consultations
        self.assertEqual(response.context['consultations'].count(), 1)
        self.assertContains(response, 'Diabetes Consultation')
    
    def test_consultation_list_view_doctor(self):
        """Test consultation list view for doctor."""
        self.client.login(email='doctor@example.com', password='doctor123')
        
        # Create another consultation for different patient
        other_patient = User.objects.create_user(
            email='other@example.com',
            password='other123',
            user_type='patient'
        )
        
        Consultation.objects.create(
            patient=other_patient,
            doctor=self.doctor,
            consultation_type='followup',
            status='scheduled'
        )
        
        response = self.client.get(reverse('consultation_list'))
        
        self.assertEqual(response.status_code, 200)
        
        # Doctor should see all their consultations
        self.assertEqual(response.context['consultations'].count(), 2)
        self.assertContains(response, 'Upcoming Appointments')
    
    def test_consultation_detail_view_patient(self):
        """Test consultation detail view for patient."""
        self.client.login(email='patient@example.com', password='patient123')
        
        response = self.client.get(reverse('consultation_detail', args=[self.consultation.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'consultations_app/consultation_detail.html')
        
        # Check context
        self.assertIn('consultation', response.context)
        self.assertEqual(response.context['consultation'], self.consultation)
        
        # Check content
        self.assertContains(response, 'Consultation Details')
        self.assertContains(response, 'Diabetes')
        self.assertContains(response, 'scheduled')
    
    def test_consultation_detail_view_doctor(self):
        """Test consultation detail view for doctor."""
        self.client.login(email='doctor@example.com', password='doctor123')
        
        response = self.client.get(reverse('consultation_detail', args=[self.consultation.id]))
        
        self.assertEqual(response.status_code, 200)
        
        # Doctor should see additional options
        self.assertContains(response, 'Update Status')
        self.assertContains(response, 'Add Prescription')
    
    def test_consultation_create_view(self):
        """Test consultation creation view."""
        self.client.login(email='patient@example.com', password='patient123')
        
        response = self.client.post(reverse('consultation_create'), {
            'doctor': self.doctor.id,
            'prediction': self.prediction.id,
            'consultation_type': 'followup',
            'symptoms': 'Increased thirst, fatigue',
            'scheduled_for': (timezone.now() + timedelta(days=2)).strftime('%Y-%m-%d %H:%M'),
            'duration_minutes': 45,
            'notes': 'Need to discuss prediction results'
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('consultation_list'))
        
        # Check consultation was created
        new_consultation = Consultation.objects.filter(
            patient=self.patient,
            doctor=self.doctor,
            consultation_type='followup'
        ).first()
        
        self.assertIsNotNone(new_consultation)
        self.assertEqual(new_consultation.symptoms, 'Increased thirst, fatigue')
        self.assertEqual(new_consultation.duration_minutes, 45)
    
    def test_consultation_update_view_doctor(self):
        """Test consultation update by doctor."""
        self.client.login(email='doctor@example.com', password='doctor123')
        
        response = self.client.post(reverse('consultation_update', args=[self.consultation.id]), {
            'status': 'completed',
            'outcome': 'Patient advised to monitor blood sugar',
            'notes': 'Consultation went well, patient understands risks'
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('consultation_detail', args=[self.consultation.id]))
        
        # Check consultation was updated
        self.consultation.refresh_from_db()
        self.assertEqual(self.consultation.status, 'completed')
        self.assertEqual(self.consultation.outcome, 'Patient advised to monitor blood sugar')
        self.assertIsNotNone(self.consultation.completed_at)
    
    def test_consultation_cancel_view_patient(self):
        """Test consultation cancellation by patient."""
        self.client.login(email='patient@example.com', password='patient123')
        
        response = self.client.post(reverse('consultation_cancel', args=[self.consultation.id]), {
            'cancellation_reason': 'Unexpected conflict'
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('consultation_list'))
        
        # Check consultation was cancelled
        self.consultation.refresh_from_db()
        self.assertEqual(self.consultation.status, 'cancelled')
        self.assertEqual(self.consultation.cancellation_reason, 'Unexpected conflict')
    
    def test_consultation_reschedule_view(self):
        """Test consultation rescheduling."""
        self.client.login(email='patient@example.com', password='patient123')
        
        new_time = timezone.now() + timedelta(days=3)
        
        response = self.client.post(reverse('consultation_reschedule', args=[self.consultation.id]), {
            'scheduled_for': new_time.strftime('%Y-%m-%d %H:%M')
        })
        
        self.assertEqual(response.status_code, 302)
        
        # Check consultation was rescheduled
        self.consultation.refresh_from_db()
        self.assertEqual(
            self.consultation.scheduled_for.date(),
            new_time.date()
        )
    
    def test_consultation_availability_view(self):
        """Test doctor availability view."""
        self.client.login(email='patient@example.com', password='patient123')
        
        response = self.client.get(reverse('doctor_availability', args=[self.doctor.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'consultations_app/availability.html')
        
        # Check context
        self.assertIn('doctor', response.context)
        self.assertIn('available_slots', response.context)
        self.assertEqual(response.context['doctor'], self.doctor)
        
        # Check content
        self.assertContains(response, 'Available Time Slots')
        self.assertContains(response, self.doctor.get_full_name())


class FeedbackViewTests(TestCase):
    """Test feedback-related views."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            email='user@example.com',
            password='testpass123'
        )
    
    def test_feedback_create_view_get(self):
        """Test feedback form page GET request."""
        self.client.login(email='user@example.com', password='testpass123')
        
        response = self.client.get(reverse('feedback_create'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'prediction_app/feedback_form.html')
        self.assertContains(response, 'Submit Feedback')
        self.assertContains(response, 'Rating')
        self.assertContains(response, 'Comments')
    
    def test_feedback_create_view_post(self):
        """Test feedback submission."""
        self.client.login(email='user@example.com', password='testpass123')
        
        response = self.client.post(reverse('feedback_create'), {
            'rating': 5,
            'comment': 'Excellent prediction system! Very accurate and user-friendly.',
            'feedback_type': 'prediction',
            'prediction_accuracy': 'accurate',
            'suggestions': 'Add more visualizations'
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('feedback_thankyou'))
        
        # Check feedback was created
        feedback = UserFeedback.objects.filter(user=self.user).first()
        self.assertIsNotNone(feedback)
        self.assertEqual(feedback.rating, 5)
        self.assertEqual(feedback.comment, 'Excellent prediction system! Very accurate and user-friendly.')
        self.assertEqual(feedback.feedback_type, 'prediction')
    
    def test_feedback_list_view_admin(self):
        """Test feedback list view for admin."""
        # Create admin user
        admin = User.objects.create_superuser(
            email='admin@example.com',
            password='admin123'
        )
        
        # Create some feedback
        UserFeedback.objects.create(user=self.user, rating=4, comment='Good')
        UserFeedback.objects.create(user=self.user, rating=5, comment='Excellent')
        
        self.client.login(email='admin@example.com', password='admin123')
        
        response = self.client.get(reverse('feedback_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'prediction_app/feedback_list.html')
        
        # Check context
        self.assertIn('feedback_list', response.context)
        self.assertEqual(response.context['feedback_list'].count(), 2)
        
        # Check content
        self.assertContains(response, 'Feedback Management')
        self.assertContains(response, 'Good')
        self.assertContains(response, 'Excellent')
    
    def test_feedback_list_view_non_admin(self):
        """Test feedback list view for non-admin user."""
        self.client.login(email='user@example.com', password='testpass123')
        
        response = self.client.get(reverse('feedback_list'))
        
        self.assertEqual(response.status_code, 403)  # Forbidden
    
    def test_feedback_resolve_view_admin(self):
        """Test feedback resolution by admin."""
        # Create admin user
        admin = User.objects.create_superuser(
            email='admin@example.com',
            password='admin123'
        )
        
        # Create feedback
        feedback = UserFeedback.objects.create(
            user=self.user,
            rating=3,
            comment='Needs improvement',
            is_resolved=False
        )
        
        self.client.login(email='admin@example.com', password='admin123')
        
        response = self.client.post(reverse('feedback_resolve', args=[feedback.id]), {
            'resolution_notes': 'Implemented suggested changes'
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('feedback_list'))
        
        # Check feedback was resolved
        feedback.refresh_from_db()
        self.assertTrue(feedback.is_resolved)
        self.assertEqual(feedback.resolved_by, admin)
        self.assertEqual(feedback.resolution_notes, 'Implemented suggested changes')
    
    def test_feedback_thankyou_view(self):
        """Test feedback thank you page."""
        self.client.login(email='user@example.com', password='testpass123')
        
        response = self.client.get(reverse('feedback_thankyou'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'prediction_app/feedback_thankyou.html')
        self.assertContains(response, 'Thank You')
        self.assertContains(response, 'Your feedback has been submitted')
    
    def test_feedback_statistics_view(self):
        """Test feedback statistics view."""
        # Create admin user
        admin = User.objects.create_superuser(
            email='admin@example.com',
            password='admin123'
        )
        
        # Create feedback with different ratings
        UserFeedback.objects.create(user=self.user, rating=5)
        UserFeedback.objects.create(user=self.user, rating=4)
        UserFeedback.objects.create(user=self.user, rating=3)
        UserFeedback.objects.create(user=self.user, rating=5)
        UserFeedback.objects.create(user=self.user, rating=2)
        
        self.client.login(email='admin@example.com', password='admin123')
        
        response = self.client.get(reverse('feedback_statistics'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'prediction_app/feedback_statistics.html')
        
        # Check context
        self.assertIn('average_rating', response.context)
        self.assertIn('rating_distribution', response.context)
        self.assertIn('feedback_types', response.context)
        self.assertIn('recent_feedback', response.context)
        
        # Check statistics
        self.assertEqual(response.context['average_rating'], 3.8)  # (5+4+3+5+2)/5
        self.assertEqual(response.context['total_feedback'], 5)
        
        # Check content
        self.assertContains(response, 'Feedback Statistics')
        self.assertContains(response, '3.8')
        self.assertContains(response, '5 feedbacks')


class MLModelViewTests(TestCase):
    """Test ML model management views."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.admin = User.objects.create_superuser(
            email='admin@example.com',
            password='admin123'
        )
        
        self.diabetes = DiseaseType.objects.create(
            name='Diabetes',
            code='diabetes'
        )
    
    def test_mlmodel_list_view_admin(self):
        """Test ML model list view for admin."""
        # Create some ML models
        MLModel.objects.create(
            disease_type=self.diabetes,
            name='Random Forest',
            version='1.0.0',
            accuracy=0.85,
            is_active=True
        )
        
        MLModel.objects.create(
            disease_type=self.diabetes,
            name='SVM',
            version='1.0.0',
            accuracy=0.82,
            is_active=False
        )
        
        self.client.login(email='admin@example.com', password='admin123')
        
        response = self.client.get(reverse('mlmodel_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'prediction_app/mlmodel_list.html')
        
        # Check context
        self.assertIn('mlmodels', response.context)
        self.assertEqual(response.context['mlmodels'].count(), 2)
        
        # Check content
        self.assertContains(response, 'ML Model Management')
        self.assertContains(response, 'Random Forest')
        self.assertContains(response, 'SVM')
    
    def test_mlmodel_list_view_non_admin(self):
        """Test ML model list view for non-admin user."""
        regular_user = User.objects.create_user(
            email='user@example.com',
            password='user123'
        )
        
        self.client.login(email='user@example.com', password='user123')
        
        response = self.client.get(reverse('mlmodel_list'))
        
        self.assertEqual(response.status_code, 403)  # Forbidden
    
    def test_mlmodel_create_view(self):
        """Test ML model creation view."""
        self.client.login(email='admin@example.com', password='admin123')
        
        # Create a dummy model file
        model_content = b'fake model content'
        model_file = SimpleUploadedFile(
            'diabetes_model.pkl',
            model_content,
            content_type='application/octet-stream'
        )
        
        response = self.client.post(reverse('mlmodel_create'), {
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
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('mlmodel_list'))
        
        # Check ML model was created
        mlmodel = MLModel.objects.filter(
            disease_type=self.diabetes,
            name='XGBoost Classifier'
        ).first()
        
        self.assertIsNotNone(mlmodel)
        self.assertEqual(mlmodel.version, '1.0.0')
        self.assertEqual(mlmodel.accuracy, 0.88)
        self.assertEqual(mlmodel.algorithm, 'xgboost')
        self.assertTrue(mlmodel.is_active)
    
    def test_mlmodel_update_view(self):
        """Test ML model update view."""
        self.client.login(email='admin@example.com', password='admin123')
        
        # Create an ML model
        mlmodel = MLModel.objects.create(
            disease_type=self.diabetes,
            name='Test Model',
            version='1.0.0',
            accuracy=0.85,
            is_active=True
        )
        
        response = self.client.post(reverse('mlmodel_update', args=[mlmodel.id]), {
            'name': 'Test Model Updated',
            'version': '1.1.0',
            'accuracy': 0.87,
            'is_active': False
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('mlmodel_list'))
        
        # Check ML model was updated
        mlmodel.refresh_from_db()
        self.assertEqual(mlmodel.name, 'Test Model Updated')
        self.assertEqual(mlmodel.version, '1.1.0')
        self.assertEqual(mlmodel.accuracy, 0.87)
        self.assertFalse(mlmodel.is_active)
    
    def test_mlmodel_delete_view(self):
        """Test ML model deletion view."""
        self.client.login(email='admin@example.com', password='admin123')
        
        # Create an ML model
        mlmodel = MLModel.objects.create(
            disease_type=self.diabetes,
            name='Test Model',
            version='1.0.0',
            accuracy=0.85
        )
        
        response = self.client.post(reverse('mlmodel_delete', args=[mlmodel.id]))
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('mlmodel_list'))
        
        # Check ML model was deleted
        with self.assertRaises(MLModel.DoesNotExist):
            MLModel.objects.get(id=mlmodel.id)
    
    def test_mlmodel_detail_view(self):
        """Test ML model detail view."""
        self.client.login(email='admin@example.com', password='admin123')
        
        # Create an ML model with performance metrics
        mlmodel = MLModel.objects.create(
            disease_type=self.diabetes,
            name='Random Forest',
            version='1.0.0',
            accuracy=0.85,
            precision=0.82,
            recall=0.87,
            f1_score=0.84,
            roc_auc=0.89,
            training_date=timezone.now(),
            dataset_size=1000,
            features=['glucose', 'bmi', 'age'],
            is_active=True
        )
        
        response = self.client.get(reverse('mlmodel_detail', args=[mlmodel.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'prediction_app/mlmodel_detail.html')
        
        # Check context
        self.assertIn('mlmodel', response.context)
        self.assertEqual(response.context['mlmodel'], mlmodel)
        
        # Check content
        self.assertContains(response, 'Random Forest')
        self.assertContains(response, '85.0%')
        self.assertContains(response, 'glucose')
        self.assertContains(response, 'bmi')
        self.assertContains(response, 'age')
    
    def test_mlmodel_performance_view(self):
        """Test ML model performance view."""
        self.client.login(email='admin@example.com', password='admin123')
        
        # Create an ML model
        mlmodel = MLModel.objects.create(
            disease_type=self.diabetes,
            name='Test Model',
            version='1.0.0',
            accuracy=0.85
        )
        
        response = self.client.get(reverse('mlmodel_performance', args=[mlmodel.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'prediction_app/mlmodel_performance.html')
        
        # Check context contains performance data
        self.assertIn('mlmodel', response.context)
        self.assertIn('performance_data', response.context)
        self.assertIn('predictions_count', response.context)
        
        # Check content
        self.assertContains(response, 'Model Performance')
        self.assertContains(response, 'Accuracy: 85.0%')


class AdminViewTests(TestCase):
    """Test admin-specific views."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.admin = User.objects.create_superuser(
            email='admin@example.com',
            password='admin123'
        )
        
        self.regular_user = User.objects.create_user(
            email='user@example.com',
            password='user123'
        )
    
    def test_admin_dashboard_view_admin(self):
        """Test admin dashboard for admin user."""
        self.client.login(email='admin@example.com', password='admin123')
        
        response = self.client.get(reverse('admin_dashboard'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'prediction_app/admin_dashboard.html')
        
        # Check context contains admin statistics
        self.assertIn('user_count', response.context)
        self.assertIn('prediction_count', response.context)
        self.assertIn('consultation_count', response.context)
        self.assertIn('feedback_count', response.context)
        
        # Check content
        self.assertContains(response, 'Admin Dashboard')
        self.assertContains(response, 'System Statistics')
    
    def test_admin_dashboard_view_non_admin(self):
        """Test admin dashboard for non-admin user."""
        self.client.login(email='user@example.com', password='user123')
        
        response = self.client.get(reverse('admin_dashboard'))
        
        self.assertEqual(response.status_code, 403)  # Forbidden
    
    def test_user_management_view_admin(self):
        """Test user management view for admin."""
        self.client.login(email='admin@example.com', password='admin123')
        
        # Create some users
        User.objects.create_user(email='user1@example.com', password='pass1')
        User.objects.create_user(email='user2@example.com', password='pass2')
        
        response = self.client.get(reverse('user_management'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users_app/user_management.html')
        
        # Check context
        self.assertIn('users', response.context)
        self.assertGreaterEqual(response.context['users'].count(), 3)  # admin + regular + 2 new
        
        # Check content
        self.assertContains(response, 'User Management')
        self.assertContains(response, 'admin@example.com')
        self.assertContains(response, 'user1@example.com')
    
    def test_user_management_view_non_admin(self):
        """Test user management view for non-admin."""
        self.client.login(email='user@example.com', password='user123')
        
        response = self.client.get(reverse('user_management'))
        
        self.assertEqual(response.status_code, 403)  # Forbidden
    
    def test_user_toggle_active_view(self):
        """Test toggling user active status."""
        self.client.login(email='admin@example.com', password='admin123')
        
        # Create an inactive user
        inactive_user = User.objects.create_user(
            email='inactive@example.com',
            password='inactive123',
            is_active=False
        )
        
        # Activate the user
        response = self.client.post(reverse('user_toggle_active', args=[inactive_user.id]))
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('user_management'))
        
        # Check user is now active
        inactive_user.refresh_from_db()
        self.assertTrue(inactive_user.is_active)
        
        # Deactivate the user
        response = self.client.post(reverse('user_toggle_active', args=[inactive_user.id]))
        
        # Check user is now inactive
        inactive_user.refresh_from_db()
        self.assertFalse(inactive_user.is_active)
    
    def test_system_logs_view_admin(self):
        """Test system logs view for admin."""
        self.client.login(email='admin@example.com', password='admin123')
        
        response = self.client.get(reverse('system_logs'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'prediction_app/system_logs.html')
        
        # Check context
        self.assertIn('log_files', response.context)
        self.assertIn('log_content', response.context)
        
        # Check content
        self.assertContains(response, 'System Logs')
        self.assertContains(response, 'Log Files')
    
    def test_system_logs_view_non_admin(self):
        """Test system logs view for non-admin."""
        self.client.login(email='user@example.com', password='user123')
        
        response = self.client.get(reverse('system_logs'))
        
        self.assertEqual(response.status_code, 403)  # Forbidden
    
    def test_system_health_view_admin(self):
        """Test system health view for admin."""
        self.client.login(email='admin@example.com', password='admin123')
        
        with patch('prediction_app.views.HealthChecker') as MockHealthChecker:
            mock_checker = MagicMock()
            mock_checker.run_health_check.return_value = {
                'summary': {'overall_status': 'healthy'},
                'checks': [
                    {'name': 'Database', 'status': 'OK'},
                    {'name': 'Redis', 'status': 'OK'},
                    {'name': 'Celery', 'status': 'OK'}
                ]
            }
            MockHealthChecker.return_value = mock_checker
            
            response = self.client.get(reverse('system_health'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'prediction_app/system_health.html')
        
        # Check context
        self.assertIn('health_status', response.context)
        self.assertIn('health_checks', response.context)
        
        # Check content
        self.assertContains(response, 'System Health')
        self.assertContains(response, 'healthy')
        self.assertContains(response, 'Database')
        self.assertContains(response, 'Redis')
    
    def test_backup_system_view(self):
        """Test system backup view."""
        self.client.login(email='admin@example.com', password='admin123')
        
        with patch('prediction_app.views.backup_database') as mock_backup:
            mock_backup.return_value = '/path/to/backup.sql'
            
            response = self.client.post(reverse('backup_system'))
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('admin_dashboard'))
        
        # Check backup was called
        mock_backup.assert_called_once()


class ErrorViewTests(TestCase):
    """Test error handling views."""
    
    def test_404_error_view(self):
        """Test custom 404 error page."""
        response = self.client.get('/non-existent-page/')
        
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, 'error_pages/404.html')
        self.assertContains(response, 'Page Not Found')
        self.assertContains(response, 'The page you are looking for does not exist')
    
    def test_403_error_view(self):
        """Test custom 403 error page."""
        # Create a view that requires authentication
        self.client.logout()
        response = self.client.get(reverse('dashboard'))
        
        # Should redirect to login, not show 403
        # For testing 403, we need a different scenario
        user = User.objects.create_user(
            email='user@example.com',
            password='user123'
        )
        
        self.client.login(email='user@example.com', password='user123')
        
        # Try to access admin-only page
        response = self.client.get(reverse('admin_dashboard'))
        
        self.assertEqual(response.status_code, 403)
        # Django's default 403 template, not our custom one
        # To test custom 403, we need to configure it in settings
    
    def test_500_error_view(self):
        """Test custom 500 error page."""
        # This is harder to test as it requires causing a server error
        # We'll test that the template exists
        from django.template.loader import render_to_string
        from django.http import HttpResponseServerError
        
        # Render the template directly
        html = render_to_string('error_pages/500.html')
        
        self.assertIn('Server Error', html)
        self.assertIn('Something went wrong on our end', html)
    
    def test_health_check_view(self):
        """Test health check endpoint."""
        response = self.client.get('/health/')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'healthy'})
    
    def test_maintenance_mode_view(self):
        """Test maintenance mode page."""
        # Enable maintenance mode via settings (simulated)
        with self.settings(MAINTENANCE_MODE=True):
            response = self.client.get(reverse('home'))
            
            # Should show maintenance page
            self.assertTemplateUsed(response, 'error_pages/maintenance.html')
            self.assertContains(response, 'Maintenance Mode')
            self.assertContains(response, 'We are currently performing maintenance')