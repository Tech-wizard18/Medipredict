from django.apps import AppConfig


class NotificationsAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notifications_app'
    verbose_name = 'Notifications System'

    def ready(self):
        """
        Import signals when app is ready
        """
        import notifications_app.signals