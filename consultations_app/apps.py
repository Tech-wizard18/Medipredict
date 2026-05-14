from django.apps import AppConfig

class ConsultationsAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'consultations_app'
    verbose_name = 'Doctor Consultations'
    
    def ready(self):
        import consultations_app.signals