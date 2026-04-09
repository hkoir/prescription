from django.conf import settings
from django.db import models
from django.utils import timezone
from accounts.models import CustomUser



class ChatThread(models.Model):
    tenant_schema = models.CharField(max_length=64, db_index=True)
    doctor_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_threads_as_doctor')
    patient_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_threads_as_patient')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    last_message_at = models.DateTimeField(null=True, blank=True)

    def get_partner(self, user):
        if user == self.doctor_user:
            return self.patient_user
        return self.doctor_user

    class Meta:
        unique_together = ('tenant_schema', 'doctor_user', 'patient_user')

    def __str__(self):
        return f"{self.tenant_schema}: {self.patient_user} ↔ {self.doctor_user}"



class ChatMessage(models.Model):
    thread = models.ForeignKey(ChatThread, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_messages_sent')
    text = models.TextField(blank=True)
    media = models.FileField(upload_to='chat_media/', blank=True, null=True) 
    sent_at = models.DateTimeField(default=timezone.now)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['sent_at']

    def is_image(self):
        return self.media and self.media.url.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))

    def is_video(self):
        return self.media and self.media.url.lower().endswith(('.mp4', '.webm', '.mov'))

    def __str__(self):
        return f"[{self.sent_at}] {self.sender}: {self.text[:30]}"




class DeviceToken(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    token = models.CharField(max_length=250)





import uuid

class BoardRoom(models.Model):
    room_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    title = models.CharField(max_length=255, blank=True)
    host = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="hosted_board_rooms",null=True,blank=True)
    host_name = models.CharField(max_length=255, blank=True)  # Add this
    start_time = models.DateTimeField()       # Add this
    created_at = models.DateTimeField(auto_now_add=True)



class BoardRoomInvite(models.Model):
    room = models.ForeignKey(BoardRoom, on_delete=models.CASCADE, related_name="invites")
    invited_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="sent_invites")
    email = models.CharField(max_length=255)
    invite_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    sent_at = models.DateTimeField(auto_now_add=True)
    accepted = models.BooleanField(default=False)

    def __str__(self):
        return f"Invite to {self.email} for {self.room}"


class BoardRoomParticipant(models.Model):
    room = models.ForeignKey(BoardRoom, on_delete=models.CASCADE, related_name="participants")
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=255, blank=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.name or self.user} in {self.room}"
