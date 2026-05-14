import pandas as pd
import numpy as np
import os
from django.conf import settings
import logging
from typing import Dict, List, Tuple, Optional ,Any
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import pickle
import joblib

logger = logging.getLogger(__name__)


class DataLoader:
    """Load and preprocess datasets for training."""
    
    def __init__(self):
        self.data_dir = os.path.join(settings.BASE_DIR, 'prediction_app', 'data')
        os.makedirs(self.data_dir, exist_ok=True)
    
    def load_diabetes_data(self) -> Tuple[pd.DataFrame, pd.Series]:
        """Load diabetes dataset."""
        # In production, load from actual dataset
        # For now, create synthetic data structure
        data = {
            'Pregnancies': [6, 1, 8, 1, 0],
            'Glucose': [148, 85, 183, 89, 137],
            'BloodPressure': [72, 66, 64, 66, 40],
            'SkinThickness': [35, 29, 0, 23, 35],
            'Insulin': [0, 0, 0, 94, 168],
            'BMI': [33.6, 26.6, 23.3, 28.1, 43.1],
            'DiabetesPedigreeFunction': [0.627, 0.351, 0.672, 0.167, 2.288],
            'Age': [50, 31, 32, 21, 33],
            'Outcome': [1, 0, 1, 0, 1]
        }
        
        df = pd.DataFrame(data)
        X = df.drop('Outcome', axis=1)
        y = df['Outcome']
        
        return X, y
    
    def load_heart_data(self) -> Tuple[pd.DataFrame, pd.Series]:
        """Load heart disease dataset."""
        data = {
            'age': [63, 37, 41, 56, 57],
            'sex': [1, 1, 0, 1, 0],
            'cp': [3, 2, 1, 1, 0],
            'trestbps': [145, 130, 130, 120, 120],
            'chol': [233, 250, 204, 236, 354],
            'fbs': [1, 0, 0, 0, 1],
            'restecg': [0, 1, 0, 1, 1],
            'thalach': [150, 187, 172, 178, 163],
            'exang': [0, 0, 0, 0, 1],
            'oldpeak': [2.3, 3.5, 1.4, 0.8, 0.6],
            'slope': [0, 0, 2, 2, 2],
            'ca': [0, 0, 0, 0, 0],
            'thal': [1, 2, 2, 2, 2],
            'target': [1, 0, 0, 0, 1]
        }
        
        df = pd.DataFrame(data)
        X = df.drop('target', axis=1)
        y = df['target']
        
        return X, y
    
    def load_kidney_data(self) -> Tuple[pd.DataFrame, pd.Series]:
        """Load kidney disease dataset."""
        # Synthetic data structure
        data = {
            'age': [48, 7, 62, 48, 51],
            'bp': [80, 50, 80, 70, 80],
            'sg': [1.020, 1.020, 1.010, 1.005, 1.010],
            'al': [1, 0, 2, 4, 2],
            'su': [0, 0, 3, 0, 0],
            'rbc': ['normal', 'normal', 'normal', 'abnormal', 'normal'],
            'pc': ['normal', 'normal', 'normal', 'abnormal', 'normal'],
            'pcc': ['notpresent', 'notpresent', 'notpresent', 'present', 'notpresent'],
            'ba': ['notpresent', 'notpresent', 'notpresent', 'notpresent', 'notpresent'],
            'bgr': [121, 0, 423, 0, 0],
            'bu': [36, 18, 53, 56, 0],
            'sc': [1.2, 0.8, 1.8, 3.8, 0.0],
            'sod': [0, 0, 0, 111, 0],
            'pot': [0, 0, 0, 2.5, 0],
            'hemo': [15.4, 11.3, 9.6, 11.2, 0.0],
            'pcv': [44, 38, 31, 32, 0],
            'wc': [7800, 6000, 0, 0, 0],
            'rc': [5.2, 0, 0, 0, 0],
            'htn': ['yes', 'no', 'yes', 'yes', 'no'],
            'dm': ['yes', 'no', 'no', 'yes', 'no'],
            'cad': ['no', 'no', 'no', 'no', 'no'],
            'appet': ['good', 'good', 'poor', 'poor', 'good'],
            'pe': ['no', 'no', 'yes', 'yes', 'no'],
            'ane': ['no', 'no', 'yes', 'yes', 'no'],
            'classification': ['ckd', 'ckd', 'ckd', 'ckd', 'notckd']
        }
        
        df = pd.DataFrame(data)
        
        # Convert categorical to numerical
        categorical_cols = ['rbc', 'pc', 'pcc', 'ba', 'htn', 'dm', 'cad', 'appet', 'pe', 'ane']
        for col in categorical_cols:
            df[col] = df[col].map({'normal': 0, 'abnormal': 1, 
                                  'notpresent': 0, 'present': 1,
                                  'no': 0, 'yes': 1,
                                  'good': 0, 'poor': 1})
        
        X = df.drop('classification', axis=1)
        y = df['classification'].map({'ckd': 1, 'notckd': 0})
        
        return X, y
    
    def preprocess_data(self, X: pd.DataFrame, y: pd.Series, 
                       test_size: float = 0.2, random_state: int = 42) -> Tuple:
        """Preprocess data for training."""
        # Handle missing values
        X = X.fillna(X.mean())
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        return X_train_scaled, X_test_scaled, y_train, y_test, scaler
    
    def save_scaler(self, scaler: StandardScaler, disease_type: str):
        """Save scaler to file."""
        scaler_dir = os.path.join(settings.BASE_DIR, 'prediction_app', 'ml_models', 'scalers')
        os.makedirs(scaler_dir, exist_ok=True)
        
        scaler_path = os.path.join(scaler_dir, f'{disease_type}_scaler.pkl')
        with open(scaler_path, 'wb') as f:
            pickle.dump(scaler, f)
        
        logger.info(f"Saved scaler to {scaler_path}")
    
    def load_dataset(self, disease_type: str) -> Optional[Tuple[pd.DataFrame, pd.Series]]:
        """Load dataset for specific disease."""
        loaders = {
            'diabetes': self.load_diabetes_data,
            'heart': self.load_heart_data,
            'kidney': self.load_kidney_data,
            # Add other diseases...
        }
        
        if disease_type in loaders:
            return loaders[disease_type]()
        else:
            logger.error(f"No dataset loader for {disease_type}")
            return None
    
    def get_feature_names(self, disease_type: str) -> List[str]:
        """Get feature names for a disease."""
        feature_names = {
            'diabetes': ['Pregnancies', 'Glucose', 'BloodPressure', 'SkinThickness',
                        'Insulin', 'BMI', 'DiabetesPedigreeFunction', 'Age'],
            'heart': ['age', 'sex', 'cp', 'trestbps', 'chol', 'fbs', 'restecg',
                     'thalach', 'exang', 'oldpeak', 'slope', 'ca', 'thal'],
            'kidney': ['age', 'bp', 'sg', 'al', 'su', 'rbc', 'pc', 'pcc', 'ba',
                      'bgr', 'bu', 'sc', 'sod', 'pot', 'hemo', 'pcv', 'wc', 'rc',
                      'htn', 'dm', 'cad', 'appet', 'pe', 'ane'],
        }
        
        return feature_names.get(disease_type, [])
    
    def get_dataset_info(self, disease_type: str) -> Dict[str, Any]:
        """Get information about a dataset."""
        X, y = self.load_dataset(disease_type)
        
        if X is None or y is None:
            return {'error': 'Dataset not available'}
        
        info = {
            'samples': len(X),
            'features': len(X.columns),
            'classes': y.unique().tolist(),
            'class_distribution': y.value_counts().to_dict(),
            'feature_names': X.columns.tolist(),
            'missing_values': X.isnull().sum().to_dict(),
            'data_types': X.dtypes.astype(str).to_dict()
        }
        
        # Add statistical summary
        info['statistics'] = {
            'mean': X.mean().to_dict(),
            'std': X.std().to_dict(),
            'min': X.min().to_dict(),
            'max': X.max().to_dict()
        }
        
        return info
    
    def validate_input_data(self, disease_type: str, input_data: Dict) -> Tuple[bool, List[str]]:
        """Validate input data against dataset schema."""
        X, _ = self.load_dataset(disease_type)
        
        if X is None:
            return False, ['Dataset not available']
        
        errors = []
        
        # Check required features
        required_features = X.columns.tolist()
        for feature in required_features:
            if feature not in input_data:
                errors.append(f"Missing required feature: {feature}")
        
        # Check data types
        for feature, value in input_data.items():
            if feature in X.columns:
                expected_type = X[feature].dtype
                try:
                    # Try to convert to expected type
                    if np.issubdtype(expected_type, np.number):
                        float(value)
                except ValueError:
                    errors.append(f"Feature {feature}: Expected numeric, got {type(value)}")
        
        return len(errors) == 0, errors
    
    def generate_synthetic_data(self, disease_type: str, n_samples: int = 100) -> pd.DataFrame:
        """Generate synthetic data for testing."""
        np.random.seed(42)
        
        if disease_type == 'diabetes':
            data = {
                'Pregnancies': np.random.randint(0, 20, n_samples),
                'Glucose': np.random.normal(120, 30, n_samples).clip(0, 300),
                'BloodPressure': np.random.normal(70, 15, n_samples).clip(0, 200),
                'SkinThickness': np.random.normal(20, 10, n_samples).clip(0, 100),
                'Insulin': np.random.normal(80, 40, n_samples).clip(0, 900),
                'BMI': np.random.normal(25, 5, n_samples).clip(0, 100),
                'DiabetesPedigreeFunction': np.random.exponential(0.5, n_samples).clip(0, 3),
                'Age': np.random.randint(20, 80, n_samples),
            }
        
        elif disease_type == 'heart':
            data = {
                'age': np.random.randint(30, 80, n_samples),
                'sex': np.random.choice([0, 1], n_samples),
                'cp': np.random.choice([0, 1, 2, 3], n_samples),
                'trestbps': np.random.normal(130, 20, n_samples).clip(90, 200),
                'chol': np.random.normal(240, 50, n_samples).clip(100, 600),
                'fbs': np.random.choice([0, 1], n_samples, p=[0.7, 0.3]),
                'restecg': np.random.choice([0, 1, 2], n_samples),
                'thalach': np.random.normal(150, 25, n_samples).clip(60, 220),
                'exang': np.random.choice([0, 1], n_samples, p=[0.6, 0.4]),
                'oldpeak': np.random.exponential(1, n_samples).clip(0, 6),
                'slope': np.random.choice([0, 1, 2], n_samples),
                'ca': np.random.choice([0, 1, 2, 3], n_samples),
                'thal': np.random.choice([0, 1, 2, 3], n_samples),
            }
        
        else:
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        
        # Generate target based on rules
        if disease_type == 'diabetes':
            risk_score = (
                df['Glucose'] / 100 * 0.3 +
                df['BMI'] / 30 * 0.2 +
                df['Age'] / 60 * 0.2 +
                df['DiabetesPedigreeFunction'] * 0.3
            )
            df['Outcome'] = (risk_score > 0.5).astype(int)
        
        elif disease_type == 'heart':
            risk_score = (
                (df['age'] > 50).astype(int) * 0.2 +
                (df['trestbps'] > 140).astype(int) * 0.2 +
                (df['chol'] > 240).astype(int) * 0.2 +
                (df['oldpeak'] > 2).astype(int) * 0.2 +
                df['exang'] * 0.2
            )
            df['target'] = (risk_score > 0.5).astype(int)
        
        return df
    
    def save_dataset(self, disease_type: str, df: pd.DataFrame):
        """Save dataset to CSV file."""
        dataset_path = os.path.join(self.data_dir, f'{disease_type}_dataset.csv')
        df.to_csv(dataset_path, index=False)
        logger.info(f"Saved dataset to {dataset_path}")
    
    def load_saved_dataset(self, disease_type: str) -> Optional[pd.DataFrame]:
        """Load dataset from saved CSV file."""
        dataset_path = os.path.join(self.data_dir, f'{disease_type}_dataset.csv')
        
        if os.path.exists(dataset_path):
            try:
                df = pd.read_csv(dataset_path)
                logger.info(f"Loaded dataset from {dataset_path}")
                return df
            except Exception as e:
                logger.error(f"Failed to load dataset: {e}")
                return None
        else:
            logger.warning(f"Dataset file not found: {dataset_path}")
            return None