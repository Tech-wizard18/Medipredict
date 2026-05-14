"""
Test cases for ML models and utilities in MEDIPREDICT
"""

import os
import json
import pickle
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from django.test import TestCase
from django.conf import settings

from prediction_app.ml_utils import (
    load_model, save_model, predict_disease,
    preprocess_input, validate_input, get_model_info,
    retrain_model, evaluate_model, compare_models
)
from prediction_app.data_loader import (
    load_dataset, preprocess_data, split_data,
    get_feature_importance, generate_synthetic_data
)
from prediction_app.models import DiseaseType, MLModel


class MLUtilsTests(TestCase):
    """Test ML utility functions."""
    
    def setUp(self):
        """Set up test data."""
        # Create a temporary directory for test models
        self.temp_dir = tempfile.mkdtemp()
        self.model_path = Path(self.temp_dir) / 'test_model.pkl'
        self.scaler_path = Path(self.temp_dir) / 'test_scaler.pkl'
        
        # Create a simple model for testing
        self.model = RandomForestClassifier(n_estimators=10, random_state=42)
        X_train = np.random.randn(100, 5)
        y_train = np.random.randint(0, 2, 100)
        self.model.fit(X_train, y_train)
        
        # Create a scaler
        self.scaler = StandardScaler()
        self.scaler.fit(X_train)
        
        # Create disease type
        self.diabetes = DiseaseType.objects.create(
            name='Diabetes',
            code='diabetes',
            input_fields=json.dumps([
                {'name': 'glucose', 'label': 'Glucose', 'type': 'number', 'min': 0, 'max': 200},
                {'name': 'bmi', 'label': 'BMI', 'type': 'number', 'step': '0.1', 'min': 0, 'max': 100},
                {'name': 'age', 'label': 'Age', 'type': 'number', 'min': 0, 'max': 120}
            ])
        )
    
    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_save_and_load_model(self):
        """Test saving and loading a model."""
        # Save model
        save_model(self.model, self.model_path)
        
        # Check file was created
        self.assertTrue(self.model_path.exists())
        
        # Load model
        loaded_model = load_model(self.model_path)
        
        # Check model type
        self.assertIsInstance(loaded_model, RandomForestClassifier)
        
        # Test prediction consistency
        X_test = np.random.randn(10, 5)
        original_pred = self.model.predict(X_test)
        loaded_pred = loaded_model.predict(X_test)
        
        np.testing.assert_array_equal(original_pred, loaded_pred)
    
    def test_save_and_load_scaler(self):
        """Test saving and loading a scaler."""
        # Save scaler
        with open(self.scaler_path, 'wb') as f:
            pickle.dump(self.scaler, f)
        
        # Load scaler
        with open(self.scaler_path, 'rb') as f:
            loaded_scaler = pickle.load(f)
        
        # Test scaling consistency
        X_test = np.random.randn(10, 5)
        original_scaled = self.scaler.transform(X_test)
        loaded_scaled = loaded_scaler.transform(X_test)
        
        np.testing.assert_array_almost_equal(original_scaled, loaded_scaled)
    
    def test_load_model_file_not_found(self):
        """Test loading a model that doesn't exist."""
        non_existent_path = Path(self.temp_dir) / 'non_existent.pkl'
        
        with self.assertRaises(FileNotFoundError):
            load_model(non_existent_path)
    
    def test_load_model_invalid_file(self):
        """Test loading an invalid model file."""
        # Create an invalid pickle file
        with open(self.model_path, 'w') as f:
            f.write('Not a pickle file')
        
        with self.assertRaises(pickle.UnpicklingError):
            load_model(self.model_path)
    
    def test_preprocess_input(self):
        """Test preprocessing input data."""
        # Test data
        input_data = {
            'glucose': 120,
            'bmi': 25.5,
            'age': 35,
            'extra_field': 'should be ignored'
        }
        
        expected_features = ['glucose', 'bmi', 'age']
        
        # Preprocess
        processed = preprocess_input(input_data, self.diabetes)
        
        # Check result
        self.assertIsInstance(processed, np.ndarray)
        self.assertEqual(processed.shape, (1, 3))  # 1 sample, 3 features
        
        # Check values
        self.assertEqual(processed[0, 0], 120)  # glucose
        self.assertEqual(processed[0, 1], 25.5)  # bmi
        self.assertEqual(processed[0, 2], 35)    # age
    
    def test_preprocess_input_missing_values(self):
        """Test preprocessing input with missing values."""
        # Test data with missing required field
        input_data = {
            'glucose': 120,
            'bmi': 25.5
            # age is missing
        }
        
        with self.assertRaises(ValueError) as context:
            preprocess_input(input_data, self.diabetes)
        
        self.assertIn('Missing required field', str(context.exception))
        self.assertIn('age', str(context.exception))
    
    def test_preprocess_input_invalid_values(self):
        """Test preprocessing input with invalid values."""
        # Test data with invalid value (negative age)
        input_data = {
            'glucose': 120,
            'bmi': 25.5,
            'age': -5  # Invalid: negative age
        }
        
        with self.assertRaises(ValueError) as context:
            preprocess_input(input_data, self.diabetes)
        
        self.assertIn('Invalid value', str(context.exception))
        self.assertIn('age', str(context.exception))
    
    def test_preprocess_input_with_scaling(self):
        """Test preprocessing input with scaling."""
        # Test data
        input_data = {
            'glucose': 120,
            'bmi': 25.5,
            'age': 35
        }
        
        # Preprocess with scaling
        processed = preprocess_input(input_data, self.diabetes, scaler=self.scaler)
        
        # Check result
        self.assertIsInstance(processed, np.ndarray)
        self.assertEqual(processed.shape, (1, 3))
        
        # Values should be scaled
        # Since we don't know exact scaling, just check they're different from original
        self.assertNotEqual(processed[0, 0], 120)
    
    def test_validate_input(self):
        """Test input validation."""
        # Valid input
        input_data = {
            'glucose': 120,
            'bmi': 25.5,
            'age': 35
        }
        
        is_valid, errors = validate_input(input_data, self.diabetes)
        
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_validate_input_invalid(self):
        """Test input validation with invalid data."""
        # Invalid input (glucose too high, age negative)
        input_data = {
            'glucose': 300,  # Above max of 200
            'bmi': 25.5,
            'age': -5  # Negative
        }
        
        is_valid, errors = validate_input(input_data, self.diabetes)
        
        self.assertFalse(is_valid)
        self.assertEqual(len(errors), 2)
        
        error_messages = [e['message'] for e in errors]
        self.assertTrue(any('glucose' in msg for msg in error_messages))
        self.assertTrue(any('age' in msg for msg in error_messages))
    
    def test_validate_input_wrong_type(self):
        """Test input validation with wrong data type."""
        # Invalid input (glucose as string)
        input_data = {
            'glucose': 'high',  # Should be number
            'bmi': 25.5,
            'age': 35
        }
        
        is_valid, errors = validate_input(input_data, self.diabetes)
        
        self.assertFalse(is_valid)
        self.assertEqual(len(errors), 1)
        self.assertIn('glucose', errors[0]['message'])
        self.assertIn('number', errors[0]['message'])
    
    def test_predict_disease(self):
        """Test disease prediction."""
        # Mock model
        mock_model = MagicMock()
        mock_model.predict.return_value = [1]
        mock_model.predict_proba.return_value = [[0.2, 0.8]]
        
        # Test data
        input_data = {
            'glucose': 120,
            'bmi': 25.5,
            'age': 35
        }
        
        # Make prediction
        result = predict_disease(
            model=mock_model,
            input_data=input_data,
            disease_type=self.diabetes
        )
        
        # Check result structure
        self.assertIsInstance(result, dict)
        self.assertIn('prediction', result)
        self.assertIn('probability', result)
        self.assertIn('confidence', result)
        self.assertIn('risk_level', result)
        self.assertIn('input_data', result)
        
        # Check values
        self.assertEqual(result['prediction'], True)  # 1 = True
        self.assertEqual(result['probability'], 0.8)
        self.assertEqual(result['confidence'], 0.8)
        self.assertEqual(result['risk_level'], 'High')
    
    def test_predict_disease_with_scaler(self):
        """Test disease prediction with scaling."""
        # Mock model and scaler
        mock_model = MagicMock()
        mock_model.predict.return_value = [0]
        mock_model.predict_proba.return_value = [[0.7, 0.3]]
        
        mock_scaler = MagicMock()
        mock_scaler.transform.return_value = np.array([[0.5, 0.2, 0.3]])
        
        # Test data
        input_data = {
            'glucose': 90,
            'bmi': 22.0,
            'age': 25
        }
        
        # Make prediction with scaler
        result = predict_disease(
            model=mock_model,
            input_data=input_data,
            disease_type=self.diabetes,
            scaler=mock_scaler
        )
        
        # Check scaler was called
        mock_scaler.transform.assert_called_once()
        
        # Check result
        self.assertEqual(result['prediction'], False)  # 0 = False
        self.assertEqual(result['probability'], 0.3)
        self.assertEqual(result['confidence'], 0.7)  # Confidence for negative class
        self.assertEqual(result['risk_level'], 'Low')
    
    def test_get_model_info(self):
        """Test getting model information."""
        # Create an MLModel instance
        mlmodel = MLModel.objects.create(
            disease_type=self.diabetes,
            name='Test Model',
            version='1.0.0',
            accuracy=0.85,
            precision=0.82,
            recall=0.87,
            f1_score=0.84,
            roc_auc=0.89,
            algorithm='random_forest',
            features=['glucose', 'bmi', 'age'],
            is_active=True
        )
        
        # Get model info
        info = get_model_info(mlmodel)
        
        # Check info structure
        self.assertIsInstance(info, dict)
        self.assertEqual(info['name'], 'Test Model')
        self.assertEqual(info['version'], '1.0.0')
        self.assertEqual(info['accuracy'], 0.85)
        self.assertEqual(info['algorithm'], 'random_forest')
        self.assertEqual(info['features'], ['glucose', 'bmi', 'age'])
        self.assertTrue(info['is_active'])
    
    @patch('prediction_app.ml_utils.load_model')
    @patch('prediction_app.ml_utils.save_model')
    def test_retrain_model(self, mock_save_model, mock_load_model):
        """Test model retraining."""
        # Mock data
        X_train = np.random.randn(100, 5)
        y_train = np.random.randint(0, 2, 100)
        X_test = np.random.randn(20, 5)
        y_test = np.random.randint(0, 2, 20)
        
        # Mock model
        mock_original_model = MagicMock()
        mock_retrained_model = MagicMock()
        
        mock_original_model.fit.return_value = None
        mock_original_model.predict.return_value = y_test
        mock_original_model.predict_proba.return_value = np.random.rand(20, 2)
        
        mock_load_model.return_value = mock_original_model
        
        # Mock metrics
        with patch('prediction_app.ml_utils.evaluate_model') as mock_evaluate:
            mock_evaluate.return_value = {
                'accuracy': 0.88,
                'precision': 0.85,
                'recall': 0.90,
                'f1_score': 0.875,
                'roc_auc': 0.92
            }
            
            # Retrain model
            result = retrain_model(
                model_path=self.model_path,
                X_train=X_train,
                y_train=y_train,
                X_test=X_test,
                y_test=y_test,
                save_path=self.model_path
            )
        
        # Check result
        self.assertIsInstance(result, dict)
        self.assertIn('accuracy', result)
        self.assertIn('precision', result)
        self.assertIn('model_path', result)
        
        self.assertEqual(result['accuracy'], 0.88)
        
        # Check model was saved
        mock_save_model.assert_called_once()
    
    def test_evaluate_model(self):
        """Test model evaluation."""
        # Create mock model
        mock_model = MagicMock()
        
        # Test data
        X_test = np.random.randn(20, 5)
        y_test = np.random.randint(0, 2, 20)
        
        # Mock predictions
        y_pred = y_test.copy()
        y_pred[0] = 1 - y_pred[0]  # Make one prediction wrong
        
        y_pred_proba = np.random.rand(20, 2)
        
        mock_model.predict.return_value = y_pred
        mock_model.predict_proba.return_value = y_pred_proba
        
        # Evaluate model
        metrics = evaluate_model(mock_model, X_test, y_test)
        
        # Check metrics structure
        self.assertIsInstance(metrics, dict)
        self.assertIn('accuracy', metrics)
        self.assertIn('precision', metrics)
        self.assertIn('recall', metrics)
        self.assertIn('f1_score', metrics)
        self.assertIn('roc_auc', metrics)
        self.assertIn('confusion_matrix', metrics)
        self.assertIn('classification_report', metrics)
        
        # Check metric values are between 0 and 1
        self.assertGreaterEqual(metrics['accuracy'], 0)
        self.assertLessEqual(metrics['accuracy'], 1)
        self.assertGreaterEqual(metrics['precision'], 0)
        self.assertLessEqual(metrics['precision'], 1)
    
    def test_compare_models(self):
        """Test model comparison."""
        # Create mock models
        model1 = MagicMock()
        model2 = MagicMock()
        
        # Test data
        X_test = np.random.randn(20, 5)
        y_test = np.random.randint(0, 2, 20)
        
        # Mock predictions
        y_pred1 = y_test.copy()
        y_pred2 = y_test.copy()
        y_pred2[0:3] = 1 - y_pred2[0:3]  # Make model2 worse
        
        y_pred_proba = np.random.rand(20, 2)
        
        model1.predict.return_value = y_pred1
        model1.predict_proba.return_value = y_pred_proba
        
        model2.predict.return_value = y_pred2
        model2.predict_proba.return_value = y_pred_proba
        
        # Compare models
        comparison = compare_models(
            models={'Model1': model1, 'Model2': model2},
            X_test=X_test,
            y_test=y_test
        )
        
        # Check comparison structure
        self.assertIsInstance(comparison, dict)
        self.assertIn('Model1', comparison)
        self.assertIn('Model2', comparison)
        self.assertIn('best_model', comparison)
        
        # Model1 should be better (perfect predictions)
        self.assertEqual(comparison['best_model'], 'Model1')
        
        # Check metrics for each model
        self.assertIn('accuracy', comparison['Model1'])
        self.assertIn('accuracy', comparison['Model2'])
        
        # Model1 should have higher accuracy
        self.assertGreater(
            comparison['Model1']['accuracy'],
            comparison['Model2']['accuracy']
        )


