from django.apps import AppConfig


class PrescriptionsAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'prescriptions_app'
    
    def ready(self):
        import prescriptions_app.signals