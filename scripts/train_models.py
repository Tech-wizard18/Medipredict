"""
Script to train and save ML models for all diseases.
Run with: python scripts/train_models.py
"""
import os
import sys
import pickle
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'disease_app.settings.base')

import django
django.setup()

from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.datasets import make_classification
from django.conf import settings

MODELS_DIR = os.path.join(settings.BASE_DIR, 'prediction_app', 'ml_models')
SCALERS_DIR = os.path.join(MODELS_DIR, 'scalers')
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(SCALERS_DIR, exist_ok=True)

DISEASE_FEATURES = {
    'diabetes': 8,
    'heart': 13,
    'kidney': 24,
    'parkinson': 22,
    'breast_cancer': 30,
    'liver': 10,
}

def train_and_save(disease, n_features):
    print(f"Training {disease} model ({n_features} features)...")
    X, y = make_classification(
        n_samples=1000,
        n_features=n_features,
        n_informative=max(2, n_features // 2),
        n_redundant=max(1, n_features // 4),
        n_repeated=0,
        random_state=42
    )

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_scaled, y)

    model_path = os.path.join(MODELS_DIR, f'{disease}_model.pkl')
    scaler_path = os.path.join(SCALERS_DIR, f'{disease}_scaler.pkl')

    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    with open(scaler_path, 'wb') as f:
        pickle.dump(scaler, f)

    print(f"  Saved: {model_path}")
    print(f"  Saved: {scaler_path}")

if __name__ == '__main__':
    for disease, n_features in DISEASE_FEATURES.items():
        train_and_save(disease, n_features)
    print("\nAll models trained and saved successfully!")
