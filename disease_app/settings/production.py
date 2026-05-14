from .base import *

DEBUG = False

ALLOWED_HOSTS = env.list('DJANGO_ALLOWED_HOSTS', default=['yourdomain.com'])

# Database
DATABASES = {
    'default': env.db('DATABASE_URL')
}

# Security Settings
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Static Files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Logging
LOGGING['handlers']['file']['filename'] = '/var/log/medipredict/django.log'
LOGGING['handlers']['error_file']['filename'] = '/var/log/medipredict/errors.log'



# settings/production.py
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = env('AWS_S3_REGION_NAME', 'us-east-1')




# Use S3 for production
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

# AWS S3 Configuration
AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = env('AWS_S3_REGION_NAME', 'us-east-1')
AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}
AWS_LOCATION = 'media'
AWS_DEFAULT_ACL = 'private'
AWS_S3_SIGNATURE_VERSION = 's3v4'
AWS_QUERYSTRING_AUTH = True
AWS_S3_FILE_OVERWRITE = False

# Media URL for S3
MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/{AWS_LOCATION}/'

# Enable virus scanning in production
FILE_VALIDATION['scan_for_viruses'] = True