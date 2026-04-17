from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/public/$', consumers.PublicChatConsumer.as_asgi()),
    re_path(r'ws/mafia/$', consumers.MafiaChatConsumer.as_asgi()),
]