class DataLoaderTests(TestCase):
    """Test data loading and preprocessing functions."""
    
    def setUp(self):
        """Set up test data."""
        # Create a temporary CSV file for testing
        self.temp_dir = tempfile.mkdtemp()
        self.csv_path = Path(self.temp_dir) / 'test_data.csv'
        
        # Create test data
        data = {
            'age': [25, 30, 35, 40, 45, 50, 55, 60, 65, 70],
            'glucose': [80, 85, 90, 95, 100, 105, 110, 115, 120, 125],
            'bmi': [20.0, 21.0, 22.0, 23.0, 24.0, 25.0, 26.0, 27.0, 28.0, 29.0],
            'blood_pressure': [70, 72, 74, 76, 78, 80, 82, 84, 86, 88],
            'target': [0, 0, 0, 0, 0, 1, 1, 1, 1, 1]  # Binary target
        }
        
        df = pd.DataFrame(data)
        df.to_csv(self.csv_path, index=False)
    
    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_load_dataset_csv(self):
        """Test loading dataset from CSV."""
        df = load_dataset(self.csv_path)
        
        # Check DataFrame
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(df.shape, (10, 5))  # 10 samples, 5 columns
        self.assertEqual(list(df.columns), ['age', 'glucose', 'bmi', 'blood_pressure', 'target'])
    
    def test_load_dataset_file_not_found(self):
        """Test loading dataset from non-existent file."""
        non_existent_path = Path(self.temp_dir) / 'non_existent.csv'
        
        with self.assertRaises(FileNotFoundError):
            load_dataset(non_existent_path)
    
    def test_load_dataset_invalid_file(self):
        """Test loading invalid dataset file."""
        # Create an invalid file
        invalid_path = Path(self.temp_dir) / 'invalid.txt'
        with open(invalid_path, 'w') as f:
            f.write('Not a valid CSV file')
        
        with self.assertRaises(pd.errors.ParserError):
            load_dataset(invalid_path)
    
    def test_preprocess_data(self):
        """Test data preprocessing."""
        # Load data
        df = load_dataset(self.csv_path)
        
        # Preprocess
        processed_df = preprocess_data(df, target_column='target')
        
        # Check preprocessing
        self.assertIsInstance(processed_df, pd.DataFrame)
        self.assertEqual(processed_df.shape[0], df.shape[0])  # Same number of samples
        
        # Check no missing values
        self.assertFalse(processed_df.isnull().any().any())
        
        # Check no duplicates
        self.assertEqual(processed_df.duplicated().sum(), 0)
    
    def test_preprocess_data_with_missing_values(self):
        """Test data preprocessing with missing values."""
        # Create data with missing values
        data = {
            'age': [25, 30, None, 40, 45],
            'glucose': [80, 85, 90, None, 100],
            'target': [0, 0, 1, 1, 0]
        }
        
        df = pd.DataFrame(data)
        
        # Preprocess
        processed_df = preprocess_data(df, target_column='target')
        
        # Check missing values were filled
        self.assertFalse(processed_df.isnull().any().any())
        
        # Age missing value should be filled with median
        self.assertEqual(processed_df['age'].iloc[2], df['age'].median())
    
    def test_preprocess_data_with_duplicates(self):
        """Test data preprocessing with duplicates."""
        # Create data with duplicates
        data = {
            'age': [25, 25, 30, 30, 35],
            'glucose': [80, 80, 85, 85, 90],
            'target': [0, 0, 1, 1, 0]
        }
        
        df = pd.DataFrame(data)
        
        # Preprocess
        processed_df = preprocess_data(df, target_column='target')
        
        # Check duplicates were removed
        self.assertEqual(processed_df.duplicated().sum(), 0)
        self.assertEqual(processed_df.shape[0], 3)  # Only 3 unique rows
    
    def test_split_data(self):
        """Test data splitting."""
        # Create data
        X = np.random.randn(100, 5)
        y = np.random.randint(0, 2, 100)
        
        # Split data
        X_train, X_test, y_train, y_test = split_data(X, y, test_size=0.2, random_state=42)
        
        # Check shapes
        self.assertEqual(X_train.shape[0], 80)
        self.assertEqual(X_test.shape[0], 20)
        self.assertEqual(y_train.shape[0], 80)
        self.assertEqual(y_test.shape[0], 20)
        
        # Check no data leakage
        self.assertFalse(np.array_equal(X_train, X_test))
        
        # Check stratification (if supported)
        # For binary classification, class proportions should be similar
        train_prop = np.mean(y_train)
        test_prop = np.mean(y_test)
        self.assertAlmostEqual(train_prop, test_prop, delta=0.1)
    
    def test_get_feature_importance(self):
        """Test feature importance calculation."""
        # Create a model
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        
        # Create data
        X = np.random.randn(100, 5)
        y = np.random.randint(0, 2, 100)
        
        # Train model
        model.fit(X, y)
        
        # Get feature importance
        feature_names = [f'feature_{i}' for i in range(5)]
        importance_df = get_feature_importance(model, feature_names)
        
        # Check result
        self.assertIsInstance(importance_df, pd.DataFrame)
        self.assertEqual(importance_df.shape[0], 5)  # 5 features
        self.assertEqual(list(importance_df.columns), ['feature', 'importance'])
        
        # Check importance values are between 0 and 1
        self.assertTrue((importance_df['importance'] >= 0).all())
        self.assertTrue((importance_df['importance'] <= 1).all())
        
        # Sum of importances should be approximately 1
        self.assertAlmostEqual(importance_df['importance'].sum(), 1.0, places=2)
    
    def test_generate_synthetic_data(self):
        """Test synthetic data generation."""
        # Generate synthetic data
        n_samples = 100
        n_features = 5
        target_proportion = 0.3  # 30% positive
        
        X, y = generate_synthetic_data(
            n_samples=n_samples,
            n_features=n_features,
            target_proportion=target_proportion,
            random_state=42
        )
        
        # Check shapes
        self.assertEqual(X.shape, (n_samples, n_features))
        self.assertEqual(y.shape, (n_samples,))
        
        # Check target proportion
        actual_proportion = np.mean(y)
        self.assertAlmostEqual(actual_proportion, target_proportion, delta=0.05)
        
        # Check data ranges (should be roughly normal)
        self.assertGreater(np.mean(X), -1)
        self.assertLess(np.mean(X), 1)
        self.assertGreater(np.std(X), 0.5)
        self.assertLess(np.std(X), 1.5)


