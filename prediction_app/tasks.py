from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import logging
from typing import List, Dict, Any, Optional
import json

from .models import Prediction, HealthReport, DiseaseModel
from .ml_utils import PredictionEngine
from .email_service import EmailService
from .data_loader import DataLoader

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(bind=True, max_retries=3)
def predict_disease_async(self, user_id: int, disease_type: str, 
                         input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Make disease prediction asynchronously."""
    try:
        user = User.objects.get(id=user_id)
        
        # Get prediction engine
        prediction_engine = PredictionEngine()
        
        # Make prediction
        result = prediction_engine.predict(disease_type, input_data)
        
        # Get disease model
        disease_model = DiseaseModel.objects.get(name=disease_type, is_active=True)
        
        # Save prediction
        prediction = Prediction.objects.create(
            user=user,
            disease_model=disease_model,
            prediction_result=result['probability'],
            prediction_label=result['label'],
            confidence=result['confidence'],
            input_data=input_data
        )
        
        # Send email notification
        if user.email:
            EmailService.send_prediction_result(user.email, {
                **result,
                'prediction_id': prediction.id,
                'created_at': prediction.created_at
            })
        
        logger.info(f"Async prediction completed for user {user_id}, disease {disease_type}")
        
        return {
            'success': True,
            'prediction_id': prediction.id,
            'result': result
        }
        
    except Exception as e:
        logger.error(f"Async prediction failed: {e}")
        self.retry(exc=e, countdown=60)
        return {'success': False, 'error': str(e)}


@shared_task(bind=True, max_retries=3)
def generate_report_async(self, user_id: int, 
                         report_date: Optional[str] = None) -> Dict[str, Any]:
    """Generate health report asynchronously."""
    try:
        user = User.objects.get(id=user_id)
        
        # Set report date
        if not report_date:
            report_date = timezone.now().date()
        else:
            report_date = timezone.datetime.strptime(report_date, '%Y-%m-%d').date()
        
        # Get user predictions for the period
        predictions = Prediction.objects.filter(
            user=user,
            created_at__date__gte=report_date - timedelta(days=30),
            created_at__date__lte=report_date
        ).select_related('disease_model')
        
        if not predictions.exists():
            return {'success': False, 'error': 'No prediction data available'}
        
        # Calculate overall risk score
        risk_scores = []
        for pred in predictions:
            # Weight risk by confidence and prediction result
            risk_weight = pred.prediction_result * pred.confidence
            if 'positive' in pred.prediction_label.lower():
                risk_weight *= 1.5  # Higher weight for positive predictions
            risk_scores.append(risk_weight)
        
        overall_risk_score = sum(risk_scores) / len(risk_scores) if risk_scores else 0
        
        # Determine risk level
        if overall_risk_score < 0.3:
            risk_level = 'low'
        elif overall_risk_score < 0.6:
            risk_level = 'moderate'
        elif overall_risk_score < 0.8:
            risk_level = 'high'
        else:
            risk_level = 'critical'
        
        # Generate recommendations
        recommendations = generate_recommendations(predictions, risk_level)
        
        # Prepare findings
        findings = {
            'total_predictions': predictions.count(),
            'disease_breakdown': {},
            'risk_factors': [],
            'trends': calculate_trends(user, report_date)
        }
        
        for pred in predictions:
            disease_name = pred.disease_model.get_name_display()
            if disease_name not in findings['disease_breakdown']:
                findings['disease_breakdown'][disease_name] = {
                    'count': 0,
                    'positive': 0,
                    'avg_confidence': 0
                }
            
            findings['disease_breakdown'][disease_name]['count'] += 1
            if 'positive' in pred.prediction_label.lower():
                findings['disease_breakdown'][disease_name]['positive'] += 1
            findings['disease_breakdown'][disease_name]['avg_confidence'] = (
                findings['disease_breakdown'][disease_name]['avg_confidence'] + 
                pred.confidence
            ) / 2
        
        # Create health report
        report = HealthReport.objects.create(
            user=user,
            report_date=report_date,
            overall_risk_score=overall_risk_score,
            risk_level=risk_level,
            recommendations=recommendations,
            findings=findings,
            generated_by='system'
        )
        
        # Send email with report
        if user.email:
            EmailService.send_health_report(user.email, {
                'report_id': report.id,
                'report_date': report.report_date,
                'risk_level': risk_level,
                'risk_score': overall_risk_score,
                'recommendations': recommendations,
                'findings_summary': generate_findings_summary(findings)
            })
        
        logger.info(f"Health report generated for user {user_id}")
        
        return {
            'success': True,
            'report_id': report.id,
            'risk_score': overall_risk_score,
            'risk_level': risk_level
        }
        
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        self.retry(exc=e, countdown=120)
        return {'success': False, 'error': str(e)}


@shared_task
def cleanup_old_predictions(days_to_keep: int = 30):
    """Clean up predictions older than specified days."""
    try:
        cutoff_date = timezone.now() - timedelta(days=days_to_keep)
        
        # Archive old predictions before deletion
        old_predictions = Prediction.objects.filter(
            created_at__lt=cutoff_date
        )
        
        count = old_predictions.count()
        
        # Optional: Archive to another table or file
        # archive_predictions(old_predictions)
        
        # Delete old predictions
        deleted_count, _ = old_predictions.delete()
        
        logger.info(f"Cleaned up {deleted_count} predictions older than {days_to_keep} days")
        
        return {'cleaned': deleted_count, 'total': count}
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return {'error': str(e)}


@shared_task
def update_model_statistics():
    """Update statistics for ML models."""
    try:
        models = DiseaseModel.objects.filter(is_active=True)
        
        for model in models:
            # Get predictions for this model
            predictions = Prediction.objects.filter(
                disease_model=model
            ).exclude(confidence__isnull=True)
            
            if predictions.exists():
                # Calculate average confidence as proxy for accuracy
                avg_confidence = predictions.aggregate(
                    avg=Avg('confidence')
                )['avg'] or model.accuracy
                
                # Update model accuracy
                model.accuracy = avg_confidence
                model.save(update_fields=['accuracy', 'updated_at'])
        
        logger.info("Model statistics updated")
        return {'success': True, 'models_updated': models.count()}
        
    except Exception as e:
        logger.error(f"Failed to update model statistics: {e}")
        return {'error': str(e)}


@shared_task
def send_weekly_summaries():
    """Send weekly summaries to all users."""
    try:
        users = User.objects.filter(
            is_active=True,
            email__isnull=False
        )
        
        success_count = 0
        failed_count = 0
        
        for user in users:
            try:
                # Generate weekly summary
                summary = generate_weekly_summary(user)
                
                # Send email
                if EmailService.send_weekly_summary(user.email, summary):
                    success_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                logger.error(f"Failed to send weekly summary to {user.email}: {e}")
                failed_count += 1
        
        logger.info(f"Weekly summaries sent: {success_count} successful, {failed_count} failed")
        
        return {
            'success': True,
            'sent': success_count,
            'failed': failed_count,
            'total': users.count()
        }
        
    except Exception as e:
        logger.error(f"Weekly summaries task failed: {e}")
        return {'error': str(e)}


@shared_task
def backup_database():
    """Create database backup."""
    try:
        from django.db import connection
        import subprocess
        import os
        from datetime import datetime
        
        # Create backup directory
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        # Generate backup filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(backup_dir, f'medipredict_backup_{timestamp}.sql')
        
        # Get database settings
        db_settings = settings.DATABASES['default']
        
        # Create backup command (PostgreSQL example)
        if db_settings['ENGINE'] == 'django.db.backends.postgresql':
            cmd = [
                'pg_dump',
                '-h', db_settings.get('HOST', 'localhost'),
                '-U', db_settings['USER'],
                '-d', db_settings['NAME'],
                '-f', backup_file
            ]
            
            # Set password via environment variable
            env = os.environ.copy()
            env['PGPASSWORD'] = db_settings['PASSWORD']
            
            # Execute backup
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Database backup created: {backup_file}")
                
                # Clean up old backups (keep last 7)
                cleanup_old_backups(backup_dir, keep_count=7)
                
                return {'success': True, 'backup_file': backup_file}
            else:
                logger.error(f"Backup failed: {result.stderr}")
                return {'error': result.stderr}
        
        else:
            logger.warning(f"Backup not implemented for {db_settings['ENGINE']}")
            return {'error': f"Backup not implemented for {db_settings['ENGINE']}"}
        
    except Exception as e:
        logger.error(f"Database backup failed: {e}")
        return {'error': str(e)}


@shared_task
def health_check():
    """Perform system health check."""
    try:
        from django.db import connection
        import psutil
        import redis
        from .ml_utils import ModelManager
        
        checks = {}
        
        # Database check
        try:
            connection.ensure_connection()
            checks['database'] = {'status': 'healthy', 'message': 'Connection successful'}
        except Exception as e:
            checks['database'] = {'status': 'unhealthy', 'error': str(e)}
        
        # Redis check
        try:
            redis_client = redis.from_url(settings.CELERY_BROKER_URL)
            redis_client.ping()
            checks['redis'] = {'status': 'healthy', 'message': 'Connection successful'}
        except Exception as e:
            checks['redis'] = {'status': 'unhealthy', 'error': str(e)}
        
        # ML models check
        try:
            models_status = ModelManager.get_all_model_info()
            loaded_models = sum(1 for info in models_status.values() if info.get('loaded'))
            checks['ml_models'] = {
                'status': 'healthy' if loaded_models > 0 else 'warning',
                'loaded': loaded_models,
                'total': len(models_status)
            }
        except Exception as e:
            checks['ml_models'] = {'status': 'unhealthy', 'error': str(e)}
        
        # System resources
        checks['system'] = {
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent
        }
        
        # Determine overall status
        unhealthy_checks = [c for c in checks.values() if isinstance(c, dict) and c.get('status') == 'unhealthy']
        
        if unhealthy_checks:
            overall_status = 'unhealthy'
        elif any(c.get('status') == 'warning' for c in checks.values() if isinstance(c, dict)):
            overall_status = 'warning'
        else:
            overall_status = 'healthy'
        
        result = {
            'timestamp': timezone.now().isoformat(),
            'status': overall_status,
            'checks': checks
        }
        
        logger.info(f"Health check completed: {overall_status}")
        
        # Send alert if unhealthy
        if overall_status == 'unhealthy':
            send_health_alert(result)
        
        return result
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {'status': 'error', 'error': str(e)}


@shared_task
def retrain_model(disease_type: str):
    """Retrain ML model with new data."""
    try:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import accuracy_score
        
        # Load data
        data_loader = DataLoader()
        X, y = data_loader.load_dataset(disease_type)
        
        if X is None or y is None:
            return {'error': 'No data available for training'}
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Train model
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        # Save model
        models_dir = os.path.join(settings.BASE_DIR, 'prediction_app', 'ml_models')
        model_path = os.path.join(models_dir, f'{disease_type}_model.pkl')
        
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
        
        # Update DiseaseModel record
        disease_model = DiseaseModel.objects.get(name=disease_type)
        disease_model.accuracy = accuracy
        disease_model.save(update_fields=['accuracy', 'updated_at'])
        
        logger.info(f"Model retrained for {disease_type}, accuracy: {accuracy:.2%}")
        
        return {
            'success': True,
            'disease': disease_type,
            'accuracy': accuracy,
            'samples': len(X),
            'model_path': model_path
        }
        
    except Exception as e:
        logger.error(f"Model retraining failed for {disease_type}: {e}")
        return {'error': str(e)}


# Helper functions
def generate_recommendations(predictions, risk_level):
    """Generate health recommendations based on predictions."""
    recommendations = []
    
    # General recommendations based on risk level
    if risk_level == 'critical':
        recommendations.extend([
            "Immediate medical consultation recommended",
            "Schedule comprehensive health checkup",
            "Monitor symptoms closely",
            "Avoid strenuous activities",
            "Follow emergency contact protocol if needed"
        ])
    elif risk_level == 'high':
        recommendations.extend([
            "Consult with healthcare provider within 1 week",
            "Monitor vital signs daily",
            "Follow prescribed medication regimen",
            "Maintain healthy diet and exercise",
            "Reduce stress through relaxation techniques"
        ])
    elif risk_level == 'moderate':
        recommendations.extend([
            "Schedule routine checkup within 1 month",
            "Continue monitoring health indicators",
            "Maintain balanced diet",
            "Regular moderate exercise",
            "Adequate sleep and hydration"
        ])
    else:
        recommendations.extend([
            "Continue regular health screenings",
            "Maintain healthy lifestyle",
            "Annual comprehensive checkup recommended",
            "Stay active and eat nutritious food",
            "Monitor for any new symptoms"
        ])
    
    # Disease-specific recommendations
    disease_specific = {}
    for pred in predictions:
        disease = pred.disease_model.name
        if disease not in disease_specific:
            disease_specific[disease] = []
        
        if 'positive' in pred.prediction_label.lower():
            if disease == 'diabetes':
                disease_specific[disease].extend([
                    "Monitor blood sugar levels regularly",
                    "Follow diabetic diet plan",
                    "Regular foot examinations",
                    "Annual eye examination"
                ])
            elif disease == 'heart':
                disease_specific[disease].extend([
                    "Monitor blood pressure daily",
                    "Low sodium diet",
                    "Regular cardiovascular exercise",
                    "Stress management"
                ])
    
    # Add disease-specific recommendations
    for disease, recs in disease_specific.items():
        if recs:
            recommendations.append(f"\nFor {disease.replace('_', ' ').title()}:")
            recommendations.extend(recs)
    
    return "\n".join(recommendations)


def calculate_trends(user, report_date):
    """Calculate health trends for user."""
    trends = {}
    
    # Get previous month's predictions
    prev_month_start = report_date - timedelta(days=60)
    prev_month_end = report_date - timedelta(days=30)
    
    prev_predictions = Prediction.objects.filter(
        user=user,
        created_at__date__gte=prev_month_start,
        created_at__date__lte=prev_month_end
    )
    
    current_predictions = Prediction.objects.filter(
        user=user,
        created_at__date__gte=report_date - timedelta(days=30),
        created_at__date__lte=report_date
    )
    
    # Calculate trends
    if prev_predictions.exists() and current_predictions.exists():
        prev_positive = prev_predictions.filter(
            prediction_label__icontains='positive'
        ).count()
        current_positive = current_predictions.filter(
            prediction_label__icontains='positive'
        ).count()
        
        prev_total = prev_predictions.count()
        current_total = current_predictions.count()
        
        if prev_total > 0 and current_total > 0:
            prev_rate = prev_positive / prev_total
            current_rate = current_positive / current_total
            
            trends['positive_rate_change'] = current_rate - prev_rate
            trends['prediction_count_change'] = current_total - prev_total
    
    return trends


def generate_weekly_summary(user):
    """Generate weekly summary for user."""
    week_ago = timezone.now() - timedelta(days=7)
    
    predictions = Prediction.objects.filter(
        user=user,
        created_at__gte=week_ago
    ).select_related('disease_model')
    
    total = predictions.count()
    positive = predictions.filter(
        prediction_label__icontains='positive'
    ).count()
    
    # Most predicted diseases
    top_diseases = predictions.values(
        'disease_model__name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')[:3]
    
    return {
        'period': 'week',
        'start_date': week_ago.date(),
        'end_date': timezone.now().date(),
        'total_predictions': total,
        'positive_predictions': positive,
        'positive_rate': positive / total if total > 0 else 0,
        'top_diseases': list(top_diseases),
        'new_features': check_new_features(),
        'tips': get_health_tips()
    }


def cleanup_old_backups(backup_dir, keep_count=7):
    """Clean up old backup files."""
    import glob
    
    backup_files = glob.glob(os.path.join(backup_dir, 'medipredict_backup_*.sql'))
    backup_files.sort(key=os.path.getmtime)
    
    # Keep only the most recent backups
    files_to_delete = backup_files[:-keep_count]
    
    for file in files_to_delete:
        try:
            os.remove(file)
            logger.info(f"Deleted old backup: {file}")
        except Exception as e:
            logger.error(f"Failed to delete backup {file}: {e}")


def send_health_alert(health_status):
    """Send alert for unhealthy system status."""
    # Send to admin emails
    admin_emails = getattr(settings, 'ADMIN_EMAILS', [])
    
    if admin_emails:
        EmailService.send_bulk_emails(
            admin_emails,
            "MEDIPREDICT - System Health Alert",
            'prediction_app/emails/health_alert.html',
            {'health_status': health_status}
        )


def check_new_features():
    """Check for new features to announce."""
    # This could be fetched from database or settings
    return [
        "New Parkinson's disease prediction model",
        "Enhanced prediction accuracy algorithms",
        "Mobile app now available for iOS and Android",
        "New symptom tracking feature"
    ]


def get_health_tips():
    """Get random health tips."""
    import random
    
    tips = [
        "Stay hydrated by drinking 8 glasses of water daily",
        "Aim for 7-9 hours of sleep each night",
        "Include fruits and vegetables in every meal",
        "Take regular breaks from sitting",
        "Practice deep breathing for stress relief",
        "Get regular health checkups",
        "Maintain a healthy weight",
        "Limit processed food intake",
        "Exercise for at least 30 minutes daily",
        "Manage stress through meditation or yoga"
    ]
    
    return random.sample(tips, 3)


def generate_findings_summary(findings):
    """Generate summary of findings for email."""
    summary = f"Total predictions: {findings.get('total_predictions', 0)}\n\n"
    
    if 'disease_breakdown' in findings:
        summary += "Disease breakdown:\n"
        for disease, stats in findings['disease_breakdown'].items():
            summary += f"- {disease}: {stats.get('count', 0)} predictions, "
            summary += f"{stats.get('positive', 0)} positive\n"
    
    if 'trends' in findings and 'positive_rate_change' in findings['trends']:
        change = findings['trends']['positive_rate_change']
        if change > 0:
            summary += f"\nTrend: Positive prediction rate increased by {change:.1%}"
        elif change < 0:
            summary += f"\nTrend: Positive prediction rate decreased by {abs(change):.1%}"
        else:
            summary += "\nTrend: Prediction rate stable"
    
    return summary