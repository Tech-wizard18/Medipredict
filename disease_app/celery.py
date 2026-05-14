# disease_app/celery.py

import os
from celery import Celery

# Set default Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'disease_app.settings')

# Create Celery app
app = Celery('disease_app')

# Load config from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
