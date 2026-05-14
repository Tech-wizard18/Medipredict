"""
URL configuration for MEDIPREDICT project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView, RedirectView
from django.contrib.sitemaps.views import sitemap
from django.contrib.auth import views as auth_views


# Import sitemaps
from prediction_app.sitemaps import PredictionSitemap
from users_app.sitemaps import UsersSitemap

# Import custom error handlers
from . import error_handlers

# Sitemaps configuration
sitemaps = {
    'prediction': PredictionSitemap,
    'users': UsersSitemap,
}

# URL patterns
urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Home & Dashboard
    path('', TemplateView.as_view(template_name='prediction_app/home.html'), name='home'),
    path('dashboard/', TemplateView.as_view(template_name='prediction_app/dashboard.html'), name='dashboard'),

    # Apps
    path('predict/', include('prediction_app.urls')),
    path('users/', include(('users_app.urls', 'users_app'), namespace='users_app')),
    path('consultations/', include('consultations_app.urls')),
    path('prescriptions/', include('prescriptions_app.urls')),
    path('notifications/', include('notifications_app.urls')),

    # API (FIXED INDENTATION)
    path('api/', include('api_app.urls', namespace='api')),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),

    # Authentication
    path('accounts/login/', auth_views.LoginView.as_view(template_name='users_app/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),

    path('accounts/password-reset/',
         auth_views.PasswordResetView.as_view(template_name='users_app/password_reset.html'),
         name='password_reset'),

    path('accounts/password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(template_name='users_app/password_reset_done.html'),
         name='password_reset_done'),

    path('accounts/reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(template_name='users_app/password_reset_confirm.html'),
         name='password_reset_confirm'),

    path('accounts/reset/done/',
         auth_views.PasswordResetCompleteView.as_view(template_name='users_app/password_reset_complete.html'),
         name='password_reset_complete'),

    # Static Pages
    path('about/', TemplateView.as_view(template_name='static_pages/about.html'), name='about'),
    path('privacy/', TemplateView.as_view(template_name='static_pages/privacy.html'), name='privacy'),
    path('terms/', TemplateView.as_view(template_name='static_pages/terms.html'), name='terms'),
    path('contact/', TemplateView.as_view(template_name='static_pages/contact.html'), name='contact'),
    path('help/', TemplateView.as_view(template_name='static_pages/help.html'), name='help'),

    # Sitemap (UPDATED NAME)
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='sitemap'),

    # Robots.txt
    path('robots.txt', TemplateView.as_view(
        template_name='robots.txt',
        content_type='text/plain'
    ), name='robots.txt'),

    # Health Check
    path('health/', include('health_check.urls')),

    # Favicon
    path('favicon.ico', RedirectView.as_view(
        url='/static/images/favicon.ico',
        permanent=True
    )),

    # Redirect old URLs
    path('old-predict/', RedirectView.as_view(pattern_name='prediction_home', permanent=True)),
    path('old-dashboard/', RedirectView.as_view(pattern_name='dashboard', permanent=True)),
    
]

# Admin titles
admin.site.site_header = 'MEDIPREDICT Administration'
admin.site.site_title = 'MEDIPREDICT Admin Portal'
admin.site.index_title = 'Welcome to MEDIPREDICT Admin Portal'

# Debug URLs
if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
        path('api/docs/', TemplateView.as_view(template_name='api_docs.html'), name='api_docs'),
        path('test-email/', TemplateView.as_view(template_name='test_email.html'), name='test_email'),
    ]

    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    urlpatterns += [
        path('400/', TemplateView.as_view(template_name='error_pages/400.html')),
        path('403/', TemplateView.as_view(template_name='error_pages/403.html')),
        path('404/', TemplateView.as_view(template_name='error_pages/404.html')),
        path('500/', TemplateView.as_view(template_name='error_pages/500.html')),
    ]

# Error Handlers
handler400 = 'disease_app.error_handlers.bad_request'
handler403 = 'disease_app.error_handlers.permission_denied'
handler404 = 'disease_app.error_handlers.page_not_found'
handler500 = 'disease_app.error_handlers.server_error'

# API versions
API_VERSIONS = {
    'v1': 'Initial release - Stable',
    'v2': 'Planned - Coming Soon',
}
