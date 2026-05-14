from django.apps import AppConfig


class ApiAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api_app'
    verbose_name = 'API Management'

    def ready(self):
        """
        Import signals when app is ready
        """
        import api_app.signals