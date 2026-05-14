
"""
Script to train and save machine learning models for disease prediction.
Run this script to train all models or specific models.
"""

import os
import sys
import json
import pickle
import argparse
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any

# ML Libraries
from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from imblearn.over_sampling import SMOTE

# Add project root to path
sys.path.append(str(Path(__file__).parent))

# Constants
BASE_DIR = Path(__file__).parent
MODELS_DIR = BASE_DIR / "prediction_app" / "ml_models"
SCALERS_DIR = MODELS_DIR / "scalers"
DATA_DIR = BASE_DIR / "data"

# Create directories
MODELS_DIR.mkdir(exist_ok=True)
SCALERS_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

class ModelTrainer:
    """Base class for training disease prediction models."""
    
    def __init__(self, disease_name: str):
        self.disease_name = disease_name
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = []
        self.metrics = {}
        
    def load_data(self) -> Tuple[pd.DataFrame, pd.Series]:
        """Load dataset for the specific disease."""
        # In a real scenario, this would load from actual medical datasets
        # For now, we'll create synthetic data for demonstration
        
        if self.disease_name == "diabetes":
            return self._create_diabetes_data()
        elif self.disease_name == "heart":
            return self._create_heart_data()
        elif self.disease_name == "kidney":
            return self._create_kidney_data()
        elif self.disease_name == "parkinson":
            return self._create_parkinson_data()
        elif self.disease_name == "breast_cancer":
            return self._create_breast_cancer_data()
        elif self.disease_name == "liver":
            return self._create_liver_data()
        else:
            raise ValueError(f"Unknown disease: {self.disease_name}")
    
    def preprocess_data(self, X: pd.DataFrame, y: pd.Series) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Preprocess the data."""
        # Handle missing values
        X = X.fillna(X.mean())
        
        # Encode categorical variables
        categorical_cols = X.select_dtypes(include=['object']).columns
        for col in categorical_cols:
            le = LabelEncoder()
            X[col] = le.fit_transform(X[col])
        
        # Store feature names
        self.feature_names = list(X.columns)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Handle class imbalance
        smote = SMOTE(random_state=42)
        X_train, y_train = smote.fit_resample(X_train, y_train)
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        return X_train_scaled, X_test_scaled, y_train, y_test
    
    def train_model(self, X_train: np.ndarray, y_train: np.ndarray):
        """Train the model with hyperparameter tuning."""
        # Define base model
        if self.disease_name in ["diabetes", "heart"]:
            model = XGBClassifier(random_state=42, n_jobs=-1)
            param_grid = {
                'n_estimators': [100, 200],
                'max_depth': [3, 5, 7],
                'learning_rate': [0.01, 0.1, 0.2]
            }
        elif self.disease_name in ["kidney", "liver"]:
            model = RandomForestClassifier(random_state=42, n_jobs=-1)
            param_grid = {
                'n_estimators': [100, 200],
                'max_depth': [10, 20, None],
                'min_samples_split': [2, 5]
            }
        else:
            model = GradientBoostingClassifier(random_state=42)
            param_grid = {
                'n_estimators': [100, 200],
                'max_depth': [3, 5],
                'learning_rate': [0.01, 0.1]
            }
        
        # Perform grid search
        grid_search = GridSearchCV(
            model, param_grid, cv=5, scoring='f1_macro', n_jobs=-1
        )
        grid_search.fit(X_train, y_train)
        
        self.model = grid_search.best_estimator_
        print(f"Best parameters for {self.disease_name}: {grid_search.best_params_}")
    
    def evaluate_model(self, X_test: np.ndarray, y_test: np.ndarray):
        """Evaluate the trained model."""
        y_pred = self.model.predict(X_test)
        y_pred_proba = self.model.predict_proba(X_test)[:, 1] if hasattr(self.model, "predict_proba") else None
        
        self.metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred, average='weighted'),
            'recall': recall_score(y_test, y_pred, average='weighted'),
            'f1_score': f1_score(y_test, y_pred, average='weighted'),
            'roc_auc': roc_auc_score(y_test, y_pred_proba) if y_pred_proba is not None else None,
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"\nMetrics for {self.disease_name}:")
        for metric, value in self.metrics.items():
            if value is not None:
                print(f"  {metric}: {value:.4f}")
    
    def save_model(self):
        """Save the trained model and scaler."""
        # Save model
        model_path = MODELS_DIR / f"{self.disease_name}_model.pkl"
        with open(model_path, 'wb') as f:
            pickle.dump(self.model, f)
        
        # Save scaler
        scaler_path = SCALERS_DIR / f"{self.disease_name}_scaler.pkl"
        with open(scaler_path, 'wb') as f:
            pickle.dump(self.scaler, f)
        
        # Save feature names and metrics
        metadata = {
            'disease_name': self.disease_name,
            'feature_names': self.feature_names,
            'metrics': self.metrics,
            'model_type': type(self.model).__name__,
            'created_at': datetime.now().isoformat()
        }
        
        metadata_path = MODELS_DIR / f"{self.disease_name}_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"\nModel saved to: {model_path}")
        print(f"Scaler saved to: {scaler_path}")
        print(f"Metadata saved to: {metadata_path}")
    
    def _create_diabetes_data(self) -> Tuple[pd.DataFrame, pd.Series]:
        """Create synthetic diabetes dataset."""
        n_samples = 1000
        np.random.seed(42)
        
        data = {
            'pregnancies': np.random.randint(0, 20, n_samples),
            'glucose': np.random.normal(120, 30, n_samples),
            'blood_pressure': np.random.normal(70, 12, n_samples),
            'skin_thickness': np.random.normal(20, 10, n_samples),
            'insulin': np.random.normal(80, 40, n_samples),
            'bmi': np.random.normal(30, 8, n_samples),
            'diabetes_pedigree': np.random.uniform(0.08, 2.5, n_samples),
            'age': np.random.randint(20, 80, n_samples)
        }
        
        # Create target based on features
        risk_score = (
            0.1 * (data['pregnancies'] > 5) +
            0.2 * (data['glucose'] > 140) +
            0.15 * (data['bmi'] > 30) +
            0.1 * (data['age'] > 50) +
            0.05 * np.random.randn(n_samples)
        )
        
        X = pd.DataFrame(data)
        y = (risk_score > 0.5).astype(int)
        
        return X, y
    
    def _create_heart_data(self) -> Tuple[pd.DataFrame, pd.Series]:
        """Create synthetic heart disease dataset."""
        n_samples = 1000
        np.random.seed(42)
        
        data = {
            'age': np.random.randint(29, 80, n_samples),
            'sex': np.random.choice([0, 1], n_samples),
            'cp': np.random.randint(0, 4, n_samples),
            'trestbps': np.random.normal(130, 17, n_samples),
            'chol': np.random.normal(240, 45, n_samples),
            'fbs': np.random.choice([0, 1], n_samples, p=[0.85, 0.15]),
            'restecg': np.random.randint(0, 3, n_samples),
            'thalach': np.random.normal(150, 22, n_samples),
            'exang': np.random.choice([0, 1], n_samples, p=[0.65, 0.35]),
            'oldpeak': np.random.uniform(0, 6, n_samples),
            'slope': np.random.randint(0, 3, n_samples),
            'ca': np.random.randint(0, 4, n_samples),
            'thal': np.random.randint(0, 4, n_samples)
        }
        
        # Create target based on features
        risk_score = (
            0.2 * (data['age'] > 55) +
            0.15 * (data['chol'] > 240) +
            0.1 * (data['trestbps'] > 140) +
            0.05 * (data['oldpeak'] > 2) +
            0.02 * np.random.randn(n_samples)
        )
        
        X = pd.DataFrame(data)
        y = (risk_score > 0.3).astype(int)
        
        return X, y
    
    def _create_kidney_data(self) -> Tuple[pd.DataFrame, pd.Series]:
        """Create synthetic kidney disease dataset."""
        n_samples = 800
        np.random.seed(42)
        
        data = {
            'age': np.random.randint(20, 90, n_samples),
            'blood_pressure': np.random.normal(80, 15, n_samples),
            'specific_gravity': np.random.uniform(1.005, 1.025, n_samples),
            'albumin': np.random.randint(0, 5, n_samples),
            'sugar': np.random.randint(0, 5, n_samples),
            'red_blood_cells': np.random.choice([0, 1], n_samples, p=[0.3, 0.7]),
            'pus_cell': np.random.choice([0, 1], n_samples, p=[0.4, 0.6]),
            'pus_cell_clumps': np.random.choice([0, 1], n_samples, p=[0.6, 0.4]),
            'bacteria': np.random.choice([0, 1], n_samples, p=[0.7, 0.3]),
            'blood_glucose_random': np.random.normal(100, 40, n_samples),
            'blood_urea': np.random.normal(30, 15, n_samples),
            'serum_creatinine': np.random.normal(1.2, 0.5, n_samples),
            'sodium': np.random.normal(140, 10, n_samples),
            'potassium': np.random.normal(4.0, 0.5, n_samples),
            'hemoglobin': np.random.normal(13.5, 2.5, n_samples),
            'packed_cell_volume': np.random.normal(40, 8, n_samples),
            'white_blood_cell_count': np.random.normal(8000, 3000, n_samples),
            'red_blood_cell_count': np.random.normal(4.7, 0.5, n_samples),
            'hypertension': np.random.choice([0, 1], n_samples, p=[0.6, 0.4]),
            'diabetes_mellitus': np.random.choice([0, 1], n_samples, p=[0.7, 0.3]),
            'coronary_artery_disease': np.random.choice([0, 1], n_samples, p=[0.8, 0.2]),
            'appetite': np.random.choice([0, 1], n_samples, p=[0.3, 0.7]),
            'peda_edema': np.random.choice([0, 1], n_samples, p=[0.7, 0.3]),
            'anemia': np.random.choice([0, 1], n_samples, p=[0.8, 0.2])
        }
        
        # Create target based on features
        risk_score = (
            0.15 * (data['serum_creatinine'] > 1.5) +
            0.1 * (data['blood_urea'] > 40) +
            0.1 * (data['albumin'] > 2) +
            0.05 * (data['age'] > 60) +
            0.03 * np.random.randn(n_samples)
        )
        
        X = pd.DataFrame(data)
        y = (risk_score > 0.25).astype(int)
        
        return X, y
    
    def _create_parkinson_data(self) -> Tuple[pd.DataFrame, pd.Series]:
        """Create synthetic Parkinson's disease dataset."""
        n_samples = 500
        np.random.seed(42)
        
        # Voice features for Parkinson's detection
        data = {
            'MDVP:Fo(Hz)': np.random.normal(200, 50, n_samples),
            'MDVP:Fhi(Hz)': np.random.normal(250, 60, n_samples),
            'MDVP:Flo(Hz)': np.random.normal(150, 40, n_samples),
            'MDVP:Jitter(%)': np.random.uniform(0.001, 0.1, n_samples),
            'MDVP:Jitter(Abs)': np.random.uniform(0.00001, 0.0001, n_samples),
            'MDVP:RAP': np.random.uniform(0.001, 0.05, n_samples),
            'MDVP:PPQ': np.random.uniform(0.001, 0.05, n_samples),
            'Jitter:DDP': np.random.uniform(0.003, 0.15, n_samples),
            'MDVP:Shimmer': np.random.uniform(0.01, 0.2, n_samples),
            'MDVP:Shimmer(dB)': np.random.uniform(0.1, 1.5, n_samples),
            'Shimmer:APQ3': np.random.uniform(0.01, 0.1, n_samples),
            'Shimmer:APQ5': np.random.uniform(0.01, 0.1, n_samples),
            'MDVP:APQ': np.random.uniform(0.01, 0.1, n_samples),
            'Shimmer:DDA': np.random.uniform(0.03, 0.3, n_samples),
            'NHR': np.random.uniform(0.001, 0.1, n_samples),
            'HNR': np.random.uniform(10, 30, n_samples),
            'RPDE': np.random.uniform(0.2, 0.8, n_samples),
            'DFA': np.random.uniform(0.5, 0.9, n_samples),
            'spread1': np.random.uniform(-10, 0, n_samples),
            'spread2': np.random.uniform(0, 0.5, n_samples),
            'D2': np.random.uniform(1.5, 3.5, n_samples),
            'PPE': np.random.uniform(0.1, 0.5, n_samples)
        }
        
        # Create target based on features
        risk_score = (
            0.2 * (data['MDVP:Jitter(%)'] > 0.05) +
            0.15 * (data['MDVP:Shimmer'] > 0.1) +
            0.1 * (data['HNR'] < 20) +
            0.05 * np.random.randn(n_samples)
        )
        
        X = pd.DataFrame(data)
        y = (risk_score > 0.25).astype(int)
        
        return X, y
    
    def _create_breast_cancer_data(self) -> Tuple[pd.DataFrame, pd.Series]:
        """Create synthetic breast cancer dataset."""
        n_samples = 600
        np.random.seed(42)
        
        # Wisconsin Breast Cancer Dataset features
        data = {
            'radius_mean': np.random.normal(15, 5, n_samples),
            'texture_mean': np.random.normal(20, 5, n_samples),
            'perimeter_mean': np.random.normal(100, 30, n_samples),
            'area_mean': np.random.normal(700, 350, n_samples),
            'smoothness_mean': np.random.uniform(0.05, 0.2, n_samples),
            'compactness_mean': np.random.uniform(0.02, 0.4, n_samples),
            'concavity_mean': np.random.uniform(0.0, 0.5, n_samples),
            'concave_points_mean': np.random.uniform(0.0, 0.3, n_samples),
            'symmetry_mean': np.random.uniform(0.1, 0.3, n_samples),
            'fractal_dimension_mean': np.random.uniform(0.04, 0.1, n_samples)
        }
        
        # Create target based on features
        risk_score = (
            0.2 * (data['radius_mean'] > 17) +
            0.15 * (data['concavity_mean'] > 0.2) +
            0.1 * (data['compactness_mean'] > 0.2) +
            0.05 * np.random.randn(n_samples)
        )
        
        X = pd.DataFrame(data)
        y = (risk_score > 0.25).astype(int)
        
        return X, y
    
    def _create_liver_data(self) -> Tuple[pd.DataFrame, pd.Series]:
        """Create synthetic liver disease dataset."""
        n_samples = 700
        np.random.seed(42)
        
        data = {
            'age': np.random.randint(20, 80, n_samples),
            'gender': np.random.choice([0, 1], n_samples),
            'total_bilirubin': np.random.normal(1.2, 1.0, n_samples),
            'direct_bilirubin': np.random.normal(0.4, 0.3, n_samples),
            'alkaline_phosphotase': np.random.normal(300, 150, n_samples),
            'alamine_aminotransferase': np.random.normal(40, 30, n_samples),
            'aspartate_aminotransferase': np.random.normal(35, 25, n_samples),
            'total_proteins': np.random.normal(7.0, 1.0, n_samples),
            'albumin': np.random.normal(4.0, 0.8, n_samples),
            'albumin_and_globulin_ratio': np.random.normal(1.2, 0.4, n_samples)
        }
        
        # Create target based on features
        risk_score = (
            0.2 * (data['total_bilirubin'] > 2.0) +
            0.15 * (data['alamine_aminotransferase'] > 60) +
            0.1 * (data['aspartate_aminotransferase'] > 50) +
            0.05 * (data['albumin'] < 3.5) +
            0.03 * np.random.randn(n_samples)
        )
        
        X = pd.DataFrame(data)
        y = (risk_score > 0.25).astype(int)
        
        return X, y
    
    def run(self):
        """Execute the complete training pipeline."""
        print(f"\n{'='*60}")
        print(f"Training model for: {self.disease_name.replace('_', ' ').title()}")
        print(f"{'='*60}")
        
        try:
            # Load data
            print("Loading data...")
            X, y = self.load_data()
            print(f"Data shape: {X.shape}")
            print(f"Class distribution:\n{y.value_counts(normalize=True).to_dict()}")
            
            # Preprocess data
            print("\nPreprocessing data...")
            X_train, X_test, y_train, y_test = self.preprocess_data(X, y)
            print(f"Training set shape: {X_train.shape}")
            print(f"Testing set shape: {X_test.shape}")
            
            # Train model
            print("\nTraining model...")
            self.train_model(X_train, y_train)
            
            # Evaluate model
            print("\nEvaluating model...")
            self.evaluate_model(X_test, y_test)
            
            # Save model
            print("\nSaving model...")
            self.save_model()
            
            print(f"\n✓ Successfully trained {self.disease_name} model!")
            
        except Exception as e:
            print(f"\n✗ Error training {self.disease_name} model: {str(e)}")
            raise

