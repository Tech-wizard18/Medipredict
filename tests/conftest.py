"""
Pytest configuration for MEDIPREDICT tests
"""

import pytest
import os
import django
from django.test import TestCase
from django.contrib.auth import get_user_model

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'disease_app.settings.testing')
django.setup()

User = get_user_model()


@pytest.fixture
def test_user():
    """Create a test user."""
    return User.objects.create_user(
        email='test@example.com',
        password='testpass123',
        first_name='Test',
        last_name='User'
    )


@pytest.fixture
def test_patient():
    """Create a test patient user."""
    return User.objects.create_user(
        email='patient@example.com',
        password='patient123',
        user_type='patient',
        first_name='Patient',
        last_name='User'
    )


@pytest.fixture
def test_doctor():
    """Create a test doctor user."""
    return User.objects.create_user(
        email='doctor@example.com',
        password='doctor123',
        user_type='doctor',
        first_name='Doctor',
        last_name='User'
    )


@pytest.fixture
def test_disease():
    """Create a test disease type."""
    from prediction_app.models import DiseaseType
    return DiseaseType.objects.create(
        name='Diabetes',
        code='diabetes',
        description='Diabetes prediction model',
        is_active=True
    )


@pytest.fixture
def test_ml_model(test_disease):
    """Create a test ML model."""
    from prediction_app.models import MLModel
    return MLModel.objects.create(
        disease_type=test_disease,
        name='Test Model',
        version='1.0.0',
        accuracy=0.85,
        path='models/test_model.pkl',
        is_active=True
    )


@pytest.fixture
def test_prediction(test_patient, test_disease, test_ml_model):
    """Create a test prediction."""
    from prediction_app.models import Prediction
    return Prediction.objects.create(
        user=test_patient,
        disease_type=test_disease,
        ml_model=test_ml_model,
        input_data={'glucose': 120, 'bmi': 25.5},
        prediction_result={'has_disease': True, 'probability': 0.78},
        confidence_score=0.78,
        is_positive=True
    )


@pytest.fixture
def api_client():
    """Create an API test client."""
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def authenticated_api_client(test_user):
    """Create an authenticated API test client."""
    from rest_framework.test import APIClient
    client = APIClient()
    
    # Get token
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(test_user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    
    return client


@pytest.fixture
def django_client():
    """Create a Django test client."""
    from django.test import Client
    return Client()


@pytest.fixture
def authenticated_django_client(test_user):
    """Create an authenticated Django test client."""
    from django.test import Client
    client = Client()
    client.login(email='test@example.com', password='testpass123')
    return client