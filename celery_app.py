"""
Celery configuration for MEDIPREDICT.
This module configures the Celery application for asynchronous task processing.
"""

import os
from celery import Celery
from celery.schedules import crontab
from django.conf import settings

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'disease_app.settings.base')

# Create Celery app
app = Celery('medipredict')

# Load configuration from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all installed apps
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

# Configure Celery Beat schedules
app.conf.beat_schedule = {
    # Daily cleanup of old prediction data
    'cleanup-old-predictions': {
        'task': 'prediction_app.tasks.cleanup_old_predictions',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
        'args': (30,),  # Delete predictions older than 30 days
    },
    
    # Send daily health summary emails
    'send-daily-health-summary': {
        'task': 'notifications_app.tasks.send_daily_health_summary',
        'schedule': crontab(hour=9, minute=0),  # Daily at 9 AM
    },
    
    # Check for scheduled consultations
    'check-upcoming-consultations': {
        'task': 'consultations_app.tasks.check_upcoming_consultations',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
    },
    
    # Backup database daily
    'backup-database': {
        'task': 'prediction_app.tasks.backup_database',
        'schedule': crontab(hour=3, minute=0),  # Daily at 3 AM
    },
    
    # Update ML models weekly
    'update-ml-models': {
        'task': 'prediction_app.tasks.update_ml_models',
        'schedule': crontab(day_of_week='sunday', hour=4, minute=0),  # Sunday at 4 AM
    },
    
    # Send appointment reminders
    'send-appointment-reminders': {
        'task': 'notifications_app.tasks.send_appointment_reminders',
        'schedule': crontab(hour=8, minute=0),  # Daily at 8 AM
    },
    
    # Generate weekly reports
    'generate-weekly-reports': {
        'task': 'prediction_app.tasks.generate_weekly_reports',
        'schedule': crontab(day_of_week='monday', hour=6, minute=0),  # Monday at 6 AM
    },
}

# Configure Celery settings
app.conf.update(
    # Task result settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    
    # Task routing
    task_routes={
        'prediction_app.tasks.*': {'queue': 'predictions'},
        'notifications_app.tasks.*': {'queue': 'notifications'},
        'consultations_app.tasks.*': {'queue': 'consultations'},
    },
    
    # Retry settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
)

# Task error handling
@app.task(bind=True)
def debug_task(self):
    """Debug task to test Celery."""
    print(f'Request: {self.request!r}')

# Health check task
@app.task
def health_check():
    """Celery health check task."""
    return {'status': 'healthy', 'timestamp': 'now'}

if __name__ == '__main__':
    app.start()