def main():
    """Main function to train models."""
    parser = argparse.ArgumentParser(description='Train disease prediction models')
    parser.add_argument('--disease', type=str, default='all',
                       choices=['all', 'diabetes', 'heart', 'kidney', 
                               'parkinson', 'breast_cancer', 'liver'],
                       help='Disease to train model for')
    parser.add_argument('--output-dir', type=str, default=str(MODELS_DIR),
                       help='Directory to save trained models')
    
    args = parser.parse_args()
    
    diseases = []
    if args.disease == 'all':
        diseases = ['diabetes', 'heart', 'kidney', 'parkinson', 'breast_cancer', 'liver']
    else:
        diseases = [args.disease]
    
    print(f"Training models for: {', '.join(diseases)}")
    print(f"Models will be saved to: {args.output_dir}")
    
    results = {}
    for disease in diseases:
        try:
            trainer = ModelTrainer(disease)
            trainer.run()
            results[disease] = 'Success'
        except Exception as e:
            results[disease] = f'Failed: {str(e)}'
    
    # Print summary
    print(f"\n{'='*60}")
    print("Training Summary:")
    print(f"{'='*60}")
    for disease, status in results.items():
        print(f"{disease.replace('_', ' ').title():20} {status}")
    
    # Save summary
    summary_path = MODELS_DIR / "training_summary.json"
    summary = {
        'training_date': datetime.now().isoformat(),
        'results': results,
        'total_diseases': len(diseases),
        'successful': sum(1 for status in results.values() if status == 'Success'),
        'failed': sum(1 for status in results.values() if status != 'Success')
    }
    
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\nSummary saved to: {summary_path}")
    print(f"\nTraining completed!")

if __name__ == '__main__':
    main()