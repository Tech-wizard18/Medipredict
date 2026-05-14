from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.core.cache import cache
from .models import APIKey, APILog

User = get_user_model()


@receiver(post_save, sender=APIKey)
def create_api_key_rate_limit(sender, instance, created, **kwargs):
    """
    Create rate limit counters when API key is created
    """
    if created:
        # Clear any existing cache entries
        cache.delete(f"api_rate_limit:{instance.key_id}:minute")
        cache.delete(f"api_rate_limit:{instance.key_id}:hour")
        cache.delete(f"api_rate_limit:{instance.key_id}:day")


@receiver(post_delete, sender=APIKey)
def delete_api_key_cache(sender, instance, **kwargs):
    """
    Clean up cache when API key is deleted
    """
    cache.delete(f"api_rate_limit:{instance.key_id}:minute")
    cache.delete(f"api_rate_limit:{instance.key_id}:hour")
    cache.delete(f"api_rate_limit:{instance.key_id}:day")


@receiver(post_save, sender=APILog)
def cleanup_old_logs(sender, instance, created, **kwargs):
    """
    Clean up old logs to prevent database bloat
    """
    if created:
        # Keep only last 100,000 logs per API key
        max_logs = 100000
        logs = APILog.objects.filter(api_key=instance.api_key)
        
        if logs.count() > max_logs:
            # Delete oldest logs
            old_logs = logs.order_by('created_at')[:logs.count() - max_logs]
            old_logs.delete()