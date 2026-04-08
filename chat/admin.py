from django.contrib import admin
from .models import ChatMessage,ChatThread,BoardRoom,BoardRoomInvite,BoardRoomParticipant


admin.site.register(ChatMessage)
admin.site.register(ChatThread)

admin.site.register(BoardRoom)
admin.site.register(BoardRoomInvite)
admin.site.register(BoardRoomParticipant)