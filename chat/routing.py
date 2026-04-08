from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
   
    re_path(r'ws/chat/(?P<tenant_prefix>\w+)/(?P<user_id>\d+)/$', consumers.ChatConsumer.as_asgi()),
    re_path(r'ws/video/(?P<thread_id>\w+)/$', consumers.VideoConsumer.as_asgi()),
    re_path(r"ws/video/group/(?P<room_id>[^/]+)/$", consumers.GroupVideoConsumer.as_asgi()),
]