class ModelTrainingTests(TestCase):
    """Test model training functions."""
    
    def setUp(self):
        """Set up test data."""
        self.diabetes = DiseaseType.objects.create(
            name='Diabetes',
            code='diabetes'
        )
    
    @patch('prediction_app.ml_utils.RandomForestClassifier')
    @patch('prediction_app.ml_utils.train_test_split')
    @patch('prediction_app.data_loader.load_dataset')
    def test_train_diabetes_model(self, mock_load_dataset, mock_split, mock_rf):
        """Test diabetes model training."""
        # Mock data
        mock_data = pd.DataFrame({
            'Pregnancies': [1, 2, 3, 4, 5],
            'Glucose': [100, 120, 140, 160, 180],
            'BloodPressure': [70, 80, 90, 100, 110],
            'SkinThickness': [20, 25, 30, 35, 40],
            'Insulin': [80, 100, 120, 140, 160],
            'BMI': [20.0, 22.0, 24.0, 26.0, 28.0],
            'DiabetesPedigreeFunction': [0.2, 0.4, 0.6, 0.8, 1.0],
            'Age': [25, 30, 35, 40, 45],
            'Outcome': [0, 0, 1, 1, 1]
        })
        
        mock_load_dataset.return_value = mock_data
        
        # Mock split
        X_train = np.random.randn(4, 8)
        X_test = np.random.randn(1, 8)
        y_train = np.array([0, 0, 1, 1])
        y_test = np.array([1])
        
        mock_split.return_value = (X_train, X_test, y_train, y_test)
        
        # Mock model
        mock_model = MagicMock()
        mock_model.fit.return_value = None
        mock_model.predict.return_value = y_test
        mock_model.predict_proba.return_value = np.array([[0.3, 0.7]])
        
        mock_rf.return_value = mock_model
        
        # Mock scaler
        with patch('prediction_app.ml_utils.StandardScaler') as mock_scaler_class:
            mock_scaler = MagicMock()
            mock_scaler.fit.return_value = None
            mock_scaler.transform.return_value = X_train
            mock_scaler_class.return_value = mock_scaler
            
            # Mock save functions
            with patch('prediction_app.ml_utils.save_model') as mock_save_model:
                with patch('prediction_app.ml_utils.pickle.dump') as mock_pickle:
                    # Import the training function
                    from scripts.train_models import ModelTrainer
                    
                    trainer = ModelTrainer()
                    
                    # Mock the model directory
                    with patch.object(trainer, 'models_dir', Path(self.diabetes.code)):
                        # Train model
                        metrics = trainer.train_for_disease('diabetes')
        
        # Check metrics were returned
        self.assertIsInstance(metrics, dict)
        self.assertIn('Random Forest', metrics)
        
        # Check model was saved
        mock_save_model.assert_called_once()
    
    def test_model_hyperparameter_tuning(self):
        """Test model hyperparameter tuning."""
        from sklearn.model_selection import GridSearchCV
        
        # Create a simple model
        model = RandomForestClassifier(random_state=42)
        
        # Define parameter grid
        param_grid = {
            'n_estimators': [10, 50, 100],
            'max_depth': [None, 10, 20],
            'min_samples_split': [2, 5, 10]
        }
        
        # Create data
        X = np.random.randn(100, 5)
        y = np.random.randint(0, 2, 100)
        
        # Perform grid search
        grid_search = GridSearchCV(
            estimator=model,
            param_grid=param_grid,
            cv=3,
            scoring='accuracy',
            n_jobs=-1,
            verbose=0
        )
        
        grid_search.fit(X, y)
        
        # Check results
        self.assertIsNotNone(grid_search.best_params_)
        self.assertIsNotNone(grid_search.best_score_)
        self.assertIsNotNone(grid_search.best_estimator_)
        
        # Best score should be reasonable
        self.assertGreaterEqual(grid_search.best_score_, 0.0)
        self.assertLessEqual(grid_search.best_score_, 1.0)
    
    def test_model_cross_validation(self):
        """Test model cross-validation."""
        from sklearn.model_selection import cross_val_score
        
        # Create a model
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        
        # Create data
        X = np.random.randn(100, 5)
        y = np.random.randint(0, 2, 100)
        
        # Perform cross-validation
        cv_scores = cross_val_score(
            estimator=model,
            X=X,
            y=y,
            cv=5,
            scoring='accuracy'
        )
        
        # Check results
        self.assertEqual(len(cv_scores), 5)
        
        # All scores should be between 0 and 1
        self.assertTrue((cv_scores >= 0).all())
        self.assertTrue((cv_scores <= 1).all())
        
        # Mean and std should be reasonable
        mean_score = cv_scores.mean()
        std_score = cv_scores.std()
        
        self.assertGreaterEqual(mean_score, 0.0)
        self.assertLessEqual(mean_score, 1.0)
        self.assertGreaterEqual(std_score, 0.0)
        self.assertLessEqual(std_score, 0.5)
    
    def test_model_ensemble(self):
        """Test model ensemble techniques."""
        from sklearn.ensemble import VotingClassifier
        from sklearn.linear_model import LogisticRegression
        from sklearn.svm import SVC
        
        # Create individual models
        model1 = LogisticRegression(random_state=42, max_iter=1000)
        model2 = RandomForestClassifier(n_estimators=10, random_state=42)
        model3 = SVC(probability=True, random_state=42)
        
        # Create ensemble
        ensemble = VotingClassifier(
            estimators=[
                ('lr', model1),
                ('rf', model2),
                ('svc', model3)
            ],
            voting='soft'  # Use probabilities
        )
        
        # Create data
        X = np.random.randn(100, 5)
        y = np.random.randint(0, 2, 100)
        
        # Train ensemble
        ensemble.fit(X, y)
        
        # Make predictions
        y_pred = ensemble.predict(X)
        y_pred_proba = ensemble.predict_proba(X)
        
        # Check predictions
        self.assertEqual(y_pred.shape, (100,))
        self.assertEqual(y_pred_proba.shape, (100, 2))
        
        # Check probabilities sum to 1
        prob_sums = y_pred_proba.sum(axis=1)
        np.testing.assert_array_almost_equal(prob_sums, np.ones(100))
    
    def test_model_persistence(self):
        """Test model persistence (save/load)."""
        import joblib
        
        # Create a model
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        
        # Create data
        X = np.random.randn(100, 5)
        y = np.random.randint(0, 2, 100)
        
        # Train model
        model.fit(X, y)
        
        # Save model
        with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as f:
            model_path = f.name
            joblib.dump(model, model_path)
        
        try:
            # Load model
            loaded_model = joblib.load(model_path)
            
            # Check predictions match
            X_test = np.random.randn(10, 5)
            original_pred = model.predict(X_test)
            loaded_pred = loaded_model.predict(X_test)
            
            np.testing.assert_array_equal(original_pred, loaded_pred)
            
            # Check probabilities match
            original_proba = model.predict_proba(X_test)
            loaded_proba = loaded_model.predict_proba(X_test)
            
            np.testing.assert_array_almost_equal(original_proba, loaded_proba)
            
        finally:
            # Clean up
            os.unlink(model_path)


