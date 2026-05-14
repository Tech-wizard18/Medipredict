""" 

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'disease_app.settings')

# Import Django and get application
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
import django

# Initialize Django
django.setup()

# Import websocket routing
from prediction_app.routing import websocket_urlpatterns
from notifications_app.routing import notification_websocket_urlpatterns

# Get Django ASGI application
django_asgi_app = get_asgi_application()

# WebSocket Protocol
websocket_application = AuthMiddlewareStack(
    AllowedHostsOriginValidator(
        URLRouter(
            websocket_urlpatterns + notification_websocket_urlpatterns
        )
    )
)

# Application Protocol Router
application = ProtocolTypeRouter({
    # HTTP requests are handled by Django
    "http": django_asgi_app,
    
    # WebSocket requests are handled by Channels
    "websocket": websocket_application,
    
    # Add other protocols here if needed
    # "channel": ChannelNameRouter({}),
})

# Optional: Add lifespan protocol support
try:
    from channels.layers import get_channel_layer
    from asgiref.lifespan import Lifespan
    
    async def lifespan_app(scope, receive, send):
        
        if scope["type"] == "lifespan":
            while True:
                message = await receive()
                if message["type"] == "lifespan.startup":
                    # Perform startup tasks
                    print("ASGI Application Starting...")
                    # Initialize WebSocket channels layer
                    channel_layer = get_channel_layer()
                    await channel_layer.group_send(
                        "system",
                        {"type": "system.startup", "message": "ASGI starting"}
                    )
                    await send({"type": "lifespan.startup.complete"})
                
                elif message["type"] == "lifespan.shutdown":
                    # Perform cleanup tasks
                    print("ASGI Application Shutting Down...")
                    # Notify WebSocket clients
                    channel_layer = get_channel_layer()
                    await channel_layer.group_send(
                        "system",
                        {"type": "system.shutdown", "message": "ASGI shutting down"}
                    )
                    await send({"type": "lifespan.shutdown.complete"})
                    break
        
        else:
            # Pass through to main application
            await application(scope, receive, send)
    
    # Wrap application with lifespan support
    application = Lifespan(application)
    
except ImportError:
    # Channels not installed or lifespan not supported
    pass

# Health Check Endpoint for ASGI
async def health_check(scope, receive, send):
    
    if scope["path"] == "/health/asgi/":
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [
                (b"content-type", b"application/json"),
            ],
        })
        await send({
            "type": "http.response.body",
            "body": b'{"status": "healthy", "service": "asgi"}',
        })
    else:
        await application(scope, receive, send)

# Optional: Add middleware for ASGI
class ASGIMiddleware:
   
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        # Add custom headers or processing here
        if scope["type"] == "http":
            # Log HTTP requests
            print(f"HTTP Request: {scope['method']} {scope['path']}")
        
        elif scope["type"] == "websocket":
            # Log WebSocket connections
            print(f"WebSocket Connection: {scope['path']}")
        
        # Process the request
        await self.app(scope, receive, send)

# Apply middleware if needed
# application = ASGIMiddleware(application)

# Performance Monitoring (Optional)
try:
    import asgi_correlation_id
    from asgi_correlation_id.middleware import CorrelationIdMiddleware
    
    # Add correlation ID for request tracing
    application = CorrelationIdMiddleware(application)
    
except ImportError:
    # Correlation ID middleware not installed
    pass

# Export application
__all__ = ['application']

# Configuration for ASGI servers
ASGI_CONFIG = {
    'protocol': 'asgi',
    'http_parser': 'auto',
    'websocket_ping_interval': 20,
    'websocket_ping_timeout': 30,
    'websocket_max_message_size': 16 * 1024 * 1024,  # 16MB
}

print(f"ASGI Application configured: {ASGI_CONFIG}")

 """




import os
from django.core.asgi import get_asgi_application

# Set correct settings file
os.environ.setdefault(
    'DJANGO_SETTINGS_MODULE',
    'disease_app.settings.base'
)

application = get_asgi_application()
