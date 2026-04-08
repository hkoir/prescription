from rest_framework import serializers
from chat.models import ChatThread, ChatMessage  # adjust path if needed
from django.contrib.auth import get_user_model

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name"]


class ChatThreadSerializer(serializers.ModelSerializer):
    doctor_user = UserSerializer()
    patient_user = UserSerializer()

    class Meta:
        model = ChatThread
        fields = ["id", "tenant_schema", "doctor_user", "patient_user", "is_active", "last_message_at"]


class ChatMessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    media_url = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = ["id", "thread", "sender", "text", "media_url", "sent_at", "read_at"]

    def get_media_url(self, obj):
        request = self.context.get("request")
        return request.build_absolute_uri(obj.media.url) if obj.media else None