class ModelEvaluationTests(TestCase):
    """Test model evaluation functions."""
    
    def test_confusion_matrix_calculation(self):
        """Test confusion matrix calculation."""
        from sklearn.metrics import confusion_matrix
        
        # True labels and predictions
        y_true = [0, 1, 0, 1, 0, 1, 0, 1]
        y_pred = [0, 1, 0, 0, 1, 1, 0, 1]
        
        # Calculate confusion matrix
        cm = confusion_matrix(y_true, y_pred)
        
        # Check shape
        self.assertEqual(cm.shape, (2, 2))
        
        # Check values
        # True Negatives: positions where both are 0
        tn = cm[0, 0]
        self.assertEqual(tn, 3)  # Indices 0, 2, 6
        
        # False Positives: predicted 1 but actually 0
        fp = cm[0, 1]
        self.assertEqual(fp, 1)  # Index 4
        
        # False Negatives: predicted 0 but actually 1
        fn = cm[1, 0]
        self.assertEqual(fn, 1)  # Index 3
        
        # True Positives: both are 1
        tp = cm[1, 1]
        self.assertEqual(tp, 3)  # Indices 1, 5, 7
    
    def test_classification_report(self):
        """Test classification report generation."""
        from sklearn.metrics import classification_report
        
        # True labels and predictions
        y_true = [0, 1, 0, 1, 0, 1, 0, 1]
        y_pred = [0, 1, 0, 0, 1, 1, 0, 1]
        
        # Generate classification report
        report = classification_report(y_true, y_pred, output_dict=True)
        
        # Check report structure
        self.assertIn('0', report)
        self.assertIn('1', report)
        self.assertIn('accuracy', report)
        self.assertIn('macro avg', report)
        self.assertIn('weighted avg', report)
        
        # Check metrics for class 0
        class0 = report['0']
        self.assertIn('precision', class0)
        self.assertIn('recall', class0)
        self.assertIn('f1-score', class0)
        self.assertIn('support', class0)
        
        # Check values (approximately)
        # Precision for class 0: TP / (TP + FP) = 3 / (3 + 1) = 0.75
        self.assertAlmostEqual(class0['precision'], 0.75, places=2)
        
        # Recall for class 0: TP / (TP + FN) = 3 / (3 + 1) = 0.75
        self.assertAlmostEqual(class0['recall'], 0.75, places=2)
        
        # F1-score: 2 * (precision * recall) / (precision + recall) = 0.75
        self.assertAlmostEqual(class0['f1-score'], 0.75, places=2)
    
    def test_roc_auc_calculation(self):
        """Test ROC AUC calculation."""
        from sklearn.metrics import roc_auc_score
        
        # True labels and predicted probabilities
        y_true = [0, 0, 1, 1]
        y_scores = [0.1, 0.4, 0.35, 0.8]
        
        # Calculate ROC AUC
        roc_auc = roc_auc_score(y_true, y_scores)
        
        # Check value (should be between 0 and 1)
        self.assertGreaterEqual(roc_auc, 0.0)
        self.assertLessEqual(roc_auc, 1.0)
        
        # For this data, AUC should be 0.75
        # Let's verify manually:
        # At threshold 0.1: TP=2, FP=1, TN=1, FN=0 → TPR=1, FPR=0.5
        # At threshold 0.35: TP=1, FP=1, TN=1, FN=1 → TPR=0.5, FPR=0.5
        # At threshold 0.4: TP=1, FP=0, TN=2, FN=1 → TPR=0.5, FPR=0
        # At threshold 0.8: TP=0, FP=0, TN=2, FN=2 → TPR=0, FPR=0
        # Area under this ROC curve is 0.75
        
        self.assertAlmostEqual(roc_auc, 0.75, places=2)
    
    def test_precision_recall_curve(self):
        """Test precision-recall curve calculation."""
        from sklearn.metrics import precision_recall_curve, auc
        
        # True labels and predicted probabilities
        y_true = [0, 0, 1, 1]
        y_scores = [0.1, 0.4, 0.35, 0.8]
        
        # Calculate precision-recall curve
        precision, recall, thresholds = precision_recall_curve(y_true, y_scores)
        
        # Check shapes
        self.assertEqual(len(precision), len(recall))
        self.assertEqual(len(thresholds), len(precision) - 1)
        
        # Precision and recall should be between 0 and 1
        self.assertTrue((precision >= 0).all() and (precision <= 1).all())
        self.assertTrue((recall >= 0).all() and (recall <= 1).all())
        
        # Calculate area under PR curve
        pr_auc = auc(recall, precision)
        
        # Check AUC value
        self.assertGreaterEqual(pr_auc, 0.0)
        self.assertLessEqual(pr_auc, 1.0)
    
    def test_calibration_curve(self):
        """Test calibration curve calculation."""
        from sklearn.calibration import calibration_curve
        
        # True labels and predicted probabilities
        y_true = [0, 0, 1, 1, 0, 1, 0, 1]
        y_prob = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
        
        # Calculate calibration curve
        prob_true, prob_pred = calibration_curve(y_true, y_prob, n_bins=3)
        
        # Check shapes
        self.assertEqual(len(prob_true), 3)
        self.assertEqual(len(prob_pred), 3)
        
        # Values should be between 0 and 1
        self.assertTrue((prob_true >= 0).all() and (prob_true <= 1).all())
        self.assertTrue((prob_pred >= 0).all() and (prob_pred <= 1).all())


