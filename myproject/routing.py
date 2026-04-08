

from django.urls import re_path
from .consumers import CallConsumer       
from chat.routing import websocket_urlpatterns as chat_routes 


websocket_urlpatterns = [    
    re_path(r'ws/call/(?P<tenant_prefix>\w+)/(?P<user_id>\d+)/$', CallConsumer.as_asgi()),
]

websocket_urlpatterns += chat_routes

