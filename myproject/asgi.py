
import os
from django.core.asgi import get_asgi_application
application = get_asgi_application()
import django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from clients.middleware import TenantMiddlewareASGI
from myproject.routing import websocket_urlpatterns as call_ws
from chat.routing import websocket_urlpatterns as chat_ws

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

django_asgi_app = get_asgi_application()
all_websockets = call_ws + chat_ws


application = ProtocolTypeRouter({
    "http": django_asgi_app,  
    "websocket": TenantMiddlewareASGI(
        AuthMiddlewareStack(
            URLRouter(all_websockets)
        )
    ),
})