class ModelDeploymentTests(TestCase):
    """Test model deployment and serving functions."""
    
    def setUp(self):
        """Set up test data."""
        self.diabetes = DiseaseType.objects.create(
            name='Diabetes',
            code='diabetes'
        )
    
    @patch('prediction_app.ml_utils.load_model')
    def test_model_serving_pipeline(self, mock_load_model):
        """Test end-to-end model serving pipeline."""
        # Mock model
        mock_model = MagicMock()
        mock_model.predict.return_value = [1]
        mock_model.predict_proba.return_value = [[0.2, 0.8]]
        mock_load_model.return_value = mock_model
        
        # Input data
        input_data = {
            'glucose': 130,
            'bmi': 28.5,
            'age': 45
        }
        
        # Load model
        model = load_model('dummy_path.pkl')
        
        # Preprocess input
        processed_input = np.array([[130, 28.5, 45]])
        
        # Make prediction
        prediction = model.predict(processed_input)[0]
        probability = model.predict_proba(processed_input)[0][1]
        
        # Check results
        self.assertEqual(prediction, 1)
        self.assertEqual(probability, 0.8)
        
        # Calculate confidence and risk level
        confidence = probability if prediction == 1 else 1 - probability
        
        if prediction == 1:
            if confidence >= 0.8:
                risk_level = 'High'
            elif confidence >= 0.6:
                risk_level = 'Medium'
            else:
                risk_level = 'Low'
        else:
            risk_level = 'Negative'
        
        self.assertEqual(confidence, 0.8)
        self.assertEqual(risk_level, 'High')
    
    def test_batch_prediction(self):
        """Test batch prediction."""
        # Create a simple model
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        
        # Create training data
        X_train = np.random.randn(100, 5)
        y_train = np.random.randint(0, 2, 100)
        
        # Train model
        model.fit(X_train, y_train)
        
        # Create batch data
        X_batch = np.random.randn(50, 5)
        
        # Make batch predictions
        batch_predictions = model.predict(X_batch)
        batch_probabilities = model.predict_proba(X_batch)
        
        # Check results
        self.assertEqual(batch_predictions.shape, (50,))
        self.assertEqual(batch_probabilities.shape, (50, 2))
        
        # Each prediction should be 0 or 1
        self.assertTrue(np.all(np.isin(batch_predictions, [0, 1])))
        
        # Probabilities should sum to 1 for each sample
        prob_sums = batch_probabilities.sum(axis=1)
        np.testing.assert_array_almost_equal(prob_sums, np.ones(50))
    
    @patch('prediction_app.ml_utils.requests.post')
    def test_model_api_endpoint(self, mock_post):
        """Test model API endpoint call."""
        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'prediction': True,
            'probability': 0.85,
            'confidence': 0.85,
            'risk_level': 'High'
        }
        mock_post.return_value = mock_response
        
        # Test data
        input_data = {
            'glucose': 130,
            'bmi': 28.5,
            'age': 45
        }
        
        # Call API
        import requests
        response = requests.post(
            'http://localhost:8000/api/predict/diabetes/',
            json=input_data,
            headers={'Content-Type': 'application/json'}
        )
        
        # Check response
        self.assertEqual(response.status_code, 200)
        
        result = response.json()
        self.assertEqual(result['prediction'], True)
        self.assertEqual(result['probability'], 0.85)
        self.assertEqual(result['confidence'], 0.85)
        self.assertEqual(result['risk_level'], 'High')
        
        # Verify API was called with correct data
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], 'http://localhost:8000/api/predict/diabetes/')
        self.assertEqual(call_args[1]['json'], input_data)
    
    def test_model_monitoring_metrics(self):
        """Test model monitoring metrics calculation."""
        # Create predictions and true labels
        y_true = [0, 1, 0, 1, 0, 1, 0, 1, 0, 1]
        y_pred = [0, 1, 0, 0, 1, 1, 0, 1, 0, 1]
        y_prob = [0.1, 0.9, 0.2, 0.4, 0.6, 0.8, 0.3, 0.7, 0.2, 0.9]
        
        from sklearn.metrics import (
            accuracy_score, precision_score, recall_score,
            f1_score, roc_auc_score
        )
        
        # Calculate metrics
        accuracy = accuracy_score(y_true, y_pred)
        precision = precision_score(y_true, y_pred, zero_division=0)
        recall = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)
        roc_auc = roc_auc_score(y_true, y_prob)
        
        # Check metrics
        self.assertAlmostEqual(accuracy, 0.8, places=2)  # 8 correct out of 10
        self.assertAlmostEqual(precision, 0.8, places=2)  # 4 TP out of 5 predicted positive
        self.assertAlmostEqual(recall, 0.8, places=2)     # 4 TP out of 5 actual positive
        self.assertAlmostEqual(f1, 0.8, places=2)        # Harmonic mean of precision and recall
        self.assertGreaterEqual(roc_auc, 0.0)
        self.assertLessEqual(roc_auc, 1.0)
    
    def test_model_drift_detection(self):
        """Test model drift detection."""
        # Create reference and current data distributions
        np.random.seed(42)
        
        # Reference data (training distribution)
        reference_data = np.random.normal(loc=0, scale=1, size=1000)
        
        # Current data (similar distribution)
        current_data_similar = np.random.normal(loc=0, scale=1, size=1000)
        
        # Current data (drifted distribution)
        current_data_drifted = np.random.normal(loc=1, scale=1, size=1000)
        
        # Calculate statistical tests
        from scipy import stats
        
        # KS test for similar distributions
        ks_stat_similar, ks_p_similar = stats.ks_2samp(reference_data, current_data_similar)
        
        # KS test for drifted distributions
        ks_stat_drifted, ks_p_drifted = stats.ks_2samp(reference_data, current_data_drifted)
        
        # Check results
        # Similar distributions should have high p-value (not significantly different)
        self.assertGreater(ks_p_similar, 0.05)
        
        # Drifted distributions should have low p-value (significantly different)
        self.assertLess(ks_p_drifted, 0.05)
        
        # Drifted distributions should have higher KS statistic
        self.assertGreater(ks_stat_drifted, ks_stat_similar)


class IntegrationTests(TestCase):
    """Test integration between ML models and Django."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='patient@example.com',
            password='testpass123',
            user_type='patient'
        )
        
        self.diabetes = DiseaseType.objects.create(
            name='Diabetes',
            code='diabetes',
            input_fields=json.dumps([
                {'name': 'glucose', 'label': 'Glucose', 'type': 'number'},
                {'name': 'bmi', 'label': 'BMI', 'type': 'number'},
                {'name': 'age', 'label': 'Age', 'type': 'number'}
            ])
        )
        
        self.ml_model = MLModel.objects.create(
            disease_type=self.diabetes,
            name='Test Model',
            version='1.0.0',
            accuracy=0.85,
            path='models/diabetes_model.pkl',
            is_active=True
        )
    
    @patch('prediction_app.ml_utils.load_model')
    @patch('prediction_app.ml_utils.preprocess_input')
    def test_prediction_workflow_integration(self, mock_preprocess, mock_load_model):
        """Test complete prediction workflow integration."""
        # Mock dependencies
        mock_model = MagicMock()
        mock_model.predict.return_value = [1]
        mock_model.predict_proba.return_value = [[0.2, 0.8]]
        mock_load_model.return_value = mock_model
        
        mock_preprocess.return_value = np.array([[120, 25.5, 35]])
        
        # Input data
        input_data = {
            'glucose': 120,
            'bmi': 25.5,
            'age': 35
        }
        
        # Load model
        model = load_model(self.ml_model.path)
        
        # Preprocess input
        processed_input = preprocess_input(input_data, self.diabetes)
        
        # Make prediction
        prediction = model.predict(processed_input)[0]
        probability = model.predict_proba(processed_input)[0][1]
        
        # Create Prediction record
        prediction_record = Prediction.objects.create(
            user=self.user,
            disease_type=self.diabetes,
            ml_model=self.ml_model,
            input_data=input_data,
            prediction_result={
                'has_disease': bool(prediction),
                'probability': float(probability)
            },
            confidence_score=float(probability) if prediction == 1 else 1 - float(probability),
            is_positive=bool(prediction)
        )
        
        # Check prediction record
        self.assertIsNotNone(prediction_record.id)
        self.assertEqual(prediction_record.user, self.user)
        self.assertEqual(prediction_record.disease_type, self.diabetes)
        self.assertEqual(prediction_record.ml_model, self.ml_model)
        self.assertEqual(prediction_record.input_data, input_data)
        self.assertTrue(prediction_record.is_positive)
        
        # Check risk level
        risk_level = prediction_record.get_risk_level()
        self.assertEqual(risk_level, 'High')  # probability 0.8
        
        # Verify mocks were called
        mock_load_model.assert_called_once_with(self.ml_model.path)
        mock_preprocess.assert_called_once_with(input_data, self.diabetes, scaler=None)
    
    def test_model_versioning(self):
        """Test ML model versioning."""
        # Create multiple versions of the same model
        model_v1 = MLModel.objects.create(
            disease_type=self.diabetes,
            name='Diabetes Model',
            version='1.0.0',
            accuracy=0.85,
            is_active=False
        )
        
        model_v2 = MLModel.objects.create(
            disease_type=self.diabetes,
            name='Diabetes Model',
            version='1.1.0',
            accuracy=0.87,
            is_active=True
        )
        
        model_v3 = MLModel.objects.create(
            disease_type=self.diabetes,
            name='Diabetes Model',
            version='2.0.0',
            accuracy=0.90,
            is_active=True
        )
        
        # Get active models for diabetes
        active_models = MLModel.objects.filter(
            disease_type=self.diabetes,
            is_active=True
        )
        
        self.assertEqual(active_models.count(), 2)
        
        # Get best model
        best_model = active_models.order_by('-accuracy').first()
        self.assertEqual(best_model, model_v3)
        self.assertEqual(best_model.version, '2.0.0')
        self.assertEqual(best_model.accuracy, 0.90)
    
    def test_prediction_statistics_aggregation(self):
        """Test prediction statistics aggregation."""
        # Create predictions with different outcomes
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
        
        Prediction.objects.create(
            user=self.user,
            disease_type=self.diabetes,
            ml_model=self.ml_model,
            is_positive=True,
            confidence_score=0.75
        )
        
        # Calculate statistics
        total_predictions = Prediction.objects.filter(user=self.user).count()
        positive_predictions = Prediction.objects.filter(user=self.user, is_positive=True).count()
        negative_predictions = Prediction.objects.filter(user=self.user, is_positive=False).count()
        average_confidence = Prediction.objects.filter(user=self.user).aggregate(
            avg_confidence=models.Avg('confidence_score')
        )['avg_confidence']
        
        # Check statistics
        self.assertEqual(total_predictions, 3)
        self.assertEqual(positive_predictions, 2)
        self.assertEqual(negative_predictions, 1)
        self.assertAlmostEqual(average_confidence, (0.85 + 0.90 + 0.75) / 3, places=2)
        
        # Disease-specific statistics
        diabetes_stats = Prediction.objects.filter(
            user=self.user,
            disease_type=self.diabetes
        ).aggregate(
            total=models.Count('id'),
            positive=models.Count('id', filter=models.Q(is_positive=True)),
            negative=models.Count('id', filter=models.Q(is_positive=False)),
            avg_confidence=models.Avg('confidence_score')
        )
        
        self.assertEqual(diabetes_stats['total'], 3)
        self.assertEqual(diabetes_stats['positive'], 2)
        self.assertEqual(diabetes_stats['negative'], 1)